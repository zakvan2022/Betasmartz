from django.db import models
import logging
import copy
from datetime import datetime

import numpy as np
import scipy.stats as st
from django.contrib.sites.models import Site
from django.core.validators import MaxValueValidator, MinValueValidator, ValidationError
from django.db import models, transaction
from django.db.models import F, Sum
from django.db.models.deletion import CASCADE, PROTECT
from django.db.models.functions import Coalesce
from django.db.models.query_utils import Q
from django.utils.functional import cached_property
from django.utils.timezone import now
from jsonfield.fields import JSONField
from pinax.eventlog import models as el_models

from .managers import GoalQuerySet
from common.structures import ChoiceEnum
from execution.models import PositionLot
from main.abstract import TransferPlan
from main.finance import mod_dietz_rate
from main.risk_profiler import validate_risk_score
from portfolios.models import AssetFeatureValue, InvestmentType, Ticker, get_default_set_id


logger = logging.getLogger('goal.models')


class GoalType(models.Model):
    name = models.CharField(max_length=255, null=False, db_index=True)
    description = models.TextField(null=True, blank=True)
    default_term = models.IntegerField(null=False)
    group = models.CharField(max_length=255, null=True)
    risk_sensitivity = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        help_text="Default risk sensitivity for this goal type. 0 = not "
                  "sensitive, 10 = Very sensitive (No risk tolerated)"
    )
    order = models.IntegerField(default=0,
                                help_text="The order of the type in the list.")
    risk_factor_weights = JSONField(null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return '%s' % self.name


class RecurringTransaction(TransferPlan):
    """
    Note: Only settings that are active will have their recurring
          transactions processed.
    """
    setting = models.ForeignKey('GoalSetting', related_name='recurring_transactions', on_delete=CASCADE)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    account_id = models.CharField(max_length=255, blank=True, null=True)  # the user chosen plaid account id
    stripe_id = models.CharField(max_length=255, blank=True, null=True)  # the stripe object id for last charge


    @staticmethod
    def get_events(recurring_transactions, start, end):
        """
        :param start: A datetime for the start
        :param end: A datetime for the end
        :param recurring_transactions:
        :return: a list of (date, amount) tuples for all the recurring
                 transaction events between the given dates.
        Not guarateed to return them in sorted order.
        """
        res = []
        for r in recurring_transactions.filter(enabled=True):
            res.extend(r.get_between(start, end))
        return res


class Portfolio(models.Model):
    setting = models.OneToOneField('GoalSetting', related_name='portfolio', on_delete=CASCADE)
    stdev = models.FloatField()
    er = models.FloatField()
    created = models.DateTimeField(auto_now_add=True)
    # Also has 'items' field from PortfolioItem
    rebalance = models.BooleanField(default=True)

    def __str__(self):
        result = u'Portfolio #%s' % self.id
        return result

    def get_items_all(self):
        return self.items.all()


class PortfolioItem(models.Model):
    portfolio = models.ForeignKey(Portfolio, related_name='items', on_delete=CASCADE)
    asset = models.ForeignKey(Ticker, on_delete=PROTECT)
    weight = models.FloatField()
    volatility = models.FloatField(help_text='variance of this asset at the time of creating this portfolio.')


class GoalSetting(models.Model):
    target = models.FloatField(default=0)
    completion = models.DateField(help_text='The scheduled completion date for the goal.')
    hedge_fx = models.BooleanField(help_text='Do we want to hedge foreign exposure?')
    # metric_group is a foreignkey rather than onetoone since a metric group can be used by more than one setting object
    metric_group = models.ForeignKey('GoalMetricGroup', related_name='settings', on_delete=PROTECT)
    rebalance = models.BooleanField(default=True, help_text='Do we want to perform automated rebalancing?')
    # also may have a 'recurring_transactions' field from RecurringTransaction model.
    # also may have a 'portfolio' field from Portfolio model. May be null if no portfolio has been assigned yet.

    def __str__(self):
        # portfolio field may be null if not assigned yet, throws error in admin
        # this try/except is a work around
        try:
            return u'Goal Settings #%s (%s)' % (self.id, self.portfolio)
        except Portfolio.DoesNotExist:
            return u'Goal Settings #%s' % (self.id)

    def get_metrics_all(self):
        return self.metric_group.metrics.all()

    def get_portfolio_items_all(self):
        return self.portfolio.items.all()

    @cached_property
    def can_rebalance(self):
        if self.rebalance and self.goal:
            if hasattr(self, 'portfolio'):
                if self.portfolio.rebalance:
                    if self.goal.approved_settings is not None:
                        return True
        return False

    @property
    def risk_score(self):
        """
        Returns the configured value of the risk score metric for this setting.
        If no risk score metric is configured, returns None.
        :return:
        """
        return GoalMetric.objects.filter(group=self.metric_group,
                                         type=GoalMetric.METRIC_TYPE_RISK_SCORE).values_list('configured_val',
                                                                                             flat=True).first()

    @property
    def goal(self):
        if hasattr(self, 'goal_selected'):
            return self.goal_selected
        if hasattr(self, 'goal_approved'):
            return self.goal_approved
        if hasattr(self, 'goal_active'):
            return self.goal_active
        return None


class GoalMetricGroup(models.Model):
    TYPE_CUSTOM = 0
    TYPE_PRESET = 1
    TYPES = (
        (TYPE_CUSTOM, 'Custom'),  # Should be deleted when it is not used by any settings object
        (TYPE_PRESET, 'Preset'),  # Exists on it's own.
    )
    type = models.IntegerField(choices=TYPES, default=TYPE_CUSTOM)
    name = models.CharField(max_length=100, null=True)
    # also has field 'metrics' from GoalMetric
    # Also has field 'settings' from GoalSetting

    def __str__(self):
        return "[{}:{}] {}".format(self.id, GoalMetricGroup.TYPES[self.type][1], self.name)

    def constraint_inputs(self):
        """
        A comparable set of inputs to all the optimisation constraints that would be generated from this group.
        :return:
        """
        features = {}
        for metric in self.metrics.all():
            if metric.type == GoalMetric.METRIC_TYPE_RISK_SCORE:
                risk = metric.configured_val
            else:
                features[metric.feature] = (metric.comparison, metric.feature, metric.configured_val)
        return risk, features


class InvalidStateError(Exception):
    """
    If an action was attempted on a stateful object and the current state was not once of the valid ones for the action
    """
    def __init__(self, current, required):
        self.current = current
        self.required = required

    def __str__(self):
        return "Invalid state: {}. Should have been one of: {}".format(self.current, self.required)


class Goal(models.Model):
    class State(ChoiceEnum):
        # The goal is currently active and ready for action.
        ACTIVE = 0, 'Active'
        # A request to archive the goal has been made, but is waiting approval.
        # The goal can be reinstated by simply changing the state back to ACTIVE
        ARCHIVE_REQUESTED = 1, 'Archive Requested'
        # A request to archive the goal has been approved, and is currently in process.
        # No further actions can be performed on the goal to reactivate it.
        CLOSING = 2, 'Closing'
        # The goal no longer owns any assets, and has a zero balance.
        # This goal is archived. No further actions can be performed on the goal
        ARCHIVED = 3, 'Archived'
        INACTIVE = 4, 'Inactive'  # the default new state

    account = models.ForeignKey('client.ClientAccount', related_name="all_goals")
    name = models.CharField(max_length=100)
    type = models.ForeignKey(GoalType)
    created = models.DateTimeField(auto_now_add=True)
    portfolio_set = models.ForeignKey('portfolios.PortfolioSet', related_name='goal', default=get_default_set_id)
    # The cash_balance field should NEVER be updated by an API. only our internal processes.
    cash_balance = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])
    # TODO: Ensure we still need to separate active_settings and approved_settings
    active_settings = models.OneToOneField(
        GoalSetting,
        related_name='goal_active',
        help_text='The settings were last used to do a rebalance.'
                  'These settings are responsible for our current market positions.',
        blank=True,
        null=True)
    approved_settings = models.OneToOneField(
        GoalSetting,
        related_name='goal_approved',
        help_text='The settings that both the client and advisor have confirmed '
                  'and will become active the next time the goal is rebalanced.',
        blank=True,
        null=True)
    selected_settings = models.OneToOneField(
        GoalSetting,
        related_name='goal_selected',
        help_text='The settings that the client has confirmed, '
                  'but are not yet approved by the advisor.',
        blank=True,
        null=True)
    # Drift score is a cached field, and is populated whenever the goal is processed at the end-of-day process.
    # As such it should not be written to anywhere else than that.
    drift_score = models.FloatField(default=0.0, help_text='The maximum ratio of current drift to maximum allowable'
                                                           ' drift from any metric on this goal.')
    state = models.IntegerField(choices=State.choices(), default=State.INACTIVE.value)
    order = models.IntegerField(default=0, help_text="The desired position in the list of Goals")

    # Also has 'positions' field from Position model.

    objects = GoalQuerySet.as_manager()

    class Meta:
        ordering = 'state', 'order'
        unique_together = ('account', 'name')

    def __init__(self, *args, **kwargs):
        super(Goal, self).__init__(*args, **kwargs)
        if hasattr(self, 'state'):
            self.__original_state = self.state
        else:
            self.__original_state = Goal.State.ACTIVE.value

        if hasattr(self, 'portfolio_set'):
            self.__original_portfolio_set = self.portfolio_set
        else:
            self.__original_portfolio_set = None

    def __str__(self):
        return '[' + str(self.id) + '] ' + self.name + " : " + self.account.primary_owner.full_name

    def get_positions_all(self):
        lots = PositionLot.objects.filter(quantity__gt=0, execution_distribution__transaction__from_goal=self,
                                          execution_distribution__execution__asset__state=Ticker.State.ACTIVE.value).\
            annotate(ticker_id=F('execution_distribution__execution__asset__id'),
                     price=F('execution_distribution__execution__asset__unit_price'))\
            .values('ticker_id', 'price').annotate(quantity=Sum('quantity'))
        return lots

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.account.confirmed:
            raise ValidationError('Account is not verified.')

        super(Goal, self).save(force_insert, force_update, using,
                               update_fields)

        return self

    @cached_property
    def has_deposit_transaction(self):
        """Checks if a deposit Transaction (one-time charge) or a RecurringTransaction
        exists for the goal.
        """
        if Transaction.objects.filter(to_goal=self, status__in=[Transaction.STATUS_AWAITING_APPROVAL, Transaction.STATUS_PENDING]).count() != 0:
            return True

        try:
            if RecurringTransaction.objects.filter(setting__goal_selected=self).count() != 0:
                return True
        except Exception as e:
            logger.error(e)
            return False

        return False

    # TODO: DEPRECATE THIS PROPERTY
    @property
    def is_active(self):
        return self.state in [self.State.ACTIVE.value,
                              self.State.ARCHIVE_REQUESTED.value]

    @property
    def is_open(self):
        return self.state in [self.State.ACTIVE.value,
                              self.State.INACTIVE.value,
                              self.State.ARCHIVE_REQUESTED.value]

    @property
    def is_pending(self):
        """
        Checks if the goal has deposit transactions either monthly or one-time for available goals.
        """
        return self.has_deposit_transaction and ((self.selected_settings != self.approved_settings and self.state == Goal.State.ACTIVE.value) or
                                                 self.state == Goal.State.INACTIVE.value)

    def archive(self):
        """
        Flags a goal as CLOSING, which will trigger the daily process to clear it.
        :return: None
        """
        if self.State(self.state) != self.State.ARCHIVE_REQUESTED:
            raise InvalidStateError(self.State(self.state), self.State.ARCHIVE_REQUESTED)

        self.state = self.State.CLOSING.value
        self.save()

    def complete_archive(self):
        """
        Completes the goal archive process once a goal has no open market positions.
        :return:
        """
        if self.get_positions_all():
            raise InvalidStateError("Cannot completely archive a goal while it has open positions.")

        # Change the name to _ARCHIVED so it doesn't affect the way the client can name any new goals, as there is a
        # unique index on account and name
        self.name += '_ARCHIVED'
        names = Goal.objects.filter(account=self.account).exclude(id=self.id).values_list('name', flat=True)
        if self.name in names:
            suf = 1
            while '{}_{}'.format(self.name, suf) in names:
                suf += 1
            self.name += '_{}'.format(suf)

        self.state = Goal.State.ARCHIVED
        self.save()

    @cached_property
    def awaiting_settings_approval(self):
        """
        UNUSED PROPERTY: Checks if this property is necessary.
        """
        if self.approved_settings != self.selected_settings:
            return True
        return False

    @transaction.atomic
    def set_selected(self, setting):
        """
        Sets the passed in setting object as the selected_setting.
        :param setting:
        :return:
        """
        old_setting = self.selected_settings
        if setting == old_setting:
            return
        self.selected_settings = setting
        # We need to validate the risk score after assigning the setting to the goal because in the risk score checking,
        # we go back to the goal from the setting to get information. If we do it any earlier, the info is not there.
        firm_config = self.account.primary_owner.firm.config
        unlimited = firm_config.risk_score_unlimited
        validate_risk_score(setting, unlimited)
        self.save()
        if old_setting not in (self.active_settings, self.approved_settings):
            old_group = old_setting.metric_group
            custom_group = old_group.type == GoalMetricGroup.TYPE_CUSTOM
            last_user = old_group.settings.count() == 1
            old_setting.delete()
            if custom_group and last_user:
                old_group.delete()

    def update_portfolio_set(self, portfolio_set):
        """
        update_portfolio_set
        If portfolio_set is changed, it should create a new selected_settings and re-calculate and
        create portfolio items for the new portfolio_set and new selected_settings should hold the
        portfolio items created.
        """
        if self.__original_portfolio_set == portfolio_set:
            return
        old_setting = self.selected_settings
        selected_settings = copy.copy(self.selected_settings)
        selected_settings.pk = None
        selected_settings.save()
        self.selected_settings = selected_settings
        self.portfolio_set = portfolio_set
        self.save(update_fields=['selected_settings', 'portfolio_set'])
        self.calculate_portfolio_for_selected()
        if old_setting is not None and old_setting != self.approved_settings and old_setting != self.active_settings:
            old_setting.delete()

    @transaction.atomic
    def calculate_portfolio_for_selected(self):
        from portfolios.providers.data.django import DataProviderDjango
        from portfolios.providers.execution.django import ExecutionProviderDjango
        from portfolios.calculation import Unsatisfiable, calculate_portfolio, get_instruments

        data_provider = DataProviderDjango()
        execution_provider = ExecutionProviderDjango()
        idata = get_instruments(data_provider)
        try:
            weights, er, stdev = calculate_portfolio(self.selected_settings,
                                                     data_provider,
                                                     execution_provider,
                                                     True,
                                                     idata)
            portfolio = Portfolio.objects.create(
                setting=self.selected_settings,
                stdev=stdev,
                er=er,
            )
            items = [PortfolioItem(portfolio=portfolio,
                                   asset=Ticker.objects.get(id=tid),
                                   weight=weight,
                                   volatility=idata[0].loc[tid, tid]) for tid, weight in weights.iteritems()]
            PortfolioItem.objects.bulk_create(items)
        except Unsatisfiable:
            # We detect when loading a goal in the allocation screen if there has been no portfolio created
            # and return a message to the user. It it perfectly reasonable for a goal to be created without a
            # portfolio.
            logger.exception("No suitable portfolio could be found. Leaving empty.")

    @transaction.atomic
    def setup_active_settings_from_approved(self):
        old_setting = self.active_settings
        # Shallow copy the active_settings from approved_settings with new metric_group
        active_settings = copy.copy(self.approved_settings)
        active_settings.pk = None
        active_settings.metric_group = GoalMetricGroup.objects.create()
        active_settings.save()

        metric_items = []
        for item in self.approved_settings.metric_group.metrics.all():
            metric_item = item
            metric_item.pk = None
            metric_item.group = active_settings.metric_group
            metric_items.append(metric_item)
        GoalMetric.objects.bulk_create(metric_items)

        if hasattr(self.approved_settings, 'portfolio'):
            # Shallow copy the portfolio for active_settings from portfolio of approved_settings
            portfolio = self.approved_settings.portfolio
            portfolio.setting = active_settings
            portfolio.pk = None
            portfolio.save(force_insert=True)

            # Copy portfolio items for active_settings from approved_settings.portfolio
            portfolio_items = []
            for item in self.approved_settings.portfolio.items.all():
                portfolio_item = item
                portfolio_item.pk = None
                portfolio_item.portfolio = portfolio
                portfolio_items.append(portfolio_item)
            PortfolioItem.objects.bulk_create(portfolio_items)

        # Copy recurring_transactions for active_settings from approved_settings.recurring_transactions
        for item in self.approved_settings.recurring_transactions.all():
            new_tx = item
            new_tx.id = None
            new_tx.setting = active_settings
            new_tx.save(force_insert=True)

        self.active_settings = active_settings
        self.save(update_fields=['active_settings'])
        if old_setting is not None and old_setting != self.approved_settings:
            old_setting.delete()

    @transaction.atomic
    def approve_selected(self):
        old_setting = self.approved_settings
        if self.selected_settings == old_setting:
            return
        self.approved_settings = self.selected_settings
        # advisor approved settings on this goal, if it was INACTIVE
        # it should be set to ACTIVE now
        if self.state == Goal.State.INACTIVE.value:
            self.state = Goal.State.ACTIVE.value
        self.save()
        if old_setting is not None and old_setting != self.active_settings:
            old_setting.delete()
        self.setup_active_settings_from_approved()
        # check transactions awaiting approval
        # if goal is now active execute charge and set transaction to pending
        # deposit transactions awaiting approval on goals that are now active
        if self.state == Goal.State.ACTIVE.value:
            from main.stripe import execute_charge
            from main.plaid import get_stripe_account_token
            waiting_transactions = Transaction.objects.filter(status=Transaction.STATUS_AWAITING_APPROVAL, to_goal=self)
            client = self.account.primary_owner
            site = Site.objects.get_current()
            if site.config().plaid_enabled:
                for trans in waiting_transactions:
                    stripe_token = get_stripe_account_token(client.user, trans.account_id)
                    charge = execute_charge(trans.amount, stripe_token)
                    trans.stripe_id = charge.id
                    trans.status = Transaction.STATUS_PENDING
                    trans.save()
            else:
                for trans in waiting_transactions:
                    # manual transfer, goal cash balance updated directly
                    trans.execute()

    @transaction.atomic
    def revert_selected(self):
        if self.approved_settings is None:
            raise ValidationError("There are no current approved settings. Cannot revert.")
        old_setting = self.selected_settings
        if self.approved_settings == old_setting:
            return
        self.selected_settings = self.approved_settings
        self.save()
        old_setting.delete()

    @property
    def available_balance(self):
        return self.total_balance - self.pending_outgoings

    @property
    def pending_transactions(self):
        return Transaction.objects.filter((Q(to_goal=self) | Q(from_goal=self)) & Q(status=Transaction.STATUS_PENDING))

    @property
    def awaiting_deposit(self):
        return Transaction.objects \
            .filter(Q(to_goal=self) & Q(status=Transaction.STATUS_AWAITING_APPROVAL)) \
            .order_by('-id') \
            .first()

    @property
    def pending_amount(self):
        pa = 0.0
        for t in self.pending_transactions:
            if self == t.from_goal:
                pa -= t.amount
            else:
                pa += t.amount
        return pa

    @property
    def pending_incomings(self):
        pd = 0.0
        for d in Transaction.objects.filter(to_goal=self, status=Transaction.STATUS_PENDING):
            pd += d.amount
        return pd

    @property
    def pending_outgoings(self):
        pw = 0.0
        for w in Transaction.objects.filter(from_goal=self, status=Transaction.STATUS_PENDING):
            pw += w.amount
        return pw

    @property
    def requested_incomings(self):
        pd = 0.0
        for d in Transaction.objects.filter(to_goal=self,
                                            status=Transaction.STATUS_EXECUTED).exclude(reason__in=(Transaction.REASON_FEE,
                                                                                                    Transaction.REASON_DIVIDEND)):
            pd += d.amount
        return pd

    @property
    def requested_outgoings(self):
        pw = 0.0
        for w in Transaction.objects.filter(from_goal=self,
                                            status=Transaction.STATUS_EXECUTED).exclude(reason__in=(Transaction.REASON_FEE,
                                                                                                    Transaction.REASON_DIVIDEND)):
            pw -= w.amount
        return pw

    @property
    def total_dividends(self):
        divs = 0.0
        for t in Transaction.objects.filter(Q(status=Transaction.STATUS_EXECUTED) &
                                            (Q(to_goal=self) | Q(from_goal=self)) &
                                            (Q(reason=Transaction.REASON_DIVIDEND))):
            divs += t.amount if self == t.to_goal else -t.amount
        return divs

    @property
    def market_changes(self):
        return 0.0

    @property
    def total_deposits(self):
        """
        :return: The total amount of the deposits into the goal from the account cash. Excluding pending.
        """
        inputs = 0.0
        for t in Transaction.objects.filter(status=Transaction.STATUS_EXECUTED,
                                            to_goal=self,
                                            reason=Transaction.REASON_DEPOSIT):
            inputs += t.amount
        return inputs

    @property
    def total_withdrawals(self):
        """
        :return: The total amount of the withdrawals from the goal to the account cash. Excluding pending.
        """
        inputs = 0.0
        for t in Transaction.objects.filter(status=Transaction.STATUS_EXECUTED,
                                            to_goal=self,
                                            reason=Transaction.REASON_WITHDRAWAL):
            inputs += t.amount
        return inputs

    @property
    def net_invested(self):
        """
        :return: The actual realised amount invested (incomings - outgoings),
                 excluding any pending transactions or performance-based transactions.

        """
        inputs = 0.0
        for t in Transaction.objects.filter(Q(status=Transaction.STATUS_EXECUTED) &
                                            (Q(to_goal=self) | Q(from_goal=self)) &
                                            (Q(reason__in=Transaction.CASH_FLOW_REASONS))):
            inputs += t.amount if self == t.to_goal else -t.amount
        return inputs

    @property
    def net_executions(self):
        """
        :return: The net realised amount invested in funds(Sum Order type transactions)
        """
        inputs = 0.0
        for t in Transaction.objects.filter(Q(status=Transaction.STATUS_EXECUTED) &
                                            (Q(to_goal=self) | Q(from_goal=self)) &
                                            Q(reason=Transaction.REASON_EXECUTION)):
            inputs += t.amount if self == t.to_goal else -t.amount
        return inputs

    @property
    def life_time_return(self):
        return 0.0

    @property
    def other_adjustments(self):
        return 0.0

    @property
    def pending_conversions(self):
        return 0

    @property
    def total_fees(self):
        fees = 0.0
        for t in Transaction.objects.filter(Q(status=Transaction.STATUS_EXECUTED) &
                                            (Q(to_goal=self) | Q(from_goal=self)) &
                                            (Q(reason=Transaction.REASON_FEE))):
            fees += t.amount if self == t.to_goal else -t.amount
        return fees

    @property
    def recharacterized(self):
        return 0

    @property
    def total_earnings(self):
        """
        Earnings after fees. (increase of value, plus dividends, minus fees)
        :return: The current total balance minus any inputs excluding dividends, plus any withdrawals excluding fees.
        """
        return self.total_balance - self.net_invested

    @property
    def investments(self):
        return {
            'deposits': self.total_deposits,
            'withdrawals': self.total_withdrawals,
            'other': self.net_invested - self.total_deposits + self.total_withdrawals,
            'net_pending': self.pending_amount,
        }

    @property
    def earnings(self):
        return {
                'market_moves': self.total_earnings - self.total_dividends + self.total_fees,
                'dividends': self.total_dividends,
                'fees': self.total_fees,
               }

    @property
    def risk_level(self):
        # Experimental
        goal_metric = GoalMetric.objects \
            .filter(type=GoalMetric.METRIC_TYPE_RISK_SCORE) \
            .filter(group__settings__goal_active=self) \
            .first()

        if goal_metric:
            return str(goal_metric.get_risk_level())
        return '0'

    @property
    def risk_level_display(self):
        # Experimental
        goal_metric = GoalMetric.objects \
            .filter(type=GoalMetric.METRIC_TYPE_RISK_SCORE) \
            .filter(group__settings__goal_approved=self) \
            .first()

        if goal_metric:
            risk_level = goal_metric.get_risk_level_display()
            return risk_level

    def balance_at(self, future_dt, confidence=0.5):
        """
        Calculates the predicted balance at the given date with the given confidence based on the current
        selected-settings.
        :param date: The date to get the predicted balance for.
        :param confidence: The confidence level to get the prediction at.
        :return: Float predicted balance.
        """
        # If we don't have a selected portfolio, we can say nothing, so return the current balance
        if self.selected_settings is None:
            return self.total_balance

        # Get the z-multiplier for the given confidence
        z_mult = -st.norm.ppf(confidence)

        # If no portfolio has been calculated, er and stdev are assumed 0.
        if not hasattr(self.selected_settings, 'portfolio'):
            er = 1.0
            stdev = 0.0
        else:
            er = 1 + self.selected_settings.portfolio.er
            stdev = self.selected_settings.portfolio.stdev

        # use naive dates for calculations
        current_time = now().replace(tzinfo=None)
        # Get the predicted cash-flow events until the provided future date
        cf_events = [(current_time, self.total_balance)]
        if hasattr(self.selected_settings, 'recurring_transactions'):
            cf_events += RecurringTransaction.get_events(self.selected_settings.recurring_transactions,
                                                         current_time,
                                                         datetime.combine(future_dt, now().timetz()))

        # TODO: Add estimated fee events to this.

        # Calculate the predicted_balance based on cash flow events, er, stdev and z_mult
        predicted = 0
        for dt, val in cf_events:
            tdelta = dt - current_time
            y_delta = (tdelta.days + tdelta.seconds/86400.0)/365.25
            predicted += val * (er ** y_delta + z_mult * stdev * (y_delta ** 0.5))

        return predicted

    @cached_property
    def on_track(self):
        if self.selected_settings is None:
            return False

        # If we don't have a target or completion date, we have no concept of OnTrack.
        if self.selected_settings.target is None or self.selected_settings.completion is None:
            return False

        predicted_balance = self.balance_at(self.selected_settings.completion)
        return predicted_balance >= self.selected_settings.target

    def _sum_holdings(self, qs):
        total_holdings = qs.filter(execution_distribution__transaction__from_goal=self).\
            annotate(cur_price=F('execution_distribution__execution__asset__unit_price')).\
            aggregate(total_value=Coalesce(Sum(F('cur_price') * F('quantity')), 0))

        result = total_holdings['total_value']
        return result

    @property
    def total_balance(self):
        b = self.cash_balance
        b += self._sum_holdings(PositionLot.objects.filter(execution_distribution__execution__asset__state=Ticker.State.ACTIVE.value))
        return b

    @property
    def current_balance(self):
        """
        :return: The current total balance including any pending transactions.
        """
        return self.total_balance + self.pending_amount

    @property
    def stock_balance(self):
        stocks = InvestmentType.Standard.STOCKS.get()
        return self._sum_holdings(
            PositionLot.objects.filter(execution_distribution__execution__asset__asset_class__investment_type=stocks,
                                       execution_distribution__execution__asset__state=Ticker.State.ACTIVE.value)
        )

    @property
    def bond_balance(self):
        bonds = InvestmentType.Standard.BONDS.get()
        return self._sum_holdings(
            PositionLot.objects.filter(execution_distribution__execution__asset__asset_class__investment_type=bonds,
                                       execution_distribution__execution__asset__state=Ticker.State.ACTIVE.value)
        )

    @property
    def core_balance(self):
        return self._sum_holdings(
            PositionLot.objects.filter(execution_distribution__execution__asset__etf=True,
                                       execution_distribution__execution__asset__state=Ticker.State.ACTIVE.value)
        )

    @property
    def satellite_balance(self):
        return self._sum_holdings(
            PositionLot.objects.filter(execution_distribution__execution__asset_etf=False,
                                       execution_distribution__execution__asset__state=Ticker.State.ACTIVE.value)
        )

    @property
    def total_return(self):
        """
        :return: Modified Dietz Rate of Return for this goal
        """
        return mod_dietz_rate([self])

    @property
    def stocks_percentage(self):
        if self.total_balance == 0:
            return 0
        return "{0}".format(int(round(self.stock_balance / self.total_balance * 100)))

    @property
    def bonds_percentage(self):
        if self.total_balance == 0:
            return 0
        return "{0}".format(int(round(self.bond_balance / self.total_balance * 100)))

    @property
    def auto_frequency(self):
        if not hasattr(self, "auto_deposit"):
            return "-"
        return self.auto_deposit.get_frequency_display()

    @property
    def auto_amount(self):
        if not hasattr(self, "auto_deposit"):
            return "-"
        return self.auto_deposit.amount

    @property
    def get_term(self):
        today = now().today()

        term = (self.selected_settings.completion.year - today.year
                if self.selected_settings else None)
        return term

    @property
    def auto_term(self):
        return "{0}y".format(self.get_term)


    @property
    def amount_achieved(self):
        if self.selected_settings is None:
            return False

        # If we don't have a target or completion date, we have no concept of OnTrack.
        if self.selected_settings.target is None:
            return False

        return self.total_balance >= self.selected_settings.target


