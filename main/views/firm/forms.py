import json

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse_lazy
from django.db.models import Q
from django.forms import inlineformset_factory
from django.forms.models import BaseModelFormSet
from django.http import Http404
from django.shortcuts import HttpResponseRedirect, get_object_or_404, \
    render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.functional import curry
from django.utils.timezone import now
from django.views.generic import CreateView, TemplateView, View
from django.views.generic.edit import ProcessFormView

from main.constants import AUTHORIZED_REPRESENTATIVE, INVITATION_ADVISOR, \
    INVITATION_SUPERVISOR, INVITATION_TYPE_DICT, PERSONAL_DATA_FIELDS, \
    SUCCESS_MESSAGE, EMPLOYMENT_STATUS_EMMPLOYED, EMPLOYMENT_STATUS_SELF_EMPLOYED
from ...forms import EmailInvitationForm
from ..base import AdminView, LegalView
from address.constants import COUNTRY_CHOICES
from address.models import Address
from advisor.models import Advisor, PricingPlanAdvisor
from brokers.interactive_brokers.onboarding.constants import IB_SALUTATION_CHOICES, IB_SUFFIX_CHOICES
from client.models import Client, IBOnboard, JointAccountConfirmationModel, PricingPlanClient
from common.helpers import Section
from firm.models import Firm, AuthorisedRepresentative, FirmData, PricingPlan
from goal.models import Goal, Transaction
from main import constants
from main.forms import BetaSmartzGenericUserSignupForm, PERSONAL_DATA_WIDGETS
from main.optimal_goal_portfolio import solve_shares_re_balance
from notifications.models import Notify
from portfolios.models import AssetClass, Commentary, Platform, Ticker, LivePortfolio, \
    LivePortfolioItem, PortfolioSet, PortfolioProvider
from scheduler.models import Schedule
from scheduler.constants import SCHEDULE_DELIVERY_CYCLE_CHOICES, SCHEDULE_WEEKDAY_CHOICES, \
    SCHEDULE_HOUR_CHOICES, SCHEDULE_TIMEZONE_CHOICES
from user.models import User, EmailInvitation

__all__ = ["InviteLegalView", "AuthorisedRepresentativeSignUp", 'FirmDataView',
           "EmailConfirmationView", 'Confirmation',
           'AdminInviteSupervisorView', 'AdminInviteAdvisorView',
           "GoalRebalance", "confirm_joint_account"]


class AuthorisedRepresentativeProfileForm(forms.ModelForm):
    user = forms.CharField(required=False)

    class Meta:
        model = AuthorisedRepresentative
        fields = PERSONAL_DATA_FIELDS + ('letter_of_authority', 'betasmartz_agreement', 'firm', 'user')

        widgets = PERSONAL_DATA_WIDGETS


class AuthorisedRepresentativeUserForm(BetaSmartzGenericUserSignupForm):
    user_profile_type = "authorised_representative"

    class Meta:
        model = User
        fields = ('email', 'first_name', 'middle_name', 'last_name', 'password', 'confirm_password')

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')
        super(AuthorisedRepresentativeUserForm, self).__init__(*args, **kwargs)
        profile_kwargs = kwargs.copy()
        if 'instance' in kwargs:
            self.profile = getattr(kwargs['instance'], self.user_profile_type, None)
            profile_kwargs['instance'] = self.profile
        self.profile_form = AuthorisedRepresentativeProfileForm(*args, **profile_kwargs)
        self.fields.update(self.profile_form.fields)
        self.initial.update(self.profile_form.initial)

        self.field_sections = [{"fields": ('first_name', 'middle_name', 'last_name', 'email', 'password',
                                           'confirm_password', 'date_of_birth', 'gender', 'phone_num'),
                                "header": "Information to establish your account"},
                               {"fields": ('letter_of_authority',),
                                "header": "Authorization",
                                "detail": "BetaSmartz requires a Letter of Authority (PDF) from the new Dealer Group"
                                          " which authorises you to act on their behalf. This letter must"
                                          " be provided by the Dealer Group on Dealer Group company letterhead."}
                               ]

    def save(self, *args, **kw):
        user = super(AuthorisedRepresentativeUserForm, self).save(*args, **kw)
        self.profile = self.profile_form.save(commit=False)
        self.profile.user = user
        self.profile.save()
        self.profile.send_confirmation_email()
        return user

    @property
    def sections(self):
        for section in self.field_sections:
            yield Section(section, self)


