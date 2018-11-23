from __future__ import unicode_literals

from .models import ChangeDealerGroup, SingleInvestorTransfer, BulkInvestorTransfer
from brokers.models import IBAccountFeed
from client.models import Client, EmailInvite, IBOnboard
from django import forms
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import QueryDict
from django.utils.safestring import mark_safe
from advisor.models import Advisor
from common.helpers import Section
from firm.models import Firm
from main.constants import CLIENT_ACCESS_LEVEL_CHOICES, CLIENT_FULL_ACCESS, CLIENT_READONLY_ACCESS, CLIENT_NO_ACCESS
from goal.models import Goal
from user.models import User
from uuid import uuid4

######################################################################
# Common forms
######################################################################

class GoalPortfolioForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ('portfolio_set',)

    def save(self, *args, **kwargs):
        goal = self.instance
        portfolio_set = self.cleaned_data.get('portfolio_set')
        goal.update_portfolio_set(portfolio_set)
        return goal


GoalPortfolioFormSet = forms.modelformset_factory(Goal, form=GoalPortfolioForm)

######################################################################
# Clients forms
######################################################################

class EmailInviteForm(forms.ModelForm):
    required_css_class = 'required'

    REASONS_RS_DISABLED = (
        (EmailInvite.REASON_PERSONAL_INVESTING, 'Personal Investing'),
    )

    class Meta:
        model = EmailInvite
        fields = 'first_name', 'middle_name', 'last_name', 'email', 'reason', \
                 'salutation', 'suffix', 'access_level', 'ib_account_number', \
                 'risk_score'

    def __init__(self, *args, **kwargs):
        retiresmartz_enabled = True
        if 'retiresmartz_enabled' in kwargs:
            retiresmartz_enabled = kwargs.pop('retiresmartz_enabled')
        super(EmailInviteForm, self).__init__(*args, **kwargs)
        self.fields['email'].required = False
        if not retiresmartz_enabled:
            self.fields['reason'] = forms.ChoiceField(choices=EmailInviteForm.REASONS_RS_DISABLED)

    def clean_email(self):
        email = self.cleaned_data['email']
        access_level = int(self.data['access_level'])

        if access_level == CLIENT_NO_ACCESS:
            # Email field is disabled in the UI, thus assigns a unique email that might be changed by IB activity feeding later.
            email = 'client-{}@betasmartz.com'.format(uuid4())
            return email

        if not email:
            raise forms.ValidationError(
                u'Email is required',
                params={'email': email},
            )
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                u'Email "%(email)s" is already in use',
                params={'email': email},
            )
        if EmailInvite.objects.filter(email=email).exists():
            raise forms.ValidationError(
                u'Invitation has already been sent to "%(email)s"',
                params={'email': email},
            )
        return email

    def clean_ib_account_number(self):
        ib_account_number = self.cleaned_data['ib_account_number']
        if ib_account_number:
            if IBAccountFeed.objects.filter(account_id=ib_account_number).count() == 0:
                raise forms.ValidationError('IB account number is not available')

            if IBOnboard.objects.filter(account_number=ib_account_number).count() > 0:
                raise forms.ValidationError('Another client already exists with this IB account number')

        return ib_account_number


