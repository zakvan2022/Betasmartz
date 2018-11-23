from __future__ import unicode_literals

import logging

from django.contrib.sites.models import Site
from django.core.validators import MaxLengthValidator, MaxValueValidator, \
    MinLengthValidator, MinValueValidator, ValidationError
from django.db import models, transaction
from django.db.models.deletion import PROTECT, CASCADE
from django.db.models.signals import post_save
from django.dispatch import receiver
from jsonfield.fields import JSONField
from pinax.eventlog.models import Log

from common.structures import ChoiceEnum
from common.utils import get_text_of_choices_enum
from goal.models import GoalSetting, GoalMetricGroup
from main.abstract import TransferPlan
from main.risk_profiler import GoalSettingRiskProfile
from .managers import RetirementPlanQuerySet, RetirementAdviceQueryset
from main import constants
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.utils.functional import cached_property
import json
from main.abstract import TimestampedModel
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from main.settings import BASE_DIR
from main.constants import GENDER_MALE
from activitylog.event import Event
from main.tasks import send_plan_agreed_email_task
logger = logging.getLogger('retiresmartz.models')
from main.celery import app as celery_app


class RetirementPlan(TimestampedModel):
    class AccountCategory(ChoiceEnum):
        EMPLOYER_DESCRETIONARY_CONTRIB = 1, 'Employer Discretionary Contributions'
        EMPLOYER_MATCHING_CONTRIB = 2, 'Employer Matching Contributions'
        SALARY_PRE_TAX_ELECTIVE_DEFERRAL = 3, 'Salary/ Pre-Tax Elective Deferral'
        AFTER_TAX_ROTH_CONTRIB = 4, 'After-Tax Roth Contributions'
        AFTER_TAX_CONTRIB = 5, 'After Tax Contributions'
        SELF_EMPLOYED_PRE_TAX_CONTRIB = 6, 'Self Employed Pre-Tax Contributions'
        SELF_EMPLOYED_AFTER_TAX_CONTRIB = 7, 'Self Employed After Tax Contributions'
        DORMANT_ACCOUNT_NO_CONTRIB = 8, 'Dormant / Inactive'

    class LifestyleCategory(ChoiceEnum):
        OK = 1, 'Doing OK'
        COMFORTABLE = 2, 'Comfortable'
        WELL = 3, 'Doing Well'
        LUXURY = 4, 'Luxury'

    class ExpenseCategory(ChoiceEnum):
        ALCOHOLIC_BEVERAGE = 1, 'Alcoholic Beverage'
        APPAREL_SERVICES = 2, 'Apparel & Services'
        EDUCATION = 3, 'Education'
        ENTERTAINMENT = 4, 'Entertainment'
        FOOD = 5, 'Food'
        HEALTHCARE = 6, 'Healthcare'
        HOUSING = 7, 'Housing'
        INSURANCE_PENSIONS_SOCIAL_SECURITY = 8, 'Insuarance, Pensions & Social Security'
        PERSONAL_CARE = 9, 'Personal Care'
        READING = 10, 'Reading'
        SAVINGS = 11, 'Savings'
        TAXES = 12, 'Taxes'
        TOBACCO = 13, 'Tobacco'
        TRANSPORTATION = 14, 'Transportation'
        MISCELLANEOUS = 15, 'Miscellaneous'

    class SavingCategory(ChoiceEnum):
        HEALTH_GAP = 1, 'Health Gap'
        EMPLOYER_CONTRIBUTION = 2, 'Employer Retirement Contributions'
        TAXABLE_PRC = 3, 'Taxable Personal Retirement Contributions'
        TAX_PAID_PRC = 4, 'Tax-paid Personal Retirement Contributions'
        PERSONAL = 5, 'Personal'
        INHERITANCE = 6, 'Inheritance'

    class HomeStyle(ChoiceEnum):
        SINGLE_DETACHED = 1, 'Single, Detached'
        SINGLE_ATTACHED = 2, 'Single, Attached'
        MULTI_9_OR_LESS = 3, 'Multi-Unit, 9 or less'
        MULTI_10_TO_20 = 4, 'Multi-Unit, 10 - 20'
        MULTI_20_PLUS = 5, 'Multi-Unit, 20+'
        MOBILE_HOME = 6, 'Mobile Home'
        RV = 7, 'RV, Van, Boat, etc'

    name = models.CharField(max_length=128, blank=True, null=True)
    description = models.TextField(null=True, blank=True)
    client = models.ForeignKey('client.Client')

    partner_plan = models.OneToOneField('RetirementPlan',
                                        related_name='partner_plan_reverse',
                                        null=True,
                                        on_delete=models.SET_NULL)

    lifestyle = models.PositiveIntegerField(choices=LifestyleCategory.choices(),
                                            default=1,
                                            help_text="The desired retirement lifestyle")

    desired_income = models.PositiveIntegerField(
        help_text="The desired annual household pre-tax retirement income in system currency")
    income = models.PositiveIntegerField(
        help_text="The current annual personal pre-tax income at the start of your plan")

    volunteer_days = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(7)],
        help_text="The number of volunteer work days selected")

    paid_days = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(7)],
        help_text="The number of paid work days selected")

    same_home = models.BooleanField(
        help_text="Will you be retiring in the same home?")

    same_location = models.NullBooleanField(
        help_text="Will you be retiring in the same general location?",
        blank=True, null=True)

    retirement_postal_code = models.CharField(
        max_length=10,
        validators=[MinLengthValidator(5), MaxLengthValidator(10)],
        help_text="What postal code will you retire in?")

    reverse_mortgage = models.BooleanField(
        help_text="Would you consider a reverse mortgage? (optional)")

    retirement_home_style = models.PositiveIntegerField(
        choices=HomeStyle.choices(), null=True, blank=True,
        help_text="The style of your retirement home")

    retirement_home_price = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="The price of your future retirement home (in today's dollars)")

    beta_partner = models.BooleanField(
        default=False,
        help_text="Will BetaSmartz manage your partner's "
                  "retirement assets as well?")

    retirement_accounts = JSONField(
        null=True,
        blank=True,
        help_text="List of retirement accounts [{id, name, acc_type, owner, balance, balance_efdt, contrib_amt, contrib_period, employer_match, employer_match_type},...]")

    expenses = JSONField(
        null=True,
        blank=True,
        help_text="List of expenses [{id, desc, cat, who, amt},...]")

    savings = JSONField(null=True,
                        blank=True,
                        help_text="List of savings [{id, desc, cat, who, amt},...]")

    initial_deposits = JSONField(null=True,
                                 blank=True,
                                 help_text="List of deposits [{id, asset, goal, amt},...]")

    income_growth = models.FloatField(default=0,
                                      help_text="Above consumer price index (inflation)")
    expected_return_confidence = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)],
                                                   help_text="Planned confidence of the portfolio returns given the "
                                                             "volatility and risk predictions.")

    retirement_age = models.PositiveIntegerField()

    btc = models.PositiveIntegerField(help_text="Annual personal before-tax "
                                                "contributions",
                                                blank=True)
    atc = models.PositiveIntegerField(help_text="Annual personal after-tax "
                                                "contributions",
                                                blank=True)

    max_employer_match_percent = models.FloatField(
        null=True, blank=True,
        help_text="The percent the employer matches of before-tax contributions"
    )

    desired_risk = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="The selected risk appetite for this retirement plan")

    # This is a field, not calculated, so we have a historical record of the value.
    recommended_risk = models.FloatField(
        editable=False, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="The calculated recommended risk for this retirement plan")

    # This is a field, not calculated, so we have a historical record of the value.
    max_risk = models.FloatField(
        editable=False, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="The maximum allowable risk appetite for this retirement "
                  "plan, based on our risk model")

    # calculated_life_expectancy should be calculated,
    # read-only don't let client create/update
    calculated_life_expectancy = models.PositiveIntegerField(editable=False, blank=True)
    selected_life_expectancy = models.PositiveIntegerField()

    agreed_on = models.DateTimeField(null=True, blank=True)

    goal_setting = models.OneToOneField(GoalSetting, null=True, related_name='retirement_plan', on_delete=PROTECT)
    partner_data = JSONField(null=True, blank=True)

    # balance of retirement account number
    balance = models.FloatField(null=True, blank=True)

    date_of_estimate = models.DateField(null=True, blank=True)

    # Install the custom manager that knows how to filter.
    objects = RetirementPlanQuerySet.as_manager()

    class Meta:
        unique_together = ('name', 'client')

    def __init__(self, *args, **kwargs):
        # Keep a copy of agreed_on so we can see if it's changed
        super(RetirementPlan, self).__init__(*args, **kwargs)
        self.__was_agreed = self.agreed_on

    def __str__(self):
        return "RetirementPlan {}".format(self.id)

    @property
    def was_agreed(self):
        return self.__was_agreed

    @transaction.atomic
    def set_settings(self, new_setting):
        """
        Updates the retirement plan with the new settings, and saves the plan
        :param new_setting: The new setting to set.
        :return:
        """
        old_setting = self.goal_setting
        self.goal_setting = new_setting
        if not(old_setting and old_setting.retirement_plan.agreed_on):
            self.save()

        if old_setting is not None:
                old_group = old_setting.metric_group
                custom_group = old_group.type == GoalMetricGroup.TYPE_CUSTOM
                last_user = old_group.settings.count() == 1
                try:
                    old_setting.delete()
                except Exception as e:
                    logger.error(e)
                if custom_group and last_user:
                    old_group.delete()

    @cached_property
    def spendable_income(self):
        if isinstance(self.savings, str):
            savings = json.loads(self.savings)
        else:
            savings = self.savings

        if isinstance(self.expenses, str):
            expenses = json.loads(self.expenses)
        else:
            expenses = self.expenses

        if self.savings:
            savings_cost = sum([s.get('amt', 0) for s in savings])
        else:
            savings_cost = 0
        if self.expenses:
            expenses_cost = sum([e.get('amt', 0) for e in expenses])
        else:
            expenses_cost = 0
        return self.income - savings_cost - expenses_cost

    def save(self, *args, **kwargs):
        """
        Override save() so we can do some custom validation of partner plans.
        """
        self.calculated_life_expectancy = self.client.life_expectancy
        bas_scores = self.client.get_risk_profile_bas_scores()
        self.recommended_risk = GoalSettingRiskProfile._recommend_risk(bas_scores)
        self.max_risk = GoalSettingRiskProfile._max_risk(bas_scores)

        if self.was_agreed:
            raise ValidationError("Cannot save a RetirementPlan that has been agreed upon")

        reverse_plan = getattr(self, 'partner_plan_reverse', None)
        if self.partner_plan is not None and reverse_plan is not None and \
           self.partner_plan != reverse_plan:
            raise ValidationError(
                "Partner plan relationship must be symmetric."
            )

        super(RetirementPlan, self).save(*args, **kwargs)

        if self.get_soa() is None and self.id is not None:
            self.generate_soa()

    def get_soa(self):
        from statements.models import RetirementStatementOfAdvice
        qs = RetirementStatementOfAdvice.objects.filter(
            retirement_plan_id=self.pk
        )
        if qs.count():
            self.statement_of_advice = qs[0]
            return qs[0]
        else:
            return self.generate_soa()

    def generate_soa(self):
        from statements.models import RetirementStatementOfAdvice
        soa = RetirementStatementOfAdvice(retirement_plan_id=self.id)
        soa.save()
        return soa

    def send_plan_agreed_email(self):
        try:
            send_plan_agreed_email_task.delay(self.id)
        except:
            self._send_plan_agreed_email(self.id)

    @staticmethod
    def _send_plan_agreed_email(plan_id):
        plan = RetirementPlan.objects.get(pk=plan_id)
        soa = plan.get_soa()
        pdf_content = soa.save_pdf()
        partner_name = plan.partner_data['name'] if plan.client.is_married and plan.partner_data else None
        context = {
            'site': Site.objects.get_current(),
            'client': plan.client,
            'advisor': plan.client.advisor,
            'firm': plan.client.firm,
            'partner_name': partner_name
        }

        # Send to client
        subject = "Your BetaSmartz Retirement Plan Completed"
        html_content = render_to_string('email/retiresmartz/plan_agreed_client.html', context)
        email = EmailMessage(subject, html_content, None, [plan.client.user.email])
        email.content_subtype = "html"
        email.attach('SOA.pdf', pdf_content, 'application/pdf')
        email.send()

        # Send to advisor
        subject = "Your clients have completed their Retirement Plan" if partner_name else \
                  "Your client completed a Retirement Plan"
        html_content = render_to_string('email/retiresmartz/plan_agreed_advisor.html', context)
        email = EmailMessage(subject, html_content, None, [plan.client.advisor.user.email])
        email.content_subtype = "html"
        email.attach('SOA.pdf', pdf_content, 'application/pdf')
        email.send()


    @property
    def portfolio(self):
        return self.goal_setting.portfolio if self.goal_setting else None

    @cached_property
    def on_track(self):
        if hasattr(self, '_on_track'):
            return self._on_track
        self._on_track = False
        return self._on_track

    @property
    def opening_tax_deferred_balance(self):
        # TODO: Sum the complete amount that is expected to be in the retirement plan accounts on account opening.
        return 0

    @property
    def opening_tax_paid_balance(self):
        # TODO: Sum the complete amount that is expected to be in the retirement plan accounts on account opening.
        return 0

    @property
    def replacement_ratio(self):
        partner_income = 0
        if self.partner_data is not None:
            partner_income = self.partner_plan.income
        return self.desired_income / (self.income + partner_income)

    @staticmethod
    def get_lifestyle_text(lifestyle):
        return get_text_of_choices_enum(lifestyle, RetirementPlan.LifestyleCategory.choices())

    @cached_property
    def lifestyle_text(self):
        return RetirementPlan.get_lifestyle_text(self.lifestyle)

    @staticmethod
    def get_expense_category_text(expense_cat):
        return get_text_of_choices_enum(expense_cat, RetirementPlan.ExpenseCategory.choices())

