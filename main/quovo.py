from django.conf import settings
import os
import requests
import logging
logger = logging.getLogger('main.quovo')

api_base = settings.QUOVO_API_BASE
username = settings.QUOVO_USERNAME
password = settings.QUOVO_PASSWORD
SESSION_TOKEN_KEY = "token"
TOKEN_NAME = "main_token"


class ErrorResp:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _create_user(req, username, fullname):
    resp = _make_request(req, "users", {'username': username, 'name': fullname})
    if resp.status_code == 201:
        return resp.json()["user"]

    return None

def _get_token(req):
    # Check that the token is still valid in Quovo
    url = os.path.join(api_base, "tokens")
    resp = requests.get(url, auth=(username, password))
    all_tokens = resp.json()["access_tokens"]
    if TOKEN_NAME not in [token["name"] for token in all_tokens]:
        # Quovo doesn't know about this token.
        # If it's in our session we need to delete it.
        if SESSION_TOKEN_KEY in req.session:
            del req.session[SESSION_TOKEN_KEY]
    elif SESSION_TOKEN_KEY not in req.session:
        # Quovo has this token, but for some reason we
        # don't, so tell Quovo to delete it
        resp = requests.delete(url, auth=(username, password), data={"name": TOKEN_NAME})

    # Now Quovo's list of our tokens and what is in our
    # session should be in sync. If the token is not in
    # the session, we need a new one.
    if SESSION_TOKEN_KEY not in req.session:
        resp = requests.post(url, auth=(username, password), data={"name": TOKEN_NAME})
        token = resp.json()["access_token"]["token"]
        req.session[SESSION_TOKEN_KEY] = token

    return req.session[SESSION_TOKEN_KEY]

"""
Given a request, an endpoint, and (if a POST request) some data,
retun a Django response object.
"""
def _make_request(req, endpoint, data=None):
    url = os.path.join(api_base, endpoint)
    try:
        token = _get_token(req)
        headers = {"Authorization": "Bearer {0}".format(token)}
        if data is None:
            # Assume a GET request for now
            return requests.get(url, headers=headers)
        else:
            # Assume a POST request for now
            return requests.post(url, headers=headers, data=data)
    except Exception as e:
        logger.error(e)
        # return a value so resp.status_code checks don't error out
        return ErrorResp(status_code=500)


def _user_exists(req, username):
    resp = _make_request(req, "users?username=" + username)
    if resp.status_code == 200:
        return resp.json()["user"]
    elif resp.status_code == 404:
        return None

    # Something went wrong with the check attempt.
    # How should we handle this?
    return None

def get_iframe_token(req, django_user):
    # The only unique and guaranteed field on a Betasmartz user is
    # the email address, so use that as the name of the Quovo user.
    username = django_user.email
    # Test if this user already exists on Quovo
    user = _user_exists(req, username)
    if not user:
        # This will be a new Quovo user. Create it with the same username
        # and full name as the Django user. We could also include the user's
        # email and phone, but as of now we're not doing that.
        user = _create_user(req, username, django_user.get_full_name())

    # Hopefully "user" exists now.
    if user:
        data = {
            "user": user["id"],
            "beta": True  # Have to add this for the time being
                          # until Quovo says it's no longer needed.
        }
        resp = _make_request(req, "iframe_token", data)
        if resp.status_code == 201:
            return resp.json()["iframe_token"]["token"]

    logger.error("unable to create Quovo user for user {0}".format(
        django_user
    ))
    return None

def get_accounts(req, django_user):
    username = django_user.email
    # Test if this user already exists on Quovo
    user = _user_exists(req, username)
    if user:
        user_id = user["id"]
        endpoint = "users/{0}/accounts".format(user_id)
        resp = _make_request(req, endpoint)
        if resp.status_code == 200:
            return resp.json()["accounts"]

    # The user doesn't exist
    logger.error("There is no Quovo account for user {0}".format(
        django_user
    ))
    return None
