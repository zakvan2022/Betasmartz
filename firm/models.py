# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.mail import send_mail
from django.core.validators import MinValueValidator, ValidationError
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.timezone import now
from phonenumber_field.modelfields import PhoneNumberField
from datetime import datetime
import uuid
from address.models import Address
from common.slug import unique_slugify
from main.abstract import NeedApprobation, NeedConfirmation, PersonalData
from main import constants
from multi_sites.models import AccountType, FiscalYear
from portfolios.models import PortfolioSet
from user.models import User
from jsonfield.fields import JSONField


class Firm(models.Model):
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255,
                                 null=True,
                                 blank=True)
    dealer_group_number = models.CharField(max_length=50,
                                           null=True,
                                           blank=True)
    slug = models.CharField(max_length=100, editable=False, unique=True)
    logo = models.ImageField(verbose_name="White logo",
                             null=True,
                             blank=True)
    knocked_out_logo = models.ImageField(verbose_name="Colored logo",
                                         null=True,
                                         blank=True)
    report_logo = models.ImageField(verbose_name="Report logo",
                                    null=True,
                                    blank=True)

    mini_logo = models.ImageField(verbose_name="Mini logo",
                                  null=True,
                                  blank=True)
    
    client_agreement_url = models.FileField(
        verbose_name="Client Agreement (PDF)",
        null=True,
        blank=True)
    form_adv_part2 = models.FileField(verbose_name="Form Adv",
                                      null=True,
                                      blank=True)
    token = models.CharField(max_length=36, editable=False)
    fee = models.PositiveIntegerField(default=0)
    can_use_ethical_portfolio = models.BooleanField(default=True)
    default_portfolio_set = models.ForeignKey(PortfolioSet)
    fiscal_years = models.ManyToManyField(FiscalYear)
    account_types = models.ManyToManyField(AccountType, help_text="The set of supported account "
                                                                  "types offered to clients of this firm.")

    @property
    def report_logo_safe(self):
        return self.report_logo or self.knocked_out_logo

    @property
    def mini_logo_safe(self):
        return self.mini_logo or self.knocked_out_logo

    def save(self,
             force_insert=False,
             force_update=False,
             using=None,
             update_fields=None):

        if self.pk is None:
            self.token = str(uuid.uuid4())

        # reset slug with name changes
        if self.pk is not None:
            orig = Firm.objects.get(pk=self.pk)
            if orig.name != self.name:
                self.slug = None

        if not self.slug:
            unique_slugify(self, self.name, slug_field_name="slug")
        else:
            unique_slugify(self, self.slug, slug_field_name="slug")

        super(Firm, self).save(force_insert, force_update, using,
                               update_fields)

    def get_current_fiscal_year(self):
        """
        Returns the FiscalYear object for the current year
        """
        current_date = datetime.today().date()
        for year in self.fiscal_years.all():
            if year.begin_date < current_date < year.end_date:
                return year
        return None

    @property
    def white_logo(self):

        if self.logo is None:
            return static('images/white_logo.png')
        elif not self.logo.name:
            return static('images/white_logo.png')

        return self.logo.url

    @property
    def colored_logo(self):

        if self.knocked_out_logo is None:
            return static('images/colored_logo.png')
        elif not self.knocked_out_logo.name:
            return static('images/colored_logo.png')

        return self.knocked_out_logo.url

    @property
    def fees_ytd(self):
        """
        Sum fees from Transaction model:
            Transaction - REASON_FEE
        YTD - from the start of the current fiscal year until now.
        """
        # filter transactions by the firm's current fiscal year
        total_fees_ytd = 0
        for advisor in self.advisors.all():
            total_fees_ytd += advisor.fees_ytd
        return total_fees_ytd

    @property
    def total_fees(self):
        """
        Sum fees from Transaction model:
            Transaction - REASON_FEE
        Within the firm's set fiscal years.
        """
        total = 0
        for advisor in self.advisors.all():
            total += advisor.total_fees
        return total

    @property
    def total_revenue(self):
        total = 0
        for advisor in self.advisors.all():
            total += advisor.total_revenue
        return total

    @property
    def total_invested(self):
        total = 0
        for advisor in self.advisors.all():
            total += advisor.total_invested
        return total

    @property
    def total_return(self):
        if self.total_invested > 0:
            return self.total_revenue / self.total_invested
        return 0

    @property
    def total_balance(self):
        total = 0
        for advisor in self.advisors.all():
            total += advisor.total_balance
        return total

    def get_clients(self):
        clients = []
        for advisor in self.advisors.all():
            clients.extend(advisor.clients.all())
        return clients

    @property
    def total_clients(self):
        return len(self.get_clients())

    @property
    def average_client_balance(self):
        return self.total_balance / self.total_clients if self.total_clients > 0 else 0

    @property
    def total_account_groups(self):
        total = 0
        for advisor in self.advisors.all():
            total += advisor.total_account_groups
        return total

    @property
    def average_group_balance(self):
        return self.total_balance / self.total_account_groups if self.total_account_groups > 0 else 0

    @property
    def content_type(self):
        return ContentType.objects.get_for_model(self).pk

    @property
    def supervisor_invite_url(self):
        if self.token is None:
            return None
        return settings.SITE_URL + "/" + self.token + "/supervisor_signup"

    @property
    def advisor_invite_url(self):
        if self.token is None:
            return None
        return settings.SITE_URL + "/" + self.token + "/advisor_signup"

    @staticmethod
    def get_inviter_type():
        return "firm"

    def get_inviter_name(self):
        return self.name

    def get_invite_url(self, application_type, email):
        if application_type == constants.INVITATION_ADVISOR:
            return self.advisor_invite_url
        if application_type == constants.INVITATION_SUPERVISOR:
            return self.supervisor_invite_url

    @property
    def config(self):
        if not hasattr(self, 'firm_config'):
            firm_config = FirmConfig(firm=self)
            firm_config.save()
            self.firm_config = firm_config
        return self.firm_config

    @property
    def details(self):
        if not hasattr(self, 'firm_details'):
            return None
        return self.firm_details

    def __str__(self):
        return self.name