class AuthorisedRepresentativeSignUp(CreateView):
    template_name = "registration/firm_form.html"
    form_class = AuthorisedRepresentativeUserForm
    success_url = reverse_lazy('login')

    def __init__(self, *args, **kwargs):
        self.firm = None
        super(AuthorisedRepresentativeSignUp, self).__init__(*args, **kwargs)

    def get_success_url(self):
        messages.info(self.request, SUCCESS_MESSAGE)
        return super(AuthorisedRepresentativeSignUp, self).get_success_url()

    def dispatch(self, request, *args, **kwargs):
        token = kwargs["token"]

        try:
            firm = Firm.objects.get(token=token)
        except ObjectDoesNotExist:
            raise Http404()

        self.firm = firm
        response = super(AuthorisedRepresentativeSignUp, self).dispatch(request, *args, **kwargs)

        if hasattr(response, 'context_data'):
            response.context_data["firm"] = self.firm
            response.context_data["sign_up_type"] = "legal representative account"
        return response


class InviteLegalView(CreateView, AdminView):
    form_class = EmailInvitationForm
    template_name = 'admin/betasmartz/legal_invite.html'

    def get_success_url(self):
        messages.info(self.request, "Invite sent successfully!")
        return self.request.get_full_path()

    def dispatch(self, request, *args, **kwargs):
        response = super(InviteLegalView, self).dispatch(request, *args, **kwargs)
        if hasattr(response, 'context_data'):
            firm = Firm.objects.get(pk=kwargs["pk"])
            response.context_data["firm"] = firm
            invitation_type = AUTHORIZED_REPRESENTATIVE
            response.context_data["invitation_type"] = invitation_type
            response.context_data["invite_url"] = firm.get_invite_url(invitation_type)
            response.context_data["invite_type"] = INVITATION_TYPE_DICT[str(invitation_type)].title()
            response.context_data["next"] = request.GET.get("next", None)
            response.context_data["invites"] = EmailInvitation.objects.filter(invitation_type=invitation_type,
                                                                              inviter_id=firm.pk,
                                                                              inviter_type=firm.content_type,
                                                                              )
        return response


class AdminInviteAdvisorView(CreateView, AdminView):
    form_class = EmailInvitationForm
    template_name = 'admin/betasmartz/legal_invite.html'

    def get_success_url(self):
        messages.info(self.request, "Invite sent successfully!")
        return self.request.get_full_path()

    def dispatch(self, request, *args, **kwargs):
        response = super(AdminInviteAdvisorView, self).dispatch(request, *args, **kwargs)
        if hasattr(response, 'context_data'):
            firm = Firm.objects.get(pk=kwargs["pk"])
            invitation_type = INVITATION_ADVISOR
            response.context_data["firm"] = firm
            response.context_data["invitation_type"] = invitation_type
            response.context_data["invite_type"] = INVITATION_TYPE_DICT[str(invitation_type)].title()
            response.context_data["invite_url"] = firm.get_invite_url(invitation_type)
            response.context_data["next"] = request.GET.get("next", None)
            response.context_data["invites"] = EmailInvitation.objects.filter(invitation_type=invitation_type,
                                                                              inviter_id=firm.pk,
                                                                              inviter_type=firm.content_type,
                                                                              )
        return response


class AdminInviteSupervisorView(CreateView, AdminView):
    form_class = EmailInvitationForm
    template_name = 'admin/betasmartz/legal_invite.html'

    def get_success_url(self):
        messages.info(self.request, "Invite sent successfully!")
        return self.request.get_full_path()

    def dispatch(self, request, *args, **kwargs):
        response = super(AdminInviteSupervisorView, self).dispatch(request, *args, **kwargs)
        if hasattr(response, 'context_data'):
            firm = Firm.objects.get(pk=kwargs["pk"])
            invitation_type = INVITATION_SUPERVISOR
            response.context_data["firm"] = firm
            response.context_data["invitation_type"] = invitation_type
            response.context_data["invite_type"] = INVITATION_TYPE_DICT[str(invitation_type)].title()
            response.context_data["next"] = request.GET.get("next", None)
            response.context_data["invite_url"] = firm.get_invite_url(invitation_type)
            response.context_data["invites"] = EmailInvitation.objects.filter(invitation_type=invitation_type,
                                                                              inviter_id=firm.pk,
                                                                              inviter_type=firm.content_type,
                                                                              )

        return response


