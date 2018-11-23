from __future__ import unicode_literals

from django.conf.urls import patterns, url
from rest_framework_extensions.routers import ExtendedSimpleRouter

from . import views

router = ExtendedSimpleRouter(trailing_slash=False)

authorised_representative_router = router.register(r'representatives', views.RepresentativeViewSet)

urlpatterns = patterns(
    '',
    url(r'^(?P<pk>\d+)/?$', views.FirmSingleView.as_view(), name='single'),
    url(r'^register-user/?$', views.FirmUserRegisterView.as_view(), name='register-user'),
    url(r'^invites/(?P<invite_key>\w+)/?$', views.FirmInvitesView.as_view(), name='invite-detail'),
    url(r'^invites/(?P<invite_key>\w+)/resend/?$', views.FirmResendInviteView.as_view(), name='resend-invite'),
    url(r'^request-onboarding/?$', views.FirmRequestOnboardingView.as_view(), name='request-onboarding'),
)

urlpatterns += router.urls