class FirmData(models.Model):
    class Meta:
        verbose_name = "Firm detail"

    firm = models.OneToOneField(Firm, related_name='firm_details')
    afsl_asic = models.CharField("AFSL/ASIC number", max_length=50,
                                 null=True, blank=True)
    afsl_asic_document = models.FileField("AFSL/ASIC doc.",
                                          null=True, blank=True)
    office_address = models.ForeignKey(Address, related_name='+',
                                       null=True, blank=True)
    postal_address = models.ForeignKey(Address, related_name='+')

    daytime_phone_num = PhoneNumberField(max_length=30)  # A firm MUST have some number to contact them by.
    mobile_phone_num = PhoneNumberField(max_length=30, null=True, blank=True)  # A firm may not have a mobile number as well.
    fax_num = PhoneNumberField(max_length=16, null=True, blank=True)  # Not all businesses have a fax.

    alternate_email_address = models.EmailField("Email address",
                                                null=True,
                                                blank=True)
    last_change = models.DateField(auto_now=True)
    fee_bank_account_name = models.CharField('Name', max_length=100,
                                             null=True, blank=True)
    fee_bank_account_branch_name = models.CharField('Branch name',
                                                    max_length=100,
                                                    null=True, blank=True)
    fee_bank_account_bsb_number = models.CharField('BSB number',
                                                   max_length=20,
                                                   null=True, blank=True)
    fee_bank_account_number = models.CharField('Account number',
                                               max_length=20,
                                               null=True, blank=True)
    fee_bank_account_holder_name = models.CharField('Account holder',
                                                    max_length=100,
                                                    null=True, blank=True)
    australian_business_number = models.CharField("ABN", max_length=20,
                                                  null=True, blank=True)

    site_url = models.CharField(max_length=255,
                                null=True,
                                blank=True,
                                default="https://www.betasmartz.com",
                                help_text="Official Site URL")

    advisor_support_phone = models.CharField(verbose_name='Advisor Support Phone',
                                            max_length=255, null=True, blank=True)

    advisor_support_email = models.EmailField(verbose_name='Advisor Support Email',
                                              null=True, blank=True)

    advisor_support_workhours = models.TextField(verbose_name='Advisor Support Workhours',
                                                 null=True, blank=True)

    client_support_phone = models.CharField(verbose_name='Client Support Phone',
                                            max_length=255, null=True, blank=True)

    client_support_email = models.EmailField(verbose_name='Client Support Email',
                                             null=True, blank=True)

    client_support_workhours = models.TextField(verbose_name='Client Support Workhours',
                                             null=True, blank=True)

    def __str__(self):
        return "FirmData for {}".format(self.firm)


class FirmConfig(models.Model):
    class Meta:
        verbose_name = "Firm Configuration"

    firm = models.OneToOneField(Firm, related_name='firm_config')

    retiresmartz_enabled = models.BooleanField(default=True,
                                               help_text='Enables RetireSmartz feature')

    soc_rsp_invest_enabled = models.BooleanField(default=True, verbose_name='Socially Responsible Investment field enabled',
                                                 help_text='Enables or disables Socially Responsible Investment field in Goal')

    risk_score_unlimited = models.BooleanField(default=False, verbose_name='Unlimited Risk score',
                                               help_text='Allows to set risk score value higher than recommended risk value')

    constraints_enabled = models.BooleanField(default=True, verbose_name='Constraints Enabled',
                                              help_text='Enables or disables constraints on Client Allocation page')

    rebalance_enabled = models.BooleanField(default=True, verbose_name='Rebalancing Enabled',
                                            help_text='Enables or disables Rebalancing settings on Client Allocation page')

    def __str__(self):
        return "FirmSetting for {}".format(self.firm)


class PricingPlanBase(models.Model):
    bps = models.FloatField(default=0., validators=[MinValueValidator(0)])
    fixed = models.FloatField(default=0., validators=[MinValueValidator(0)])

    class Meta:
        abstract = True

    @property
    def total_bps(self) -> float:
        raise NotImplementedError()

    @property
    def total_fixed(self) -> float:
        raise NotImplementedError()