@receiver(post_save, sender=RetirementPlan)
def resolve_retirement_invitations(sender, instance, created, **kwargs):
    """Create a matching profile whenever a user object is created."""
    from client.models import EmailInvite
    try:
        invitation = instance.client.user.invitation
    except EmailInvite.DoesNotExist:
        invitation = None
    if created and invitation \
            and invitation.status != EmailInvite.STATUS_COMPLETE \
            and invitation.reason == EmailInvite.REASON_RETIREMENT:
        invitation.onboarding_data = None
        invitation.tax_transcript = None
        invitation.status = EmailInvite.STATUS_COMPLETE
        invitation.save()


class RetirementPlanEinc(TransferPlan):
    name = models.CharField(max_length=128)
    account_type = models.IntegerField(choices=constants.ACCOUNT_TYPES, null=True, blank=True)
    plan = models.ForeignKey(RetirementPlan, related_name='external_income')


class RetirementSpendingGoal(models.Model):
    plan = models.ForeignKey(RetirementPlan, related_name='retirement_goals')
    goal = models.OneToOneField('goal.Goal', related_name='retirement_plan')


class RetirementPlanAccount(models.Model):
    """
    TODO: Comment what this is.
    """
    plan = models.ForeignKey(RetirementPlan, related_name='retiree')
    account = models.OneToOneField('client.ClientAccount', related_name='retirement')

    def __str__(self):
        return "%s Plan %s Account %s" % (self.id, self.plan, self.account)


