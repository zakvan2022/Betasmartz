from client.models import HealthDevice
from django.core.urlresolvers import reverse
from django.conf import settings
from datetime import datetime, date, timedelta
from support.models import SupportRequest
from main.settings import FITBIT_SETTINGS, GOOGLEFIT_SETTINGS, MICROSOFTHEALTH_SETTINGS, \
    JAWBONE_SETTINGS, TOMTOM_SETTINGS, UNDERARMOUR_SETTINGS, WITHINGS_SETTINGS
from apiclient.discovery import build
from oauth2client.client import OAuth2Credentials, OAuth2WebServerFlow
from MicrosoftHealth import MHOauth2Client, MH
from MicrosoftHealth.Exceptions import *
from withings import WithingsAuth, WithingsApi, WithingsCredentials
from functools import reduce
import base64
import urllib.request as urllib2
from urllib.parse import quote_plus
import urllib
import json
import httplib2
import requests

def get_json_response(req):
    response = urllib2.urlopen(req)
    full_response = response.read()
    return json.loads(full_response.decode("utf-8"))

PERIOD = 7 # days
def get_data(client):
    try:
        healthdevice = client.health_device
    except:
        return None
    if healthdevice.provider == HealthDevice.ProviderType.FITBIT.value:
        return fitbit_get_data(healthdevice)
    if healthdevice.provider == HealthDevice.ProviderType.GOOGLE_FIT.value:
        return googlefit_get_data(healthdevice)
    if healthdevice.provider == HealthDevice.ProviderType.MICROSOFT_HEALTH.value:
        return microsofthealth_get_data(healthdevice)
    if healthdevice.provider == HealthDevice.ProviderType.UNDERARMOUR.value:
        return underarmour_get_data(healthdevice)
    if healthdevice.provider == HealthDevice.ProviderType.JAWBONE.value:
        return jawbone_get_data(healthdevice)
    if healthdevice.provider == HealthDevice.ProviderType.WITHINGS.value:
        return withings_get_data(healthdevice)
    if healthdevice.provider == HealthDevice.ProviderType.TOMTOM.value:
        return tomtom_get_data(healthdevice)
    return None


# FITBIT module
def fitbit_connect(client, code):
    try:
        healthdevice = client.health_device
    except:
        healthdevice = HealthDevice(client=client)

    token_url = '{}/oauth2/token'.format(FITBIT_SETTINGS['API_BASE'])

    #Form the data payload
    body_text = {'code' : code,
                'redirect_uri' : '{}/oauth2/health-devices/fitbit/'.format(settings.SITE_URL),
                'client_id' : FITBIT_SETTINGS['CLIENT_ID'],
                'grant_type' : 'authorization_code'}

    return fitbit_save_fields(healthdevice, token_url, body_text)


def fitbit_refresh_token(healthdevice):
    token_url = '{}/oauth2/token'.format(FITBIT_SETTINGS['API_BASE'])
    #Form the data payload
    body_text = {'grant_type' : 'refresh_token',
                 'refresh_token' : healthdevice.refresh_token,
                 'expires_in': FITBIT_SETTINGS['EXPIRES_IN']}

    return fitbit_save_fields(healthdevice, token_url, body_text)


def fitbit_get_redirect_uri():
    url = 'https://www.fitbit.com/oauth2/authorize'
    scope = '%20'.join([
        'activity',
        'profile',
        'weight'
    ])
    query = '&'.join([
        'response_type=code',
        'client_id={}'.format(FITBIT_SETTINGS['CLIENT_ID']),
        'redirect_uri={}%2Foauth2%2Fhealth-devices%2Ffitbit%2F'.format(settings.SITE_URL),
        'scope={}'.format(scope),
        'expires_in={}'.format(FITBIT_SETTINGS['EXPIRES_IN'])
    ])
    return '{}?{}'.format(url, query)


def fitbit_should_refresh_token(res):
    return 'success' in res and not res['success'] and res['errors']['errorType'] == 'expired_token'


