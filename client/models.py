import logging
import uuid
from datetime import datetime
from itertools import chain

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.core.validators import MaxValueValidator, MinValueValidator, ValidationError
from django.db import models, transaction
from django.db.models import CASCADE, PROTECT, SET_NULL
from django.db.models.aggregates import Max, Min, Sum
from django.template.loader import render_to_string
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext as _
from jsonfield.fields import JSONField
from rest_framework.reverse import reverse

from common.structures import ChoiceEnum
from common.utils import get_text_of_choices_enum
from address.models import Address
from advisor.models import AccountGroup
from firm.models import PricingPlan, PricingPlanBase, PricingPlanPersonBase
from goal.models import Goal
from main import constants
from main.abstract import NeedApprobation, NeedConfirmation, PersonalData, TransferPlan
from main.constants import GENDER_MALE, ACCOUNT_TYPES, JOINT_ACCOUNT_TYPES, CLIENT_ACCESS_LEVEL_CHOICES, CLIENT_FULL_ACCESS
from main.finance import mod_dietz_rate
from portfolios.models import Platform, Region
from retiresmartz.models import RetirementAdvice, RetirementPlan
from user.models import User
from brokers.interactive_brokers.onboarding import onboarding
from brokers.interactive_brokers.onboarding.constants import IB_EMPLOY_STATUSES, IB_EMPLOY_STAT_EMPLOYED, \
     SOURCE_OF_FUNDS_TYPES, SOURCE_OF_FUNDS_TYPE_INTEREST, IB_SUFFIX_CHOICES, \
     IB_SALUTATION_CHOICES, IB_SALUTATION_MR
from brokers.models import IBAccountFeed
from address.constants import COUNTRY_CHOICES
from .managers import ClientAccountQuerySet, ClientQuerySet, ExternalAssetQuerySet

logger = logging.getLogger('client.models')


