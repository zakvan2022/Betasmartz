import logging
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect, \
    JsonResponse
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from advisor.models import Advisor
from client.models import Client, ClientAccount
from advisor.models import AccountGroup
from goal.models import Goal
from portfolios.models import Platform, PortfolioSet
from main.views.base import AdvisorView
from notifications.models import Notify
from ..forms import AdvisorCompositeForm, GoalPortfolioFormSet

logger = logging.getLogger(__name__)


class AdvisorCompositeOverview(ListView, AdvisorView):
    model = AccountGroup
    template_name = 'advisor/overview.html'
    context_object_name = 'groups'

    def get_context_data(self, **kwargs):
        ctx = super(AdvisorCompositeOverview, self).get_context_data(
            **kwargs)
        groups = self.get_queryset()
        ctx["groups"] = groups

        pre_clients = Client.objects.filter(user__prepopulated=False,
                                            advisor=self.advisor)
        clients = set(pre_clients)

        for client in set(pre_clients.distinct().all()):
            for group in set(groups.distinct().all()):
                for account in set(group.accounts.distinct().all()):
                    if account.primary_owner.id == client.pk:
                        clients.remove(client)

        ctx['clients'] = clients
        return ctx
    def get_queryset(self):
        q = super(AdvisorCompositeOverview, self).get_queryset()
        return q.filter(Q(advisor=self.advisor) |
                        Q(secondary_advisors__in=[self.advisor]),
                        accounts_all__isnull=False,
                        accounts_all__confirmed=True,
                        accounts_all__primary_owner__user__prepopulated=False,
                        ).distinct()


class AdvisorCompositeNew(AdvisorCompositeForm, CreateView, AdvisorView):
    template_name = "advisor/composites-create.html"
    model = AccountGroup
    fields = ('advisor', 'name')
    account_list = None

    """
    def post(self, request, *args, **kwargs):
        account_list = request.POST.getlist('accounts')
        account_list = ClientAccount.objects.filter(
            pk__in=account_list,
            primary_owner__advisor=self.advisor)
        if account_list.count() == 0:
            redirect = reverse('advisor:composites:create')
            messages.error(request,
                'Failed to create household. Make sure you add at least one account')
            return HttpResponseRedirect(redirect)
        self.account_list = account_list
        return super(AdvisorCompositeNew, self).post(request, *args, **kwargs)
    """

    def get_success_url(self):
        Notify.ADVISOR_CREATE_GROUP.send(
            actor=self.advisor,
            recipient=self.advisor.user,
            target=self.object,
        )
        messages.info(self.request, mark_safe(
            '<span class="mpicon accept"></span>Successfully created group.'))

        return super(AdvisorCompositeNew, self).get_success_url()


class AdvisorAccountGroupDetails(DetailView, AdvisorView):
    template_name = "advisor/composites-detail.html"
    model = AccountGroup

    def get_queryset(self):
        qs = super(AdvisorAccountGroupDetails, self).get_queryset()
        return (qs
                .filter(Q(advisor=self.advisor) |
                        Q(secondary_advisors__in=[self.advisor]))
                .distinct())

    def get_context_data(self, **kwargs):
        c = super(AdvisorAccountGroupDetails, self).get_context_data(**kwargs)
        accounts = []
        for account in self.object.accounts.all():
            if account.all_goals.count():
                formset = GoalPortfolioFormSet(queryset=Goal.objects.filter(account=account))
            else:
                formset = None
            accounts.append({
                'account': account,
                'formset': formset
            })
        c.update({
            'accounts': accounts
        })
        return c

    def post(self, request, pk, **kwargs):
        formset = GoalPortfolioFormSet(request.POST)
        for form in formset:
            if form.instance.is_open and form.is_valid() and 'id' in form.cleaned_data:
                form.save()
        return HttpResponseRedirect(
            reverse('advisor:composites:detail', kwargs={'pk': pk})
        )


class AdvisorCompositeEdit(AdvisorCompositeForm, UpdateView, AdvisorView):
    template_name = "advisor/composites-edit.html"
    model = AccountGroup
    fields = ('advisor', 'name')
    account_list = None

    def post(self, request, *args, **kwargs):
        account_list = request.POST.getlist('accounts')
        account_list = ClientAccount.objects.filter(
            pk__in=account_list,
            primary_owner__advisor=self.advisor)
        self.account_list = account_list
        return super(AdvisorCompositeEdit, self).post(request, *args, **kwargs)


class AdvisorRemoveAccountFromGroupView(AdvisorView):
    def post(self, request, *args, **kwargs):

        account_id = kwargs["account_id"]
        account_group_id = kwargs["account_group_id"]

        try:
            account = ClientAccount.objects.get(
                pk=account_id,
                account_group__pk=account_group_id,
                primary_owner__advisor=self.advisor)
        except ObjectDoesNotExist:
            raise Http404()

        group_name = account.remove_from_group()

        if group_name:
            # account group deleted (cause no accounts in it any more)
            Notify.ADVISOR_REMOVE_GROUP.send(
                actor=self.advisor,
                recipient=self.advisor.user,
                target=account,
            )
            redirect = reverse('advisor:overview')
        else:
            # account group not deleted (just the account)
            redirect = reverse('advisor:composites:edit',
                kwargs={'pk': account_group_id})

        return HttpResponseRedirect(redirect)