def fitbit_save_fields(healthdevice, url, body_text):
    body_url_encoded = urllib.parse.urlencode(body_text)

    #Start the request
    req = urllib2.Request(url, body_url_encoded.encode('utf-8'))

    #Add the headers, first we base64 encode the client id and client secret with a : inbetween and create the authorisation header
    req.add_header('Authorization', bytes('Basic ', 'utf-8') + base64.b64encode(bytes(FITBIT_SETTINGS['CLIENT_ID'] + ":" + FITBIT_SETTINGS['CLIENT_SECRET'], 'utf-8')))
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')

    #Fire off the request
    try:
        res = get_json_response(req)
        healthdevice.provider = HealthDevice.ProviderType.FITBIT.value
        healthdevice.access_token = res['access_token']
        healthdevice.refresh_token = res['refresh_token']
        healthdevice.expires_at = datetime.now() + timedelta(seconds=int(res['expires_in']))
        healthdevice.meta = {
            'scope': res['scope'],
            'token_type': res['token_type'],
            'user_id': res['user_id']
        }
        healthdevice.save()
        return True
    except urllib2.URLError as e:
        print(e.code)
        print(e.read())
        return False


def fitbit_get_data(healthdevice):
    #These are the Fitbit URLs
    profile_url = '{}/1/user/-/profile.json'.format(FITBIT_SETTINGS['API_BASE'])
    activity_url = '{}/1/user/-/activities/goals/daily.json'.format(FITBIT_SETTINGS['API_BASE'])

    try:
        #Start the request
        req = urllib2.Request(profile_url)
        req.add_header('Authorization', 'Bearer ' + healthdevice.access_token)
        res = get_json_response(req)
        if fitbit_should_refresh_token(res):
            fitbit_refresh_token(healthdevice)
            res = get_json_response(req)

        height = float(res['user']['height'])
        weight = float(res['user']['weight'])
        h_mul = 0.3048 if res['user']['heightUnit'] == 'en_US' else 1 # feet to cm
        w_mul = 0.453592 if res['user']['weightUnit'] == 'en_US' else 1 # oz to kg

        req = urllib2.Request(activity_url)
        req.add_header('Authorization', 'Bearer ' + healthdevice.access_token)
        response = urllib2.urlopen(req)
        full_response = response.read()
        res = json.loads(full_response.decode("utf-8"))

        active_minutes = res['goals']['activeMinutes']

        return {
            'height': round(height / h_mul, 1),
            'weight': round(weight / w_mul, 1),
            'daily_exercise': active_minutes
        }
    except urllib2.URLError as e:
        print(e.code)
        print(e.read())
        return None


# Google Fit module
google_scopes = [
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.body.read',
    'https://www.googleapis.com/auth/fitness.body.write',
    'https://www.googleapis.com/auth/fitness.reproductive_health.read',
]

def googlefit_get_redirect_uri():
    url = 'https://accounts.google.com/o/oauth2/v2/auth'
    query = '&'.join([
        'prompt=consent',
        'response_type=code',
        'client_id={}'.format(GOOGLEFIT_SETTINGS['CLIENT_ID']),
        'redirect_uri={}/oauth2/health-devices/google-fit/'.format(settings.SITE_URL),
        'scope={}'.format('+'.join(google_scopes)),
        'access_type=offline'
    ])
    return '{}?{}'.format(url, query)


def googlefit_connect(client, code):
    try:
        healthdevice = client.health_device
    except:
        healthdevice = HealthDevice(client=client)

    flow = OAuth2WebServerFlow(GOOGLEFIT_SETTINGS['CLIENT_ID'],
                               GOOGLEFIT_SETTINGS['CLIENT_SECRET'],
                               google_scopes,
                               '{}/oauth2/health-devices/google-fit/'.format(settings.SITE_URL))
    try:
        credentials = flow.step2_exchange(code)

        healthdevice.provider = HealthDevice.ProviderType.GOOGLE_FIT.value
        healthdevice.access_token = credentials.access_token
        healthdevice.refresh_token = credentials.refresh_token
        healthdevice.expires_at = credentials.token_expiry
        healthdevice.meta = {}
        healthdevice.save()
        return True
    except:
        return False


def to_nano_epoch(dt):
    return int(round(dt.timestamp() * 1000000000))