class Client(NeedApprobation, NeedConfirmation, PersonalData):
    class CoverageType(ChoiceEnum):
        SINGLE = 'Single', 'Single'
        FAMILY = 'Family', 'Family'

    WORTH_AFFLUENT = 'affluent'
    WORTH_HIGH = 'high'
    WORTH_VERY_HIGH = 'very-high'
    WORTH_ULTRA_HIGH = 'ultra-high'

    WORTH_CHOICES = (
        (WORTH_AFFLUENT, 'Mass affluent'),
        (WORTH_HIGH, 'High net worth'),
        (WORTH_VERY_HIGH, 'Very high net worth'),
        (WORTH_ULTRA_HIGH, 'Ultra high net worth'),
    )

    WORTH_RANGES = (
        (WORTH_AFFLUENT, 0, 100000),
        (WORTH_HIGH, 100000, 1000000),
        (WORTH_VERY_HIGH, 1000000, 10000000),
        (WORTH_ULTRA_HIGH, 10000000, 1000000000),
    )

    advisor = models.ForeignKey('advisor.Advisor',
                                related_name='all_clients',
                                # Must reassign clients before removing advisor
                                on_delete=PROTECT)
    secondary_advisors = models.ManyToManyField(
        'advisor.Advisor',
        related_name='secondary_clients',
        editable=False)
    create_date = models.DateTimeField(auto_now_add=True)
    client_agreement = models.FileField()

    user = models.OneToOneField('user.User', related_name='client')

    employment_status = models.IntegerField(choices=constants.EMPLOYMENT_STATUSES,
                                            null=True, blank=True)
    income = models.FloatField(verbose_name="Income ($)", default=0)
    occupation = models.CharField(choices=constants.OCCUPATION_TYPES,
                                  max_length=20, null=True, blank=True)
    industry_sector = models.CharField(choices=constants.INDUSTRY_TYPES,
                                       max_length=20, null=True, blank=True)
    employer_type = models.IntegerField(choices=constants.EMPLOYER_TYPES,
                                        null=True, blank=True)
    employer = models.CharField(max_length=255, null=True, blank=True)
    politically_exposed = models.BooleanField(default=False)

    student_loan = models.NullBooleanField(null=True, blank=True)
    student_loan_assistance_program = models.NullBooleanField(blank=True, null=True,
            verbose_name='Assistance Program',
            help_text='Does your employer offer a loan repayment assistance program?')
    student_loan_graduate_looking = models.NullBooleanField(blank=True, null=True,
            verbose_name='Graduate',
            help_text='Are you a graduate looking to refinance your student loans?')
    student_loan_parent_looking = models.NullBooleanField(blank=True, null=True,
            verbose_name='Parent',
            help_text='Are you a parent looking to refinance Parent Plus loans?')

    hsa_eligible = models.NullBooleanField(blank=True, null=True)
    hsa_provider_name = models.CharField(max_length=255, null=True, blank=True)
    hsa_state = models.CharField(max_length=255, null=True, blank=True)
    hsa_coverage_type = models.CharField(choices=CoverageType.choices(), max_length=32, null=True, blank=True)

    smoker = models.NullBooleanField(null=True, blank=True)
    daily_exercise = models.PositiveIntegerField(null=True, blank=True,
                                                 help_text="In Minutes")
    weight = models.FloatField(null=True, blank=True, help_text="In kilograms")
    height = models.FloatField(null=True, blank=True, help_text="In centimeters")

    drinks = models.PositiveIntegerField(null=True, blank=True, help_text='Number of drinks per day')

    betasmartz_agreement = models.BooleanField(default=False)
    advisor_agreement = models.BooleanField(default=False)

    agreement_time = models.PositiveIntegerField(null=True, blank=True)  # for stripe agreement time
    agreement_ip = models.CharField(max_length=45, null=True, blank=True)  # for stripe agreement ip address

    last_action = models.DateTimeField(null=True)

    other_income = models.IntegerField(null=True, blank=True)

    risk_profile_group = models.ForeignKey('RiskProfileGroup', related_name='clients', null=True)

    risk_profile_responses = models.ManyToManyField('RiskProfileAnswer')

    # Initiated with risk_score from abridged onboarding
    risk_score = models.FloatField(blank=True, null=True,
                                   validators=[MinValueValidator(0), MaxValueValidator(1)])

    readonly_access = models.BooleanField(default=False)

    # User entered value of their home
    home_value = models.FloatField(null=True, blank=True)

    # Default growth rate applied to the users home_value
    home_growth = models.FloatField(null=True, blank=True)

    # Social security estimated benefit in todays dollars based on full retirement age (fra)
    ss_fra_todays = models.FloatField(null=True, blank=True)

    # Social security estimated benefit in retirement dollars based on full retirement age (fra)
    ss_fra_retirement = models.FloatField(null=True, blank=True)

    # State tax levied against income
    state_tax_after_credits = models.FloatField(null=True, blank=True)

    # State tax effective rate
    state_tax_effrate = models.FloatField(null=True, blank=True)

    # Name of pension or annuity income stream number
    pension_name = models.CharField(max_length=255, null=True, blank=True)

    # Amount of pension income in todays dollars for number
    pension_amount = models.FloatField(null=True, blank=True)

    # Start date of retirement income stream number
    pension_start_date = models.DateField(null=True, blank=True)

    # last tax year employee contributions into retirement account number
    employee_contributions_last_year = models.FloatField(null=True, blank=True)

    # last tax year employer contributions into retirement account number #
    employer_contributions_last_year = models.FloatField(null=True, blank=True)

    # total of all contributions last year into retirement account number
    total_contributions_last_year = models.FloatField(null=True, blank=True)

    objects = ClientQuerySet.as_manager()

    def __str__(self):
        return self.user.get_full_name()

    @staticmethod
    def get_employment_status_text(employment_status):
        return get_text_of_choices_enum(employment_status, constants.EMPLOYMENT_STATUSES)

    @cached_property
    def employment_status_text(self):
        return Client.get_employment_status_text(self.employment_status)

    @staticmethod
    def get_employer_type_text(employer_type):
        return get_text_of_choices_enum(employer_type, constants.EMPLOYER_TYPES)

    @cached_property
    def employer_type_text(self):
        return Client.get_employer_type_text(self.employer_type)

    @staticmethod
    def get_occupation_text(occupation):
        return get_text_of_choices_enum(occupation, constants.OCCUPATION_TYPES)

    @cached_property
    def occupation_text(self):
        return Client.get_occupation_text(self.occupation)

    @cached_property
    def salutation(self):
        if hasattr(self, 'ib_onboard'):
            return self.ib_onboard.salutation
        elif hasattr(self.user, 'invitation'):
            return self.user.invitation.salutation
        else:
            return None

    @cached_property
    def suffix(self):
        if hasattr(self, 'ib_onboard'):
            return self.ib_onboard.suffix
        elif hasattr(self.user, 'invitation'):
            return self.user.invitation.suffix
        else:
            return None

    def _net_worth(self):
        # Sum ExternalAssets for the client
        assets = self.external_assets.all()
        assets_worth = 0.0
        today = datetime.now().date()
        for a in assets:
            # daily growth not annual
            assets_worth += float(a.get_growth_valuation(to_date=today))
        # Sum personal type Betasmartz Accounts - the total balance for the account is
        personal_accounts_worth = 0.0
        for ca in self.primary_accounts.filter(account_type=constants.ACCOUNT_TYPE_PERSONAL):
            personal_accounts_worth += ca.cash_balance
            for goal in ca.all_goals.exclude(state=Goal.State.ARCHIVED.value):
                personal_accounts_worth += goal.total_balance
        return assets_worth + personal_accounts_worth

    @cached_property
    def net_worth(self):
        return self._net_worth()

    @cached_property
    def bmi(self):
        if self.height is None or self.weight is None:
            return None
        cm_to_m2 = self.height * 0.0001
        if cm_to_m2 > 0:
            return self.weight / cm_to_m2
        return None

    @property
    def accounts_all(self):
        # TODO: Make this work
        return self.primary_accounts

    @property
    def accounts(self):
        return self.accounts_all.filter(confirmed=True)

    def get_worth(self):
        # why it should be a property? it shouldn't
        total_balance = self.total_balance

        for worth_range in self.WORTH_RANGES:
            if worth_range[1] <= total_balance < worth_range[2]:
                return worth_range[0]

    def get_worth_display(self):
        worth = dict(self.WORTH_CHOICES)
        return worth.get(self.get_worth())

    @property
    def firm(self):
        return self.advisor.firm

    @property
    def email(self):
        return self.user.email

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def total_balance(self):
        return sum(account.total_balance for account in self.accounts.all())

    @property
    def stocks_percentage(self):
        return 0

    @property
    def bonds_percentage(self):
        return 0

    @property
    def total_returns(self):
        return 0

    @property
    def total_earnings(self):
        return sum(a.total_earnings for a in self.accounts)

    @property
    def fees_ytd(self):
        """
        """
        # get client accounts
        # check transactions for client accounts from current fiscal year
        # firm has fiscal years set, find current
        from client.models import ClientAccount

        fiscal_year = self.firm.get_current_fiscal_year()
        total_fees = 0.0
        if fiscal_year:
            for ca in ClientAccount.objects.filter(client=self):
                for goal in ca.goals:
                    txs = Transaction.objects.filter(Q(to_goal=goal) | Q(from_goal=goal),
                                                     status=Transaction.STATUS_EXECUTED,
                                                     reason=Transaction.REASON_FEE,
                                                     executed__gte=fiscal_year.begin_date,
                                                     executed__lte=datetime.today())
                    for tx in txs:
                        total_fees += tx.amount
        return 0

    @property
    def current_risk_profile_responses(self):
        """
         Get the answers for the current risk profile questions and ensure they
         are recent and valid, otherwise returns None
         :return: A valid RiskProfileAnswer queryset, or None if questions changed
        """
        if not hasattr(self.risk_profile_group, 'questions'):
            # No risk questions assigned, so we can't say anything about their willingness to take risk.
            return None
        qids = set(self.risk_profile_group.questions.all().values_list('id', flat=True))
        if len(qids) == 0:
            # No risk questions assigned, so we can't say anything about their willingness to take risk.
            return None

        aqs = self.risk_profile_responses.all()
        if not self.risk_profile_responses:
            # No risk responses given, so we can't say anything about their willingness to take risk.
            return None

        if not qids == set(aqs.values_list('question_id', flat=True)):
            # Risk responses are not complete, so we can't say anything about their willingness to take risk.
            return None

        return aqs

    @cached_property
    def on_track(self):
        """
            If any of client's accounts are off track,
            return False.  If all accounts are
            on track, return True.
        """
        for account in self.accounts:
            if not account.on_track:
                return False
        return True

    @cached_property
    def life_expectancy(self):
        average_life_expectancy = 85
        calculated_life_expectancy = float(average_life_expectancy)
        if self.smoker:
            if self.gender == GENDER_MALE:
                diff = 7.7
            else:
                diff = 7.3
            calculated_life_expectancy -= diff

        if self.daily_exercise is None:
            self.daily_exercise = 0
        if self.daily_exercise == 20:
            calculated_life_expectancy += 2.2
        elif self.daily_exercise > 20:
            calculated_life_expectancy += 3.2

        if self.drinks is None:
            self.drinks = 0
        if self.drinks > 1:
            if self.gender == GENDER_MALE:
                calculated_life_expectancy -= 2.2
            else:
                calculated_life_expectancy -= 1.8

        if self.bmi:
            if self.bmi > 30:
                if self.gender == GENDER_MALE:
                    calculated_life_expectancy -= 5.7
                else:
                    calculated_life_expectancy -= 5.8

        return calculated_life_expectancy

    def get_risk_profile_bas_scores(self):
        """
        Get the scores for an entity's willingness to take risk, based on a previous elicitation of its preferences.
        :return: Tuple of floats [0-1] (b_score, a_score, s_score)
        """

        answers = self.current_risk_profile_responses
        if not answers:
            # TODO: consider and find better way to use risk_score
            if self.risk_score is not None:
                # Mock bas score with self.risk_score
                return [self.risk_score] * 3
            return None

        scores = (answers.values('b_score', 'a_score', 's_score').aggregate(b_score=Sum('b_score'),
                                                                            a_score=Sum('a_score'),
                                                                            s_score=Sum('s_score')))

        extents = (
            RiskProfileAnswer.objects.filter(question__group=self.risk_profile_group)
            .values('question').annotate(
                min_b=Min('b_score'), max_b=Max('b_score'),
                min_a=Min('a_score'), max_a=Max('a_score'),
                min_s=Min('s_score'), max_s=Max('s_score'),
            ).aggregate(
                min_b_sum=Sum('min_b'), max_b_sum=Sum('max_b'),
                min_a_sum=Sum('min_a'), max_a_sum=Sum('max_a'),
                min_s_sum=Sum('min_s'), max_s_sum=Sum('max_s'),
            )
        )

        max_b = extents['max_b_sum']
        max_a = extents['max_a_sum']
        max_s = extents['max_s_sum']
        return (
            scores['b_score'] / max_b if max_b > 0 else 0,
            scores['a_score'] / max_a if max_a > 0 else 0,
            scores['s_score'] / max_s if max_s > 0 else 0,
        )

    @property
    def my_pricing_plan(self) -> PricingPlanBase:
        firm = self.advisor.firm

        for obj in [self, self.advisor, firm]:
            try:
                return getattr(obj, 'pricing_plan')
            except AttributeError:
                pass

    @staticmethod
    @transaction.atomic
    def create_no_access_client(invitation):
        # Create user
        password = User.objects.make_random_password()
        user_params = {
            'email': invitation.email,
            'username': invitation.email,
            'first_name': invitation.first_name,
            'middle_name': invitation.middle_name,
            'last_name': invitation.last_name,
            'password': password,
        }
        user = User.objects.create_user(**user_params)

        # Set null address
        address = Address()
        address.update_address(address1='Unset', state_code='U', country='UN')

        # Create client 
        client_params = {
            'advisor': invitation.advisor,
            'user': user,
            'is_confirmed': False,
            'residential_address': address,
            'risk_score': invitation.risk_score,
            'betasmartz_agreement': True
        }
        client = Client.objects.create(**client_params)

        # Create the client's personal account
        client_account = client.primary_accounts.create(
            account_type=constants.ACCOUNT_TYPE_PERSONAL,
            default_portfolio_set=client.advisor.default_portfolio_set,
            confirmed=True,
        )

        # Create IBOnboard object for the client
        ib_onboard_params = {
            'client': client,
            'salutation': invitation.salutation,
            'suffix': invitation.suffix,
            'account_number': invitation.ib_account_number
        }
        ib_onboard = IBOnboard.objects.create(**ib_onboard_params)

        # if IB account number is present, link it to Personal Account
        if ib_onboard.account_number is not None: # If the client already has IB account create and link IBAccount object
            ib_account = IBAccount(bs_account=client_account, ib_account=ib_onboard.account_number)
            ib_account.save()

        # Mark invitation complete
        invitation.user = user
        invitation.status = EmailInvite.STATUS_COMPLETE
        invitation.save()

        # try:
            # Sync with existing IBAccountFeed
        ib_account_feed = IBAccountFeed.objects.get(account_id=invitation.ib_account_number)
        ib_onboard.feed_ib_client(ib_account_feed)
        # except:
        #     pass

        return client


