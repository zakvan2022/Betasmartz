from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone
from client.models import AccountTypeRiskProfileGroup, ClientAccount
from common.constants import GROUP_SUPPORT_STAFF
from activitylog.event import Event
from activitylog.models import ActivityLogEvent
from main import constants
from main.constants import ACCOUNT_TYPE_PERSONAL, ACCOUNT_TYPE_ROTH401K
from main.tests.fixture import Fixture1
from multi_sites.models import AccountType
from .factories import GroupFactory, SecurityAnswerFactory, \
    ClientAccountFactory, AccountBeneficiaryFactory
from dateutil.relativedelta import relativedelta
from django.core import mail
import os
from django.conf import settings
from unittest import skip


class AccountTests(APITestCase):
    def setUp(self):
        self.support_group = GroupFactory(name=GROUP_SUPPORT_STAFF)
        self.personal_account_type = AccountType.objects.create(id=constants.ACCOUNT_TYPE_PERSONAL)
        self.roth401k = AccountType.objects.create(id=constants.ACCOUNT_TYPE_ROTH401K)

    def test_create_account(self):
        url = '/api/v1/accounts'
        client = Fixture1.client1()
        data = {
            'account_type': ACCOUNT_TYPE_PERSONAL,
            'account_name': 'Test Account',
            'account_number': '1234567890',
            'primary_owner': client.id,
        }
        old_count = ClientAccount.objects.count()
        self.client.force_authenticate(user=Fixture1.client1_user())
        response = self.client.post(url, data)

        # First off, the test should fail, as personal accounts are not activated for the firm yet.
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Add the personal account type, then the post should succeed
        Fixture1.client1().advisor.firm.account_types.add(self.personal_account_type)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ClientAccount.objects.count(), 1)
        self.assertTrue('id' in response.data)
        self.assertEqual(response.data['account_name'], data['account_name'])
        self.assertEqual(response.data['account_number'], data['account_number'])

        # Don't let them create a second personal account
        data = {
            'account_type': ACCOUNT_TYPE_PERSONAL,
            'account_name': 'Test Account 2',
            'account_number': '1234567890',
            'primary_owner': client.id,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(ClientAccount.objects.count(), 1)

    def test_create_us_retirement_fail(self):
        Fixture1.client1().advisor.firm.account_types.add(self.roth401k)
        url = '/api/v1/accounts'
        client = Fixture1.client1()
        data = {
            'account_type': ACCOUNT_TYPE_ROTH401K,
            'account_name': 'Test Failing Account',
            'primary_owner': client.id,
        }
        self.client.force_authenticate(user=Fixture1.client1_user())
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue('are not user creatable' in str(response.content))

    def test_update_account(self):
        account = ClientAccountFactory.create()
        url = '/api/v1/accounts/' + str(account.id)
        test_name = 'Holy Pingalicious Test Account'
        account_number = '1234512345'
        self.assertNotEqual(account.account_name, test_name)
        sa1 = SecurityAnswerFactory.create(user=account.primary_owner.user, question='question one')
        sa2 = SecurityAnswerFactory.create(user=account.primary_owner.user, question='question two')

        data = {
            'account_name': test_name,
        }
        self.client.force_authenticate(user=account.primary_owner.user)
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = {
            'account_name': test_name,
            'question_one': sa1.pk,
            'answer_one': 'test',
            'question_two': sa2.pk,
            'answer_two': 'test',
            'account_number': account_number,
        }
        old_count = ClientAccount.objects.count()
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ClientAccount.objects.count(), old_count)  # No extra account created
        self.assertTrue('id' in response.data)  # Correct response serializer used
        self.assertEqual(response.data['account_name'], test_name)  # New value returned
        self.assertEqual(response.data['account_number'], account.account_number)  # account number can't be modified on update.
        self.assertEqual(Fixture1.personal_account1().account_name, test_name)  # Value in db actually changed

    def test_get_no_activity(self):
        url = '/api/v1/accounts/{}/activity'.format(Fixture1.personal_account1().id)
        self.client.force_authenticate(user=Fixture1.client1_user())
        response = self.client.get(url)
        self.assertEqual(response.data, [])

    def test_get_all_activity(self):
        # First add some transactions, balances and eventlogs, and make sure the ActivityLogs are set
        Fixture1.settings_event1()
        Fixture1.transaction_event1()
        Fixture1.populate_balance1() # 2 Activity lines
        ActivityLogEvent.get(Event.APPROVE_SELECTED_SETTINGS)
        ActivityLogEvent.get(Event.GOAL_BALANCE_CALCULATED)
        ActivityLogEvent.get(Event.GOAL_DEPOSIT_EXECUTED)

        url = '/api/v1/accounts/{}/activity'.format(Fixture1.personal_account1().id)
        self.client.force_authenticate(user=Fixture1.client1_user())
        response = self.client.get(url)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(response.data[3], {'goal': 1,
                                            'account': 1,
                                            'time': 946684800,
                                            'type': ActivityLogEvent.get(Event.APPROVE_SELECTED_SETTINGS).activity_log.id})  # Setting change
        self.assertEqual(response.data[2], {'balance': 0.0,
                                            'time': 978220800,
                                            'type': ActivityLogEvent.get(Event.GOAL_BALANCE_CALCULATED).activity_log.id}) # Balance
        self.assertEqual(response.data[1], {'balance': 3000.0,
                                            'time': 978307200,
                                            'type': ActivityLogEvent.get(Event.GOAL_BALANCE_CALCULATED).activity_log.id}) # Balance
        self.assertEqual(response.data[0], {'data': [3000.0],
                                            'goal': 1,
                                            'account': 1,
                                            'time': 978307200,
                                            'type': ActivityLogEvent.get(Event.GOAL_DEPOSIT_EXECUTED).activity_log.id}) # Deposit

    def test_get_beneficiaries(self):
        beneficiary = AccountBeneficiaryFactory.create()
        beneficiary2 = AccountBeneficiaryFactory.create(account=beneficiary.account)
        url = '/api/v1/accounts/{}/beneficiaries'.format(beneficiary.account.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=beneficiary.account.primary_owner.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['id'], beneficiary.id)
        self.assertEqual(response.data[0]['name'], beneficiary.name)
        self.assertEqual(response.data[0]['share'], beneficiary.share)

    def test_create_beneficiary(self):
        account = ClientAccountFactory.create()
        data = {
            'type': 0,
            'name': 'tester9',
            'relationship': 1,
            'birthdate': timezone.now().date() - relativedelta(years=40),
            'share': 0.5,
        }
        url = '/api/v1/accounts/{}/beneficiaries'.format(account.id)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=account.primary_owner.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['name'], 'tester9')
        self.assertEqual(response.data[0]['share'], 0.5)

    def test_get_beneficiary(self):
        beneficiary = AccountBeneficiaryFactory.create()
        url = '/api/v1/clients/{}/beneficiaries/{}'.format(beneficiary.account.primary_owner.id, beneficiary.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=beneficiary.account.primary_owner.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], beneficiary.id)
        self.assertEqual(response.data['name'], beneficiary.name)
        self.assertEqual(response.data['share'], beneficiary.share)

    def test_update_beneficiary(self):
        beneficiary = AccountBeneficiaryFactory.create()
        url = '/api/v1/clients/{}/beneficiaries/{}'.format(beneficiary.account.primary_owner.id, beneficiary.id)
        data = {
            'id': beneficiary.id,
            'name': beneficiary.name,
            'relationship': 2,
            'birthdate': timezone.now().date() - relativedelta(years=40),
            'share': 0.1,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=beneficiary.account.primary_owner.user)
        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], beneficiary.id)
        self.assertEqual(response.data['name'], beneficiary.name)
        self.assertEqual(response.data['share'], 0.1)
        self.assertEqual(response.data['relationship'], 2)

    def test_update_beneficiary_share_too_high(self):
        beneficiary = AccountBeneficiaryFactory.create()
        url = '/api/v1/clients/{}/beneficiaries/{}'.format(beneficiary.account.primary_owner.id, beneficiary.id)
        data = {
            'id': beneficiary.id,
            'name': beneficiary.name,
            'relationship': 2,
            'birthdate': timezone.now().date() - relativedelta(years=40),
            'share': 1.5,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=beneficiary.account.primary_owner.user)
        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_beneficiary_share_too_high(self):
        account = ClientAccountFactory.create()
        data = {
            'type': 0,
            'name': 'tester9',
            'relationship': 1,
            'birthdate': timezone.now().date() - relativedelta(years=40),
            'share': 1.5,
        }
        url = '/api/v1/accounts/{}/beneficiaries'.format(account.id)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=account.primary_owner.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_beneficiary(self):
        beneficiary = AccountBeneficiaryFactory.create()
        url = '/api/v1/clients/{}/beneficiaries/{}'.format(beneficiary.account.primary_owner.id, beneficiary.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=beneficiary.account.primary_owner.user)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, 'null')

    def test_update_different_client_beneficiaries(self):
        beneficiary = AccountBeneficiaryFactory.create()
        account = ClientAccountFactory.create()
        url = '/api/v1/clients/{}/beneficiaries/{}'.format(beneficiary.account.primary_owner.id, beneficiary.id)
        data = {
            'id': beneficiary.id,
            'name': beneficiary.name,
            'relationship': 2,
            'birthdate': timezone.now().date() - relativedelta(years=40),
            'share': 0.1,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=account.primary_owner.user)
        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_different_client_beneficiary(self):
        beneficiary = AccountBeneficiaryFactory.create()
        account = ClientAccountFactory.create()
        url = '/api/v1/clients/{}/beneficiaries/{}'.format(beneficiary.account.primary_owner.id, beneficiary.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=account.primary_owner.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_different_client_beneficiary(self):
        beneficiary = AccountBeneficiaryFactory.create()
        account = ClientAccountFactory.create()
        url = '/api/v1/clients/{}/beneficiaries/{}'.format(beneficiary.account.primary_owner.id, beneficiary.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=account.primary_owner.user)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_close_account_liquidate(self):
        account = ClientAccountFactory.create()
        url = '/api/v1/accounts/{}/close'.format(account.id)
        data = {
            'account': account.id,
            'close_choice': 0,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # test liquidate
        self.client.force_authenticate(user=account.primary_owner.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lookup_account = ClientAccount.objects.get(id=account.id)
        self.assertEqual(lookup_account.status, 1)
        self.assertEqual(mail.outbox[0].subject, 'Close Client Account Request')
        self.assertEqual(len(mail.outbox), 2)

    def test_close_account_transfer_internal(self):
        account = ClientAccountFactory.create()
        to_account = ClientAccountFactory.create(primary_owner=account.primary_owner)
        url = '/api/v1/accounts/{}/close'.format(account.id)
        data = {
            'account': account.id,
            'close_choice': 1,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # test liquidate
        self.client.force_authenticate(user=account.primary_owner.user)
        response = self.client.post(url, data)
        # 400, account_transfer_form required for account transfer close_choice
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        with open(os.path.join(settings.BASE_DIR, 'pdf_parsers', 'samples', 'sample_2006.pdf'), mode="rb") as pdf_upload:
            data['account_transfer_form'] = pdf_upload
            response = self.client.post(url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lookup_account = ClientAccount.objects.get(id=account.id)
        self.assertEqual(lookup_account.status, 1)
        self.assertEqual(mail.outbox[0].subject, 'Close Client Account Request')
        self.assertEqual(len(mail.outbox), 1)

    def test_close_account_transfer_custodian(self):
        account = ClientAccountFactory.create()
        url = '/api/v1/accounts/{}/close'.format(account.id)
        data = {
            'account': account.id,
            'close_choice': 2,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # test liquidate
        self.client.force_authenticate(user=account.primary_owner.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lookup_account = ClientAccount.objects.get(id=account.id)
        self.assertEqual(lookup_account.status, 1)
        self.assertEqual(mail.outbox[0].subject, 'Close Client Account Request')
        self.assertEqual(len(mail.outbox), 2)

    def test_close_account_transfer_direct(self):
        account = ClientAccountFactory.create()
        url = '/api/v1/accounts/{}/close'.format(account.id)
        data = {
            'account': account.id,
            'close_choice': 3,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # test liquidate
        self.client.force_authenticate(user=account.primary_owner.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lookup_account = ClientAccount.objects.get(id=account.id)
        self.assertEqual(lookup_account.status, 1)
        self.assertEqual(mail.outbox[0].subject, 'Close Client Account Request')
        self.assertEqual(len(mail.outbox), 2)

    @skip("TODO: Add tests after implementing acats transfer")
    def test_make_acats_transfer(self):
        pass