def googlefit_get_data(healthdevice):
    height_source = 'derived:com.google.height:com.google.android.gms:merge_height'
    weight_source = 'derived:com.google.weight:com.google.android.gms:merge_weight'
    activity_source = 'derived:com.google.activity.segment:com.google.android.gms:merge_activity_segments'
    # The ID is formatted like: "startTime-endTime" where startTime and endTime are
    # 64 bit integers (epoch time with nanoseconds).
    DATA_SET = "0-{}".format(to_nano_epoch(datetime.now()))

    credentials = OAuth2Credentials(healthdevice.access_token,
                      GOOGLEFIT_SETTINGS['CLIENT_ID'],
                      GOOGLEFIT_SETTINGS['CLIENT_SECRET'],
                      healthdevice.refresh_token,
                      healthdevice.expires_at,
                      'https://accounts.google.com/o/oauth2/token', # token_uri
                      None) # user_agent

    http = httplib2.Http()
    http = credentials.authorize(http)
    fitness_service = build('fitness', 'v1', http=http, cache_discovery=False)

    res = fitness_service.users().dataSources().datasets(). \
              get(userId='me', dataSourceId=height_source, datasetId=DATA_SET, limit=1). \
              execute()
    height = res['point'][0]['value'][0]['fpVal'] * 100 if len(res['point']) > 0 else 0

    res = fitness_service.users().dataSources().datasets(). \
              get(userId='me', dataSourceId=weight_source, datasetId=DATA_SET, limit=1). \
              execute()
    weight = res['point'][0]['value'][0]['fpVal'] if len(res['point']) > 0 else 0

    activity_data_set = '{}-{}'.format(to_nano_epoch(datetime.now() - timedelta(days=PERIOD)), to_nano_epoch(datetime.now()))
    res = fitness_service.users().dataSources().datasets(). \
              get(userId='me', dataSourceId=activity_source, datasetId=activity_data_set). \
              execute()
    if len(res['point']) > 0:
        daily_exercise = reduce((lambda acc, item: acc + int(item['endTimeNanos'])-int(item['startTimeNanos'])), res['point'], 0) / PERIOD
    else:
        daily_exercise = 0

    return {
        'height': round(height, 1),
        'weight': round(weight, 1),
        'daily_exercise': round(daily_exercise / (1000000000 * 60)) # nano sec to minutes
    }


# Microsoft Health Module
microsoft_scopes = [
    'mshealth.ReadProfile',
    'mshealth.ReadActivityHistory',
]

microsoft_redirect_uri = '{}/oauth2/health-devices/microsoft-health/'.format(settings.SITE_URL)
def microsofthealth_get_redirect_uri():
    url = 'https://login.live.com/oauth20_authorize.srf'
    query = '&'.join([
        'response_type=code',
        'client_id={}'.format(MICROSOFTHEALTH_SETTINGS['CLIENT_ID']),
        'redirect_uri={}'.format(microsoft_redirect_uri),
        'scope={}'.format('+'.join(microsoft_scopes))
    ])
    return '{}?{}'.format(url, query)


def microsofthealth_connect(client, code):
    try:
        healthdevice = client.health_device
    except:
        healthdevice = HealthDevice(client=client)

    mh_oauth_object = MHOauth2Client(client_id = MICROSOFTHEALTH_SETTINGS['CLIENT_ID'],
                                   client_secret = MICROSOFTHEALTH_SETTINGS['CLIENT_SECRET'])

    try:
        token_info = mh_oauth_object.fetch_access_token(code, redirect_uri=microsoft_redirect_uri)
        healthdevice.provider = HealthDevice.ProviderType.MICROSOFT_HEALTH.value
        healthdevice.access_token = token_info['access_token']
        if 'refresh_token' in token_info:
            healthdevice.refresh_token = token_info['refresh_token']
        healthdevice.expires_at = datetime.now() + timedelta(seconds=int(token_info['expires_in']))
        healthdevice.meta = {
            'user_id': token_info['user_id']
        }
        healthdevice.save()
        return True
    except:
        return False


def microsofthealth_get_data(healthdevice):
    dt_start = datetime.now() - timedelta(days=PERIOD)
    activity_url = '/v1/me/Summaries/daily?startTime={}Z'.format(dt_start.isoformat())
    try:
        mh_object = MH(microsoft_health_key = MICROSOFTHEALTH_SETTINGS['CLIENT_ID'],
                      microsoft_health_secret = MICROSOFTHEALTH_SETTINGS['CLIENT_SECRET'],
                      access_token = healthdevice.access_token,
                      refresh_token = healthdevice.refresh_token)
        profile = mh_object.user_profile_get(user_id=healthdevice.meta['user_id'])

        height = float(profile['height']) / 10
        weight = float(profile['weight']) / 1000
        daily_summary = mh_object.make_request(mh_object.API_ENDPOINT + activity_url)
        total_seconds = reduce(lambda acc, item: acc + (item['activeHours'] * 3600 if 'activeHours' in item else 0) + (item['activeSeconds'] if 'activeSeconds' in item else 0), daily_summary['summaries'], 0)
        return {
            'height': round(height, 1),
            'weight': round(weight, 1),
            'daily_exercise': round(total_seconds / 60, 0)
        }
    except HTTPNotFound as e:
        # return e
        return None