class HistoricalBalance(models.Model):
    """
    The historical balance model is a cache of the information that can be built from the Execution and Transaction
    models. It enables fast historical view of a goals's balance.
    This model should only ever be updated by code, and calculated from the source data in the Execution and Transaction
    models.
    """
    goal = models.ForeignKey(Goal, related_name='balance_history')
    date = models.DateField()
    balance = models.FloatField()

    class Meta:
        unique_together = 'goal', 'date'


class GoalMetric(models.Model):
    """
    A goal metric can currently be used to:
     - Specify what percentage of assets in a goal should have a particular feature, or -
     - Specify what risk score is desired for a goal. This is the normalised risk score range (0-1)
    For example:
        "Minimum 30% of my portfolio should be Australian, and rebalance whenever it becomes proportionally 5% different"
        {
            type: 0 (Portfolio Mix)
            feature: 1 (or whatever the ID is for the "Australian" feature value),
            comparison: 0 (Minimum),
            rebalance_type: 1,
            rebalance_thr: 0.05,
            configured_val: 0.3
        }
    """
    METRIC_TYPE_PORTFOLIO_MIX = 0
    METRIC_TYPE_RISK_SCORE = 1
    METRIC_COMPARISON_MINIMUM = 0
    METRIC_COMPARISON_EXACTLY = 1
    METRIC_COMPARISON_MAXIMUM = 2
    metric_types = {
        METRIC_TYPE_PORTFOLIO_MIX: 'Portfolio Mix',
        METRIC_TYPE_RISK_SCORE: 'RiskScore'
    }
    comparisons = {
        METRIC_COMPARISON_MINIMUM: 'Minimum',
        METRIC_COMPARISON_EXACTLY: 'Exactly',
        METRIC_COMPARISON_MAXIMUM: 'Maximum',
    }
    REBALANCE_TYPE_ABSOLUTE = 0
    REBALANCE_TYPE_RELATIVE = 1
    rebalance_types = {
        REBALANCE_TYPE_ABSOLUTE: 'Absolute',
        REBALANCE_TYPE_RELATIVE: 'Relative',
    }

    # Experimental
    RISK_LEVEL_PROTECTED = 0 # 0.0
    RISK_LEVEL_SEMI_PROTECTED = 19 # 0.19
    RISK_LEVEL_MODERATE = 35 # 0.35
    RISK_LEVEL_SEMI_DYNAMIC = 54 # 0.54
    RISK_LEVEL_DYNAMIC = 70 # 0.7

    RISK_LEVELS = (
        (RISK_LEVEL_PROTECTED, 'Protected'),
        (RISK_LEVEL_SEMI_PROTECTED, 'Semi-protected'),
        (RISK_LEVEL_MODERATE, 'Moderate'),
        (RISK_LEVEL_SEMI_DYNAMIC, 'Semi-dynamic'),
        (RISK_LEVEL_DYNAMIC, 'Dynamic'),
    )

    # OBSOLETED # setting = models.ForeignKey(GoalSetting, related_name='metrics', null=True)
    group = models.ForeignKey('GoalMetricGroup', related_name='metrics')
    type = models.IntegerField(choices=metric_types.items())
    feature = models.ForeignKey(AssetFeatureValue, null=True, on_delete=PROTECT)
    comparison = models.IntegerField(default=1, choices=comparisons.items())
    rebalance_type = models.IntegerField(choices=rebalance_types.items(),
                                         help_text='Is the rebalance threshold an absolute threshold or relative (percentage difference) threshold?')
    rebalance_thr = models.FloatField(
        help_text='The difference between configured and measured value at which a rebalance will be recommended.')
    configured_val = models.FloatField(help_text='The value of the metric that was configured.')


    @classmethod
    def risk_level_range(cls, risk_level):
        risk_min = risk_level
        risk_max = min([r[0] for r in cls.RISK_LEVELS if r[0] > risk_min] or [100]) # 100% or 101%?
        return [risk_min, risk_max]

    def get_risk_level(self):
        for risk_level_choice in self.RISK_LEVELS:
            risk_min, risk_max = self.risk_level_range(risk_level_choice[0])

            if self.configured_val < risk_max / 100:
                return risk_min

    @property
    def measured_val(self):
        asset_ids = AssetFeatureValue.objects.all().filter(id=self.feature.id)\
            .annotate(asset_id=F('assets__id'))\
            .values_list('asset_id', flat=True)

        goal = Goal.objects.get(active_settings__metric_group_id=self.group_id)
        sum = float(np.sum([pos['price']*pos['quantity'] if pos['ticker_id'] in asset_ids else 0 for pos in goal.get_positions_all()]))
        return sum/goal.available_balance

    @property
    def risk_level(self):
        return self.get_risk_level()

    def get_risk_level_display(self):
        risk_level = self.get_risk_level()

        if risk_level is not None:
            return dict(self.RISK_LEVELS)[risk_level]

    @property
    def drift_score(self):
        """
        Drift score is a multiplier of how many times the rebalance trigger level the current difference between the
        measured value and configured value is. The range will typically be [-1.0,1.0], but may extend higher or lower
        under extreme drift situations.
        Our rebalancing aims to keep the drift score for a goal between [-1.0,1.0].
        :return: Float - The drift score
        """
        if self.measured_val is None:
            return 0.0

        if self.rebalance_type == self.REBALANCE_TYPE_ABSOLUTE:
            return (self.measured_val - self.configured_val) / self.rebalance_thr
        else:
            return ((self.measured_val - self.configured_val) / self.configured_val) / self.rebalance_thr

    def __str__(self):
        if self.type == 0:
            return "[{}] {} {}% {} for Metric: {}".format(self.id,
                                                          self.comparisons[self.comparison],
                                                          self.configured_val * 100,
                                                          self.feature.name,
                                                          self.id)
        else:
            return "[{}] Risk Score {} {} for Metric: {}".format(self.id,
                                                                 self.comparisons[self.comparison],
                                                                 1 + self.configured_val * 99,
                                                                 self.id)


