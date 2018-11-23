from django.conf import settings
from user.models import PlaidUser
import logging
from plaid import Client as PlaidClient

logger = logging.getLogger('main.plaid')

client_id = settings.PLAID_CLIENT_ID
public_key = settings.PLAID_PUBLIC_KEY
secret = settings.PLAID_SECRET
environment = settings.PLAID_ENVIRONMENT


def create_public_token():
    """]
    Public tokens are coming from Plaid on the frontend, this function is
    purely for testing purposes.
    """
    client = PlaidClient(client_id=client_id, secret=secret, public_key=public_key, environment=environment)
    resp = client.Item.create(credentials=dict(username='user_good',
                                    password='pass_good'),
                   institution_id='ins_109508',
                   initial_products=['auth']);
    return resp


def create_access_token(django_user, public_token):
    client = PlaidClient(client_id=client_id, secret=secret, public_key=public_key, environment=environment)
    try:
        resp = client.Item.public_token.exchange(public_token)
    except Exception as e:
        logger.error("Unable to exchange public token for access token for user {0}".format(
            django_user
        ))
        logger.error(e)
        return False

    # else "client.access_token" should now be populated with
    # a valid access_token for making authenticated requests

    # Get the plaid user for this django user; make one if nec.
    if not getattr(django_user, 'plaid_user', False):
        plaid_user = PlaidUser(user=django_user)
        plaid_user.save()

    plaid_user = django_user.plaid_user
    plaid_user.access_token = resp['access_token']
    plaid_user.save()
    return True


def get_accounts(django_user): 
    plaid_user = getattr(django_user, 'plaid_user', False)
    if not plaid_user:
        logger.error("There is no Plaid user corresponding to user {0}".format(
            django_user
        ))
        return None

    access_token = getattr(plaid_user, 'access_token', False)
    if not access_token:
        logger.error("User {0} has a Plaid User but no access token".format(
            django_user
        ))
        return None

    client = PlaidClient(client_id=client_id, secret=secret, public_key=public_key, environment=environment)
    try:
        resp = client.Accounts.get(access_token=access_token)
    except Exception as e:
        logger.error("Unable to retrieve plaid accounts for user {0}".format(
            django_user
        ))
        logger.error(e)
        return None

    return resp['accounts']


def get_stripe_account_token(django_user, plaid_account_id):
    """
    Retrieves a stripe_bank_account_token for plaid-stripe integration.
    """
    plaid_user = getattr(django_user, 'plaid_user', False)
    if not plaid_user:
        logger.error("There is no Plaid user corresponding to user {0}".format(
            django_user
        ))
        return None

    access_token = getattr(plaid_user, 'access_token', False)
    if not access_token:
        logger.error("User {0} has a Plaid User but no access token".format(
            django_user
        ))
        return None

    client = PlaidClient(client_id=client_id, secret=secret, public_key=public_key, environment=environment)
    try:
        stripe_response = client.Processor.stripeBankAccountTokenCreate(access_token, plaid_account_id)
    except Exception as e:
        logger.error("Unable to create stripe bank account token for user {} account_id {}".format(
            django_user, plaid_account_id
        ))
        logger.error(e)
        return None

    bank_account_token = stripe_response.get('stripe_bank_account_token', None)
    if bank_account_token is None:
        logger.error("Unable to exchange token")
        logger.error(stripe_response)

    return bank_account_token


def get_bank_account_data(django_user, plaid_account_id):
    plaid_user = getattr(django_user, 'plaid_user', False)
    if not plaid_user:
        logger.error("There is no Plaid user corresponding to user {0}".format(
            django_user
        ))
        return None

    access_token = getattr(plaid_user, 'access_token', False)
    if not access_token:
        logger.error("User {0} has a Plaid User but no access token".format(
            django_user
        ))
        return None

    client = PlaidClient(client_id=client_id, secret=secret, public_key=public_key, environment=environment)
    
    try:
        resp = client.Accounts.get(access_token=access_token, accounts_ids=[plaid_account_id])
    except Exception as e:
        logger.error("Unable to retrieve plaid account for user {0}".format(
            django_user
        ))
        logger.error(e)
        return None

    return resp['accounts']


def get_identity(django_user):
    plaid_user = getattr(django_user, 'plaid_user', False)
    if not plaid_user:
        logger.error("There is no Plaid user corresponding to user {0}".format(
            django_user
        ))
        return None

    access_token = getattr(plaid_user, 'access_token', False)
    if not access_token:
        logger.error("User {0} has a Plaid User but no access token".format(
            django_user
        ))
        return None

    client = PlaidClient(client_id=client_id, secret=secret, public_key=public_key, environment=environment)
    try:
        resp = client.Identity.get(access_token=access_token)
    except Exception as e:
        logger.error("Unable to retrieve plaid account for user {0}".format(
            django_user
        ))
        logger.error(e)
        return None
    logger.error(resp)
    return resp