# Under Armour
def underarmour_get_redirect_uri():
    url = 'https://www.mapmyfitness.com/v7.1/oauth2/authorize/'
    query = '&'.join([
        'response_type=code',
        'client_id={}'.format(UNDERARMOUR_SETTINGS['CLIENT_ID']),
        'redirect_uri={}/oauth2/health-devices/under-armour/'.format(settings.SITE_URL)
    ])
    return '{}?{}'.format(url, query)


def underarmour_connect(client, code):
    try:
        healthdevice = client.health_device
    except:
        healthdevice = HealthDevice(client=client)
    access_token_url = 'https://api.mapmyfitness.com/v7.1/oauth2/access_token/'
    access_token_data = {
        'grant_type': 'authorization_code',
        'client_id': UNDERARMOUR_SETTINGS['CLIENT_ID'],
        'client_secret': UNDERARMOUR_SETTINGS['CLIENT_SECRET'],
        'code': code
    }
    response = requests.post(url=access_token_url,
                             data=access_token_data,
                             headers={'Api-Key': UNDERARMOUR_SETTINGS['CLIENT_ID']})
    return underarmour_save_fields(healthdevice, response)


def underarmour_refresh_token(healthdevice):
    refresh_token_url = '{}/oauth2/access_token/'.format(UNDERARMOUR_SETTINGS['API_BASE'])
    #Form the data payload
    refresh_token_data = {'grant_type' : 'refresh_token',
                          'refresh_token' : healthdevice.refresh_token,
                          'client_id': UNDERARMOUR_SETTINGS['CLIENT_ID'],
                          'client_secret': UNDERARMOUR_SETTINGS['CLIENT_SECRET']}
    response = requests.post(url=refresh_token_url, data=refresh_token_data,
                             headers={'api-key': UNDERARMOUR_SETTINGS['CLIENT_ID'],
                                      'authorization': 'Bearer %s' % healthdevice.access_token})
    return underarmour_save_fields(healthdevice, response)


def underarmour_save_fields(healthdevice, response):
    try:
        token_info = response.json()

        healthdevice.provider = HealthDevice.ProviderType.UNDERARMOUR.value
        healthdevice.access_token = token_info['access_token']
        healthdevice.refresh_token = token_info['refresh_token']
        healthdevice.expires_at = datetime.now() + timedelta(seconds=int(token_info['expires_in']))
        healthdevice.meta = {
            'token_type': token_info['token_type'],
            'user_id': token_info['user_id'],
            'scope': token_info['scope'],
            'user_href': token_info['user_href']
        }
        healthdevice.save()
        return True
    except:
        print(response)
        print(response.content)
        return False


def underarmour_make_request(url, healthdevice):
    return requests.get(url=url, verify=False,
                        headers={'api-key': UNDERARMOUR_SETTINGS['CLIENT_ID'],
                                 'authorization': 'Bearer %s' % healthdevice.access_token})