class FirmDataForm(forms.ModelForm):
    class Meta:
        model = FirmData
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')
        super(FirmDataForm, self).__init__(*args, **kwargs)

        self.field_sections = [{"fields": ('afsl_asic', 'afsl_asic_document'),
                                "header": "Dealer Group Details",
                                "detail": "Please provide the advisor’s AFSL Number/ASIC Authorised "
                                          "Representative Number and attach a copy of AFSL."},
                               {"fields": ('daytime_phone_num',
                                           'mobile_phone_num', 'fax_num', 'alternate_email_address'),
                                "header": "Dealer contact details"},
                               {"fields": ('fee_bank_account_name', 'fee_bank_account_branch_name',
                                           'fee_bank_account_bsb_number', 'fee_bank_account_number',
                                           'fee_bank_account_holder_name'),
                                "header": "Bank  account for fee payments",
                                "detail": "Fees will be paid into the following account Name of financial institution"},
                               {"fields": ('australian_business_number',),
                                "header": " Taxation details",
                                "detail": "Please provide the Australian Business Number (ABN) "
                                          "of the Licensee. Fees cannot be paid if an ABN is not supplied."},
                               {"fields": (),
                                "header": "Investor transfer",
                                "detail": "If investors are to be transferred to the new dealer group please"
                                          "complete a Bulk Investor Transfer form or Single Investor Transfer form"
                                          " available from betasmartz.com"},

                               ]

    def clean(self):
        cleaned_data = super(FirmDataForm, self).clean()
        self._validate_unique = False
        self.cleaned_data = cleaned_data

    def save(self, *args, **kw):
        try:
            self.instance = FirmData.objects.get(firm=self.cleaned_data.get('firm'))
        except ObjectDoesNotExist:
            pass
        return super(FirmDataForm, self).save(*args, **kw)

    @property
    def sections(self):
        for section in self.field_sections:
            yield Section(section, self)


