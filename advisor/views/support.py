import logging
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.views.generic import CreateView, DetailView, ListView, \
    TemplateView, UpdateView
from main.views.base import AdvisorView
from notifications.models import Notify
from documents.models import DocumentUpload
from support.models import SupportRequest
from ..forms import BulkInvestorTransferForm, \
    ChangeDealerGroupForm, SingleInvestorTransferForm
from ..models import BulkInvestorTransfer, ChangeDealerGroup, \
    SingleInvestorTransfer

logger = logging.getLogger(__name__)


class AdvisorSupport(TemplateView, AdvisorView):
    template_name = "advisor/support.html"


class AdvisorSupportGettingStarted(AdvisorView, TemplateView):
    template_name = 'advisor/support-getting-started.html'

    def acats(self):
        acats = DocumentUpload.objects.get(name='ACATS Transfer Form')
        return acats


class AdvisorSupportForms(TemplateView, AdvisorView):
    template_name = "advisor/support-forms.html"


class AdvisorChangeDealerGroupView(AdvisorView, CreateView):
    template_name = "advisor/form-firm.html"
    success_url = "/advisor/support/forms"
    form_class = ChangeDealerGroupForm

    def get_context_data(self, **kwargs):
        ctx_data = super(AdvisorChangeDealerGroupView, self).get_context_data(**kwargs)
        ctx_data["form_name"] = "Change of dealer group"
        return ctx_data

    def get_success_url(self):
        Notify.SUBMIT_FORM.send(
            actor=self.advisor,
            target=self.object
        )
        messages.success(self.request, "Change of dealer group submitted successfully")
        return super(AdvisorChangeDealerGroupView, self).get_success_url()

    def get_initial(self):
        return {"advisor": self.advisor, "old_firm": self.advisor.firm, "new_email": self.advisor.email}

    def dispatch(self, request, *args, **kwargs):

        try:
            user = SupportRequest.target_user(request)
            cdg = ChangeDealerGroup.objects.exclude(approved=True).get(advisor=user.advisor)
            return HttpResponseRedirect("/advisor/support/forms/change/firm/update/{0}".format(cdg.pk))
        except ObjectDoesNotExist:
            return super(AdvisorChangeDealerGroupView, self).dispatch(request, *args, **kwargs)


class AdvisorChangeDealerGroupUpdateView(AdvisorView, UpdateView):
    template_name = "advisor/form-firm.html"
    success_url = "/advisor/support/forms"
    form_class = ChangeDealerGroupForm
    model = ChangeDealerGroup

    def get_context_data(self, **kwargs):
        ctx_data = super(AdvisorChangeDealerGroupUpdateView, self).get_context_data(**kwargs)
        ctx_data["form_name"] = "Change of dealer group"
        ctx_data["object"] = self.object
        return ctx_data

    def get_success_url(self):
        Notify.UPDATE_FORM.send(
            actor=self.advisor,
            target=self.object
        )
        messages.success(self.request, "Change of dealer group submitted successfully")
        return super(AdvisorChangeDealerGroupUpdateView, self).get_success_url()

    def get_initial(self):
        return {"advisor": self.advisor, "old_firm": self.advisor.firm, "new_email": self.advisor.email}


class AdvisorSingleInvestorTransferView(AdvisorView, CreateView):
    template_name = "advisor/form-firm.html"
    success_url = "/advisor/support/forms"
    form_class = SingleInvestorTransferForm

    def get_context_data(self, **kwargs):
        ctx_data = super(AdvisorSingleInvestorTransferView, self).get_context_data(**kwargs)
        ctx_data["form_name"] = "Single client transfer"
        return ctx_data

    def get_success_url(self):
        Notify.SUBMIT_FORM.send(
            actor=self.advisor,
            target=self.object
        )
        messages.success(self.request, "Single client transfer submitted successfully")
        return super(AdvisorSingleInvestorTransferView, self).get_success_url()

    def get_initial(self):
        return {"from_advisor": self.advisor}

    def dispatch(self, request, *args, **kwargs):

        try:
            user = SupportRequest.target_user(request)
            sit = SingleInvestorTransfer.objects.exclude(approved=True).get(from_advisor=user.advisor)
            return HttpResponseRedirect("/advisor/support/forms/transfer/single/update/{0}".format(sit.pk))
        except ObjectDoesNotExist:
            return super(AdvisorSingleInvestorTransferView, self).dispatch(request, *args, **kwargs)


class AdvisorSingleInvestorTransferUpdateView(AdvisorView, UpdateView):
    template_name = "advisor/form-firm.html"
    success_url = "/advisor/support/forms"
    form_class = SingleInvestorTransferForm
    model = SingleInvestorTransfer

    def get_context_data(self, **kwargs):
        ctx_data = super(AdvisorSingleInvestorTransferUpdateView, self).get_context_data(**kwargs)
        ctx_data["form_name"] = "Single client transfer"
        ctx_data["object"] = self.object
        return ctx_data

    def get_success_url(self):
        Notify.UPDATE_FORM.send(
            actor=self.advisor,
            target=self.object
        )
        messages.success(self.request, "Single client transfer submitted successfully")
        return super(AdvisorSingleInvestorTransferUpdateView, self).get_success_url()

    def get_initial(self):
        return {"from_advisor": self.advisor}


class AdvisorBulkInvestorTransferView(AdvisorView, CreateView):
    template_name = "advisor/form-firm.html"
    success_url = "/advisor/support/forms"
    form_class = BulkInvestorTransferForm

    def get_context_data(self, **kwargs):
        ctx_data = super(AdvisorBulkInvestorTransferView, self).get_context_data(**kwargs)
        ctx_data["form_name"] = "Bulk client transfer"
        return ctx_data

    def get_success_url(self):
        Notify.SUBMIT_FORM.send(
            actor=self.advisor,
            target=self.object
        )
        messages.success(self.request, "Bulk client transfer submitted successfully")
        return super(AdvisorBulkInvestorTransferView, self).get_success_url()

    def get_initial(self):
        return {"from_advisor": self.advisor}

    def dispatch(self, request, *args, **kwargs):

        try:
            user = SupportRequest.target_user(request)
            sit = BulkInvestorTransfer.objects.exclude(approved=True).get(from_advisor=user.advisor)
            return HttpResponseRedirect("/advisor/support/forms/transfer/bulk/update/{0}".format(sit.pk))
        except ObjectDoesNotExist:
            return super(AdvisorBulkInvestorTransferView, self).dispatch(request, *args, **kwargs)


class AdvisorBulkInvestorTransferUpdateView(AdvisorView, UpdateView):
    template_name = "advisor/form-firm.html"
    success_url = "/advisor/support/forms"
    form_class = BulkInvestorTransferForm
    model = BulkInvestorTransfer

    def get_context_data(self, **kwargs):
        ctx_data = super(AdvisorBulkInvestorTransferUpdateView, self).get_context_data(**kwargs)
        ctx_data["form_name"] = "Bulk investor transfer"
        ctx_data["object"] = self.object
        return ctx_data

    def get_success_url(self):
        Notify.UPDATE_FORM.send(
            actor=self.advisor,
            target=self.object
        )
        messages.success(self.request, "Bulk investor transfer submitted successfully")
        return super(AdvisorBulkInvestorTransferUpdateView, self).get_success_url()

    def get_initial(self):
        return {"from_advisor": self.advisor}