def underarmour_get_data(healthdevice):
    #These are the Fitbit URLs
    profile_url = '{}/user/self/'.format(UNDERARMOUR_SETTINGS['API_BASE'])
    aggregate_url = '{}/aggregate'.format(UNDERARMOUR_SETTINGS['API_BASE'])

    height = None
    weight = None
    daily_exercise = None
    profile_error = False
    aggregate_error = False

    response = underarmour_make_request(profile_url, healthdevice)
    if response.status_code == 401: # token expired
        underarmour_refresh_token(healthdevice)
        response = underarmour_make_request(profile_url, healthdevice)

    try:
        profile_json = response.json()
        print(profile_json)
        height = round(profile_json['height'] * 100, 1)
        weight = round(profile_json['weight'], 1)
    except:
        print(response)
        profile_error = True

    query = '&'.join([
        'data_types=sessions_summary',
        'end_datetime={}Z'.format(datetime.now().isoformat()),
        'period=P1D',
        'start_datetime={}Z'.format((datetime.now() - timedelta(days=PERIOD)).isoformat()),
        'user_id={}'.format(healthdevice.meta['user_id'])
    ])
    response = underarmour_make_request('{}?{}'.format(aggregate_url, query), healthdevice)
    try:
        aggregate_json = response.json()
        print(aggregate_json)
        aggregates = aggregate_json['_embedded']['aggregates']
        total_seconds = reduce(lambda acc, item: acc + (item['summary']['value']['sessions_active_time_sum'] if 'summary' in item else 0), aggregates, 0)
        daily_exercise = round(total_seconds / (PERIOD * 60), 0)
    except:
        print(response)
        aggregate_error = True

    if profile_error and aggregate_error:
        return None
    else:
        return {
            'height': height,
            'weight': weight,
            'daily_exercise': daily_exercise
        }


# JAWBONE
def jawbone_get_redirect_uri():
    url = 'https://jawbone.com/auth/oauth2/auth'
    query = '&'.join([
        'response_type=code',
        'client_id={}'.format(JAWBONE_SETTINGS['CLIENT_ID']),
        'scope=basic_read+extended_read+weight_read+move_read',
        'redirect_uri={}/oauth2/health-devices/jawbone/'.format(settings.SITE_URL)
    ])
    return '{}?{}'.format(url, query)


def jawbone_connect(client, code):
    try:
        healthdevice = client.health_device
    except:
        healthdevice = HealthDevice(client=client)
    access_token_url = 'https://jawbone.com/auth/oauth2/token'
    access_token_data = {
        'grant_type': 'authorization_code',
        'client_id': JAWBONE_SETTINGS['CLIENT_ID'],
        'client_secret': JAWBONE_SETTINGS['CLIENT_SECRET'],
        'code': code
    }
    response = requests.post(url=access_token_url, data=access_token_data)
    return jawbone_save_fields(healthdevice, response)


def jawbone_save_fields(healthdevice, response):
    try:
        token_info = response.json()

        healthdevice.provider = HealthDevice.ProviderType.JAWBONE.value
        healthdevice.access_token = token_info['access_token']
        healthdevice.refresh_token = token_info['refresh_token']
        healthdevice.expires_at = datetime.now() + timedelta(seconds=int(token_info['expires_in']))
        healthdevice.meta = {
            'token_type': token_info['token_type']
        }
        healthdevice.save()
        return True
    except:
        print(response)
        print(response.content)
        return False


def jawbone_make_request(url, healthdevice):
    return requests.get(url=url, headers={'Accept': 'application/json',
                                          'authorization': 'Bearer %s' % healthdevice.access_token})


def jawbone_refresh_token(healthdevice):
    refresh_token_url = 'https://jawbone.com/auth/oauth2/token'
    #Form the data payload
    refresh_token_data = {'grant_type' : 'refresh_token',
                          'refresh_token' : healthdevice.refresh_token,
                          'client_id': JAWBONE_SETTINGS['CLIENT_ID'],
                          'client_secret': JAWBONE_SETTINGS['CLIENT_SECRET']}
    response = requests.post(url=refresh_token_url, data=refresh_token_data)
    return jawbone_save_fields(healthdevice, response)


def jawbone_get_data(healthdevice):
    #These are the Fitbit URLs
    profile_url = '{}/users/@me'.format(JAWBONE_SETTINGS['API_BASE'])
    moves_url = '{}/users/@me/moves'.format(JAWBONE_SETTINGS['API_BASE'])

    height = None
    weight = None
    daily_exercise = None
    profile_error = False
    moves_error = False

    response = jawbone_make_request(profile_url, healthdevice)
    profile_json = response.json()
    if response.status_code >= 400: # token expired
        jawbone_refresh_token(healthdevice)
        response = jawbone_make_request(profile_url, healthdevice)
        profile_json = response.json()

    try:
        profile_json = response.json()
        height = round(profile_json['data']['height'] * 100, 1)
        weight = round(profile_json['data']['weight'], 1)
    except:
        profile_error = True

    query = '&'.join([
        'start_time={}'.format(int((datetime.now() - timedelta(days=PERIOD)).timestamp())),
        'end_time={}'.format(int(datetime.now().timestamp()))
    ])
    response = jawbone_make_request('{}?{}'.format(moves_url, query), healthdevice)
    try:
        moves_json = response.json()
        moves_items = moves_json['data']['items']
        total_seconds = reduce(lambda acc, item: acc + (item['details']['active_time'] if 'details' in item else 0), moves_items, 0)
        daily_exercise = round(total_seconds / (PERIOD * 60), 0)
    except:
        moves_error = True

    if profile_error and moves_error:
        return None
    else:
        return {
            'height': height,
            'weight': weight,
            'daily_exercise': daily_exercise
        }


