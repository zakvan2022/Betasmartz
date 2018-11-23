from __future__ import unicode_literals

from django.conf.urls import include, patterns, url

from . import views


composites_urlpatterns = patterns(
    '',

    url(r'^create$', views.AdvisorCompositeNew.as_view(),
        name='create'),
    url(r'^(?P<pk>\d+)$', views.AdvisorAccountGroupDetails.as_view(),
        name='detail'),
    url(r'^(?P<pk>\d+)/edit$', views.AdvisorCompositeEdit.as_view(),
        name='edit'),
    url(
        r'^(?P<account_id>\d+)/account-groups/(?P<account_group_id>\d+)$',
        views.AdvisorRemoveAccountFromGroupView.as_view(),
        name='detail-account-groups-delete'),
    url(r'^(?P<pk>\d+)/clients$',
        views.AdvisorAccountGroupClients.as_view(),
        name='detail-clients'),
    url(r'^(?P<pk>\d+)/secondary-advisors$',
        views.AdvisorAccountGroupSecondaryDetailView.as_view(),
        name='detail-secondary-advisors'),
    url(r'^(?P<pk>\d+)/secondary-advisors/create$',
        views.AdvisorAccountGroupSecondaryCreateView.as_view(),
        name='detail-secondary-advisors-create'),
    url(r'^(?P<pk>\d+)/secondary-advisors/(?P<sa_pk>\d+)$',
        views.AdvisorAccountGroupSecondaryDeleteView.as_view(),
        name='detail-secondary-advisors-delete'),
    url(r'^client-accounts/(?P<pk>\d+)/fee$',
        views.AdvisorClientAccountChangeFee.as_view(),
        name='client-accounts-fee'),
)


clients_urlpatterns = patterns(
    '',

    url(r'^$', views.AdvisorClients.as_view(), name='list'),
    url(r'^(?P<pk>\d+)$', views.AdvisorClientDetails.as_view(),
        name='detail'),
    url(r'^(?P<pk>\d+)/accounts$', views.AdvisorClientAccountsDetails.as_view(),
        name='accountsdetail'),
    url(r'^(?P<pk>\d+)/account-invites$',
        views.AdvisorCreateNewAccountForExistingClient.as_view(),
        name='account-invites'),

    url(r'^(?P<pk>\d+)/account-invites/create$',
        views.AdvisorCreateNewAccountForExistingClientSelectAccountType.as_view(),
        name='account-invites-create'),

    url(r'^invites$', views.AdvisorClientInvites.as_view(), name='invites'),
    url(r'^invites/(?P<pk>\d+)/resend$', views.AdvisorNewClientResendInviteView.as_view(), name='invites-resend'),
    url(r'^invites/new$', views.AdvisorNewClientInviteView.as_view(), name='invites-new'),

    url(r'^invites/create$', views.AdvisorClientInviteNewView.as_view(),
        name='invites-create'),
    url(r'^invites/create/profile$',
        views.CreateNewClientPrepopulatedView.as_view(),
        name='invites-create-profile'),
    url(r'^invites/(?P<pk>\d+)/create/personal-details$',
        views.BuildPersonalDetails.as_view(),
        name='invites-create-personal-details'),
    url(r'^invites/(?P<pk>\d+)/create/financial-details$',
        views.BuildFinancialDetails.as_view(),
        name='invites-create-financial-details'),
    url(r'^invites/(?P<pk>\d+)/create/confirm$',
        views.BuildConfirm.as_view(), name='invites-create-confirm'),
    url(r'^invites/(?P<pk>\d+)/delete$', views.AdvisorClientInvitesDeleteView.as_view(),name='delete'),

)


support_form_urlpatterns = patterns(
    '',
    url(r'^$', views.AdvisorSupportForms.as_view(), name='list'),
    url(r'^change/firm$', views.AdvisorChangeDealerGroupView.as_view(),
        name='change-firm'),
    url(r'^change/firm/update/(?P<pk>\d+)$',
        views.AdvisorChangeDealerGroupUpdateView.as_view()),
    url(r'^transfer/single$',
        views.AdvisorSingleInvestorTransferView.as_view(),
        name='transfer-single'),
    url(r'^transfer/single/update/(?P<pk>\d+)$',
        views.AdvisorSingleInvestorTransferUpdateView.as_view()),
    url(r'^transfer/bulk$',
        views.AdvisorBulkInvestorTransferView.as_view(),
        name='transfer-bulk'),
    url(r'^transfer/bulk/update/(?P<pk>\d+)$',
        views.AdvisorBulkInvestorTransferUpdateView.as_view()),
)


urlpatterns = patterns(
    '',
    url(r'^overview', views.AdvisorCompositeOverview.as_view(), name='overview'),

    url(r'^composites/', include(composites_urlpatterns, namespace='composites', app_name='composites')),

    url(r'^clients/', include(clients_urlpatterns, namespace='clients', app_name='clients')),

    url(r'^agreements$', views.AdvisorAgreements.as_view(), name='agreements'),
    url(r'^agreements/(?P<client_id>\d+)/download$', views.AdvisorDownloadAgreement.as_view(), name='download-agreement'),

    url(r'^support$', views.AdvisorSupport.as_view(), name='support'),
    url(r'^support/getting-started$', views.AdvisorSupportGettingStarted.as_view(),
        name='support-getting-started'),
    url(r'^support/forms/?', include(support_form_urlpatterns, namespace='support-forms', app_name='support-forms')),
)
