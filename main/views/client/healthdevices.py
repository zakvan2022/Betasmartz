from client import healthdevice
from client.models import HealthDevice
from datetime import datetime, timedelta
from django.shortcuts import render
from support.models import SupportRequest
from withings import WithingsAuth, WithingsApi
from main.settings import WITHINGS_SETTINGS

def fitbit(request):
    user = SupportRequest.target_user(request)
    code = request.GET.get('code', None)
    status = False
    if code is not None:
        status = healthdevice.fitbit_connect(user.client, code)

    context = {
        'provider': HealthDevice.ProviderType.FITBIT.value,
        'status': status
    }
    return render(request, 'healthdevices/oauth2.html', context)

def google_fit(request):
    user = SupportRequest.target_user(request)
    code = request.GET.get('code', None)
    status = False
    if code is not None:
        status = healthdevice.googlefit_connect(user.client, code)

    context = {
        'provider': HealthDevice.ProviderType.GOOGLE_FIT.value,
        'status': status
    }
    return render(request, 'healthdevices/oauth2.html', context)

def microsoft_health(request):
    user = SupportRequest.target_user(request)
    code = request.GET.get('code', None)
    status = False
    if code is not None:
        status = healthdevice.microsofthealth_connect(user.client, code)

    context = {
        'provider': HealthDevice.ProviderType.MICROSOFT_HEALTH.value,
        'status': status
    }
    return render(request, 'healthdevices/oauth2.html', context)

def under_armour(request):
    user = SupportRequest.target_user(request)
    code = request.GET.get('code', None)
    status = False
    if code is not None:
        status = healthdevice.underarmour_connect(user.client, code)

    context = {
        'provider': HealthDevice.ProviderType.UNDERARMOUR.value,
        'status': status
    }
    return render(request, 'healthdevices/oauth2.html', context)

def withings_redirect(request):
    auth = WithingsAuth(WITHINGS_SETTINGS['CONSUMER_KEY'],
                        WITHINGS_SETTINGS['CONSUMER_SECRET'],
                        healthdevice.withings_get_callback_uri())
    authorize_url = auth.get_authorize_url()
    request.session['withings_oauth_token'] = auth.oauth_token
    request.session['withings_oauth_secret'] = auth.oauth_secret
    context = {
        'authorize_url': authorize_url
    }
    return render(request, 'healthdevices/oauth_redirect.html', context)

def withings(request):
    user = SupportRequest.target_user(request)
    oauth_verifier = request.GET.get('oauth_verifier', None)
    status = False
    if 'withings_oauth_token' in request.session and oauth_verifier is not None:
        oauth_token = request.session.pop('withings_oauth_token')
        oauth_secret = request.session.pop('withings_oauth_secret')
        status = healthdevice.withings_connect(user.client, oauth_verifier, oauth_token, oauth_secret)

    context = {
        'provider': HealthDevice.ProviderType.WITHINGS.value,
        'status': status
    }
    return render(request, 'healthdevices/oauth2.html', context)

def jawbone(request):
    user = SupportRequest.target_user(request)
    code = request.GET.get('code', None)
    status = False
    if code is not None:
        status = healthdevice.jawbone_connect(user.client, code)

    context = {
        'provider': HealthDevice.ProviderType.JAWBONE.value,
        'status': status
    }
    return render(request, 'healthdevices/oauth2.html', context)

def tomtom(request):
    user = SupportRequest.target_user(request)
    code = request.GET.get('code', None)
    status = False
    if code is not None:
        status = healthdevice.tomtom_connect(user.client, code)

    context = {
        'provider': HealthDevice.ProviderType.TOMTOM.value,
        'status': status
    }
    return render(request, 'healthdevices/oauth2.html', context)
