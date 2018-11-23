from django.conf.urls import include, patterns, url
from django.contrib import admin
from django.core.urlresolvers import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from filebrowser.sites import site
from api.v1.user.views import PasswordResetView
from main import settings
from main.views import *
from .swagger import schema_view as swagger


def ok_response_json(*args, **kwargs):
    return HttpResponse("[]", content_type='application/json')

# TODO: modularize later
urlpatterns_firm = patterns(
    '',
    url(r'^overview$', FirmOverview.as_view(), name='overview'),
    url(r'^analytics$', FirmAnalyticsOverviewView.as_view(), name='analytics'), # aka 'analytics-overview'
    url(r'^analytics/metric$', FirmAnalyticsOverviewMetricView.as_view(), name='analytics-overview-metric'),
    url(r'^analytics/advisors$', FirmAnalyticsAdvisorsView.as_view(), name='analytics-advisors'),
    url(r'^analytics/advisors/(?P<pk>\d+)$', FirmAnalyticsAdvisorsDetailView.as_view(), name='analytics-advisors-detail'),
    url(r'^analytics/clients$', FirmAnalyticsClientsView.as_view(), name='analytics-clients'),
    url(r'^analytics/clients/(?P<pk>\d+)$', FirmAnalyticsClientsDetailView.as_view(), name='analytics-clients-detail'),

    url(r'^activity$', FirmActivityView.as_view(), name='activity'),
    url(r'^reporting$', FirmReportingView.as_view(), name='reporting'),
    url(r'^reporting/(?P<pk>\d+)$', FirmReportingDetailView.as_view(), name='reporting-detail'),
    url(r'^reporting/(?P<pk>\d+)/edit$', FirmReportingUpdateView.as_view(), name='reporting-edit'),
    url(r'^reporting/(?P<pk>\d+)/generate$', FirmReportingGenerateReportView.as_view(), name='reporting-generate'),
    url(r'^reporting/(?P<pk>\d+)/email-clients$', FirmReportingSendEmailToClientsView.as_view(), name='email-clients'),
    url(r'^reporting/(?P<pk>\d+)/email-advisors$', FirmReportingSendEmailToAdvisorsView.as_view(), name='email-advisors'),
    url(r'^reporting/(?P<pk>\d+)/schedule$', FirmReportingScheduleView.as_view(), name='reporting-schedule'),
    url(r'^reporting/new$', FirmReportingCreateView.as_view(), name='reporting-new'),
    url(r'^reporting/commentary/new$', FirmReportingCommentaryNewView.as_view(), name='reporting-commentary-new'),
    url(r'^reporting/commentary/(?P<pk>\d+)/edit$', FirmReportingCommentaryEditView.as_view(), name='reporting-commentary-edit'),
    url(r'^application$', FirmApplicationView.as_view(), name='application'),
    url(r'^application/new$', FirmApplicationCreateView.as_view(), name='application-new'),
    url(r'^application/import/$', FirmApplicationImportView.as_view(), name='application-import'),
    url(r'^application/(?P<pk>\d+)$', FirmApplicationDetailView.as_view(), name='application-detail'),
    url(r'^application/(?P<pk>\d+)/send-email/$', FirmApplicationSendEmailView.as_view(), name='application-send-email'),
    url(r'^support$', FirmSupport.as_view(), name='support'),
    url(r'^support/forms$', FirmSupportForms.as_view(), name='support-forms'),
    url(r'^support/pricing$', FirmSupportPricingView.as_view(), name='support-pricing'),

    # url(r'^advisor_invites', FirmAdvisorInvites.as_view()), # TODO: revamp
    # url(r'^supervisor_invites', FirmSupervisorInvites.as_view()), # TODO: revamp

    url(r'^edit$', FirmDataView.as_view(), name='edit'), # TODO: revamp

    url(r'^overview/advisors/(?P<pk>\d+)$', FirmAdvisorAccountOverview.as_view(), name='overview-advisor'),
    url(r'^overview/advisors/(?P<pk>\d+)/clients$', FirmAdvisorClients.as_view(), name='overview-advisor-clients'),
    url(r'^overview/advisors/(?P<advisor_id>\d+)/client/(?P<pk>\d+)$', FirmAdvisorClientDetails.as_view(), name='overview-advisor-clients-detail'),

    # OBSOLETED # url(r'^agreements$', FirmAgreements.as_view()),

    url(r'^supervisors$', FirmSupervisors.as_view(), name='supervisors'),
    url(r'^supervisors/create$', FirmSupervisorsCreate.as_view(), name='supervisors-create'),
    url(r'^supervisors/(?P<pk>\d+)/edit', FirmSupervisorsEdit.as_view(), name='supervisors-edit'),
    url(r'^supervisors/(?P<pk>\d+)/delete', FirmSupervisorDelete.as_view(), name='supervisors-delete'),

    url(r'^acquiresmartz/', include('acquiresmartz.urls', namespace='acquiresmartz', app_name='acquiresmartz')),
)