class IBAccount(models.Model):
    '''
    Specification of Interactive Brokers Account
    '''
    ib_account = models.CharField(max_length=32)
    bs_account = models.OneToOneField('ClientAccount', related_name='ib_account', null=True)
    broker = "IB"

    def __str__(self):
        return self.ib_account

class APEXAccount(models.Model):
    apex_account = models.CharField(max_length=32)
    bs_account = models.OneToOneField('ClientAccount', related_name='apex_account', null=True)
    broker = "ETNA"
    def __str__(self):
        return self.apex_account

class AccountBeneficiary(models.Model):
    class Type(ChoiceEnum):
        primary = 0, 'Primary'
        contingent = 1, 'Contingent'

    class Relationship(ChoiceEnum):
        legal = 0, 'Legal entity (e.g. charity)'
        family_or_friend = 1, 'Family member/friend'
        spouse = 2, 'Spouse'
        estate = 3, 'My estate'

    type = models.IntegerField(null=True, choices=Type.choices())
    name = models.CharField(max_length=255)
    relationship = models.IntegerField(null=True, choices=Relationship.choices())
    birthdate = models.DateField()
    share = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    account = models.ForeignKey('ClientAccount', on_delete=models.CASCADE)


class AssetFeePlan(models.Model):
    """
    To calculate the fees for an asset and client, get the AssetFeePlan for the account, then lookup on the AssetFee
    model for all the fees applicable for the Asset and Plan.
    """
    name = models.CharField(max_length=127, unique=True)
    description = models.TextField(null=True)

    def __str__(self):
        return "[{}] {}".format(self.id, self.name)


class AssetFee(models.Model):
    name = models.CharField(max_length=127)
    plan = models.ForeignKey(AssetFeePlan)
    collector = models.ForeignKey('multi_sites.Company')
    asset = models.ForeignKey('portfolios.Ticker')
    applied_per = models.IntegerField(choices=constants.ASSET_FEE_EVENTS)
    fixed_level_unit = models.IntegerField(choices=constants.ASSET_FEE_UNITS)
    fixed_level_type = models.IntegerField(choices=constants.ASSET_FEE_LEVEL_TYPES)
    fixed_levels = models.TextField(help_text=constants._asset_fee_ht)
    prop_level_unit = models.IntegerField(choices=constants.ASSET_FEE_UNITS)
    prop_apply_unit = models.IntegerField(choices=constants.ASSET_FEE_UNITS)
    prop_level_type = models.IntegerField(choices=constants.ASSET_FEE_LEVEL_TYPES)
    prop_levels = models.TextField(help_text=constants._asset_fee_ht)

    def __str__(self):
        return "[{}] {}".format(self.id, self.name)


