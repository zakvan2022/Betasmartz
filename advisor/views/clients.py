from __future__ import unicode_literals

import logging

from django import http
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, \
    ValidationError
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Q
from django.views.generic import CreateView, ListView, TemplateView, DeleteView, \
    DetailView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from operator import itemgetter

from ..forms import ClientAccessForm, EmailInviteForm, GoalPortfolioFormSet, \
    PrepopulatedUserForm, BuildPersonalDetailsForm, BuildFinancialDetailsForm
from client.models import Client, ClientAccount, EmailInvite
from firm.models import PricingPlan
from main.constants import ACCOUNT_TYPES, CLIENT_NO_ACCESS
from goal.models import Goal
from main.views.base import AdvisorView
from notifications.models import Notify
from portfolios.models import PortfolioSet
from support.models import SupportRequest
from user.models import User
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect, \
    JsonResponse
from django.template.loader import render_to_string
from user.autologout import SessionExpire


logger = logging.getLogger(__name__)


class AdvisorClients(TemplateView, AdvisorView):
    model = Client
    template_name = 'advisor/clients/list.html'
    col_dict = {"full_name": 1, 'status': 2, "current_balance": 3, 'email_address': 4}

    def __init__(self, *args, **kwargs):
        super(AdvisorClients, self).__init__(*args, **kwargs)
        self.filter = "0"
        self.search = ""
        self.sort_col = "current_balance"
        self.sort_dir = "desc"

    def get(self, request, *args, **kwargs):

        self.filter = request.GET.get("filter", self.filter)
        self.search = request.GET.get("search", self.search)
        self.sort_col = request.GET.get("sort_col", self.sort_col)
        self.sort_dir = request.GET.get("sort_dir", self.sort_dir)
        response = super(AdvisorClients, self).get(request, *args, **kwargs)
        return response

    @property
    def clients(self):
        pre_clients = self.model.objects.filter(user__prepopulated=False)

        if self.filter == "1":
            pre_clients = pre_clients.filter(advisor=self.advisor)
        elif self.filter == "2":
            pre_clients = pre_clients.filter(
                secondary_advisors__in=[self.advisor])
        else:
            pre_clients = pre_clients.filter(Q(advisor=self.advisor) | Q(
                secondary_advisors__in=[self.advisor]))

        if self.search:
            sq = Q(user__first_name__icontains=self.search) | Q(
                user__last_name__icontains=self.search)
            pre_clients = pre_clients.filter(sq)

        clients = []

        for client in set(pre_clients.distinct().all()):
            relationship = "Primary" if client.advisor == self.advisor else "Secondary"
            clients.append([client.pk, client.full_name, client.on_track, client.total_balance,
                            client.email, relationship])

        reverse = self.sort_dir != "asc"

        clients = sorted(clients,
                         key=itemgetter(self.col_dict[self.sort_col]),
                         reverse=reverse)
        return clients

    def get_context_data(self, **kwargs):
        ctx = super(AdvisorClients, self).get_context_data(**kwargs)
        ctx.update({
            "filter": self.filter,
            "search": self.search,
            "sort_col": self.sort_col,
            "sort_dir": self.sort_dir,
            "sort_inverse": 'asc' if self.sort_dir == 'desc' else 'desc',
            "clients": self.clients
        })
        return ctx