class RetirementLifestyle(models.Model):
    cost = models.PositiveIntegerField(
        help_text="The minimum expected cost in system currency of this "
                  "lifestyle in today's dollars"
    )
    holidays = models.TextField(help_text="The text for the holidays block")
    eating_out = models.TextField(
        help_text="The text for the eating out block"
    )
    health = models.TextField(help_text="The text for the health block")
    interests = models.TextField(help_text="The text for the interests block")
    leisure = models.TextField(help_text="The text for the leisure block")
    default_volunteer_days = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(7)],
        help_text="The default number of volunteer work days selected "
                  "for this lifestyle"
    )

    default_paid_days = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(7)],
        help_text="The default number of paid work days selected "
                  "for this lifestyle"
    )

    def __str__(self):
        return "RetirementLifestyle {}".format(self.id)


class RetirementAdvice(models.Model):
    plan = models.ForeignKey(RetirementPlan, related_name='advice', on_delete=CASCADE)
    trigger = models.ForeignKey(Log, related_name='advice', on_delete=PROTECT)
    dt = models.DateTimeField(auto_now_add=True)
    read = models.DateTimeField(blank=True, null=True)
    text = models.CharField(max_length=512)

    """
    actions: List of actions JSON.= models.FloatField(default=0,
                                      help_text="Above consumer price index (inflation)")
        'label': Button label in string.
        'type': Api type in string that front-end web app can use to get url from.
        'url': Api URL, Both type or url should not be used together.
        'data': JSON request data to send to backend with api request.
    """
    actions = JSONField(null=True,
                        blank=True,
                        help_text="List of actions [{label, type/url, data},...]")

    objects = RetirementAdviceQueryset.as_manager()

    def save(self, *args, **kwargs):
        if self.actions:
            for action in self.actions:
                if not action['label']:
                    raise ValidationError('Must provide action label')
        super(RetirementAdvice, self).save(*args, **kwargs)

    def __str__(self):
        return "{} Advice {}".format(self.plan, self.id)


