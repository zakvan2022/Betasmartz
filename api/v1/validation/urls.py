from __future__ import unicode_literals

from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^email', views.EmailValidationView.as_view(), name='email'),
    url(r'^phonenumber', views.PhoneNumberValidationView.as_view(), name='phonenumber'),
    url(r'^ib-account', views.IBAccountValidationView.as_view(), name='ib-account'),
    url(r'^composite', views.CompositeValidationView.as_view(), name='composite'),
)
