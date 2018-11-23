import logging

from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from main.views.base import AdvisorView
from notifications.models import Notify


logger = logging.getLogger(__name__)


class AdvisorAgreements(TemplateView, AdvisorView):
    template_name = "commons/agreements.html"

    def __init__(self, *args, **kwargs):
        super(AdvisorAgreements, self).__init__(*args, **kwargs)
        self.search = ""

    def get(self, request, *args, **kwargs):
        self.search = request.GET.get("search", self.search)
        return super(AdvisorAgreements, self).get(request, *args, **kwargs)

    @property
    def clients(self):
        clients = self.advisor.clients
        if self.search:
            sq = Q(user__first_name__icontains=self.search)
            clients = clients.filter(sq)
        return clients.all()

    def get_context_data(self, **kwargs):
        ctx = super(AdvisorAgreements, self).get_context_data(**kwargs)
        ctx.update({
            "clients": self.clients,
            "search": self.search,
            "firm": self.advisor.firm,
        })
        return ctx


class AdvisorDownloadAgreement(AdvisorView):
    def get(self, request, client_id):
        try:
            client = self.advisor.clients.get(pk=client_id)
        except Client.DoesNotExist:
            return HttpResponseForbidden()
        try:
            url = client.client_agreement.url
        except ValueError:
            logger.error('Client %s does not have agreement.', client_id)
            return HttpResponseRedirect(reverse('advisor:agreements'))
        Notify.ADVISOR_CLIENT_AGREEMENT_DOWNLOAD.send(
            actor=self.advisor,
            recipient=self.advisor.user,
            target=client
        )
        return HttpResponseRedirect(url)