def determine_accounts(plan):
    """
    Generates a list of (account_type, max_contribution)
    in order of contribution priority where the account
    to put max contributions in first is first.
    """
    # get max contribution for each account
    account_type_contributions = {at[0]: 0 for at in constants.ACCOUNT_TYPES}
    if plan.max_employer_match_percent:
        if plan.max_employer_match_percent > 0:
            match = True
        else:
            match = False
    else:
        match = False

    transcript_data = plan.client.regional_data.get('tax_transcript_data', None)
    if transcript_data and isinstance(transcript_data, dict):
        status = transcript_data.get('FILING STATUS', None)
        if not status:
            logger.warn("Client for plan: {} has no filing status available. Assuming single".format(plan.id))
        if status == 'Married Filing Joint':
            joint = True
        else:
            joint = False
    else:
        joint = False

    if plan.client.employment_status == constants.EMPLOYMENT_STATUS_EMMPLOYED:
        has_401k = True
    else:
        has_401k = False

    if plan.client.date_of_birth < (datetime.now().date() - relativedelta(years=50)):
        # total including employer is 53k
        max_contributions_pre_tax = 18000
    else:
        # total including employer is 56k
        max_contributions_pre_tax = 24000

    roth_first = False

    if plan.client.employment_status == constants.EMPLOYMENT_STATUS_SELF_EMPLOYED:
        # self employed
        if plan.income >= 27500:
            # sep ira pre tax up to 53000
            account_type_contributions[constants.ACCOUNT_TYPE_IRA] += 53000
        else:
            # roth ira post tax up to 5,500/6,600
            account_type_contributions[constants.ACCOUNT_TYPE_ROTHIRA] += 6600

    elif plan.client.employment_status == constants.EMPLOYMENT_STATUS_UNEMPLOYED:
        # unemployed
        # income or dependent on spouse?
        if plan.income > 0 or joint:
            #  If over 131k single/193k joint
            # pre-tax trad IRA up to 5,500/6,600
            account_type_contributions[constants.ACCOUNT_TYPE_IRA] += 6600
        else:
            # Roth IRA up to 5,500/6,600
            account_type_contributions[constants.ACCOUNT_TYPE_ROTHIRA] += 6600

    else:
        # employed
        if has_401k:
            if match:
                # contribute to 401k up to 18/24k limit
                account_type_contributions[constants.ACCOUNT_TYPE_401K] += 24000

                if (plan.income >= 131000 and not joint) or (plan.income >= 193000 and joint):
                    # over 131k single / 193k joint
                    # contribute remainder to trad IRA up to 5.5/6.5 limit
                    account_type_contributions[constants.ACCOUNT_TYPE_IRA] += 24000
                else:
                    # under 131k single / 193k joint
                    # contribute remainder to roth IRA up to 5.5/6.5 limit
                    account_type_contributions[constants.ACCOUNT_TYPE_ROTHIRA] += 6500
            else:
                if (plan.income >= 131000 and not joint) or (plan.income >= 193000 and joint):
                    # over 131k single / 193k joint
                    # contribute to 401k up to 18/24k limit
                    account_type_contributions[constants.ACCOUNT_TYPE_401K] += 24000
                    # contribute remainder to trad IRA up to 5.5/6.5 limit
                    account_type_contributions[constants.ACCOUNT_TYPE_IRA] += 6500
                else:
                    # under 131k single / 193k joint
                    # contribute to roth IRA up to 5.5/6.5 limit
                    roth_first = True
                    account_type_contributions[constants.ACCOUNT_TYPE_ROTHIRA] += 6500
                    # contribute remainder to 401k up to 18/24k limit
                    account_type_contributions[constants.ACCOUNT_TYPE_ROTH401K] += 24000
        else:
            if (plan.income >= 131000 and not joint) or (plan.income >= 193000 and joint):
                # over 131k single / 193k joint
                # contribute to trad IRA up to 5.5/6.5 limit
                account_type_contributions[constants.ACCOUNT_TYPE_IRA] += 6500
            else:
                # under 131k single / 193k joint
                # contribute to roth IRA up to 5.5/6.5 limit
                account_type_contributions[constants.ACCOUNT_TYPE_ROTHIRA] += 6500

    sorted_contribs = sorted(account_type_contributions, key=account_type_contributions.get, reverse=True)
    rv = [(ac, min(account_type_contributions[ac], max_contributions_pre_tax)) for ac in sorted_contribs]
    if roth_first:
        tmp = rv[1]
        tmp2 = rv[0]
        rv[0] = tmp
        rv[1] = tmp2
    return rv


