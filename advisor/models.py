from django.db import models
from django.db.models.deletion import PROTECT
from django.db.models.query_utils import Q
from django.conf import settings
from django.utils.functional import cached_property
from django.utils.timezone import now
from phonenumber_field.modelfields import PhoneNumberField
from datetime import datetime

from firm.models import Firm, PricingPlanPersonBase
from goal.models import Goal, Transaction
from main import constants
from main.abstract import NeedApprobation, NeedConfirmation, PersonalData
from main.finance import mod_dietz_rate
from portfolios.models import PortfolioSet
from user.models import User
import logging
import uuid


logger = logging.getLogger('advisor.models')


class Advisor(NeedApprobation, NeedConfirmation, PersonalData):
    user = models.OneToOneField(User, related_name="advisor")
    token = models.CharField(max_length=36, null=True, editable=False)
    firm = models.ForeignKey(Firm, related_name="advisors")
    letter_of_authority = models.FileField()
    work_phone_num = PhoneNumberField(null=True, max_length=30)
    betasmartz_agreement = models.BooleanField()
    last_action = models.DateTimeField(null=True)
    default_portfolio_set = models.ForeignKey(PortfolioSet)

    @property
    def dashboard_url(self):
        return "/advisor/summary"

    @property
    def clients(self):
        return self.all_clients.filter(user__prepopulated=False)

    @property
    def firm_colored_logo(self):
        return self.firm.knocked_out_logo

    def get_invite_url(self, invitation_type=None, email=None):
        try:
            user = User.objects.get(email=email, prepopulated=True)
        except User.DoesNotExist:
            user = None

        email_invite = self.invites.filter(email=email).first()
        invitation_url = settings.SITE_URL + "/client/onboarding/" + email_invite.invite_key

        # resending invitation
        if user:
            try:
                invitation_url += "/" + str(user.pk) + "/" + user.client.primary_accounts.first().token
            except ObjectDoesNotExist:
                # client does not exist for this user
                pass
        return invitation_url

    @staticmethod
    def get_inviter_type():
        return "advisor"

    @property
    def households(self):
        all_households = (list(self.primary_account_groups.all()) +
                          list(self.secondary_account_groups.all()))
        active_households = []
        for h in all_households:
            if list(h.accounts.all()):
                active_households.append(h)

        return active_households

    @property
    def client_accounts(self):
        accounts = []
        for household in self.households:
            all_accounts = household.accounts.all()
            accounts.extend(all_accounts)
        return set(accounts)

    @property
    def total_balance(self):
        """
        This means total assets under management (AUM)
        :return:
        """
        from client.models import ClientAccount

        accounts = ClientAccount.objects.filter(primary_owner__advisor=self)

        return sum(acc.total_balance for acc in accounts)

    @property
    def primary_clients_size(self):
        return self.all_clients.filter(user__prepopulated=False).count()

    @property
    def secondary_clients_size(self):
        return (self.secondary_clients.filter(user__prepopulated=False)
                .distinct().count())

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
            for ca in ClientAccount.objects.filter(primary_owner__advisor=self):
                for goal in ca.goals:
                    txs = Transaction.objects.filter(Q(to_goal=goal) | Q(from_goal=goal),
                                                     status=Transaction.STATUS_EXECUTED,
                                                     reason=Transaction.REASON_FEE,
                                                     executed__gte=fiscal_year.begin_date,
                                                     executed__lte=datetime.today())
                    for tx in txs:
                        total_fees += tx.amount
        return total_fees

    @property
    def total_fees(self):
        """
        """
        from client.models import ClientAccount
        total_fees = 0.0
        for ca in ClientAccount.objects.filter(primary_owner__advisor=self):
            for year in self.firm.fiscal_years.all():
                for goal in ca.goals:
                    txs = Transaction.objects.filter(Q(to_goal=goal) | Q(from_goal=goal),
                                                     status=Transaction.STATUS_EXECUTED,
                                                     reason=Transaction.REASON_FEE,
                                                     executed__gte=year.begin_date,
                                                     executed__lte=year.end_date)
                    for tx in txs:
                        total_fees += tx.amount
        return total_fees

    @property
    def average_return(self):
        goals = Goal.objects.filter(account__in=self.client_accounts)
        return mod_dietz_rate(goals)

    @property
    def total_account_groups(self):
        return len(self.households)

    @property
    def average_group_balance(self):
        return self.total_balance / self.total_account_groups if self.total_account_groups > 0 else 0

    @property
    def average_client_balance(self):
        balances = [client.total_balance for client in self.clients]
        return sum(balances) / len(balances) if balances else 0

    def get_inviter_name(self):
        return self.user.get_full_name()

    def save(self, *args, **kw):
        send_confirmation_mail = False
        if self.pk is None:
            # generate token for advisor on first save
            self.token = str(uuid.uuid4())

        if self.pk is not None:
            orig = Advisor.objects.get(pk=self.pk)
            if (orig.is_accepted != self.is_accepted) and (
                        self.is_accepted is True):
                send_confirmation_mail = True

        super(Advisor, self).save(*args, **kw)
        if send_confirmation_mail and (self.confirmation_key is not None):
            self.user.email_user(
                "BetaSmartz advisor account confirmation",
                "You advisor account have been approved, "
                "please confirm your email here: "
                "{site_url}/advisor/confirm_email/{confirmation_key}/"
                " \n\n\n  The BetaSmartz Team".format(
                    confirmation_key=self.confirmation_key,
                    site_url=settings.SITE_URL))


