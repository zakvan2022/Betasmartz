from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from user.models import User
from client.models import IBOnboard
from .factories import ClientFactory, IBAccountFeedFactory, UserFactory, \
    EmailInviteFactory, FirmEmailInviteFactory
import json

class ValidationTests(APITestCase):
    def setUp(self):
        self.user = UserFactory.create()

    def tearDown(self):
        self.client.logout()

    def test_phone_number_valid(self):
        url = reverse('api:v1:validate:phonenumber')
        data = {
            'number': '15592467777',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Unauthenticated phone number validation fails')

        self.client.force_authenticate(self.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Authenticated valid phone number returns 200')
        self.assertEqual(response.data['number'], '15592467777')

    def test_phone_number_valid_with_symbols(self):
        url = reverse('api:v1:validate:phonenumber')
        data = {
            'number': '+1 (212) 246-5555',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Unauthenticated phone number validation fails')

        self.client.force_authenticate(self.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Authenticated valid phone number returns 200')
        self.assertEqual(response.data['number'], '+12122465555')

    def test_phone_number_invalid(self):
        url = reverse('api:v1:validate:phonenumber')
        data = {
            'number': '15555555555',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Unauthenticated phone number validation fails')

        self.client.force_authenticate(self.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='Authenticated invalid phone number validation returns 400')

    def test_phone_number_non_number(self):
        url = reverse('api:v1:validate:phonenumber')
        data = {
            'number': 'asdasda',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Unauthenticated phone number validation fails')

        self.client.force_authenticate(self.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='Authenticated invalid phone number validation returns 400')

    def test_phone_number_with_symbols(self):
        url = reverse('api:v1:validate:phonenumber')
        data = {
            'number': '+1-234-234-2342',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Unauthenticated phone number validation fails')

        self.client.force_authenticate(self.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Authenticated valid phone number with + and - symbols returns 200')
        self.assertEqual(response.data['number'], '+12342342342')

    def test_email_is_valid(self):
        url = reverse('api:v1:validate:email')
        data = {
            'email': self.user.email,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Unauthenticated email validation fails')

        self.client.force_authenticate(self.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='Validation of Existing user email')

        
        client_invite = EmailInviteFactory.create()
        data = {
            'email': client_invite.email,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='Validation of onboarding client email')

        rep_invite = FirmEmailInviteFactory.create()
        data = {
            'email': rep_invite.email,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='Validation of onboarding representative email')

        data = {
            'email': 'unused_email@address.com',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Validation of new email')


    def test_validate_ib_account(self):
        url = reverse('api:v1:validate:ib-account')
        betasmartz_client = ClientFactory.create(user=self.user)
        ib_onboard = IBOnboard.objects.create(client=betasmartz_client, account_number='U1234567')
        ib_account_feed1 = IBAccountFeedFactory.create(account_id='U1234567')
        ib_account_feed2 = IBAccountFeedFactory.create(account_id='U1111111')

        data = {
            'account_number': 'U1234567',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Unauthenticated, IB account number validation fails')

        self.client.force_authenticate(self.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='Authenticated, Existing client\'s IB account number validation fails')

        data = {
            'account_number': 'U1111111',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Authenticated, Available IB account number validation returns 200')

        data = {
            'account_number': 'U9999999',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='Authenticated, Validation of IB account number not in the feeds fails')

    def test_validate_composite_individual(self):
        url = reverse('api:v1:validate:composite')
        betasmartz_client = ClientFactory.create(user=self.user)
        ib_onboard = IBOnboard.objects.create(client=betasmartz_client, account_number='U1234567')
        ib_account_feed1 = IBAccountFeedFactory.create(account_id='U1234567')
        ib_account_feed2 = IBAccountFeedFactory.create(account_id='U1111111')

        data = {
            'phone_numbers': [
                '+1 (415) 332-1532',
                '11111'
            ],
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Unauthenticated, IB account number validation fails')

        self.client.force_authenticate(self.user)
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Authenticated, Validation of phone numbers')
        self.assertEqual(response.data['phone_numbers'][0]['number'], '+1 (415) 332-1532')
        self.assertFalse('errors' in response.data['phone_numbers'][0])
        self.assertEqual(response.data['phone_numbers'][1]['number'], '11111')
        self.assertTrue('errors' in response.data['phone_numbers'][1])

        data = {
            'emails': [
                'test@unused.email',
                self.user.email,
                'invalidemail'
            ],
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['emails'][0]['email'], 'test@unused.email')
        self.assertFalse('errors' in response.data['emails'][0])
        self.assertEqual(response.data['emails'][1]['email'], self.user.email)
        self.assertTrue('errors' in response.data['emails'][1])
        self.assertEqual(response.data['emails'][2]['email'], 'invalidemail')
        self.assertTrue('errors' in response.data['emails'][2])

        data = {
            'ib_account_numbers': [
                'U1111111',
                'U1234567',
                'U9999999'
            ]
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ib_account_numbers'][0]['account_number'], 'U1111111')
        self.assertFalse('errors' in response.data['ib_account_numbers'][0])
        self.assertEqual(response.data['ib_account_numbers'][1]['account_number'], 'U1234567')
        self.assertTrue('errors' in response.data['ib_account_numbers'][1],
                        msg='Existing client\'s IB account number validation has errors')
        self.assertEqual(response.data['ib_account_numbers'][2]['account_number'], 'U9999999')
        self.assertTrue('errors' in response.data['ib_account_numbers'][2],
                        msg='Validation of IB account number not in the feeds has errors')

    def test_validate_composite_all_in_one(self):
        url = reverse('api:v1:validate:composite')
        betasmartz_client = ClientFactory.create(user=self.user)
        ib_onboard = IBOnboard.objects.create(client=betasmartz_client, account_number='U1234567')
        ib_account_feed1 = IBAccountFeedFactory.create(account_id='U1234567')
        ib_account_feed2 = IBAccountFeedFactory.create(account_id='U1111111')

        data = {
            'phone_numbers': [
                '+1 (415) 332-1532',
                '11111'
            ],
            'emails': [
                'test@unused.email',
                self.user.email,
                'invalidemail'
            ],
            'ib_account_numbers': [
                'U1111111',
                'U1234567',
                'U9999999'
            ]
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(url, data)
        self.assertTrue('phone_numbers' in response.data)
        self.assertTrue('emails' in response.data)
        self.assertTrue('ib_account_numbers' in response.data)