class RetirementProjection(models.Model):
    plan = models.OneToOneField(RetirementPlan, null=True, on_delete=models.CASCADE, related_name='projection')

    proj_data = JSONField(null=True, blank=True, help_text="Calculated Projection data for api response")
    on_track = models.BooleanField(default=False, null=False, help_text="Whether the retirement plan is on track")
    #user
    income_actual_monthly = JSONField(null=True, blank=True, help_text="List of monthly actual income")
    income_desired_monthly = JSONField(null=True, blank=True, help_text="List of monthly desired income")
    taxable_assets_monthly = JSONField(null=True, blank=True, help_text="List of monthly taxable assets")
    nontaxable_assets_monthly = JSONField(null=True, blank=True, help_text="List of monthly nontaxable assets")
    proj_balance_at_retire_in_todays = models.FloatField(default=0, null=True, help_text="Projected balance at retirement in today's money")
    proj_inc_actual_at_retire_in_todays = models.FloatField(default=0, null=True, help_text="Projected monthly income actual at retirement in today's money")
    proj_inc_desired_at_retire_in_todays = models.FloatField(default=0, null=True, help_text="Projected monthly income desired at retirement in today's money")
    savings_end_date_as_age = models.FloatField(default=0, null=True, help_text="Projected age post retirement when taxable assets first deplete to zero")
    current_percent_soc_sec = models.FloatField(default=0, null=True, help_text="Current percentage of monthly income represented by payments made towards social security")
    current_percent_medicare = models.FloatField(default=0, null=True, help_text="Current percentage of monthly income represented by payments made towards medicare")
    current_percent_fed_tax = models.FloatField(default=0, null=True, help_text="Current percentage of monthly income represented by payments made towards federal taxes")
    current_percent_state_tax = models.FloatField(default=0, null=True, help_text="Current percentage of monthly income represented by payments made towards state taxes")
    non_taxable_inc = JSONField(null=True, blank=True, help_text="List of annual non taxable monthly income received")
    tot_taxable_dist = JSONField(null=True, blank=True, help_text="List of annual total taxable distributions received")
    annuity_payments = JSONField(null=True, blank=True, help_text="List of ammual annuity payments received")
    pension_payments = JSONField(null=True, blank=True, help_text="List of annual pension payments received")
    ret_working_inc = JSONField(null=True, blank=True, help_text="List of annual retirement working payments received")
    soc_sec_benefit = JSONField(null=True, blank=True, help_text="List of annual social security benefit payments received")
    taxable_accounts = JSONField(null=True, blank=True, help_text="List of annual taxable accounts")
    non_taxable_accounts = JSONField(null=True, blank=True, help_text="List of annual nontaxable accounts")
    list_of_account_balances = JSONField(null=True, blank=True, help_text="List of annual accounts")
    reverse_mort = models.BooleanField(default=False, null=False, help_text="Whether user has a reverse mortgage")
    house_value = models.FloatField(default=0, null=True, help_text="Current value of house")
    house_value_at_retire_in_todays = models.FloatField(default=0, null=True, help_text="Future value of house in todays")
    reverse_mort_pymnt_at_retire_in_todays = models.FloatField(default=0, null=True, help_text="Future value of monthly reverse mortgage payment in todays")

    #partner
    part_income_actual_monthly = JSONField(null=True, blank=True, help_text="List of monthly actual income")
    part_income_desired_monthly = JSONField(null=True, blank=True, help_text="List of monthly desired income")
    part_taxable_assets_monthly = JSONField(null=True, blank=True, help_text="List of monthly taxable assets")
    part_nontaxable_assets_monthly = JSONField(null=True, blank=True, help_text="List of monthly nontaxable assets")
    part_proj_balance_at_retire_in_todays = models.FloatField(default=0, null=True, help_text="Projected balance at retirement in today's money")
    part_proj_inc_actual_at_retire_in_todays = models.FloatField(default=0, null=True, help_text="Projected monthly income actual at retirement in today's money")
    part_proj_inc_desired_at_retire_in_todays = models.FloatField(default=0, null=True, help_text="Projected monthly income desired at retirement in today's money")
    part_savings_end_date_as_age = models.FloatField(default=0, null=True, help_text="Projected age post retirement when taxable assets first deplete to zero")
    part_current_percent_soc_sec = models.FloatField(default=0, null=True, help_text="Current percentage of monthly income represented by payments made towards social security")
    part_current_percent_medicare = models.FloatField(default=0, null=True, help_text="Current percentage of monthly income represented by payments made towards medicare")
    part_current_percent_fed_tax = models.FloatField(default=0, null=True, help_text="Current percentage of monthly income represented by payments made towards federal taxes")
    part_current_percent_state_tax = models.FloatField(default=0, null=True, help_text="Current percentage of monthly income represented by payments made towards state taxes")
    part_non_taxable_inc = JSONField(null=True, blank=True, help_text="List of annual non taxable monthly income received")
    part_tot_taxable_dist = JSONField(null=True, blank=True, help_text="List of annual total taxable distributions received")
    part_annuity_payments = JSONField(null=True, blank=True, help_text="List of annual annuity payments received")
    part_pension_payments = JSONField(null=True, blank=True, help_text="List of annual pension payments received")
    part_ret_working_inc = JSONField(null=True, blank=True, help_text="List of annual retirement working payments received")
    part_soc_sec_benefit = JSONField(null=True, blank=True, help_text="List of annual social security benefit payments received")
    part_taxable_accounts = JSONField(null=True, blank=True, help_text="List of annual taxable accounts")
    part_non_taxable_accounts = JSONField(null=True, blank=True, help_text="List of annual nontaxable accounts")
    part_list_of_account_balances = JSONField(null=True, blank=True, help_text="List of annual accounts")
    part_house_value = models.FloatField(default=0, null=True, help_text="Current value of house")
    part_house_value_at_retire_in_todays = models.FloatField(default=0, null=True, help_text="Future value of house in todays")
    part_reverse_mort_pymnt_at_retire_in_todays = models.FloatField(default=0, null=True, help_text="Future value of monthly reverse mortgage payment in todays")

    def save(self, *args, **kwargs):
        super(RetirementProjection, self).save(*args, **kwargs)

    def __str__(self):
        return "{} Projection {}".format(self.plan, self.id)