urlpatterns_oauth1healthdevice = patterns(
    '',
    url(r'^withings/', healthdevices.withings, name='withings'),
    url(r'^withings-redirect/', healthdevices.withings_redirect, name='withings-redirect'),
)

urlpatterns_oauth2healthdevice = patterns(
    '',
    url(r'^fitbit/', healthdevices.fitbit, name='fitbit'),
    url(r'^google-fit/', healthdevices.google_fit, name='google-fit'),
    url(r'^microsoft-health/', healthdevices.microsoft_health, name='microsoft-health'),
    url(r'^under-armour/', healthdevices.under_armour, name='under-armour'),
    url(r'^jawbone/', healthdevices.jawbone, name='jawbone'),
    url(r'^tomtom/', healthdevices.tomtom, name='tomtom'),
)

urlpatterns = patterns(
    '',
    url(r'^api/', include('api.urls', namespace='api')),
    url(r'^api-docs/', swagger, name='swagger'),
    url(r'^admin/filebrowser/', include(site.urls)),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^nested_admin/', include('nested_admin.urls')),  # For nested stackable admin
    url(r'^support/', include('pages.urls')),

    # Firm views
    url(r'^firm/', include(urlpatterns_firm, namespace='firm')),
    # Client views
    url(r'^client/', include('client.urls', namespace='client', app_name='client')),
    # Health device views
    url(r'^oauth/health-devices/', include(urlpatterns_oauth1healthdevice, namespace='oauth1healthdevices')),
    url(r'^oauth2/health-devices/', include(urlpatterns_oauth2healthdevice, namespace='oauth2healthdevices')),
    # Client statements
    url(r'^statements/', include('statements.urls', namespace='statements', app_name='statements')),
    # Advisor views
    url(r'^advisor/', include('advisor.urls', namespace='advisor', app_name='advisors')),

    url(r'^session',
        csrf_exempt(Session.as_view()),
        name="session"),
    url(r'^betasmartz_admin/firm/(?P<pk>\d+)/invite_legal',
        InviteLegalView.as_view(),
        name='betasmartz_admin:invite_legal'),
    url(r'^betasmartz_admin/firm/(?P<pk>\d+)/invite_advisor',
        AdminInviteAdvisorView.as_view(),
        name='betasmartz_admin:invite_advisor'),
    url(r'^betasmartz_admin/firm/(?P<pk>\d+)/invite_supervisor',
        AdminInviteSupervisorView.as_view(),
        name='betasmartz_admin:invite_supervisor'),

    url(r'^$', lambda x: HttpResponseRedirect(reverse_lazy('login'))),

    url(r'^login$', login, name='login'),
    url(r'^logout$', logout, name='logout'),
    url(r'^(?P<token>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/legal_signup$',
        AuthorisedRepresentativeSignUp.as_view(),
        name='representative_signup'),
    url(r'^(?P<token>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/advisor_signup',
        AdvisorSignUpView.as_view()),
    url(r'^confirm_email/(?P<type>\d+)/(?P<token>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})',
        EmailConfirmationView.as_view()),

    url(r'^confirm-joint-account/(?P<token>\w{64})$', confirm_joint_account, name='confirm-joint-account'),

    url(r'^confirmation$', Confirmation.as_view(), name='confirmation'),

    url(r'^betasmartz_admin/rebalance/(?P<pk>\d+)$', GoalRebalance.as_view()),

    url(r'^password/reset/$', PasswordResetView.as_view(), name='password_reset'),
    url(r'^password/reset/done/$',
        'django.contrib.auth.views.password_reset_done', name='password_reset_done'),
    url(r'^password/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        'django.contrib.auth.views.password_reset_confirm',
        {'post_reset_redirect': '/login'},
        name='password_reset_confirm'),

    url(r'^anymail/', include('anymail.urls')),

    #url(r'^client/2.0/api/',  include(router.urls)),

    # Legal Related
    url('^privacy-notice/$', TemplateView.as_view(template_name="legal/privacy_notice.html"), name='privacy_notice'),
    url('^terms-of-use/$', TemplateView.as_view(template_name="legal/terms_of_use.html"), name='terms_of_use'),
    url('^legal/$', TemplateView.as_view(template_name="legal/legal.html"), name='legal'),
    url('^product-brochure/$', TemplateView.as_view(template_name="legal/product_brochure.html"), name='product-brochure'),
    url('^oddcast/$', oddcast.index, name='oddcast')
)

if settings.DEBUG:
    urlpatterns += patterns(
        '',
        url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    )


media_storage = getattr(settings, 'DEFAULT_FILE_STORAGE', None)
if settings.DEBUG and media_storage != 'swift.storage.SwiftStorage':
    urlpatterns += patterns(
        '',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT,
          'show_indexes': True}),
    )