class EventMemo(models.Model):
    event = models.ForeignKey(el_models.Log,
                              related_name="memos",
                              on_delete=PROTECT,  # We shouldn't be deleting event logs anyway.
                             )
    comment = models.TextField()
    staff = models.BooleanField(help_text="Staff memos can only be seen by staff members of the firm."
                                          " Non-Staff memos inherit the permissions of the logged event."
                                          " I.e. Whoever can see the event, can see the memo.")


class Transaction(models.Model):
    """
    A transaction is a flow of funds to or from a goal.
    Deposits have a to_goal, withdrawals have a from_goal, transfers have both
    Every Transaction must have one or both.
    When one is null, it means it was to/from the account's cash.
    """
    # Import event here so we have it within our transaction.
    from activitylog.event import Event

    STATUS_AWAITING_APPROVAL = 'AWAITING APPROVAL'
    STATUS_PENDING = 'PENDING'
    STATUS_EXECUTED = 'EXECUTED'
    STATUS_FAILED = 'FAILED'  # stripe charge failed
    STATUSES = (('PENDING', 'PENDING'),
                ('EXECUTED', 'EXECUTED'),
                ('AWAITING APPROVAL', 'AWAITING APPROVAL'),
                ('FAILED', 'FAILED'))

    REASON_DIVIDEND = 0  # TODO: don't use 0 for that, never (for very special values only)
    REASON_DEPOSIT = 1
    REASON_WITHDRAWAL = 2
    REASON_REBALANCE = 3
    REASON_TRANSFER = 4
    REASON_FEE = 5
    # Transaction is for a MarketOrderRequest. It's a transient transaction, for reserving funds. It will always be pending.
    # It will have it's amount reduced over time (converted to executions or rejections) until it's eventually removed.
    REASON_ORDER = 6
    # Transaction is for an Order Execution Distribution that occurred. Will always be in executed state.
    REASON_EXECUTION = 7
    REASONS = (
        (REASON_DIVIDEND, "DIVIDEND"),  # Dividend re-investment from an asset owned by the goal
        (REASON_DEPOSIT, "DEPOSIT"),  # Deposit from the account to the goal
        (REASON_WITHDRAWAL, 'WITHDRAWAL'),  # Withdrawal from the goal to the account
        (REASON_REBALANCE, 'REBALANCE'),  # As part of a rebalance, we may transfer from goal to goal.
        (REASON_TRANSFER, 'TRANSFER'),  # Amount transferred from one goal to another.
        (REASON_FEE, 'FEE'),
        (REASON_ORDER, 'ORDER'),
        (REASON_EXECUTION, 'EXECUTION'),
    )
    # The set of Transaction reasons that are considered investor cash flow in or out of the goal.
    CASH_FLOW_REASONS = [REASON_DEPOSIT, REASON_WITHDRAWAL, REASON_REBALANCE, REASON_TRANSFER]

    # The list of events that are related to transaction executions
    EXECUTION_EVENTS = [
        Event.GOAL_DIVIDEND_DISTRIBUTION,
        Event.GOAL_DEPOSIT_EXECUTED,
        Event.GOAL_WITHDRAWAL_EXECUTED,
        Event.GOAL_REBALANCE_EXECUTED,
        Event.GOAL_TRANSFER_EXECUTED,
        Event.GOAL_FEE_LEVIED,
        Event.GOAL_ORDER_DISTRIBUTION,
    ]

    reason = models.IntegerField(choices=REASONS, db_index=True)
    from_goal = models.ForeignKey(Goal,
                                  related_name="transactions_from",
                                  null=True,
                                  blank=True,
                                  db_index=True,
                                  on_delete=PROTECT  # Cannot remove a goal that has transactions
                                 )
    to_goal = models.ForeignKey(Goal,
                                related_name="transactions_to",
                                null=True,
                                blank=True,
                                db_index=True,
                                on_delete=PROTECT  # Cannot remove a goal that has transactions
                               )
    amount = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_PENDING)
    created = models.DateTimeField(auto_now_add=True)
    executed = models.DateTimeField(null=True, db_index=True)

    account_id = models.CharField(max_length=255, blank=True, null=True)  # the user chosen plaid account id
    stripe_id = models.CharField(max_length=255, blank=True, null=True)  # the stripe object id for charge or transfer

    # May also have 'execution_request' field from the ExecutionRequest model if it has reason ORDER
    # May also have 'execution_distribution' field from the ExecutionDistribution model if it has reason EXECUTION

    def save(self, *args, **kwargs):
        if self.from_goal is None and self.to_goal is None:
            raise ValidationError("One or more of from_goal and to_goal is required")
        if self.from_goal == self.to_goal:
            raise ValidationError("Cannot transact with myself.")
        super(Transaction, self).save(*args, **kwargs)

    @transaction.atomic
    def execute(self):
        if self.status != Transaction.STATUS_AWAITING_APPROVAL and self.status != Transaction.STATUS_PENDING:
            return False
        if self.reason == Transaction.REASON_DEPOSIT:
            self.to_goal.cash_balance += self.amount
            self.to_goal.save(update_fields=['cash_balance'])
        elif self.reason == Transaction.REASON_WITHDRAWAL:
            self.from_goal.cash_balance -= self.amount
            self.from_goal.save(update_fields=['cash_balance'])
        else:
            # TODO: implement for other status
            return False
        self.status = Transaction.STATUS_EXECUTED
        self.executed = datetime.now()
        self.save()
        return True

    def __str__(self):
        return '{}|{}|{}|{}|{}'.format(self.id, self.created, self.reason, self.status, self.amount)