class FirmDataView(CreateView, LegalView):
    form_class = FirmDataForm
    template_name = 'registration/firm_details_form.html'
    success_url = reverse_lazy('support-forms')

    def get_object(self):
        if hasattr(self.firm, 'firm_details'):
            return self.firm.firm_details
        else:
            return None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return ProcessFormView.get(self, request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return ProcessFormView.post(self, request, *args, **kwargs)

    def form_valid(self, form):
        try:
            details = self.firm.firm_details
        except ObjectDoesNotExist:
            details = None
        Notify.SUBMIT_FORM.send(
            actor=self.request.user,
            target=self.firm,
            action_object=details
        )
        return super(FirmDataView, self).form_valid(form)


class EmailConfirmationView(View):
    def get(self, request, *args, **kwargs):

        token = kwargs.get("token")
        _type = kwargs.get("type")

        try:
            object_class = ContentType.objects.get(pk=_type).model_class()
        except ObjectDoesNotExist:
            raise Http404("Page not found")

        try:
            db_object = object_class.objects.get(confirmation_key=token)
        except ObjectDoesNotExist:
            db_object = None

        if db_object is None:
            messages.error(request, "Bad confirmation code")
        else:
            if db_object.is_confirmed:
                messages.error(request, "{0} already confirmed".format(object_class.__name__))
            else:
                messages.info(request, "You email have been confirmed, you can login in")
                db_object.is_confirmed = True

            db_object.confirmation_key = None
            db_object.save()

        return HttpResponseRedirect(reverse_lazy('login'))


class Confirmation(TemplateView):
    # TODO: add a real django form instead of "homebrewed" stuff
    template_name = 'registration/confirmation.html'

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        account_types = ('advisor', 'authorised_representative', 'supervisor', 'client')

        try:
            user = User.objects.get(email=email)
        except ObjectDoesNotExist:
            messages.error(request, "Account not found")
            return HttpResponseRedirect(reverse_lazy('login'))

        confirmations = 0

        for _type in account_types:
            if hasattr(user, _type):
                profile = getattr(user, _type)
                if profile.is_confirmed:
                    pass
                else:
                    profile.send_confirmation_email()
                    confirmations += 1

        if not confirmations:
            messages.error(request, "Account already confirmed")
            return HttpResponseRedirect(reverse_lazy('login'))

        messages.info(request, "The new confirmation email has been sent")
        return HttpResponseRedirect(reverse_lazy('login'))


class GoalRebalance(TemplateView, AdminView):
    template_name = 'admin/betasmartz/transaction-form-2.html'
    goal = None
    transaction = None

    def get_context_data(self, **kwargs):
        portfolio_set = Platform.objects.first().portfolio_set
        ctx = super(GoalRebalance, self).get_context_data(**kwargs)
        ctx["transaction"] = serializers.serialize('json', [self.transaction])
        ctx["amount"] = self.transaction.amount
        ctx["account"] = json.loads(serializers.serialize('json', [self.transaction.account]))[0]["fields"]
        ctx["account"]["owner_full_name"] = self.transaction.account.account.primary_owner.user.get_full_name()
        ctx["account"][
            "advisor_full_name"] = self.transaction.account.account.primary_owner.advisor.user.get_full_name()
        ctx["account"]["firm_name"] = self.transaction.account.account.primary_owner.advisor.firm.name
        ctx["account"]["fee"] = self.transaction.account.account.fee

        ctx["tickers"] = Ticker.objects.filter(asset_class__in=portfolio_set.asset_classes.all())

        goal = self.transaction.account
        target_allocation_dict = goal.target_allocation

        tickers_pk = []
        tickers_prices = []
        target_allocation = []
        current_shares = []
        result_dict = {}
        current_shares_dict = {}
        price_dict = {}
        result_a = []
        target_allocation_dict_2 = {}

        for ticker in ctx["tickers"]:
            tickers_pk.append(ticker.pk)
            tickers_prices.append(ticker.unit_price)
            target_allocation.append(target_allocation_dict.get(ticker.asset_class.name, 0))
            positions = Position.objects.filter(goal=self.transaction.account, ticker=ticker).all()
            cs = 0
            if positions:
                for p in positions:
                    cs += p.share
            current_shares.append(cs)
        if self.transaction.status == Transaction.STATUS_PENDING:

            if self.transaction.type == TRANSACTION_TYPE_ALLOCATION:
                result_a = solve_shares_re_balance(current_shares, tickers_prices, target_allocation)
                ctx["amount"] = 1
                ctx["account"]["fee"] = sum(abs(result_a * tickers_prices)) * ctx["account"]["fee"]

        for i in range(len(result_a)):
            result_dict[str(tickers_pk[i])] = result_a[i]
            current_shares_dict[str(tickers_pk[i])] = current_shares[i]
            price_dict[str(tickers_pk[i])] = tickers_prices[i]
            target_allocation_dict_2[str(tickers_pk[i])] = target_allocation[i]

        ctx["price_dict"] = price_dict
        ctx["target_allocation_dict"] = target_allocation_dict_2
        ctx["current_shares_dict"] = current_shares_dict
        ctx["result_dict"] = result_dict
        ctx["account"] = json.dumps(ctx["account"])
        ctx["tickers"] = serializers.serialize('json', ctx["tickers"])
        ctx["is_executed"] = self.transaction.status == Transaction.STATUS_EXECUTED
        return ctx

    def dispatch(self, request, *args, **kwargs):
        self.goal = get_object_or_404(Goal, pk=kwargs["pk"])
        self.transaction = Transaction(account=self.goal,
                                       amount=self.goal.allocation,
                                       type=TRANSACTION_TYPE_ALLOCATION,
                                       status=Transaction.STATUS_PENDING,
                                       created=now().today())
        response = super(GoalRebalance, self).dispatch(request, *args, **kwargs)
        return response

    def post(self, request, *args, **kwargs):
        data = json.loads(request.POST.get("data"))
        positions = []
        new_amount = 0
        old_amount = 0
        new_shares = []
        old_shares = []

        for pk, v in data.items():
            if v != 0:
                ticker = Ticker.objects.get(pk=pk)
                new_p = Position(ticker=ticker, goal=self.transaction.account, share=v)
                positions.append(new_p)
                new_amount += new_p.value
                new_shares.append(new_p.value)

        for old_p in self.transaction.account.positions.all():
            old_amount += old_p.value
            old_shares.append(old_p.value)

        amount = abs(new_amount - old_amount)
        # delete old positions
        self.transaction.account.positions.all().delete()
        # save new
        # mark transaction as executed
        self.transaction.executed = now()

        self.transaction.type = Transaction.REASON_REBALANCE
        self.transaction.status = Transaction.STATUS_EXECUTED

        list(map(lambda x: x.save(), positions))
        self.transaction.save()
        self.goal.drift = self.goal.get_drift
        self.goal.save()

        return HttpResponseRedirect('/admin/main/goal')


def confirm_joint_account(request, token):
    try:
        jacm = JointAccountConfirmationModel.objects.get(
            token=token,
            date_confirmed__isnull=True,
        )
    except JointAccountConfirmationModel.DoesNotExist:
        return render_to_response('firm/confirm-joint-account.html', {
            'error': True,
        }, status=403)

    jacm.date_confirmed = now()
    jacm.save(update_fields=['date_confirmed'])

    account = jacm.account
    account.confirmed = True
    account.save(update_fields=['confirmed'])

    sender = jacm.primary_owner
    cosignee = jacm.cosignee

    def send(user, path, **context):
        render = curry(render_to_string,
                       context=(RequestContext(request, context)))
        user.email_user(
            subject=render('%s/subject.txt' % path).strip(),
            message=render('%s/message.txt' % path),
            html_message=render('%s/message.html' % path),
            from_email=settings.DEFAULT_FROM_EMAIL,
        )

    base_path = 'email/client/joint-confirmed'

    # notify primary owner account confirmed
    send(sender.user, '%s/%s' % (base_path, 'client'), confirmation=jacm)

    # notify advisor(s) account confirmed
    context = {
        'site': get_current_site(self.request),
        'confirmation': jacm,
        'advisor': sender.advisor,
        'client': sender,
        'firm': sender.advisor.firm
    }
    advisor_path = '%s/%s' % (base_path, 'advisor')
    send(sender.advisor.user, advisor_path, **context)
    if sender.advisor != cosignee.advisor:
        sender.secondary_advisors.add(cosignee.advisor)
        sender.save(update_fields=['secondary_advisors'])
        cosignee.secondary_advisors.add(sender.advisor)
        cosignee.save(update_fields=['secondary_advisors'])

        send(cosignee.advisor.user, advisor_path, **context)

    return render_to_response('firm/confirm-joint-account.html', {
        'confirmation': jacm,
    })


class PricingPlanForm(forms.ModelForm):
    bps = forms.FloatField(required=False, min_value=0)
    fixed = forms.FloatField(required=False, min_value=0)

    class Meta:
        model = PricingPlan
        fields = 'bps', 'fixed'


class PricingPlanAdvisorForm(forms.ModelForm):
    bps = forms.FloatField(required=False, min_value=0)
    fixed = forms.FloatField(required=False, min_value=0)

    class Meta:
        model = PricingPlanAdvisor
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('initial', {'bps': '', 'fixed': ''})
        super(PricingPlanAdvisorForm, self).__init__(*args, **kwargs)
        pass


class PricingPlanClientForm(forms.ModelForm):
    bps = forms.FloatField(required=False, min_value=0)
    fixed = forms.FloatField(required=False, min_value=0)

    class Meta:
        model = PricingPlanClient
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('initial', {'bps': '', 'fixed': ''})
        super(PricingPlanClientForm, self).__init__(*args, **kwargs)
        pass


class PricingPlanBaseFormset(BaseModelFormSet):
    def set_firm(self, value):
        for form in self.forms:
            person_field = form.fields['person']
            q = Q(pricing_plan__isnull=True)
            if form.instance.id:
                q |= Q(pk=form.instance.person.id)
            person_field.queryset = person_field.queryset.filter(
                q,
                **self._get_firm_kwargs(value),
            )
    firm = property(None, set_firm)

    def _get_firm_kwargs(self, firm):
        raise NotImplementedError()


class PricingPlanBaseAdvisorFormset(PricingPlanBaseFormset):
    def _get_firm_kwargs(self, firm):
        return {
            'firm': firm,
        }


class PricingPlanBaseClientFormset(PricingPlanBaseFormset):
    def _get_firm_kwargs(self, firm):
        return {
            'advisor__firm': firm,
        }


PricingPlanAdvisorFormset = forms.modelformset_factory(
    model=PricingPlanAdvisor,
    form=PricingPlanAdvisorForm,
    formset=PricingPlanBaseAdvisorFormset,
    can_delete=True,
)
PricingPlanClientFormset = forms.modelformset_factory(
    model=PricingPlanClient,
    form=PricingPlanClientForm,
    formset=PricingPlanBaseClientFormset,
    can_delete=True,
)


class AddressHelper():
    def update_address(self, address, prefix):
        if address is None:
            address = Address()
        address.update_address(
            address1=self.cleaned_data[prefix + 'address1'],
            address2=self.cleaned_data[prefix + 'address2'],
            city=self.cleaned_data[prefix + 'city'],
            post_code=self.cleaned_data[prefix + 'post_code'],
            state_code=self.cleaned_data[prefix + 'state'],
            country=self.cleaned_data[prefix + 'country']
        )
        return address


class FirmClientApplicationFormBase(forms.ModelForm):
    required_css_class = 'required'

    first_name = forms.CharField(label='First Name')
    middle_name = forms.CharField(label='Middle Name', required=False)
    last_name = forms.CharField(label='Last Name')
    email = forms.CharField(label='Email')

    advisor = forms.ModelChoiceField(queryset=Advisor.objects.all())
    address1 = forms.CharField(label='Address 1')
    address2 = forms.CharField(label='Address 2', required=False)
    city = forms.CharField(label='City')
    post_code = forms.CharField(label='Zip code', max_length=16, required=False)
    state = forms.CharField(label='State', max_length=128)
    country = forms.ChoiceField(label='Country', choices=COUNTRY_CHOICES)

    ssn = forms.CharField(label='Social Security Number', required=False)

    salutation = forms.CharField(label='Salutation', max_length=10, widget=forms.Select(choices=IB_SALUTATION_CHOICES))
    suffix = forms.CharField(label='Suffix', max_length=10, widget=forms.Select(choices=IB_SUFFIX_CHOICES), required=False)

    def __init__(self, *args, **kwargs):
        self.firm = kwargs.pop('firm')
        super(FirmClientApplicationFormBase, self).__init__(*args, **kwargs)
        self.fields['advisor'].queryset = Advisor.objects.filter(firm=self.firm)
        self.fields['advisor'].initial = self.instance.advisor if self.instance.pk else None

    class Meta:
        model = Client
        fields = ['first_name', 'middle_name', 'last_name', 'email', # User model
                  'address1', 'address2', 'city', 'post_code',  'state', 'country', # Address fields
                  'advisor', 'gender', 'civil_status', 'phone_num', 'date_of_birth', 'politically_exposed', # Client model
                  'employer_type', 'employer', 'employment_status', 'income', 'other_income', 'industry_sector', 'occupation', # Client model - employement
                  'ssn', # Client regional_data
                  'student_loan', 'student_loan_assistance_program', 'student_loan_graduate_looking', # Misc Client model
                  'student_loan_parent_looking', 'hsa_eligible', 'hsa_provider_name', 'hsa_state', 'hsa_coverage_type', # Misc Client model
                  'salutation', 'suffix',]  # IBOnboard


class FirmApplicationClientCreateForm(FirmClientApplicationFormBase, AddressHelper):
    class Meta:
        model = Client
        fields = ['first_name', 'middle_name', 'last_name', 'email', 'advisor', # User model
                  'address1', 'address2', 'city', 'post_code',  'state', 'country', # Address fields
                  'gender', 'civil_status', 'phone_num', 'date_of_birth', 'politically_exposed', # Client model
                  'employer_type', 'employer', 'employment_status', 'income', 'other_income', 'industry_sector', 'occupation', # Client model - employement
                  'ssn', # Client regional_data
                  'student_loan', 'student_loan_assistance_program', 'student_loan_graduate_looking', # Misc Client model
                  'student_loan_parent_looking', 'hsa_eligible', 'hsa_provider_name', 'hsa_state', 'hsa_coverage_type', # Misc Client model
                  'salutation', 'suffix',]  # IBOnboard

    def clean_email(self):
        if User.objects.filter(email=self.cleaned_data['email']).count() > 0:
            raise forms.ValidationError("Email already exists")
        return self.cleaned_data['email']

    def clean(self):
        cleaned_data = super(FirmApplicationClientCreateForm, self).clean()
        # employed_statuses = [EMPLOYMENT_STATUS_EMMPLOYED, EMPLOYMENT_STATUS_SELF_EMPLOYED]
        # print(cleaned_data['income'])
        # if cleaned_data['employment_status'] in employed_statuses and cleaned_data['income'] is None:
        #     raise forms.ValidationError("Income field is required")
        if cleaned_data['country'] != 'US':
            del cleaned_data['ssn']
        return cleaned_data

    def save(self, commit=True, *args, **kwargs):
        user = User.objects.create(
            first_name = self.cleaned_data['first_name'],
            middle_name = self.cleaned_data['middle_name'],
            last_name = self.cleaned_data['last_name'],
            email = self.cleaned_data['email'],
        )

        client = super(FirmApplicationClientCreateForm, self).save(commit=False, *args, **kwargs)
        client.user = user

        regional_data = client.regional_data
        if self.cleaned_data['country'] == 'US':
            regional_data['ssn'] = self.cleaned_data['ssn']
        else:
            if 'ssn' in regional_data:
                del regional_data['ssn']
            if 'tax_transcript' in regional_data:
                del regional_data['tax_transcript']
            if 'tax_transcript_data' in regional_data:
                del regional_data['tax_transcript_data']
            if 'tax_transcript_data_ex' in regional_data:
                del regional_data['tax_transcript_data_ex']
            if 'social_security_statement' in regional_data:
                del regional_data['social_security_statement']
            if 'social_security_statement_data' in regional_data:
                del regional_data['social_security_statement_data']
            if 'partner_social_security_statement' in regional_data:
                del regional_data['partner_social_security_statement']
            if 'partner_social_security_statement_data' in regional_data:
                del regional_data['partner_social_security_statement_data']

        client.regional_data = regional_data
        client.residential_address = self.update_address(None, '')

        if commit:
            client.save()

        return client


class FirmApplicationClientForm(FirmClientApplicationFormBase, AddressHelper):
    tax_transcript = forms.FileField(label='Tax Transcript', required=False)
    social_security_statement = forms.FileField(label='Social Security Statement', required=False)
    additional_document = forms.FileField(required=False)

    email_to_client = forms.BooleanField(label='Client', required=False)
    email_to_advisor = forms.BooleanField(label='Advisor', required=False)

    class Meta:
        model = Client
        fields = ['first_name', 'middle_name', 'last_name', 'email', # User model
                  'tax_transcript', 'social_security_statement', # Invitation model
                  'address1', 'address2', 'city', 'post_code',  'state', 'country', # Address fields
                  'gender', 'civil_status', 'phone_num', 'date_of_birth', 'politically_exposed', # Client model
                  'employer_type', 'employer', 'employment_status', 'income', 'other_income', 'industry_sector', 'occupation', # Client model - employement
                  'ssn', # Client regional_data
                  'student_loan', 'student_loan_assistance_program', 'student_loan_graduate_looking', # Misc Client model
                  'student_loan_parent_looking', 'hsa_eligible', 'hsa_provider_name', 'hsa_state', 'hsa_coverage_type', # Misc Client model
                  'salutation', 'suffix',]  # IBOnboard

    def __init__(self, *args, **kwargs):
        super(FirmApplicationClientForm, self).__init__(*args, **kwargs)
        client = kwargs['instance']
        user = client.user
        address = client.residential_address

        self.fields['first_name'].initial = user.first_name
        self.fields['middle_name'].initial = user.middle_name
        self.fields['last_name'].initial = user.last_name
        self.fields['email'].initial = user.email

        try:
            invitation = user.invitation
            self.fields['tax_transcript'].initial = invitation.tax_transcript
            self.fields['social_security_statement'].initial = invitation.social_security_statement
        except:
            pass

        self.fields['address1'].initial = address.address1
        self.fields['address2'].initial = address.address2
        self.fields['city'].initial = address.city
        self.fields['post_code'].initial = address.post_code
        self.fields['state'].initial = address.region.code
        self.fields['country'].initial = address.region.country

        self.fields['ssn'].initial = client.regional_data.get('ssn', '')

        try:
            ib_onboard = client.ib_onboard
            self.fields['salutation'].initial = ib_onboard.salutation
            self.fields['suffix'].initial = ib_onboard.suffix
        except:
            pass

    def clean(self):
        cleaned_data = super(FirmApplicationClientForm, self).clean()
        # employed_statuses = [EMPLOYMENT_STATUS_EMMPLOYED, EMPLOYMENT_STATUS_SELF_EMPLOYED]
        # print(cleaned_data['income'])
        # if cleaned_data['employment_status'] in employed_statuses and cleaned_data['income'] is None:
        #     raise forms.ValidationError("Income field is required")
        if cleaned_data['country'] != 'US':
            del cleaned_data['ssn']
        return cleaned_data

    def save(self, commit=True, *args, **kwargs):
        client = super(FirmApplicationClientForm, self).save(commit=False, *args, **kwargs)

        regional_data = client.regional_data
        if self.cleaned_data['country'] == 'US':
            regional_data['ssn'] = self.cleaned_data['ssn']
        else:
            if 'ssn' in regional_data:
                del regional_data['ssn']
            if 'tax_transcript' in regional_data:
                del regional_data['tax_transcript']
            if 'tax_transcript_data' in regional_data:
                del regional_data['tax_transcript_data']
            if 'tax_transcript_data_ex' in regional_data:
                del regional_data['tax_transcript_data_ex']
            if 'social_security_statement' in regional_data:
                del regional_data['social_security_statement']
            if 'social_security_statement_data' in regional_data:
                del regional_data['social_security_statement_data']
            if 'partner_social_security_statement' in regional_data:
                del regional_data['partner_social_security_statement']
            if 'partner_social_security_statement_data' in regional_data:
                del regional_data['partner_social_security_statement_data']

        client.regional_data = regional_data
        client.residential_address = self.update_address(client.residential_address, '')

        if commit:
            client.save()

        user = client.user
        user.first_name = self.cleaned_data['first_name']
        user.middle_name = self.cleaned_data['middle_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']

        if commit:
            user.save()

        try:
            invitation = user.invitation
            invitation.tax_transcript = self.cleaned_data['tax_transcript']
            invitation.social_security_statement = self.cleaned_data['social_security_statement']
            if commit:
                invitation.save()
        except ObjectDoesNotExist:
            pass

        try:
            ib_onboard = client.ib_onboard
        except ObjectDoesNotExist:
            ib_onboard = IBOnboard(client=client)

        ib_onboard.salutation = self.cleaned_data['salutation']
        ib_onboard.suffix = self.cleaned_data['suffix']

        if commit:
            ib_onboard.save()

        return client


class FirmApplicationIBOnboardForm(forms.ModelForm, AddressHelper):
    required_css_class = 'required'

    tax_address1 = forms.CharField(label='Address 1')
    tax_address2 = forms.CharField(label='Address 2', required=False)
    tax_city = forms.CharField(label='City')
    tax_post_code = forms.CharField(label='Zip code', max_length=16, required=False)
    tax_state = forms.CharField(label='State', max_length=128)
    tax_country = forms.ChoiceField(label='Country', choices=COUNTRY_CHOICES)

    emp_address1 = forms.CharField(label='Address 1')
    emp_address2 = forms.CharField(label='Address 2', required=False)
    emp_city = forms.CharField(label='City')
    emp_post_code = forms.CharField(label='Zip code', max_length=16, required=False)
    emp_state = forms.CharField(label='State', max_length=128)
    emp_country = forms.ChoiceField(label='Country', choices=COUNTRY_CHOICES)

    class Meta:
        model = IBOnboard
        exclude = ['salutation', 'suffix', 'doc_exec_ts', 'doc_exec_login_ts']

    def __init__(self, *args, **kwargs):
        super(FirmApplicationIBOnboardForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            ib_onboard = kwargs['instance']
            if ib_onboard.tax_address:
                self.fields['tax_address1'].initial = ib_onboard.tax_address.address1
                self.fields['tax_address2'].initial = ib_onboard.tax_address.address2
                self.fields['tax_city'].initial = ib_onboard.tax_address.city
                self.fields['tax_post_code'].initial = ib_onboard.tax_address.post_code
                self.fields['tax_state'].initial = ib_onboard.tax_address.region.code
                self.fields['tax_country'].initial = ib_onboard.tax_address.region.country

            if ib_onboard.employer_address:
                self.fields['emp_address1'].initial = ib_onboard.employer_address.address1
                self.fields['emp_address2'].initial = ib_onboard.employer_address.address2
                self.fields['emp_city'].initial = ib_onboard.employer_address.city
                self.fields['emp_post_code'].initial = ib_onboard.employer_address.post_code
                self.fields['emp_state'].initial = ib_onboard.employer_address.region.code
                self.fields['emp_country'].initial = ib_onboard.employer_address.region.country

    def save(self, commit=True, *args, **kwargs):
        ib_onboard = super(FirmApplicationIBOnboardForm, self).save(commit=False, *args, **kwargs)
        ib_onboard.tax_address = self.update_address(ib_onboard.tax_address, 'tax_')
        ib_onboard.employer_address = self.update_address(ib_onboard.employer_address, 'emp_')

        if commit:
            ib_onboard.save()
        return ib_onboard


FirmApplicationIBOnboardFormSet = inlineformset_factory(Client, IBOnboard,
                                                        form=FirmApplicationIBOnboardForm,
                                                        exclude=['salutation', 'suffix', 'doc_exec_ts', 'doc_exec_login_ts'])


class LivePortfolioForm(forms.ModelForm):
    required_css_class = 'required'

    name = forms.CharField(max_length=255)
    clients = forms.ModelMultipleChoiceField(queryset=Client.objects.all())

    class Meta:
        model = LivePortfolio
        fields = ('name', 'clients', )


class LivePortfolioItemForm(forms.ModelForm):
    required_css_class = 'required'

    asset = forms.ModelChoiceField(queryset=Ticker.objects.all())
    percentage = forms.FloatField(label='Allocation percentage (between 0 and 100%)')

    def __init__(self, *args, **kwargs):
        super(LivePortfolioItemForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            liveportfolio_item = kwargs['instance']
            self.fields['percentage'].initial = round(liveportfolio_item.weight * 100, 2)

    def save(self, commit=True, *args, **kwargs):
        instance = super(LivePortfolioItemForm, self).save(commit=False, *args, **kwargs)
        instance.weight = self.cleaned_data['percentage'] / 100
        if commit == True:
            instance.save()
        return instance

    class Meta:
        model = LivePortfolioItem
        fields = ('asset', 'weight', )


LivePortfolioItemFormSet = inlineformset_factory(LivePortfolio, LivePortfolioItem,
                                                 form=LivePortfolioItemForm, fields=['asset', 'percentage'], min_num=1, extra=0)


class ReportCommentaryForm(forms.ModelForm):
    required_css_class = 'required'

    portfolio = forms.ModelChoiceField(queryset=LivePortfolio.objects.all(), required=False, widget=forms.HiddenInput())
    category = forms.ChoiceField(choices=constants.COMMENTARY_CATEGORY_CHOICES, required=True, widget=forms.HiddenInput())
    key_commentary = forms.CharField(required=True, widget=forms.Textarea)
    near_term_outlook = forms.CharField(required=False, widget=forms.Textarea)
    publish_at = forms.DateTimeField(widget=forms.DateTimeInput)

    class Meta:
        model = Commentary
        fields = ('portfolio', 'category', 'key_commentary', 'near_term_outlook', 'publish_at', )


class ReportScheduleForm(forms.ModelForm):
    required_css_class = 'required'

    delivery_cycle = forms.ChoiceField(choices=SCHEDULE_DELIVERY_CYCLE_CHOICES, required=True)
    day = forms.IntegerField(required=False, widget=forms.HiddenInput())
    day_of_week = forms.ChoiceField(choices=SCHEDULE_WEEKDAY_CHOICES, required=False, help_text='Day of the week')
    day_of_month = forms.IntegerField(min_value=1, max_value=31, required=False, help_text='Day of the month')
    day_of_quarter = forms.IntegerField(min_value=1, max_value=90, required=False, help_text='Day of the quarter')
    time = forms.ChoiceField(choices=SCHEDULE_HOUR_CHOICES, required=False)
    timezone = forms.ChoiceField(choices=SCHEDULE_TIMEZONE_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner')
        super(ReportScheduleForm, self).__init__(*args, **kwargs)

    def save(self, commit=True, *args, **kwargs):
        schedule = super(ReportScheduleForm, self).save(commit=False, *args, **kwargs)
        schedule.owner = self.owner
        if self.owner.schedule is not None: # if schedule already exists update it
            schedule.pk = self.owner.schedule.pk
        if commit == True:
            schedule.save()

    class Meta:
        model = Schedule
        fields = ('delivery_cycle', 'day', 'time', 'timezone', )