class AdvisorClientAccountsDetails(DetailView, AdvisorView):
    template_name = "advisor/clients/accountdetail.html"
    client = None
    model = Client

    def get(self, request, *args, **kwargs):
        client_id = kwargs["pk"]
        client = Client.objects.filter(pk=client_id)
        client = client.filter(Q(advisor=self.advisor) | Q(
            secondary_advisors__in=[self.advisor])).all()

        if not client:
            raise http.Http404("Client not found")

        self.client = client[0]

        return super(AdvisorClientAccountsDetails, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(AdvisorClientAccountsDetails, self).get_context_data(**kwargs)
        accounts = []
        for account in self.client.accounts.all():
            if account.all_goals.count():
                formset = GoalPortfolioFormSet(queryset=Goal.objects.filter(account=account))
            else:
                formset = None
            accounts.append({
                'account': account,
                'formset': formset
            })
        ctx.update({
            'accounts': accounts
        })
        return ctx

    def post(self, request, pk, **kwargs):
        pricing_plan_pk = request.POST.get('pricing_plan_pk', None)

        if pricing_plan_pk:
            try:
                plan = PricingPlan.objects.get(pk=pricing_plan_pk)
                bps = request.POST.get('pricing_plan_bps', None)
                fixed = request.POST.get('pricing_plan_fixed', None)
                plan.bps = bps
                plan.fixed = fixed
                plan.save(update_fields=['bps','fixed'])
            except ObjectDoesNotExist:
                pass
        else:
            formset = GoalPortfolioFormSet(request.POST)
            for form in formset:
                if form.instance.is_open and form.is_valid() and 'id' in form.cleaned_data:
                    form.save()

        return HttpResponseRedirect(
            reverse('advisor:clients:accountsdetail',kwargs={'pk': pk})
        )
        # FIXME: hack, emulates ApiRenderer output
        return JsonResponse({
            'meta': {
                'session_expires_on': SessionExpire(request).expire_time(),
            },
            'error': []
        })


class AdvisorClientDetails(UpdateView, AdvisorView):
    template_name = "advisor/clients/detail.html"
    client = None
    model = Client
    form_class = ClientAccessForm

    def get_success_url(self):
        return reverse('advisor:clients:detail', kwargs={'pk': self.client.id})

    def set_client(self, request, *args, **kwargs):
        client_id = kwargs["pk"]
        client = Client.objects.filter(pk=client_id)
        client = client.filter(Q(advisor=self.advisor) | Q(
            secondary_advisors__in=[self.advisor])).all()

        if not client:
            raise http.Http404("Client not found")

        self.client = client[0]

    def get(self, request, *args, **kwargs):
        self.set_client(request, *args, **kwargs)
        return super(AdvisorClientDetails, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.set_client(request, *args, **kwargs)
        return super(AdvisorClientDetails, self).post(request, *args, **kwargs)


class AdvisorCreateNewAccountForExistingClient(AdvisorView, CreateView):
    template_name = "advisor/clients/invites/confirm-account.html"
    model = ClientAccount
    fields = ('primary_owner', 'account_class')
    client = None
    account_class = None

    def get_success_url(self):
        messages.success(self.request, "New account confirmation email sent successfully.")
        return reverse_lazy('advisor:clients:detail', kwargs={'pk': self.client.pk})

    def dispatch(self, request, *args, **kwargs):
        client_pk = kwargs["pk"]
        account_class = request.POST.get("account_type", request.GET.get("account_type", None))

        if account_class is None:
            account_class = request.POST.get("account_class", request.GET.get("account_class", None))

        if account_class not in ["joint_account", "trust_account"]:
            raise http.Http404()

        user = SupportRequest.target_user(request)
        advisor = user.advisor

        try:
            client = advisor.clients.get(pk=client_pk)
        except ObjectDoesNotExist:
            raise PermissionDenied()

        self.client = client
        self.account_class = account_class

        return super(AdvisorCreateNewAccountForExistingClient, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super(AdvisorCreateNewAccountForExistingClient, self).form_valid(form)
        self.object.send_confirmation_email()
        return response

    def get_context_data(self, **kwargs):
        ctx_data = super(AdvisorCreateNewAccountForExistingClient, self).get_context_data(**kwargs)
        ctx_data["client"] = self.client
        ctx_data["account_class"] = self.account_class
        account_type_name = self.account_class
        for i in ACCOUNT_TYPES:
            if i[0] == self.account_class:
                account_type_name = i[1]
        ctx_data["account_type_name"] = account_type_name
        return ctx_data


class AdvisorClientInvites(ListView, AdvisorView):
    template_name = 'advisor/clients/invites/list.html'
    context_object_name = 'invites'

    def get_queryset(self):
        return self.advisor.invites.all()

class AdvisorClientInvitesDeleteView(DeleteView,AdvisorView):
    template_name = "advisor/clients/invites/confirm_delete.html"

    def get_success_url(self):
        return reverse('advisor:clients:invites')

    def get_queryset(self):
        return self.advisor.invites.all()


class AdvisorNewClientInviteView(CreateView, AdvisorView):
    template_name = 'advisor/clients/invites/new.html'
    form_class = EmailInviteForm

    def get_success_url(self):
        return reverse('advisor:clients:invites')

    def get_form_kwargs(self):
        kwargs = super(AdvisorNewClientInviteView, self).get_form_kwargs()
        firm = self.request.user.advisor.firm
        kwargs.update({
            'retiresmartz_enabled': firm.config.retiresmartz_enabled
        })
        return kwargs

    def process_create_no_access_client(self, invite):
        client = Client.create_no_access_client(invite)
        
        context = {
            'site': get_current_site(self.request),
            'advisor': self.advisor,
            'client': client,
            'category': 'Customer onboarding',
            'login_url': '{}?next=/client/{}'.format(client.user.login_url(), client.id),
        }
        subject = 'New {} Client Account'.format(self.advisor.firm.name)

        try:
            self.advisor.user.email_user(subject,
                                         html_message=render_to_string(
                                            'email/client/no_client_access_setup.html', context))
            Notify.ADVISOR_INVITE_NEW_CLIENT.send(
                actor=self.advisor,
                target=invite,
            )
            messages.success(self.request, 'Successfuly created a new client and you have been emailed with client login information.')
        except ValidationError as e:
            messages.error(self.request, str(e))
        except Exception as e:
            logger.error('Cannot send invitation email (%s)', e)
            messages.error(self.request, 'Cannot send the email with client login information!')

    def process_post_invitation(self, invite):
        try:
            invite.send()
            Notify.ADVISOR_INVITE_NEW_CLIENT.send(
                actor=self.advisor,
                target=invite,
            )
            messages.success(self.request, 'Invitation email sent.')
        except ValidationError as e:
            messages.error(self.request, str(e))
        except Exception as e:
            logger.error('Cannot send invitation email (%s)', e)
            messages.error(self.request, 'Cannot send invitation email!')

    def form_valid(self, form):
        self.object = invite = form.save(commit=False)
        invite.advisor = self.advisor
        invite.save()
        if invite.access_level == CLIENT_NO_ACCESS:
            self.process_create_no_access_client(invite)
        else:
            self.process_post_invitation(invite)

        return http.HttpResponseRedirect(self.get_success_url())


class AdvisorCreateNewAccountForExistingClientSelectAccountType(AdvisorView, TemplateView):
    template_name = "advisor/clients/invites/create-account-type.html"
    client = None

    def dispatch(self, request, *args, **kwargs):
        client_pk = kwargs["pk"]
        user = SupportRequest.target_user(request)
        advisor = user.advisor

        try:
            client = advisor.clients.get(pk=client_pk)
        except ObjectDoesNotExist:
            raise PermissionDenied()

        self.client = client

        return super(AdvisorCreateNewAccountForExistingClientSelectAccountType,
                     self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx_data = super(AdvisorCreateNewAccountForExistingClientSelectAccountType, self).get_context_data(**kwargs)
        ctx_data["client"] = self.client
        return ctx_data


class AdvisorNewClientResendInviteView(SingleObjectMixin, AdvisorView):
    queryset = EmailInvite.objects.all()

    def post(self, request, *args, **kwargs):
        invite = self.get_object()
        invite.send()
        Notify.ADVISOR_RESEND_INVITE.send(
            actor=self.advisor,
            target=invite)
        messages.success(self.request, "Invite sent successfully!")
        return http.HttpResponseRedirect(reverse('advisor:clients:invites'))


class AdvisorClientInviteNewView(TemplateView, AdvisorView):
    """Docstring for AdvisorClientInviteNewView. """

    template_name = 'advisor/clients-invites-create.html'


class CreateNewClientPrepopulatedView(AdvisorView, TemplateView):
    template_name = 'advisor/clients-invites-create-profile.html'
    form_class = PrepopulatedUserForm
    account_type = None
    invite_type = None

    def post(self, request, *args, **kwargs):

        try:
            user = User.objects.get(email=request.POST.get("email", None))

            if not user.prepopulated:
                messages.error(request, "User already exists")
                response = super(CreateNewClientPrepopulatedView, self).get(
                    request, *args, **kwargs)
                response.context_data["form"] = self.form_class(
                    data=request.POST)
                return response
            else:
                return HttpResponseRedirect(
                    reverse('advisor:clients:invites-create-personal-details',
                        kwargs={'pk': user.client.pk})
                )

        except ObjectDoesNotExist:
            pass

        form = self.form_class(data=request.POST)

        if form.is_valid():
            form.define_advisor(self.advisor)
            form.add_account_class(self.account_type)
            user = form.save()
            if self.invite_type == "blank":
                return HttpResponseRedirect(
                    reverse('advisor:clients:invites-create-confirm',
                        kwargs={'pk': user.client.pk}) + '?invitation_type=blank'
                )

            else:
                return HttpResponseRedirect(self.get_success_url())

        else:
            response = super(CreateNewClientPrepopulatedView, self).get(
                request, *args, **kwargs)
            response.context_data["form"] = form
            return response

    def dispatch(self, request, *args, **kwargs):
        self.account_type = request.GET.get("account_type", request.POST.get(
            "account_type", None))
        self.invite_type = request.GET.get("invite_type", request.POST.get(
            "invite_type", None))

        if self.account_type not in ["joint_account", "trust_account"]:
            messages.error(request, "Please select an account type")

            return HttpResponseRedirect(
                reverse('advisor:clients:invites') \
                + '?invitation_type={0}'.format(self.invite_type)
            )

        return super(CreateNewClientPrepopulatedView, self).dispatch(
            request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return super(CreateNewClientPrepopulatedView, self).get(request, *args,
                                                                **kwargs)

    def get_success_url(self):
        messages.info(self.request, "Invite sent successfully!")
        return reverse('advisor:clients:invites')

    def get_context_data(self, **kwargs):
        context_data = super(CreateNewClientPrepopulatedView,
                             self).get_context_data(**kwargs)
        context_data["account_type"] = self.account_type
        context_data["invite_type_new_email"] = self.invite_type
        context_data['form'] = self.form_class()

        return context_data


class BuildPersonalDetails(AdvisorView, UpdateView):
    template_name = 'advisor/clients-invites-create-personal-details.html'
    model = Client
    form_class = BuildPersonalDetailsForm

    def get_queryset(self):
        q = super(BuildPersonalDetails, self).get_queryset()
        q.filter(advisor=self.advisor, user__prepopulated=True)
        return q

    def get_success_url(self):
        return reverse('advisor:clients:invites-create-financial-details',
                kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context_data = super(BuildPersonalDetails, self).get_context_data(
            **kwargs)
        context_data["years"] = list(range(1895, now().year))
        context_data["days"] = list(range(1, 31))
        context_data["years"].reverse()
        return context_data


class BuildFinancialDetails(AdvisorView, UpdateView):
    template_name = 'advisor/clients-invites-create-financial-details.html'
    model = Client
    form_class = BuildFinancialDetailsForm

    def get_queryset(self):
        q = super(BuildFinancialDetails, self).get_queryset()
        q.filter(advisor=self.advisor, user__prepopulated=True)
        return q

    def get_success_url(self):
        return reverse('advisor:clients:invites-create-confirm',
                kwargs={'pk': self.object.pk})


class BuildConfirm(AdvisorView, TemplateView):
    template_name = 'advisor/clients:invites-create-confirm.html'
    object = None
    invitation_type = None

    def dispatch(self, request, *args, **kwargs):
        pk = kwargs["pk"]
        self.invitation_type = self.request.GET.get(
            "invitation_type", self.request.POST.get('invitation_type', None))

        try:
            self.object = Client.objects.get(pk=pk,
                                             advisor=request.user.advisor)
        except ObjectDoesNotExist:
            raise Http404()

        return super(BuildConfirm, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context_data = super(BuildConfirm, self).get_context_data(**kwargs)
        attributes = []
        user_values = []
        user_verbose_names = []
        for key in USER_DETAILS:
            user_verbose_names.append(User._meta.get_field_by_name(key)[
                                          0].verbose_name.title())
            user_values.append(getattr(self.object.user,
                                       "get_{0}_display".format(key), getattr(
                    self.object.user, key, "")))
        user_dict = dict(zip(user_verbose_names, user_values))
        user_dict["Full Name"] = "{0} {1} {2}".format(
            user_dict.pop("First Name"), user_dict.pop("Middle Name(S)"),
            user_dict.pop("Last Name"))

        verbose_names = []
        values = []
        for key in PERSONAL_DETAILS:
            if key in ("month", "year", "day"):
                continue
            verbose_names.append(Client._meta.get_field_by_name(key)[
                                     0].verbose_name.title())
            values.append(getattr(self.object, "get_{0}_display".format(key),
                                  getattr(self.object.user, key, "")))

        personal_dict = dict(zip(verbose_names, values))

        verbose_names = []
        values = []
        for key in FINANCIAL_DETAILS:
            verbose_names.append(Client._meta.get_field_by_name(key)[
                                     0].verbose_name.title())
            values.append(getattr(self.object, "get_{0}_display".format(key),
                                  getattr(self.object.user, key, "")))

        financial_dict = dict(zip(verbose_names, values))

        for k, v in user_dict.items():
            if v:
                attributes.append({"name": k, "value": v})

        if self.invitation_type != "blank":

            for k, v in personal_dict.items():
                if v:
                    attributes.append({"name": k, "value": v})

            for k, v in financial_dict.items():
                if v:
                    attributes.append({"name": k, "value": v})

        context_data["attributes"] = attributes
        context_data["inviter_type"] = self.advisor.content_type
        context_data["inviter_id"] = self.advisor.pk
        context_data["invitation_type"] = INVITATION_CLIENT
        context_data["email"] = self.object.user.email

        return context_data