class ClientAccount(models.Model):
    """
    A ClientAccount is not just for Personal accounts. It is our base account,
    from which other data can be attached.
    It is the primary financial entity in the Betasmartz system.
    """
    class Status(ChoiceEnum):
        open = (0, 'Open')
        pending_close = (1, 'Pending Close From Admin')
        closed = (2, 'Closed')
    account_group = models.ForeignKey('advisor.AccountGroup',
                                      related_name="accounts_all",
                                      null=True)
    custom_fee = models.PositiveIntegerField(default=0)
    account_type = models.IntegerField(choices=constants.ACCOUNT_TYPES)
    account_name = models.CharField(max_length=255, default='PERSONAL')
    primary_owner = models.ForeignKey('Client',
                                      related_name="primary_accounts")
    account_number = models.CharField(max_length=16, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    token = models.CharField(max_length=36, editable=False)
    # The confirmed field indicates the account is fully ready to be used by the client.
    # The ClientAccount should be responsible for checking and setting the confirmed filed through
    # an as yet undefined set_confirmed() method.
    confirmed = models.BooleanField(default=False)
    tax_loss_harvesting_consent = models.BooleanField(default=False)
    tax_loss_harvesting_status = models.CharField(max_length=255, choices=(
        ("USER_OFF", "USER_OFF"),
        ("USER_ON", "USER_ON")), default="USER_OFF")
    asset_fee_plan = models.ForeignKey(AssetFeePlan, null=True)
    default_portfolio_set = models.ForeignKey('portfolios.PortfolioSet')
    cash_balance = models.FloatField(default=0,
                                     help_text='The amount of cash in this '
                                               'account available to be used.')
    supervised = models.BooleanField(default=True,
                                     help_text='Is this account supervised '
                                               'by an advisor?')
    signatories = models.ManyToManyField('Client',
                                         related_name='signatory_accounts',
                                         help_text='Other clients authorised '
                                                   'to operate the account.',
                                         blank=True)
    status = models.IntegerField(null=True, choices=Status.choices(), default=0)
    # also has broker_account foreign key to BrokerAccount

    objects = ClientAccountQuerySet.as_manager()

    class Meta:
        unique_together = ('primary_owner', 'account_name')

    def __init__(self, *args, **kwargs):
        super(ClientAccount, self).__init__(*args, **kwargs)
        self.__was_confirmed = self.confirmed

    @property
    def goals(self):
        return self.all_goals.exclude(state=Goal.State.ARCHIVED.value)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.pk is None:
            self.token = str(uuid.uuid4())
        if self.confirmed != self.__was_confirmed:
            self.on_confirmed_modified()
        ret_value = super(ClientAccount, self).save(force_insert, force_update, using, update_fields)
        self.__was_confirmed = self.confirmed
        return ret_value

    def on_confirmed_modified(self):
        from client.models import EmailInvite
        try:
            invitation = self.primary_owner.user.invitation
        except EmailInvite.DoesNotExist: invitation = None

        if invitation \
                and invitation.status != EmailInvite.STATUS_COMPLETE \
                and invitation.reason == EmailInvite.REASON_PERSONAL_INVESTING:
            invitation.onboarding_data = None
            invitation.status = EmailInvite.STATUS_COMPLETE
            invitation.save()

    def remove_from_group(self):
        old_group = self.account_group

        # get personal group or create it
        group_name = "{0}".format(self.primary_owner.full_name)
        groups = AccountGroup.objects.filter(
            name=group_name,
            advisor=self.primary_owner.advisor)
        if groups:
            group = groups[0]
        else:
            group = AccountGroup(name=group_name,
                                 advisor=self.primary_owner.advisor)
            group.save()

        self.account_group = group
        self.save()

        if old_group:
            if old_group.accounts.count() == 0:
                old_group_name = old_group.name
                # delete account group
                old_group.delete()
                return old_group_name

    def add_to_account_group(self, account_group):
        old_account_group = self.account_group
        self.account_group = account_group
        self.save()

        if old_account_group:
            if old_account_group.accounts.count() == 0:
                # delete account group
                old_account_group.delete()

    @property
    def advisors(self):
        return chain([self.primary_owner.advisor, self.account_group.advisor],
                     self.account_group.secondary_advisors.all())

    @property
    def target(self):
        total_target = 0
        for goal in self.goals.all():
            total_target += goal.target
        return total_target

    @property
    def fee(self):
        platform = Platform.objects.first()
        if platform:
            platform_fee = platform.fee
        else:
            platform_fee = 0
        if self.custom_fee != 0:
            return self.custom_fee + platform_fee
        else:
            return self.primary_owner.advisor.firm.fee + \
                   platform_fee

    @property
    def fee_fraction(self):
        return self.fee / 1000

    @property
    def name(self):
        """if self.account_name == PERSONAL_ACCOUNT:
            return "{0}'s Personal Account".format(
                self.primary_owner.user.first_name)"""

        return "{0}'s {1}".format(self.primary_owner.user.first_name,
                                  self.account_name.title())

    @property
    def total_balance(self):
        balance = sum(goal.total_balance for goal in self.goals.all())
        return balance + self.cash_balance

    @property
    def stock_balance(self):
        b = 0
        for goal in self.goals.all():
            b += goal.stock_balance
        return b

    @property
    def bond_balance(self):
        b = 0
        for goal in self.goals.all():
            b += goal.bond_balance
        return b

    @property
    def core_balance(self):
        b = 0
        for goal in self.goals.all():
            b += goal.core_balance
        return b

    @property
    def satellite_balance(self):
        b = 0
        for goal in self.goals.all():
            b += goal.satellite_balance
        return b

    @property
    def average_return(self):
        return mod_dietz_rate(self.goals)

    @property
    def total_earnings(self):
        return sum(g.total_earnings for g in self.goals)

    @property
    def stocks_percentage(self):
        if self.total_balance == 0:
            return 0
        return "{0}".format(
            int(round(self.stock_balance / self.total_balance * 100)))

    @property
    def bonds_percentage(self):
        if self.total_balance == 0:
            return 0
        return "{0}".format(
            int(round(self.bond_balance / self.total_balance * 100)))

    @property
    def core_percentage(self):
        if self.total_balance == 0:
            return 0
        return "{0}".format(
            int(round(self.core_balance / self.total_balance * 100)))

    @property
    def satellite_percentage(self):
        if self.total_balance == 0:
            return 0
        return "{0}".format(
            int(round(self.satellite_balance / self.total_balance * 100)))

    @property
    def owners(self):
        return self.primary_owner.full_name

    @property
    def account_type_name(self):
        return dict(constants.ACCOUNT_TYPES).get(self.account_type,
                                                 constants.ACCOUNT_UNKNOWN)

    @cached_property
    def on_track(self):
        """
            If any of client's goals are off track,
            return False.  If all goals are
            on track, return True.
        """
        for goal in self.goals:
            if not goal.on_track:
                return False
        return True

    @property
    def goals_length(self):
        return len(self.goals.all())

    def get_worth(self):
        total_balance = self.total_balance

        for worth_range in Client.WORTH_RANGES:
            if worth_range[1] <= total_balance < worth_range[2]:
                return worth_range[0]

    def get_worth_display(self):
        worth = dict(Client.WORTH_CHOICES)
        return worth.get(self.get_worth())

    @property
    def get_term(self):
        total_term = 0
        goals_with_term = 0
        for goal in self.goals.all():
            goal_term = goal.get_term
            if goal_term != 0:
                total_term += goal_term
                goals_with_term += 1
        if goals_with_term == 0:
            return 0
        return total_term / goals_with_term

    @property
    def confirmation_url(self):
        return settings.SITE_URL + "/client/confirm/account/{0}".format(
            self.pk)

    def send_confirmation_email(self):

        subject = "BetaSmartz new account confirmation"

        context = {
            'site': Site.objects.get_current(),
            'advisor': self.primary_owner.advisor,
            'confirmation_url': self.confirmation_url,
            'account_type': self.get_account_class_display(),
        }

        send_mail(subject,
                  '',
                  None,
                  [self.primary_owner.user.email],
                  html_message=render_to_string(
                      'email/confirm_new_client_account.html', context))

    def __str__(self):
        return "{0}:{1}:{2}:({3})".format(
            self.primary_owner.full_name,
            self.primary_owner.advisor.first_name,
            self.primary_owner.advisor.firm.name,
            self.account_type_name)

    @property
    def broker(self):
        #account = ClientAccount.objects.filter(id=self.id)
        #account.filter(ib_account__isnull=False)
        if hasattr(self, 'ib_account'):
            return "IB"
        elif hasattr(self, 'apex_account'):
            return "ETNA"
        else:
            return None

    @property
    def broker_account(self):
        if hasattr(self, 'ib_account'):
            return self.ib_account
        elif hasattr(self, 'apex_account'):
            return self.apex_account
        else:
            return None

    @property
    def broker_acc_id(self):
        if hasattr(self, 'ib_account'):
            return self.ib_account.ib_account
        elif hasattr(self, 'apex_account'):
            return self.apex_account.apex_account
        else:
            return None

    @staticmethod
    def get_account_type_text(acc_type):
        return get_text_of_choices_enum(acc_type, constants.ACCOUNT_TYPES)

    @cached_property
    def account_type_text(self):
        return ClientAccount.get_account_type_text(self.account_type)


class RiskProfileGroup(models.Model):
    """
    A way to group a set of predefined risk profile questions to
    be asked together.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    # Also has properties:
    #   'accounts' which is all the accounts this group is used on.
    # From the ClientAccount model 'questions' which is all the risk profile
    # questions that form this group. From the RiskProfileQuestion model
    #   'account-types' which is all the account types where this group is
    # the default group for the account type.

    def __str__(self):
        return "[{}] {}".format(self.id, self.name)


class AccountTypeRiskProfileGroup(models.Model):
    account_type = models.IntegerField(choices=constants.ACCOUNT_TYPES,
                                       unique=True)
    risk_profile_group = models.ForeignKey('RiskProfileGroup',
                                           related_name='account_types')


class RiskProfileQuestion(models.Model):
    """
    The set of predefined risk profile questions.
    """
    group = models.ForeignKey('RiskProfileGroup', related_name='questions')
    order = models.IntegerField()
    text = models.TextField()
    explanation = models.TextField()
    image = models.ImageField(_('question_image'), blank=True, null=True)
    figure = models.TextField(blank=True, null=True)

    # Also has property 'answers' which is all the predefined answers for
    # this question.

    class Meta:
        ordering = ['order']
        unique_together = ('group', 'order')

    def __str__(self):
        return self.text


class RiskProfileAnswer(models.Model):
    """
    The set of predefined answers to a risk profile question.
    """
    question = models.ForeignKey('RiskProfileQuestion', related_name='answers')
    order = models.IntegerField()
    text = models.TextField()
    image = models.ImageField(_('answer_image'), blank=True, null=True)
    b_score = models.FloatField(help_text="Indication of Behaviour towards risk. "
                                          "Higher means higher risk is idealogically acceptable.")
    a_score = models.FloatField(help_text="Indication of Ability to take risk. "
                                          "Higher means losses due to risk has less critical impact on the investor")
    s_score = models.FloatField(help_text="Indication of Investor sophistication. "
                                          "Higher means investor understands risk and investment matters.")

    # Also has property 'responses' which is all the responses given
    # that use this answer.

    class Meta:
        ordering = ['order']
        unique_together = ('question', 'order')

    def __str__(self):
        return self.text


class EmailNotificationPrefs(models.Model):
    client = models.OneToOneField('Client', related_name='notification_prefs')
    auto_deposit = models.BooleanField(
        verbose_name=_('to remind me a day before my automatic '
                       'deposits will be transferred'),
        default=True)
    hit_10mln = models.BooleanField(
        verbose_name=_('when my account balance hits $10,000,000'),
        default=False)


def generate_token():
    secret = str(uuid.uuid4()) + str(uuid.uuid4())
    return secret.replace('-', '')[:64]


class EmailInvite(models.Model):
    STATUS_CREATED = 0
    STATUS_SENT = 1
    STATUS_ACCEPTED = 2
    STATUS_EXPIRED = 3
    STATUS_COMPLETE = 4
    STATUSES = (
        (STATUS_CREATED, 'Created'),
        (STATUS_SENT, 'Sent'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_COMPLETE, 'Complete')
    )
    REASON_RETIREMENT = 1
    REASON_PERSONAL_INVESTING = 2
    REASONS = (
        (REASON_RETIREMENT, 'Retirement'),
        (REASON_PERSONAL_INVESTING, 'Personal Investing'),
    )

    advisor = models.ForeignKey('advisor.Advisor', related_name='invites')

    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    user = models.OneToOneField('user.User', related_name='invitation',
                                null=True, blank=True)

    invite_key = models.CharField(max_length=64,
                                  default=generate_token)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    last_sent_at = models.DateTimeField(blank=True, null=True)
    send_count = models.PositiveIntegerField(default=0)

    reason = models.PositiveIntegerField(choices=REASONS,
                                         blank=True, null=True)
    status = models.PositiveIntegerField(choices=STATUSES,
                                         default=STATUS_CREATED)

    onboarding_data = JSONField(null=True, blank=True)
    tax_transcript = models.FileField(null=True, blank=True)
    social_security_statement = models.FileField(null=True, blank=True)
    partner_social_security_statement = models.FileField(null=True, blank=True)
    photo_verification = models.FileField(null=True, blank=True)

    access_level = models.IntegerField(choices=CLIENT_ACCESS_LEVEL_CHOICES, default=CLIENT_FULL_ACCESS)

    salutation = models.CharField(max_length=10, choices=IB_SALUTATION_CHOICES,
                           default=IB_SALUTATION_MR)
    suffix = models.CharField(max_length=10, choices=IB_SUFFIX_CHOICES,
                       blank=True, null=True)
    risk_score = models.FloatField(blank=True, null=True,
                                   validators=[MinValueValidator(0), MaxValueValidator(1)])
    ib_account_number = models.CharField(max_length=32, null=True, blank=True,
                                         verbose_name='Interactive Brokers Account Number')

    def __str__(self):
        return '{} {} {} ({})'.format(self.first_name, self.middle_name[:1],
                                      self.last_name, self.email)

    def save(self, *args, **kwargs):
        if self.status == EmailInvite.STATUS_ACCEPTED:
            # clear sensitive information from onboarding_data,
            # that information has been used by ClientUserRegistration
            # if EmailInvite.STATUS_ACCEPTED
            if self.onboarding_data:
                if 'login' in self.onboarding_data:
                    if 'steps' in self.onboarding_data['login']:
                        info = self.onboarding_data['login']['steps'][0]
                        if 'password' in info:
                            self.onboarding_data['login']['steps'][0]['password'] = ''
                        if 'passwordConfirmation' in info:
                            self.onboarding_data['login']['steps'][0]['passwordConfirmation'] = ''
                        if 'primarySecurityQuestion' in info:
                            self.onboarding_data['login']['steps'][0]['primarySecurityQuestion'] = ''
                        if 'primarySecurityAnswer' in info:
                            self.onboarding_data['login']['steps'][0]['primarySecurityAnswer'] = ''
                        if 'secondarySecurityQuestion' in info:
                            self.onboarding_data['login']['steps'][0]['secondarySecurityQuestion'] = ''
                        if 'secondarySecurityAnswer' in info:
                            self.onboarding_data['login']['steps'][0]['secondarySecurityAnswer'] = ''
        super(EmailInvite, self).save(*args, **kwargs)

    @property
    def can_resend(self):
        return self.status in [self.STATUS_CREATED, self.STATUS_SENT, self.STATUS_ACCEPTED]

    def send(self):
        if not self.can_resend:
            raise ValidationError('Can be resend only in status '
                                  'CREATED or SENT')

        subject = "Welcome to {}".format(self.advisor.firm.name)

        context = {
            'site': Site.objects.get_current(),
            'invite_url': self.advisor.get_invite_url('client', self.email),
            'advisor': self.advisor,
            'category': 'Customer onboarding'
        }

        html_message = render_to_string('email/client/invitation_sent.html',
                                        context)
        send_mail(subject, '', None, [self.email], html_message=html_message)
        self.last_sent_at = now()
        if self.status != self.STATUS_ACCEPTED and self.status != self.STATUS_COMPLETE:
            self.status = self.STATUS_SENT
        self.send_count += 1

        self.save(update_fields=['last_sent_at', 'send_count', 'status'])

    class Meta:
        # shouldn't have multiple EmailInvites from same advisor to same email address
        unique_together = ('advisor', 'email')


class RiskCategory(models.Model):
    name = models.CharField(max_length=64, null=False, blank=False, unique=True)
    upper_bound = models.FloatField(validators=[MinValueValidator(0),
                                                MaxValueValidator(1)])

    class Meta:
        ordering = ['upper_bound']
        verbose_name = 'Risk Category'
        verbose_name_plural = 'Risk Categories'

    def __str__(self):
        return '[<{}] {}'.format(self.upper_bound, self.name)


class CloseAccountRequest(models.Model):
    class CloseChoice(ChoiceEnum):
        liquidate = 0, 'Liquidate assets'
        transfer_to_account = 1, 'Transfer assets to another account'
        transfer_to_custodian = 2, 'Transfer assets to another custodian'
        direct_custody = 3, 'Take direct custody of your assets'

    account = models.ForeignKey('ClientAccount', on_delete=models.CASCADE)
    close_choice = models.IntegerField(null=True, choices=CloseChoice.choices())
    account_transfer_form = models.FileField(blank=True, null=True)

    def send_advisor_email(self):
        """Email Client Advisor when an account is closed"""
        subject = "Close Client Account Request"

        context = {
            'site': Site.objects.get_current(),
            'account': self.account,
        }

        if self.close_choice == CloseAccountRequest.CloseChoice.liquidate.value:
            send_mail(subject,
                      '',
                      None,
                      [self.account.primary_owner.advisor.user.email],
                      html_message=render_to_string(
                          'email/advisor_liquidate_account.html', context))
        elif self.close_choice == CloseAccountRequest.CloseChoice.transfer_to_custodian.value:
            send_mail(subject,
                      '',
                      None,
                      [self.account.primary_owner.advisor.user.email],
                      html_message=render_to_string(
                          'email/advisor_transfer_custodian_account.html', context))
        elif self.close_choice == CloseAccountRequest.CloseChoice.direct_custody.value:
            send_mail(subject,
                      '',
                      None,
                      [self.account.primary_owner.advisor.user.email],
                      html_message=render_to_string(
                          'email/advisor_transfer_direct_account.html', context))

    def send_admin_email(self):
        """Email Betasmartz Admin when an account is closed"""
        subject = "Close Client Account Request"

        context = {
            'site': Site.objects.get_current(),
            'account': self.account,
        }

        if self.close_choice == CloseAccountRequest.CloseChoice.liquidate.value:
            send_mail(subject,
                      '',
                      None,
                      [settings.ADMIN_EMAIL],
                      html_message=render_to_string(
                          'email/advisor_liquidate_account.html', context))
        elif self.close_choice == CloseAccountRequest.CloseChoice.transfer_to_account.value:
            send_mail(subject,
                      '',
                      None,
                      [settings.ADMIN_EMAIL],
                      html_message=render_to_string(
                          'email/admin_transfer_to_account.html', context))
        elif self.close_choice == CloseAccountRequest.CloseChoice.transfer_to_custodian.value:
            send_mail(subject,
                      '',
                      None,
                      [settings.ADMIN_EMAIL],
                      html_message=render_to_string(
                          'email/advisor_transfer_custodian_account.html', context))
        elif self.close_choice == CloseAccountRequest.CloseChoice.direct_custody.value:
            send_mail(subject,
                      '',
                      None,
                      [settings.ADMIN_EMAIL],
                      html_message=render_to_string(
                          'email/advisor_transfer_direct_account.html', context))


class PricingPlanClient(PricingPlanPersonBase):
    parent = models.ForeignKey('firm.PricingPlan',
                               related_name='client_overrides')
    person = models.OneToOneField('client.Client',
                                  related_name='pricing_plan')


class JointAccountConfirmationModel(models.Model):
    primary_owner = models.ForeignKey('client.Client', related_name='owner_confirmation')
    cosignee = models.ForeignKey('client.Client', related_name='cosignee_confirmation')
    account = models.ForeignKey('client.ClientAccount', related_name='joint_confirmation')
    date_created = models.DateTimeField(auto_now_add=True)
    date_confirmed = models.DateTimeField(blank=True, null=True)
    token = models.CharField(max_length=64)

    @property
    def url(self):
        return reverse('confirm-joint-account', kwargs={
            'token': self.token,
        })

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.token:
            self.token = generate_token()
        super(JointAccountConfirmationModel, self).save(force_insert,
                                                        force_update,
                                                        using, update_fields)


class HealthDevice(models.Model):
    class ProviderType(ChoiceEnum):
        GOOGLE_FIT = 1, 'Google Fit'
        FITBIT = 2, 'Fitbit'
        SAMSUNG_DIGI_HEALTH = 3, 'Samsung Digital Health'
        MICROSOFT_HEALTH = 4, 'Microsoft Health'
        JAWBONE = 5, 'Jawbone'
        UNDERARMOUR = 6, 'Under Armour'
        WITHINGS = 7, 'Withings'
        TOMTOM = 8, 'TomTom'
        GARMIN = 9, 'Garmin'

    client = models.OneToOneField('client.Client', related_name='health_device', help_text='The health device owner')
    provider = models.IntegerField(null=True, choices=ProviderType.choices(), help_text='Heath device provider')
    access_token = models.CharField(max_length=2000, default='', help_text='OAuth access Token')
    refresh_token = models.CharField(max_length=1000, null=True, blank=True, help_text='OAuth refresh token')
    expires_at = models.DateTimeField(null=True, blank=True, help_text='OAuth token expiry time')
    meta = JSONField(null=True, blank=True, help_text='Meta data')


class IBOnboard(models.Model):
    STATE_INIT = 0
    STATE_SUBMITTED = 1
    STATE_REJECTED = 2
    STATE_ACTIVE = 3
    STATE_AWAITING_FEED = 4

    ONBOARD_STATES = (
        (STATE_INIT, 'Initialized'), # Initial state
        (STATE_SUBMITTED, 'Submitted'), # New IB Account application submitted.
        (STATE_REJECTED, 'Rejected'), # Submission rejected
        (STATE_ACTIVE, 'Active'), # Submission approved or IB account number is verified and feeded.
        (STATE_AWAITING_FEED, 'Awaiting Feed'), # Waiting for feed file to be synced for the first time
    )

    class PhoneType(ChoiceEnum):
        WORK = "Work", "Work"
        HOME = "Home", "Home"
        FAX = "Fax", "Fax"
        MOBILE = "Mobile", "Mobile"
        MOBILE_WORK = "Mobile (work)", "Mobile (work)"
        MOBILE_OTHER = "Mobile (other)", "Mobile (other)"
        BUSINESS = "Business", "Business"
        OTHER = "Other (voice)", "Other (voice)"

    class TinType(ChoiceEnum):
        SSN = 'SSN', 'SSN'
        EIN = 'EIN', 'EIN'
        NON_US_NATIONAL_IID = 'NonUS_NationalIID', 'NonUS_NationalIID'

    class StkControlType(ChoiceEnum):
        DIRECTOR = 1, 'A Director',
        SHAREHOLDER = 2, 'A 10% Shareholder'
        POLICYMAKING_OFFICER = 3, 'A Policy-Making Officer'

    class NetWorthType(ChoiceEnum):
        NET_WORTH_OPTION_0 = 0, '0 ~ 19,999'
        NET_WORTH_OPTION_1 = 1, '20,000 ~ 50,000'
        NET_WORTH_OPTION_2 = 2, '50,001 ~ 75,000'
        NET_WORTH_OPTION_3 = 3, '75,001 ~ 100,000'
        NET_WORTH_OPTION_4 = 4, '100,001 ~ 250,000'
        NET_WORTH_OPTION_5 = 5, '250,001 ~ 500,000'
        NET_WORTH_OPTION_6 = 6, '500,001 ~ 1,000,000'
        NET_WORTH_OPTION_7 = 7, '1,000,001 ~ 5,000,000'
        NET_WORTH_OPTION_8 = 8, '5,000,001 ~ 10,000,000'
        NET_WORTH_OPTION_9 = 9, '10,000,001 ~ 25,000,000'
        NET_WORTH_OPTION_10 = 10, '25,000,001 ~ 30,000,000'
        NET_WORTH_OPTION_11 = 11, '30,000,001 ~ 50,000,000'
        NET_WORTH_OPTION_12 = 12, '50,000,001 ~ '

    class NetWorthLiquidType(ChoiceEnum):
        NET_WORTH_LIQUID_OPTION_0 = 0, '0 ~ 19,999'
        NET_WORTH_LIQUID_OPTION_1 = 1, '20,000 ~ 50,000'
        NET_WORTH_LIQUID_OPTION_2 = 2, '50,001 ~ 75,000'
        NET_WORTH_LIQUID_OPTION_3 = 3, '75,001 ~ 100,000'
        NET_WORTH_LIQUID_OPTION_4 = 4, '100,001 ~ 250,000'
        NET_WORTH_LIQUID_OPTION_5 = 5, '250,001 ~ 500,000'
        NET_WORTH_LIQUID_OPTION_6 = 6, '500,001 ~ 1,000,000'
        NET_WORTH_LIQUID_OPTION_7 = 7, '1,000,001 ~ 5,000,000'
        NET_WORTH_LIQUID_OPTION_8 = 8, '5,000,001 ~ '

    class AnnualNetIncomeType(ChoiceEnum):
        ANNUAL_NET_INCOE_OPTION_0 = 0, '0 ~ 39,999'
        ANNUAL_NET_INCOE_OPTION_1 = 1, '40,000 ~ 45,000'
        ANNUAL_NET_INCOE_OPTION_2 = 2, '45,001 ~ 50,000'
        ANNUAL_NET_INCOE_OPTION_3 = 3, '50,001 ~ 100,000'
        ANNUAL_NET_INCOE_OPTION_4 = 4, '100,001 ~ 150,000'
        ANNUAL_NET_INCOE_OPTION_5 = 5, '150,001 ~ 250,000'
        ANNUAL_NET_INCOE_OPTION_6 = 6, '250,001 ~ 500,000'
        ANNUAL_NET_INCOE_OPTION_7 = 7, '500,001 ~ 1,000,000'
        ANNUAL_NET_INCOE_OPTION_8 = 8, '1,000,001 ~ '

    class TotalAssetsType(ChoiceEnum):
        TOTAL_ASSETS_OPTION_0 = 0, '0 ~ 19,999'
        TOTAL_ASSETS_OPTION_1 = 1, '20,000 ~ 49,999'
        TOTAL_ASSETS_OPTION_2 = 2, '50,000 ~ 74,999'
        TOTAL_ASSETS_OPTION_3 = 3, '75,000 ~ 99,999'
        TOTAL_ASSETS_OPTION_4 = 4, '100,000 ~ 249,999'
        TOTAL_ASSETS_OPTION_5 = 5, '250,000 ~ 499,999'
        TOTAL_ASSETS_OPTION_6 = 6, '500,000 ~ 999,999'
        TOTAL_ASSETS_OPTION_7 = 7, '1,000,000 ~ 4,999,999'
        TOTAL_ASSETS_OPTION_8 = 8, '5,000,000 ~ 9,999,999'
        TOTAL_ASSETS_OPTION_9 = 9, '10,000,000 ~ 249,999,999'
        TOTAL_ASSETS_OPTION_10 = 10, '250,000,000 ~ 499,999,999'
        TOTAL_ASSETS_OPTION_11 = 11, '500,000,000 ~ '

    account_number = models.CharField(max_length=32, null=True, blank=True, unique=True)
    ib_entity = models.CharField(max_length=32, null=True, blank=True, unique=True)
    ib_user_id = models.CharField(max_length=32, null=True, blank=True, unique=True)
    ib_password = models.CharField(max_length=32, null=True, blank=True, unique=True)
    ib_user = models.CharField(max_length=32, null=True, blank=True, unique=True)
    state = models.IntegerField(choices=ONBOARD_STATES, default=STATE_INIT)
    account_type = models.IntegerField(choices=constants.ACCOUNT_TYPES, default=constants.ACCOUNT_TYPE_PERSONAL, null=True, blank=True)
    client = models.OneToOneField('Client', related_name='ib_onboard', null=True, blank=True)
    employer_address = models.OneToOneField('address.Address', related_name='ib_onboard_employer', null=True, blank=True)
    ib_employment_status = models.IntegerField(choices=IB_EMPLOY_STATUSES, default=IB_EMPLOY_STAT_EMPLOYED, blank=True, null=True, verbose_name='IB Employment Status',
                                              help_text='IB Employment Status')
    tax_address = models.OneToOneField('address.Address', related_name='ib_onboard_tax', null=True, blank=True)
    country_of_birth = models.CharField(max_length=250, blank=True, null=True, help_text='Country of birth', choices=COUNTRY_CHOICES)
    num_dependents = models.IntegerField(blank=True, null=True, verbose_name='Number of dependents',
                                         help_text='Number of dependents')
    phone_type = models.CharField(choices=PhoneType.choices(), max_length=32, null=True, blank=True, default='Home',
                                  help_text='Phone Type')
    identif_leg_citizenship = models.CharField(max_length=250, blank=True, null=True, verbose_name='Legal residence citizenship',
                                               help_text='Legal residence citizenship', choices=COUNTRY_CHOICES)
    fin_info_tot_assets = models.IntegerField(choices=TotalAssetsType.choices(), blank=True, null=True, verbose_name='Total Assets',
                                              help_text='Total assets')
    fin_info_liq_net_worth = models.IntegerField(choices=NetWorthLiquidType.choices(), blank=True, null=True, verbose_name='Liquid Net Worth',
                                                 help_text='Liquid net worth')
    fin_info_ann_net_inc = models.IntegerField(choices=AnnualNetIncomeType.choices(), blank=True, null=True, verbose_name='Annual Net Income',
                                               help_text='Annual net income')
    fin_info_net_worth = models.IntegerField(choices=NetWorthType.choices(), blank=True, null=True, verbose_name='Net Worth',
                                             help_text='Net worth')
    asset_exp_0_knowledge = models.IntegerField(blank=True, null=True, verbose_name='STK trading knowledge',
                                             help_text='STK trading knowledge')
    asset_exp_0_yrs = models.IntegerField(blank=True, null=True, verbose_name='STK trading experience',
                                       help_text='STK trading experience')
    asset_exp_0_trds_per_yr = models.IntegerField(blank=True, null=True, verbose_name='STK trading frequency',
                                               help_text='STK trading frequency')
    asset_exp_1_knowledge = models.IntegerField(blank=True, null=True, verbose_name='FUNDS trading knowledge',
                                             help_text='FUNDS trading knowledge')
    asset_exp_1_yrs = models.IntegerField(blank=True, null=True, verbose_name='FUNDS trading experience',
                                       help_text='FUNDS trading experience')
    asset_exp_1_trds_per_yr = models.IntegerField(blank=True, null=True, verbose_name='Fund Trades Per Year',
                                               help_text='FUNDS trading frequency')
    reg_status_broker_deal = models.NullBooleanField(blank=True, null=True, verbose_name='BROKERDEALER',
                                                     help_text='BROKERDEALER')
    reg_status_exch_memb = models.NullBooleanField(blank=True, null=True, verbose_name='EXCHANGEMEMBERSHIP',
                                                   help_text='EXCHANGEMEMBERSHIP')
    reg_status_disp = models.NullBooleanField(blank=True, null=True, verbose_name='DISPUTE', help_text='DISPUTE')
    reg_status_investig = models.NullBooleanField(blank=True, null=True, verbose_name='Investigation', help_text='INVESTIGATION')
    reg_status_stk_cont = models.IntegerField(choices=StkControlType.choices(), blank=True, null=True,
                                              help_text='STKCONTROL')
    tax_resid_0_tin_type = models.CharField(choices=TinType.choices(), max_length=250, blank=True, null=True, default='SSN',
                                            verbose_name='Tax residency TIN type', help_text='Tax residency TIN type')
    tax_resid_0_tin = models.CharField(max_length=250, blank=True, null=True, verbose_name='Tax residency TIN',
                                       help_text='Tax residency TIN')
    doc_exec_ts = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    doc_exec_login_ts = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    signature = models.CharField(max_length=250, blank=True, null=True, verbose_name='Document signed by',
                                     help_text='Document signed by')
    salutation = models.CharField(max_length=10, choices=IB_SALUTATION_CHOICES,
                                  default=IB_SALUTATION_MR, help_text='Salutation')
    suffix = models.CharField(max_length=10, choices=IB_SUFFIX_CHOICES, blank=True, null=True, help_text='Suffix')

    other_income_source = models.IntegerField(choices=SOURCE_OF_FUNDS_TYPES, default=SOURCE_OF_FUNDS_TYPE_INTEREST, null=True, blank=True)

    joint_type = models.CharField(max_length=250, blank=True, null=True, help_text='Type of joint account', choices=JOINT_ACCOUNT_TYPES)

    xml_outbound = models.TextField(null=True, blank=True)
    xml_inbound = JSONField(null=True, blank=True)

    @cached_property
    def residential_address(self):
        if self.client:
            return self.client.residential_address
        else:
            return None

    @cached_property
    def date_of_birth(self):
        if self.client:
            return self.client.date_of_birth
        else:
            return None

    @cached_property
    def email(self):
        if self.client:
            return self.client.user.email
        else:
            return None

    @cached_property
    def first_name(self):
        if self.client:
            return self.client.user.first_name
        else:
            return None

    @cached_property
    def last_name(self):
        if self.client:
            return self.client.user.last_name
        else:
            return None

    @cached_property
    def identif_ssn(self):
        try:
            return self.client.regional_data['ssn']
        except:
            return None

    @cached_property
    def civil_status(self):
        if self.client:
            return self.client.civil_status
        else:
            return None

    @cached_property
    def income(self):
        if self.client:
            return self.client.income
        else:
            return None

    @cached_property
    def employment_status(self):
        if self.client:
            return self.client.employment_status
        else:
            return None

    @cached_property
    def phone_number(self):
        if self.client:
            return self.client.phone_num
        else:
            return None

    @cached_property
    def gender(self):
        if self.client:
            return self.client.gender
        else:
            return None

    @cached_property
    def employer(self):
        if self.client:
            return self.client.employer
        else:
            return None


    @cached_property
    def occupation(self):
        if self.client:
            return self.client.occupation
        else:
            return None

    @cached_property
    def empl_business(self):
        if self.client:
            return self.client.industry_sector
        else:
            return None

    def __str__(self):
        return "{0} ({1})".format(
            self.client.name,
            self.account_number or 'None')

    def feed_ib_client(self, ib_account_feed):
        """
        ib_account_feed: IBAccountFeed model instance from brokers
        """
        client = self.client
        residential_address = client.residential_address
        if not client.residential_address:
            residential_address = Address()
        
        tax_address = self.tax_address
        if not tax_address:
            tax_address = Address()

        tax_address.copy_from_address(ib_account_feed.address)
        self.tax_address = tax_address
        self.state = IBOnboard.STATE_ACTIVE
        self.save()

        residential_address.copy_from_address(ib_account_feed.address)
        client.residential_address = residential_address
        client.save()

        # if No Client Access, copy email from the feed.
        if not client.is_confirmed:
            user = client.user
            if User.objects.filter(email=ib_account_feed.primary_email).count() == 0:
                user.email = ib_account_feed.primary_email
                user.save()
            invitation = user.invitation
            if EmailInvite.objects.filter(email=ib_account_feed.primary_email).count() == 0:
                invitation.email = ib_account_feed.primary_email
                invitation.save()


class ExternalAsset(models.Model):
    class Type(ChoiceEnum):
        FAMILY_HOME = (0, 'Family Home')
        INVESTMENT_PROPERTY = (1, 'Investment Property')
        INVESTMENT_PORTFOLIO = (2, 'Investment Portfolio')
        SAVINGS_ACCOUNT = (3, 'Savings Account')
        PROPERTY_LOAN = (4, 'Property Loan')
        TRANSACTION_ACCOUNT = (5, 'Transaction Account')
        RETIREMENT_ACCOUNT = (6, 'Retirement Account')
        OTHER = (7, 'Other')

    type = models.IntegerField(choices=Type.choices())
    name = models.CharField(max_length=128)
    owner = models.ForeignKey('client.Client', related_name='external_assets')
    description = models.TextField(blank=True, null=True)
    valuation = models.DecimalField(decimal_places=2,
                                    max_digits=15,  # Up to 9.9... trillion
                                    help_text='In the system currency. Could be negative if a debt')
    valuation_date = models.DateField(help_text='Date when the asset was valued')
    growth = models.DecimalField(decimal_places=4,
                                 max_digits=5,
                                 help_text='Modeled annualized growth of the asset - pos or neg. 0.0 is no growth')
    acquisition_date = models.DateField(help_text="Could be in the future if it's a future acquisition")
    debt = models.OneToOneField('ExternalAsset',
                                related_name='for_asset',
                                help_text="Any debt that is directly associated to the asset.",
                                null=True,
                                on_delete=SET_NULL)
    # Also has a 'transfer_plan' field from ExternalAssetTransfer

    # Override the manager with one that has permission capabilities.
    objects = ExternalAssetQuerySet.as_manager()

    def get_growth_valuation(self, to_date=None):
        # daily growth not annual
        if to_date is None:
            to_date = datetime.now().date()
        delta = to_date - self.valuation_date

        return self.valuation * pow(1 + self.growth, delta.days)

    class Meta:
        unique_together = ('name', 'owner')


class ExternalAccount(ExternalAsset):
    institution = models.CharField(max_length=128, help_text='Institute where the account is held.')
    account_id = models.CharField(max_length=64)


class ExternalAssetTransfer(TransferPlan):
    asset = models.OneToOneField(ExternalAsset, related_name='transfer_plan', on_delete=CASCADE)