# WITHINGS
def withings_get_redirect_uri():
    return settings.SITE_URL + reverse('oauth1healthdevices:withings-redirect')


def withings_get_callback_uri():
    return settings.SITE_URL + reverse('oauth1healthdevices:withings')


def withings_authorize_url(client):
    auth = WithingsAuth(WITHINGS_SETTINGS['CONSUMER_KEY'],
                        WITHINGS_SETTINGS['CONSUMER_SECRET'],
                        withings_get_callback_uri())
    authorize_url = auth.get_authorize_url()
    auth.oauth_token
    auth.oauth_secret


def withings_connect(client, oauth_verifier, oauth_token, oauth_secret):
    try:
        healthdevice = client.health_device
    except:
        healthdevice = HealthDevice(client=client)
    auth = WithingsAuth(WITHINGS_SETTINGS['CONSUMER_KEY'],
                        WITHINGS_SETTINGS['CONSUMER_SECRET'],
                        withings_get_callback_uri())
    auth.oauth_token = oauth_token
    auth.oauth_secret = oauth_secret
    print(oauth_verifier, oauth_token, oauth_secret)
    creds = auth.get_credentials(oauth_verifier)
    try:
        healthdevice = client.health_device
    except:
        healthdevice = HealthDevice(client=client)
    healthdevice.provider = HealthDevice.ProviderType.WITHINGS.value
    healthdevice.access_token = creds.access_token
    healthdevice.refresh_token = ''
    healthdevice.expires_at = datetime.now() + timedelta(days=365)
    healthdevice.meta = {
        'access_token_secret': creds.access_token_secret,
        'user_id': creds.user_id
    }
    healthdevice.save()
    return True


def withings_get_item_duration(item):
    if 'data' in item:
        data = item['data']
        if 'effduration' in data:
            return data['effduration']
        elif 'duration' in data:
            return data['duration']
        return 0
    else:
        return 0


def withings_get_data(healthdevice):
    height = None
    weight = None
    daily_exercise = None

    creds= WithingsCredentials(access_token=healthdevice.access_token,
                               access_token_secret=healthdevice.meta['access_token_secret'],
                               consumer_key=WITHINGS_SETTINGS['CONSUMER_KEY'],
                               consumer_secret=WITHINGS_SETTINGS['CONSUMER_SECRET'],
                               user_id=healthdevice.meta['user_id'])

    client = WithingsApi(creds)
    try:
        measures = client.get_measures(limit=1, meastype='1') # measure type: weight
        weight = measures[0].weight
    except:
        pass

    try:
        measures = client.get_measures(limit=1, meastype='4') # mesuare type: height
        height = measures[0].height * 100
    except:
        pass

    try:
        workouts_params = {
            'userid': healthdevice.meta['user_id'],
            'startdateymd': (date.today() - timedelta(days=PERIOD)).isoformat(),
            'enddateymd': date.today().isoformat()
        }
        workouts = client.request('v2/measure', 'getworkouts', params=workouts_params)
        if 'series' in workouts:
            total_seconds = reduce(lambda acc, item: acc + withings_get_item_duration(item), workouts['series'], 0)
            daily_exercise = round(total_seconds / (PERIOD * 60), 0)
    except:
        pass

    if height is None and weight is None and daily_exercise is None:
        return None
    else:
        return {
            'height': height,
            'weight': weight,
            'daily_exercise': daily_exercise
        }