class PricingPlan(PricingPlanBase):
    firm = models.OneToOneField('firm.Firm',
                                related_name='pricing_plan')
    system_bps = models.FloatField(default=0., validators=[MinValueValidator(0)])
    system_fixed = models.FloatField(default=0., validators=[MinValueValidator(0)])

    def __str__(self):
        return str(self.firm)

    @property
    def system_fee(self) -> (float, float):
        return self.system_bps, self.system_fixed

    @system_fee.setter
    def system_fee(self, value):
        self.system_bps, self.system_fixed = value

    @property
    def total_bps(self) -> float:
        return self.bps + self.system_bps

    @property
    def total_fixed(self) -> float:
        return self.fixed + self.system_fixed


class PricingPlanPersonBase(PricingPlanBase):
    class Meta:
        abstract = True

    @property
    def total_bps(self) -> float:
        return self.bps + self.parent.system_bps

    @property
    def total_fixed(self) -> float:
        return self.fixed + self.parent.system_fixed


class AuthorisedRepresentative(NeedApprobation, NeedConfirmation, PersonalData):
    user = models.OneToOneField(User, related_name='authorised_representative')
    firm = models.ForeignKey(Firm, related_name='authorised_representatives')
    letter_of_authority = models.FileField()
    betasmartz_agreement = models.BooleanField()


class Supervisor(models.Model):
    user = models.OneToOneField(User, related_name="supervisor")
    firm = models.ForeignKey(Firm, related_name="supervisors")
    # has full authorization to make action in name of advisor and clients
    can_write = models.BooleanField(
        default=False,
        verbose_name="Has Full Access?",
        help_text="A supervisor with 'full access' can perform actions for "
                  "their advisors and clients.")

    def __str__(self):
        return "Supervisor {} for {}".format(self.user, self.firm)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):

        is_new_instance = False

        if self.pk is None:
            is_new_instance = True

        ret = super(Supervisor, self).save(force_insert, force_update, using, update_fields)

        if is_new_instance:
            self.send_confirmation_email()

        return ret

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def name(self):
        return self.user.first_name + " " + self.user.last_name

    @property
    def email(self):
        return self.user.email

    def send_confirmation_email(self):
        account_type = self._meta.verbose_name

        subject = "BetaSmartz new {0} account confirmation".format(account_type)

        context = {
            'site': Site.objects.get_current(),
            'subject': subject,
            'account_type': account_type,
            'firm': self.firm
        }

        send_mail(
            subject,
            '',
            None,
            [self.user.email],
            html_message=render_to_string('email/new_supervisor.html', context))


def generate_token():
    secret = str(uuid.uuid4()) + str(uuid.uuid4())
    return secret.replace('-', '')[:64]


class FirmEmailInvite(models.Model):
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

    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = PhoneNumberField(max_length=30, blank=True, null=True)
    user = models.OneToOneField('user.User', related_name='firm_invitation',
                                null=True, blank=True)
    firm_agreement_url = models.FileField(null=True, blank=True)

    invite_key = models.CharField(max_length=64,
                                  default=generate_token,
                                  unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    last_sent_at = models.DateTimeField(blank=True, null=True)
    send_count = models.PositiveIntegerField(default=0)

    status = models.PositiveIntegerField(choices=STATUSES,
                                         default=STATUS_CREATED)

    onboarding_data = JSONField(null=True, blank=True)

    def __str__(self):
        return '{} {} {} ({})'.format(self.first_name, self.middle_name[:1],
                                      self.last_name, self.email)

    @property
    def firm_onboarding_url(self):
        return settings.SITE_URL + "/client/firm-onboarding/" + self.invite_key

    def save(self, *args, **kwargs):
        if self.status == FirmEmailInvite.STATUS_ACCEPTED:
            # clear sensitive information from onboarding_data,
            # that information has been used by AuthorisedRepresentativeUserRegistration
            # if FirmEmailInvite.STATUS_ACCEPTED
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
        super(FirmEmailInvite, self).save(*args, **kwargs)

    @property
    def can_resend(self):
        return self.status in [self.STATUS_CREATED, self.STATUS_SENT, self.STATUS_ACCEPTED]

    def send(self):
        if not self.can_resend:
            raise ValidationError('Can be resent only if status is '
                                  'CREATED or SENT')

        site = Site.objects.get_current()
        subject = "Welcome to {}".format(site.name)

        context = {
            'site': site,
            'invite_url': self.firm_onboarding_url,
            'category': 'Firm onboarding'
        }

        html_message = render_to_string('email/firm/invitation_sent.html', context)
        send_mail(subject, '', None, [self.email], html_message=html_message)
        self.last_sent_at = now()
        if self.status != self.STATUS_ACCEPTED and self.status != self.STATUS_COMPLETE:
            self.status = self.STATUS_SENT
        self.send_count += 1

        self.save(update_fields=['last_sent_at', 'send_count', 'status'])


# --------------------------------- Signals -----------------------------------


@receiver(models.signals.post_save, sender=Firm)
def create_firm_empty_pricing_plan(sender, instance, created, **kwargs):
    if created:
        PricingPlan.objects.create(firm=instance)