class AccountGroup(models.Model):
    """
    We use the term 'Households' on the Advisor page for this as well.
    """

    advisor = models.ForeignKey(
        Advisor, related_name="primary_account_groups",
        # Must reassign account groups before removing advisor
        on_delete=PROTECT
    )
    secondary_advisors = models.ManyToManyField(
        Advisor,
        related_name='secondary_account_groups'
    )
    name = models.CharField(max_length=100)

    @property
    def accounts(self):
        return self.accounts_all.filter(
            confirmed=True,
            primary_owner__user__prepopulated=False
        )

    @property
    def total_balance(self):
        return sum(a.total_balance for a in self.accounts.all())

    @property
    def average_return(self):
        goals = Goal.objects.filter(account__in=self.accounts.all())
        return mod_dietz_rate(goals)

    @property
    def allocation(self):
        return 0

    @property
    def stock_balance(self):
        return sum(a.stock_balance for a in self.accounts.all())

    @property
    def core_balance(self):
        return sum(a.core_balance for a in self.accounts.all())

    @property
    def satellite_balance(self):
        return sum(a.satellite_balance for a in self.accounts.all())

    @property
    def bond_balance(self):
        return sum(a.bond_balance for a in self.accounts.all())

    @property
    def stocks_percentage(self):
        if self.total_balance == 0:
            return 0
        percentage = self.stock_balance / self.total_balance * 100
        return "{0}".format(int(round(percentage)))

    @property
    def bonds_percentage(self):
        if self.total_balance == 0:
            return 0
        percentage = self.bond_balance / self.total_balance * 100
        return "{0}".format(int(round(percentage)))

    @property
    def core_percentage(self):
        if self.total_balance == 0:
            return 0
        percentage = self.core_balance / self.total_balance * 100
        return "{0}".format(int(round(percentage)))

    @property
    def satellite_percentage(self):
        if self.total_balance == 0:
            return 0
        percentage = self.satellite_balance / self.total_balance * 100
        return "{0}".format(int(round(percentage)))

    @cached_property
    def on_track(self):
        """
            If any of the advisors' client accounts are
            off track, return False.  If all client
            accounts are on track, return True.
        """
        for account in self.accounts.all():
            if not account.on_track:
                return False
        return True

    @cached_property
    def pending_settings_approval(self):
        for account in self.accounts.all():
            for goal in account.goals:
                if goal.is_pending:
                    return True
        return False

    @property
    def since(self):
        min_created_at = self.accounts.first().created_at

        for account in self.accounts.all():
            if min_created_at > account.created_at:
                min_created_at = account.created_at

        return min_created_at

    def __str__(self):
        return self.name