class ClientAccessForm(forms.ModelForm):
    access_level = forms.ChoiceField(choices=CLIENT_ACCESS_LEVEL_CHOICES)

    class Meta:
        model = Client
        fields = ('access_level',)

    def __init__(self, *args, **kwargs):
        super(ClientAccessForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            instance = kwargs['instance']
            if instance.is_confirmed:
                if instance.readonly_access:
                    access_level = CLIENT_READONLY_ACCESS
                else:
                    access_level = CLIENT_FULL_ACCESS
            else:
                access_level = CLIENT_NO_ACCESS
            self.fields['access_level'].initial = access_level

    def save(self, *args, **kwargs):
        client = super(ClientAccessForm, self).save(commit=False, *args, **kwargs)
        access_level = int(self.cleaned_data.get('access_level'))
        if access_level == CLIENT_FULL_ACCESS:
            client.readonly_access = False
            client.is_confirmed = True
        elif access_level == CLIENT_READONLY_ACCESS:
            client.readonly_access = True
            client.is_confirmed = True
        elif access_level == CLIENT_NO_ACCESS:
            client.readonly_access = True
            client.is_confirmed = False
        client.save(update_fields=['readonly_access', 'is_confirmed'])
        return client

USER_DETAILS = ('first_name', 'middle_name', 'last_name', 'email')

UNSET_ADDRESS_ID = '__XX_UNSET_XX__'


class PrepopulatedUserForm(forms.ModelForm):
    advisor = None
    account_class = ""

    def define_advisor(self, advisor):
        self.advisor = advisor

    def add_account_class(self, account_class):
        self.account_class = account_class

    class Meta:
        model = User
        fields = USER_DETAILS

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.instance = User(password="KONfLOP212=?hlokifksi21f6s1",
                             prepopulated=True,
                             **self.cleaned_data)
        self.instance.save()
        # create client instance
        defs = {
            'address': 'Default Unset Address',
            'region': Region.objects.get_or_create(country='AU', name='New South Wales')[0]
        }
        # TODO: Change this so we only create a client once all the info is complete from external onboarding.
        # TODO: Until then, they're just a user.
        new_client = Client(
            advisor=self.advisor,
            user=self.instance,
            client_agreement=self.advisor.firm.client_agreement_url,
            residential_address=Address.objects.get_or_create(global_id=UNSET_ADDRESS_ID, defaults=defs)[0]
        )
        new_client.save()
        personal_account = new_client.accounts_all.all()[0]
        personal_account.account_class = self.account_class
        personal_account.save()
        return self.instance


PERSONAL_DETAILS = ('date_of_birth', "month", "day", "year", "gender", "phone_num", "residential_address")


class BuildPersonalDetailsForm(forms.ModelForm):
    month = forms.CharField(required=False, max_length=150)
    day = forms.CharField(required=False, max_length=150)
    year = forms.CharField(required=False, max_length=150)

    class Meta:
        model = Client
        fields = PERSONAL_DETAILS

    def __init__(self, *args, **kwargs):
        # first call parent's constructor
        super(BuildPersonalDetailsForm, self).__init__(*args, **kwargs)
        # there's a `fields` property now
        for k, field in self.fields.items():
            field.required = False
        if self.instance and self.instance.date_of_birth:
            self.fields["month"].initial = self.instance.date_of_birth.month
            self.fields["year"].initial = self.instance.date_of_birth.year
            self.fields["day"].initial = self.instance.date_of_birth.day

    def clean(self):
        cleaned_data = super(BuildPersonalDetailsForm, self).clean()
        year = cleaned_data.get("year", "")
        month = cleaned_data.get("month", "")
        day = cleaned_data.get("day", "")

        if "" not in (day, month, year):

            try:
                date_b = "{year}-{month}-{day}".format(year=year,
                                                       month=month,
                                                       day=day)

                date_b = datetime.strptime(date_b, "%Y-%m-%d")
                cleaned_data["date_of_birth"] = date_b
            except ValueError:
                date_b = None
                self._errors['date_of_birth'] = mark_safe(
                    u'<ul class="errorlist"><li>Invalid Date</li></ul>')

            if date_b:
                cleaned_data["date_of_birth"] = date_b
                date_diff = now().year - date_b.year
                if date_diff < 18:
                    self._errors['date_of_birth'] = \
                        mark_safe(u'<ul class="errorlist"><li>Client under 18 </li></ul>')

        return cleaned_data


FINANCIAL_DETAILS = ('employment_status', 'occupation', 'employer', 'income',
                     'regional_data')


class BuildFinancialDetailsForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = FINANCIAL_DETAILS

    def __init__(self, *args, **kwargs):
        # first call parent's constructor
        super(BuildFinancialDetailsForm, self).__init__(*args, **kwargs)
        # there's a `fields` property now
        for k, field in self.fields.items():
            field.required = False


######################################################################
# Composites forms
######################################################################

class AdvisorCompositeForm:
    def get_context_data(self, **kwargs):
        ctx = super(AdvisorCompositeForm, self).get_context_data(**kwargs)
        client_id = self.request.GET.get('client_id', None)

        if client_id:

            try:
                ctx["client_id"] = int(client_id)
            except ValueError:
                return ctx

            try:
                ctx["selected_client"] = Client.objects.get(
                    advisor=self.advisor,
                    pk=ctx["client_id"])
            except ObjectDoesNotExist:
                pass

            ctx["accounts"] = ctx["selected_client"].accounts

        if self.object:
            ctx["object"] = self.object
            if "accounts" in ctx:
                ctx["accounts"] = ctx["accounts"] \
                    .exclude(pk__in=list(map(lambda obj: obj.pk, self.object.accounts.all())))
        ctx["name"] = self.request.GET.get("name", "")
        return ctx

    def form_valid(self, form):
        response = super(AdvisorCompositeForm, self).form_valid(form)

        if self.account_list:
            for account in self.account_list:
                account.add_to_account_group(self.object)

        return response

    def get_success_url(self):
        if self.object:
            return reverse('advisor:composites:edit', kwargs={'pk': self.object.pk})
        else:
            return reverse('advisor:composites:create')

    def get_queryset(self):
        return super(AdvisorCompositeForm, self).get_queryset().filter(
            advisor=self.advisor)


######################################################################
# Support forms
######################################################################

class ChangeDealerGroupForm(forms.ModelForm):
    clients = forms.ModelMultipleChoiceField(required=False, widget=forms.SelectMultiple(attrs={"disabled": True}),
                                             queryset=None)

    class Meta:
        model = ChangeDealerGroup
        fields = ("advisor", "old_firm", "new_firm", "work_phone", "new_email", "letter_new_group",
                  "letter_previous_group", "signature", "clients")

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')
        if "data" in kwargs:
            q = QueryDict('', mutable=True)
            q.update(kwargs["data"])
            initial = dict()
            initial["advisor"] = str(kwargs["initial"]["advisor"].pk)
            initial["old_firm"] = str(kwargs["initial"]["old_firm"].pk)
            q.update(initial)
            kwargs["data"] = q
        super(ChangeDealerGroupForm, self).__init__(*args, **kwargs)

        self.field_sections = [{"fields": ('new_firm', 'work_phone', 'new_email'),
                                "header": "New arrangements"},
                               {"fields": ('clients',),
                                "header": "Your current investors"},
                               {"fields": ('letter_previous_group',),
                                "header": "Previous Dealer Group Release Authorization",
                                "detail": mark_safe("A letter from your previous Dealer Group authorising the release "
                                                    "of your current investors. A template of this letter has been supplied, "
                                                    "This letter must be provided on the previous Dealer Group's "
                                                    "company letterhead. <a target='_blank' href='{}'>Example</a>".format(
                                                        static('docs/previous_dealer_group_release_authorization.pdf')))},
                               {"fields": ('letter_new_group',),
                                "header": "New Dealer Group Acceptance Authorization",
                                "detail": mark_safe("A letter from the new Dealer Group accepting the transfer of your "
                                                    "current investors. A template of this letter has been supplied. This letter"
                                                    "must be provided on the new Dealer Group's company letterhead. "
                                                    "<a target='_blank' href='{}'>Example</a>".format(
                                                        static('docs/new_dealer_group_acceptance_authorization.pdf')))},
                               {"fields": ('signature',),
                                "header": "Advisor Signature",
                                "detail": mark_safe(
                                    "Please upload a signature approval by an Authorised Signatory of the new Dealer Group. "
                                    "<a target='_blank' href='{}'>Example</a>".format(
                                        static('docs/advisor_signature_change_dealer_group.pdf')))},
                               ]
        self.fields["new_firm"].queryset = Firm.objects.exclude(pk=self.initial["old_firm"].pk)
        self.fields["clients"].queryset = self.initial["advisor"].clients

    def clean_new_email(self):
        email = self.cleaned_data["new_email"]
        if User.objects.exclude(pk=self.initial["advisor"].user.pk).filter(email=email).count():
            self._errors['new_email'] = "User with this email already exists"

        return email

    @property
    def sections(self):
        for section in self.field_sections:
            yield Section(section, self)


class SingleInvestorTransferForm(forms.ModelForm):
    class Meta:
        model = SingleInvestorTransfer
        fields = ("from_advisor", "to_advisor", "investor", "signatures",)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')
        if "data" in kwargs:
            q = QueryDict('', mutable=True)
            q.update(kwargs["data"])
            initial = dict()
            initial["from_advisor"] = str(kwargs["initial"]["from_advisor"].pk)
            q.update(initial)
            kwargs["data"] = q

        super(SingleInvestorTransferForm, self).__init__(*args, **kwargs)

        self.field_sections = [{"fields": ('to_advisor',),
                                "header": "To Advisor"},
                               {"fields": ('investor',),
                                "header": "Client"},
                               {"fields": ('signatures',),
                                "header": "Signatures",
                                "detail": mark_safe("Signature of existing advisor or authorised firm representative. "
                                                    "<a target='_blank' href='{}'>Example</a>".format(
                                                        static('docs/account_transfer_between_advisors_in_the_same_firm.pdf')))},
                               ]

        self.fields["investor"].queryset = self.initial["from_advisor"].clients
        self.fields["to_advisor"].queryset = Advisor.objects.filter(firm=self.initial["from_advisor"].firm)

    @property
    def sections(self):
        for section in self.field_sections:
            yield Section(section, self)


class BulkInvestorTransferForm(forms.ModelForm):
    class Meta:
        model = BulkInvestorTransfer
        fields = ("from_advisor", "to_advisor", "investors", "signatures",)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')
        if "data" in kwargs:
            q = QueryDict('', mutable=True)
            q.update(kwargs["data"])
            initial = dict()
            initial["from_advisor"] = str(kwargs["initial"]["from_advisor"].pk)
            q.update(initial)
            kwargs["data"] = q

        super(BulkInvestorTransferForm, self).__init__(*args, **kwargs)

        self.field_sections = [{"fields": ('to_advisor',),
                                "header": "To Advisor"},
                               {"fields": ('investors',),
                                "detail": "You can select 2 or more investors for transfer",
                                "header": "Investors"},
                               {"fields": ('signatures',),
                                "header": "Signatures",
                                "detail": mark_safe("Signature of existing advisor or authorised firm representative. "
                                                    "<a target='_blank' href='{}'>Example</a>".format(
                                                        static('docs/account_transfer_between_advisors_in_the_same_firm.pdf')))},
                               ]

        self.fields["investors"].queryset = self.initial["from_advisor"].clients
        self.fields["to_advisor"].queryset = Advisor.objects.filter(firm=self.initial["from_advisor"].firm)

    def clean_investors(self):
        investors = self.cleaned_data["investors"]
        if len(investors) < 2:
            self._errors["investors"] = "Please select 2 or more investors"
        return investors

    @property
    def sections(self):
        for section in self.field_sections:
            yield Section(section, self)

