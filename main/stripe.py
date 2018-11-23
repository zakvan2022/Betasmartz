# -*- coding: utf-8 -*-
import os
import io
import json
import uuid
import stripe
from django.conf import settings
import logging
from user.models import StripeUser

logger = logging.getLogger('main.stripe')

stripe.api_key = settings.STRIPE_API_SECRET


class MonkeyPatchedIO(io.BytesIO):

    @property
    def name(self):
        return 'monkeypatched.png'


def convert_dollars_to_cents(input):
    """
    Converts float dollar to integer cents.  Stripe expects
    integer cents for amounts.
    """
    input_split = str(input).split('.')
    dollars = int(input_split[0]) * 100
    if '.' in str(input):
        return dollars + int(input_split[1])
    else:
        return dollars


def create_stripe_account(django_user, stripe_bank_account_token):
    if stripe_bank_account_token is None:
        logger.error('Missing stripe bank account token for stripe account create')
        return None

    if hasattr(django_user, 'stripe_user'):
        account = stripe.Account.retrieve(django_user.stripe_user.account_id)
    else:
        account = stripe.Account.create(
            country='US',
            managed=True,
            email=django_user.email,
        )
        stripe_user, _ = StripeUser.objects.get_or_create(user=django_user, account_id=account['id'])

        # legal_entity and tos_acceptance requirements for verifying
        # managed accounts on stripe, if stripe says we have to use managed accounts
        # then we'll need to add tos link to our tos and record user ip address and acceptance time
        account.tos_acceptance.date = django_user.client.agreement_time
        account.tos_acceptance.ip = django_user.client.agreement_ip

        regional_data = json.loads(django_user.client.regional_data)

        account.legal_entity.first_name = django_user.first_name
        account.legal_entity.last_name = django_user.last_name
        account.legal_entity.type = 'individual'
        account.legal_entity.dob.day = django_user.client.date_of_birth.day
        account.legal_entity.dob.month = django_user.client.date_of_birth.month
        account.legal_entity.dob.year = django_user.client.date_of_birth.year
        account.legal_entity.ssn_last_4 = regional_data.get('ssn')[-4:]
        account.legal_entity.personal_id_number = regional_data.get('ssn')
        account.legal_entity.address.city = django_user.client.residential_address.city
        account.legal_entity.address.line1 = django_user.client.residential_address.address1
        account.legal_entity.address.postal_code = django_user.client.residential_address.post_code
        account.legal_entity.address.state = django_user.client.residential_address.state_code
        account.save()

        tmp_filename = '/tmp/' + str(uuid.uuid4()) + '.png'
        with open(tmp_filename, 'wb+') as f:
            for chunk in django_user.invitation.photo_verification.chunks():
                f.write(chunk)

        with open(tmp_filename, 'rb') as fp:
            file_obj = stripe.FileUpload.create(
              purpose='identity_document',
              file=fp,
              stripe_account=account['id'],
            )
            file = file_obj.id
            account.legal_entity.verification.document = file
        account.save()

    account.external_accounts.create(external_account=stripe_bank_account_token)
    return account


def execute_charge(amount, stripe_bank_account_token):
    """
    Takes an amount and stripe_bank_account_token and
    executes the charge through Stripe.

    stripe_bank_account_token can be retrieved from plaid API
    using main.plaid.get_stripe_account_token
    """
    o = stripe.Charge.create(
        amount=convert_dollars_to_cents(amount),
        currency="usd",
        source=stripe_bank_account_token,
    )
    return o


def execute_withdrawal(django_user, amount, stripe_bank_account_token):
    try:
        account = create_stripe_account(django_user, stripe_bank_account_token)
    except Exception as e:
        logger.error('Failed to create stripe account for user %s' % django_user)
        logger.error(e)
        return

    try:
        # stripe instant Payout doesn't work with bank accounts only cards it seems
        # o = stripe.Payout.create(
        #     amount=convert_dollars_to_cents(amount),
        #     currency='usd',
        #     method='instant',
        #     stripe_account=account['id'],
        # )
        o = stripe.Transfer.create(
            amount=convert_dollars_to_cents(amount),
            currency='usd',
            destination=account['id'],
        )
        return o
    except Exception as e:
        logger.error(e)
        return
