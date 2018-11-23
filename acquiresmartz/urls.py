from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect

from .views import *

urlpatterns = patterns(
    '',
    url(r'^$', lambda x: HttpResponseRedirect(reverse_lazy('firm:acquiresmartz:leads')), name='index'),
    url(r'^leads$', FirmAcquireSmartzLeads.as_view(), name='leads'),
    url(r'^leads/(?P<pk>\d+)$', FirmAcquireSmartzLeads.as_view(), name='leads-campaign'),
    url(r'^targets$', FirmAcquireSmartzTargets.as_view(), name='targets'),
    url(r'^targets/(?P<pk>\d+)$', FirmAcquireSmartzTargets.as_view(), name='targets-campaign'),
    url(r'^targets/add$', FirmAcquireSmartzAddTargetUser.as_view(), name='targets-add'),
    url(r'^cognitics$', FirmAcquireSmartzCognitics.as_view(), name='cognitics'),
    url(r'^cognitics/(?P<pk>\d+)$', FirmAcquireSmartzCognitics.as_view(), name='cognitics-campaign'),
    url(r'^campaign$', FirmAcquireSmartzCampaignNew.as_view(), name='campaign-new'),
    url(r'^campaign/(?P<pk>\d+)$', FirmAcquireSmartzCampaignEdit.as_view(), name='campaign-edit'),
    url(r'^personality-insights/(?P<pk>\d+)$', FirmAcquireSmartzPersonalityInsights.as_view(), name='personality-insights'),
)