class AdvisorAccountGroupClients(DetailView, AdvisorView):
    template_name = "advisor/composites-detail-clients.html"
    model = AccountGroup

    def get_queryset(self):
        return super(AdvisorAccountGroupClients, self).get_queryset() \
            .filter(Q(advisor=self.advisor) | Q(secondary_advisors__in=[self.advisor])).distinct()

    def get_context_data(self, **kwargs):
        ctx = super(AdvisorAccountGroupClients, self).get_context_data(
            **kwargs)
        ctx["object"] = self.object

        ctx["household_clients"] = set(map(lambda x: x.primary_owner,
                                           self.object.accounts.all()))

        return ctx


class AdvisorAccountGroupSecondaryDetailView(DetailView, AdvisorView):
    template_name = "advisor/composites-detail-secondary-advisors.html"
    model = AccountGroup

    def get_queryset(self):
        return super(AdvisorAccountGroupSecondaryDetailView,
                     self).get_queryset().filter(advisor=self.advisor)


class AdvisorAccountGroupSecondaryCreateView(UpdateView, AdvisorView):
    template_name = "advisor/composites-detail-secondary-advisors.html"
    model = AccountGroup
    fields = ('secondary_advisors',)
    secondary_advisor = None

    def get_queryset(self):
        return super(AdvisorAccountGroupSecondaryCreateView,
                     self).get_queryset().filter(advisor=self.advisor)

    def get_success_url(self):
        msg = '<span class="mpicon accept"></span>'
        msg += 'Successfully added {0} as a secondary advisor to {1}'
        msg = msg.format(self.secondary_advisor.user.get_full_name().title(),
                         self.object.name)

        Notify.ADVISOR_ADD_SECONDARY_ADVISOR.send(
            actor=self.advisor,
            recipient=self.advisor.user,
            target=self.secondary_advisor,
            action_object=self.object
        )

        messages.info(self.request, mark_safe(msg))

        return reverse('advisor:composites:detail-secondary-advisors-create',
                kwargs={'pk': self.object.pk})

    def get_form(self, form_class=None):
        form = super(AdvisorAccountGroupSecondaryCreateView,
                     self).get_form(form_class)

        def save_m2m():
            secondary_advisors = self.request.POST.get("secondary_advisors",
                                                       None)
            if secondary_advisors:

                try:
                    advisor = Advisor.objects.get(pk=secondary_advisors)
                except ObjectDoesNotExist:
                    raise Http404()

                self.object.secondary_advisors.add(advisor)
                self.secondary_advisor = advisor
            else:
                raise Http404()

        def save(*args, **kwargs):
            save_m2m()
            return self.object

        form.save = save
        form.save_m2m = save_m2m

        return form

    def get_context_data(self, **kwargs):
        ctx = super(AdvisorAccountGroupSecondaryCreateView,
                    self).get_context_data(**kwargs)
        ctx["new"] = True
        ctx["s_advisors"] = self.advisor.firm.advisors.exclude(
            pk=self.advisor.pk)
        ctx["s_advisors"] = ctx["s_advisors"].exclude(
            pk__in=list(map(lambda x: x.pk, self.object.secondary_advisors.all(
            ))))

        return ctx


class AdvisorAccountGroupSecondaryDeleteView(AdvisorView):
    def post(self, request, *args, **kwargs):
        account_group_pk = kwargs["pk"]
        s_advisor_pk = kwargs["sa_pk"]

        try:
            account_group = AccountGroup.objects.get(pk=account_group_pk,
                                                     advisor=self.advisor)
        except ObjectDoesNotExist:
            raise Http404()

        try:
            advisor = Advisor.objects.get(pk=s_advisor_pk)
        except ObjectDoesNotExist:
            raise Http404()

        account_group.secondary_advisors.remove(advisor)

        messages.info(request, mark_safe(
            '<span class="mpicon accept"></span>Successfully removed secondary '
            'advisor from {0}'.format(account_group.name)))

        Notify.ADVISOR_REMOVE_SECONDARY_ADVISOR.send(
            actor=self.advisor,
            recipient=self.advisor.user,
            target=advisor,
            action_object=account_group
        )

        return HttpResponseRedirect(
            reverse('advisor:composites:detail-secondary-advisors-create',
                kwargs={'pk': account_group_pk})
        )


class AdvisorClientAccountChangeFee(UpdateView, AdvisorView):
    model = ClientAccount
    fields = ('custom_fee',)
    template_name = 'advisor/form-fee.js'
    content_type = 'text/javascript'

    def get_context_data(self, **kwargs):
        ctx = super(AdvisorClientAccountChangeFee, self).get_context_data(
            **kwargs)
        ctx["object"] = self.object
        ctx["platform"] = Platform.objects.first()
        ctx["firm"] = self.advisor.firm
        html_output = render_to_string("advisor/form-fee.html",
                                       RequestContext(self.request, ctx))
        html_output = mark_safe(html_output.replace("\n", "\\n").replace(
            '"', '\\"').replace("'", "\\'"))
        ctx["html_output"] = html_output
        return ctx

    def get_queryset(self):
        return super(AdvisorClientAccountChangeFee, self).get_queryset().distinct() \
            .filter(Q(account_group__advisor=self.advisor) | Q(account_group__secondary_advisors__in=[self.advisor]))

    def get_form(self, form_class=None):
        form = super(AdvisorClientAccountChangeFee, self).get_form(form_class)
        old_save = form.save

        def save(*args, **kwargs):
            instance = old_save(*args, **kwargs)
            if self.request.POST.get("is_custom_fee", "false") == "false":
                instance.custom_fee = 0
                instance.save()

            return instance

        form.save = save
        return form

    def get_success_url(self):
        return '/composites/{0}'.format(self.object.account_group.pk)

