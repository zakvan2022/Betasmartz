from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from common.constants import GROUP_SUPPORT_STAFF
from main.constants import ACCOUNT_TYPES
from user.models import User
from main.tests.fixture import Fixture1
from .factories import AccountTypeRiskProfileGroupFactory, AdvisorFactory, \
    ClientFactory, GroupFactory, UserFactory, SecurityAnswerFactory
import json


class UserTests(APITestCase):
    def setUp(self):
        self.support_group = GroupFactory(name=GROUP_SUPPORT_STAFF)
        self.user = UserFactory.create()

        # Populate the AccountType -> RiskProfileGroup mapping
        for atid, _ in ACCOUNT_TYPES:
            AccountTypeRiskProfileGroupFactory.create(account_type=atid)

        self.user2 = UserFactory.create()
        self.client2 = ClientFactory(user=self.user2, income=5555.01)

        self.client3 = ClientFactory()
        self.client3.user.groups_add(User.GROUP_CLIENT)

    def tearDown(self):
        self.client.logout()

    def test_login(self):
        url = '/api/v1/login'
        usr = Fixture1.client1_user()
        usr.set_password('temppass')
        usr.save()
        data = {
            'username': usr.email,
            'password': 'temppass',
        }
        response = self.client.post(url, data)
        self.assertIn('sessionid', response.cookies)

    def test_get_client_user_settings(self):
        client = ClientFactory(user=self.user)
        client.user.groups_add(User.GROUP_CLIENT)

        url = reverse('api:v1:user-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='403 for unauthenticated request to get user settings')
        self.client.force_authenticate(client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='200 for authenticated get request to get user settings')

        self.assertTrue(response.data['first_name'] == self.user.first_name)
        self.assertTrue(response.data['id'] == self.user.id)
        self.assertTrue(response.data['client']['id'] == self.user.client.id)
        self.assertTrue(response.data['client']['income'] == self.user.client.income)

        # lets make a new client with a different income and check results on it
        self.user2.groups_add(User.GROUP_CLIENT)
        self.client.force_authenticate(self.user2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='200 for authenticated get request to get user settings')
        self.assertTrue(response.data['id'] == self.user2.id)
        self.assertTrue(response.data['client']['id'] == self.client2.id)
        self.assertTrue(response.data['client']['income'] == self.client2.income)
        self.assertEqual(response.data['client']['residential_address']['address'],
                         self.client2.residential_address.address)

    def test_update_user_settings(self):
        # the user must be a client, advisor or possibly supportstaff here, otherwise 403
        client = ClientFactory(user=self.user)
        client.user.groups_add(User.GROUP_CLIENT)
        sa1 = SecurityAnswerFactory.create(user=self.user, question='question one')
        sa2 = SecurityAnswerFactory.create(user=self.user, question='question two')

        url = reverse('api:v1:user-me')
        new_name = 'Bruce Wayne'
        data = {
            'first_name': new_name,
            'last_name': self.user.last_name,
            'email': self.user.email,
            'password': 'test',
            'password2': 'test',
            'oldpassword': 'test',
        }
        # 403 unauthenticated request
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='403 for unauthenticated request to update user settings')

        self.client.force_authenticate(self.user)

        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='Put without question and answers returns 400')
        data['question_one'] = sa1.pk
        data['answer_one'] = 'test'
        data['question_two'] = sa2.pk
        data['answer_two'] = 'test'
        response = self.client.put(url, data)
        # 200 for put request
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='200 for authenticated put request to update user settings')
        # We gave a get control response so we can compare the two.
        control_response = self.client.get(url)

        # MAke sure put and get return same data
        self.assertEqual(control_response.data, response.data)
        self.assertEqual(response.data['first_name'], new_name)
        self.assertEqual(response.data['id'], self.user.id)

    def test_update_user_settings_bad_question_answers(self):
        # the user must be a client, advisor or possibly supportstaff here, otherwise 403
        client = ClientFactory(user=self.user)
        client.user.groups_add(User.GROUP_CLIENT)
        sa1 = SecurityAnswerFactory.create(user=self.user, question='question one')
        sa2 = SecurityAnswerFactory.create(user=self.user, question='question two')

        url = reverse('api:v1:user-me')
        new_name = 'Bruce Wayne'
        data = {
            'first_name': new_name,
            'last_name': self.user.last_name,
            'email': self.user.email,
            'password': 'test',
            'password2': 'test',
            'oldpassword': 'test',
            'question_one': sa1.pk,
            'answer_one': 'wrong answer',
            'question_two': sa2.pk,
            'answer_two': 'test',
        }

        self.client.force_authenticate(self.user)
        response = self.client.put(url, data)
        # 400 for put request
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 for wrong answer_one with put request to update user settings')
        self.assertEqual(content['error']['errors']['answer_one'], ['Wrong answer'])

    def test_update_user_user_settings(self):
        # the user must be a client, advisor or possibly supportstaff here, otherwise 403
        client = ClientFactory(user=self.user)
        client.user.groups_add(User.GROUP_CLIENT)
        sa1 = SecurityAnswerFactory.create(user=self.user, question='question one')
        sa2 = SecurityAnswerFactory.create(user=self.user, question='question two')

        url = reverse('api:v1:user-user', args=[client.user.id, ])
        new_name = 'Bruce Wayne'
        data = {
            'first_name': new_name,
            'last_name': self.user.last_name,
            'email': self.user.email,
            'password': 'test',
            'password2': 'test',
            'oldpassword': 'test',
        }
        # 403 unauthenticated request
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='403 for unauthenticated request to update user settings')

        self.advisor2 = AdvisorFactory.create()
        self.client.force_authenticate(self.advisor2.user)
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Only client\'s advisors can update the user settings the client')

        self.client.force_authenticate(self.user)

        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='Put without question and answers returns 400')
        data['question_one'] = sa1.pk
        data['answer_one'] = 'test'
        data['question_two'] = sa2.pk
        data['answer_two'] = 'test'
        response = self.client.put(url, data)
        # 200 for put request
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='200 for authenticated put request to update user settings')
        # We gave a get control response so we can compare the two.
        control_response = self.client.get(url)

        # Make sure put and get return same data
        self.assertEqual(control_response.data, response.data)
        self.assertEqual(response.data['first_name'], new_name)
        self.assertEqual(response.data['id'], self.user.id)

        self.client.force_authenticate(client.advisor.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Client\'s advisor can also update user settings')

    def test_firm_access(self):
        url = '/api/v1/me/firm/'
        response = self.client.get(url)
        self.assertEqual(response.status_code,status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.client2.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code,status.HTTP_200_OK)

        self.client.force_authenticate(self.client2.advisor.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code,status.HTTP_200_OK)