# TOMTOM module
def tomtom_get_redirect_uri():
    url = '{}/oauth2/authorize'.format(TOMTOM_SETTINGS['API_BASE'])
    query = '&'.join([
        'Api-Key={}'.format(TOMTOM_SETTINGS['API_KEY']),
        'response_type=code',
        'scope=physiology+tracking',
        'client_id={}'.format(TOMTOM_SETTINGS['CLIENT_ID']),
        'redirect_uri={}/oauth2/health-devices/tomtom/'.format(settings.SITE_URL)
    ])
    return '{}?{}'.format(url, query)


def tomtom_connect(client, code):
    try:
        healthdevice = client.health_device
    except:
        healthdevice = HealthDevice(client=client)
    access_token_url = '{}/oauth2/token'.format(TOMTOM_SETTINGS['API_BASE'])
    access_token_data = {
        'grant_type': 'authorization_code',
        'client_id': TOMTOM_SETTINGS['CLIENT_ID'],
        'redirect_uri': '{}/oauth2/health-devices/tomtom/'.format(settings.SITE_URL),
        'code': code
    }
    auth_header = bytes('Basic ', 'utf-8') + \
        base64.b64encode(bytes(TOMTOM_SETTINGS['CLIENT_ID'] + ":" + TOMTOM_SETTINGS['CLIENT_SECRET'], 'utf-8'))
    response = requests.post(url=access_token_url,
                             data=access_token_data,
                             headers={'Authorization': auth_header,
                                      'Api-Key': TOMTOM_SETTINGS['API_KEY']})
    return tomtom_save_fields(healthdevice, response)


def tomtom_save_fields(healthdevice, response):
    try:
        token_info = response.json()
        print('success: ', token_info)

        healthdevice.provider = HealthDevice.ProviderType.TOMTOM.value
        healthdevice.access_token = token_info['access_token']
        healthdevice.refresh_token = token_info['refresh_token']
        healthdevice.expires_at = datetime.now() + timedelta(seconds=int(token_info['expires_in']))
        healthdevice.meta = {
            'token_type': token_info['token_type'],
            'scope': token_info['scope']
        }
        healthdevice.save()
        return True
    except:
        print(response.content)
        return False


def tomtom_refresh_token(healthdevice):
    refresh_token_url = '{}/oauth2/token'.format(TOMTOM_SETTINGS['API_BASE'])
    #Form the data payload
    auth_header = bytes('Basic ', 'utf-8') + \
        base64.b64encode(bytes(TOMTOM_SETTINGS['CLIENT_ID'] + ":" + TOMTOM_SETTINGS['CLIENT_SECRET'], 'utf-8'))
    refresh_token_data = {'grant_type' : 'refresh_token',
                          'refresh_token' : healthdevice.refresh_token,
                          'client_id': TOMTOM_SETTINGS['CLIENT_ID'],
                          'redirect_uri': '{}/oauth2/health-devices/tomtom/'.format(settings.SITE_URL)}
    response = requests.post(url=refresh_token_url,
                             data=refresh_token_data,
                             headers={'Authorization': auth_header,
                                      'Api-Key': TOMTOM_SETTINGS['API_KEY']})
    return tomtom_save_fields(healthdevice, response)



def tomtom_get_item_summary(item):
    date_key = list(item.keys())[0]
    return float(item[date_key]['summary'])

def tomtom_get_data(healthdevice):
    height = None
    weight = None
    daily_exercise = None

    req_headers = {'Authorization': 'Bearer ' + healthdevice.access_token,
             'Api-Key': TOMTOM_SETTINGS['API_KEY']}

    tracking_url = '{}/1/tracking?days={}'.format(TOMTOM_SETTINGS['API_BASE'], PERIOD)
    response = requests.get(url=tracking_url, headers=req_headers)
    print(response.content, response.status_code)
    if response.status_code >= 401: # token expired
        tomtom_refresh_token(healthdevice)
        response = requests.get(url=tracking_url, headers=req_headers)

    tracking_json = response.json()
    weights = tracking_json['series']['weight']
    active_times = tracking_json['series']['active_time']

    if len(weights) > 0:
        weight = round(tomtom_get_item_summary(weights[0]), 1)

    if len(active_times) > 0:
        daily_exercise = round(reduce((lambda acc, item: acc + tomtom_get_item_summary(item)), active_times, 0) / (PERIOD * 60))

    if height is None and weight is None and daily_exercise is None:
        return None
    else:
        return {
            'height': height,
            'weight': weight,
            'daily_exercise': daily_exercise
        }