class ChangeDealerGroup(models.Model):
    advisor = models.ForeignKey(Advisor)
    old_firm = models.ForeignKey('firm.Firm', related_name="old_advisors")
    new_firm = models.ForeignKey('firm.Firm', related_name="new_advisors")
    approved = models.BooleanField(default=False)
    create_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    work_phone = PhoneNumberField()
    new_email = models.EmailField()
    letter_previous_group = models.FileField(verbose_name="Prev. Group Letter")
    letter_new_group = models.FileField("New Group Letter")
    signature = models.FileField()

    def approve(self):
        self.approved = True
        self.advisor.firm = self.new_firm
        self.advisor.user.email = self.new_email
        self.advisor.work_phone_num = self.work_phone
        """
        self.advisor.office_address_line_1 = self.office_address_line_1
        self.advisor.office_address_line_2 = self.office_address_line_2
        self.advisor.office_state = self.office_state
        self.advisor.office_city = self.office_city
        self.advisor.office_post_code = self.office_post_code
        self.advisor.postal_address_line_1 = self.postal_address_line_1
        self.advisor.postal_address_line_2 = self.postal_address_line_2
        self.advisor.postal_state = self.postal_state
        self.advisor.same_address = self.same_address
        self.advisor.postal_city = self.postal_city
        self.advisor.postal_post_code = self.postal_post_code
        self.advisor.daytime_phone_number = self.daytime_phone_number
        self.advisor.mobile_phone_number = self.mobile_phone_number
        self.advisor.fax_number = self.fax_number
        self.advisor.alternate_email_address = self.advisor.alternate_email_address
        """
        self.advisor.save()
        self.approved_at = now()
        self.save()


class SingleInvestorTransfer(models.Model):
    from_advisor = models.ForeignKey(Advisor)
    to_advisor = models.ForeignKey(Advisor, verbose_name="To Advisor",
                                   related_name="single_transfer_to_advisors")
    approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True)
    create_at = models.DateTimeField(auto_now_add=True)
    investor = models.ForeignKey('client.Client')
    firm = models.ForeignKey('firm.Firm', editable=False)
    signatures = models.FileField()

    def __str__(self):
        return "Transfer {} to {}".format(self.investor, self.to_advisor)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):

        if self.pk is None:
            self.firm = self.from_advisor.firm

        return super(SingleInvestorTransfer, self).save(
            force_insert, force_update, using, update_fields
        )

    def approve(self):
        self.investor.advisor = self.to_advisor
        self.investor.save()
        for account in self.investor.accounts.all():
            account.remove_from_group()
            account.save()
        self.approved = True
        self.approved_at = now()
        self.save()


class BulkInvestorTransfer(models.Model):
    from_advisor = models.ForeignKey(Advisor)
    to_advisor = models.ForeignKey(Advisor, verbose_name="To Advisor", related_name="bulk_transfer_to_advisors")
    approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True)
    firm = models.ForeignKey('firm.Firm', editable=False)
    create_at = models.DateTimeField(auto_now_add=True)
    investors = models.ManyToManyField('client.Client')
    signatures = models.FileField()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):

        if self.pk is None:
            self.firm = self.from_advisor.firm

        return super(BulkInvestorTransfer, self).save(force_insert=False,
                                                      force_update=False, using=None, update_fields=None)

    def approve(self):
        for investor in self.investors.all():
            investor.advisor = self.to_advisor
            investor.save()
            for account in investor.accounts.all():
                account.remove_from_group()
                account.save()

        self.approved = True
        self.approved_at = now()
        self.save()


class PricingPlanAdvisor(PricingPlanPersonBase):
    parent = models.ForeignKey('firm.PricingPlan',
                               related_name='advisor_overrides')
    person = models.OneToOneField('advisor.Advisor',
                                   related_name='pricing_plan')
