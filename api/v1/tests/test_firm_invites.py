import json
from datetime import date
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import Client as DjangoClient
from common.constants import GROUP_SUPPORT_STAFF
from main.constants import ACCOUNT_TYPE_PERSONAL
from .factories import AdvisorFactory, SecurityQuestionFactory, FirmEmailInviteFactory
from .factories import AccountTypeRiskProfileGroupFactory, AddressFactory, \
    ClientAccountFactory, ClientFactory, GroupFactory, RegionFactory, \
    RiskProfileGroupFactory, UserFactory, AuthorisedRepresentativeFactory
from main.constants import EMPLOYMENT_STATUS_EMMPLOYED, GENDER_MALE
from user.models import User
from firm.models import FirmEmailInvite


class FirmInviteTests(APITestCase):
    def setUp(self):
        self.maxDiff = None
        self.support_group = GroupFactory(name=GROUP_SUPPORT_STAFF)
        # client with some personal assets, cash balance and goals
        self.region = RegionFactory.create()
        self.betasmartz_client_address = AddressFactory(region=self.region)
        self.risk_group = RiskProfileGroupFactory.create(name='Personal Risk Profile Group')
        self.personal_account_type = AccountTypeRiskProfileGroupFactory.create(account_type=ACCOUNT_TYPE_PERSONAL,
                                                                               risk_profile_group=self.risk_group)
        self.advisor = AdvisorFactory.create()
        self.question_one = SecurityQuestionFactory.create()
        self.question_two = SecurityQuestionFactory.create()

    def test_request_onboarding_with_valid_data(self):
        url = reverse('api:v1:firm:request-onboarding')
        data = {
            'first_name': 'test',
            'last_name': 'firm',
            'email': 'testfirm@email.com',
            'phone_number': '+1-234-234-2342',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['phone_number'], '+12342342342')
        self.assertTrue('firm_onboarding_url' in response.data)

    def test_request_onboarding_with_invalid_phone(self):
        url = reverse('api:v1:firm:request-onboarding')
        data = {
            'first_name': 'test',
            'last_name': 'firm',
            'email': 'testfirm2@email.com',
            'phone_number': '1234567890',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_request_onboarding_with_existing_email(self):
        user = UserFactory.create()
        url = reverse('api:v1:firm:request-onboarding')
        data = {
            'first_name': 'test',
            'last_name': 'firm',
            'email': user.email,
            'phone_number': '1234567890',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_prevent_register_when_another_user_is_loggedin(self):
        user = UserFactory.create()
        user.groups_add(User.GROUP_AUTHORIZED_REPRESENTATIVE)
        self.rep = AuthorisedRepresentativeFactory.create(user=user)
        self.client.force_authenticate(user=self.rep.user)
        url = reverse('api:v1:firm:register-user')
        data = {
            'first_name': 'test',
            'last_name': 'user',
            'invite_key': '1234567890',
            'password': 'test',
            'question_one': 'what is the first answer?',
            'question_one_answer': 'answer one',
            'question_two': 'what is the second answer?',
            'question_two_answer': 'answer two',
        }
        response = self.client.post(url, dict(data, question_one=''))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='403 forbidden')

    def tearDown(self):
        self.client.logout()

    def test_register_with_name_email(self):
        invite = FirmEmailInviteFactory.create(status=FirmEmailInvite.STATUS_SENT)
        url = reverse('api:v1:firm:register-user')
        data = {
            'first_name': 'Test',
            'middle_name': '',
            'last_name': 'User',
            'email': 'test@email.com',
            'invite_key': invite.invite_key,
            'password': 'test',
            'question_one': 'what is the first answer?',
            'question_one_answer': 'answer one',
            'question_two': 'what is the second answer?',
            'question_two_answer': 'answer two',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Test')
        self.assertEqual(response.data['middle_name'], '')
        self.assertEqual(response.data['last_name'], 'User')
        self.assertEqual(response.data['email'], 'test@email.com')

    def test_register_without_name_email(self):
        # Defaults name and email to the fields of invite
        invite = FirmEmailInviteFactory.create(status=FirmEmailInvite.STATUS_SENT)
        url = reverse('api:v1:firm:register-user')
        data = {
            'invite_key': invite.invite_key,
            'password': 'test',
            'question_one': 'what is the first answer?',
            'question_one_answer': 'answer one',
            'question_two': 'what is the second answer?',
            'question_two_answer': 'answer two',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], invite.first_name)
        self.assertEqual(response.data['last_name'], invite.last_name)
        self.assertEqual(response.data['email'], invite.email)

    def test_register_without_security_questions(self):
        invite = FirmEmailInviteFactory.create(status=FirmEmailInvite.STATUS_SENT)
        url = reverse('api:v1:firm:register-user')
        data = {
            'invite_key': invite.invite_key,
            'password': 'test'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_register_without_security_question_answers_fails(self):
        invite = FirmEmailInviteFactory.create(status=FirmEmailInvite.STATUS_SENT)
        url = reverse('api:v1:firm:register-user')
        data = {
            'first_name': invite.first_name,
            'last_name': invite.last_name,
            'invite_key': invite.invite_key,
            'question_one': 'what is the first answer?',
            'question_two': 'what is the second answer?',
            'password': 'test'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_clears_sensitive_onboarding_login_data_from_FirmEmailInvite(self):
        # check to make sure sensitive information isn't stored in onboarding_data
        # since user is registered now
        invite = FirmEmailInviteFactory.create(status=FirmEmailInvite.STATUS_SENT)
        onboarding = '{"risk":{"steps":[{"completed":false}],"completed":false},"agreements":{"steps":[{"advisorAgreement":false,\
          "betasmartzAgreement":false,"completed":false}],"completed":false},\
          "info":{"steps":[{"completed":false},{"completed":false},{"completed":false},{"completed":false}],"completed":false}, \
          "login":{"steps":[{"primarySecurityQuestion":"What was the name of your elementary school?","password":"t47LLRtur7O*PI", \
                "primarySecurityAnswer":"1","passwordConfirmation":"t47LLRtur7O*PI","secondarySecurityAnswer":"None",\
                "secondarySecurityQuestion":"What was the name of your favorite childhood friend?"}],"completed":true}}'
        invite.onboarding_data = json.loads(onboarding)
        invite.save()
        url = reverse('api:v1:firm:register-user')
        data = {
            'first_name': invite.first_name,
            'last_name': invite.last_name,
            'invite_key': invite.invite_key,
            'password': 'test',
            'question_one': 'what is the first answer?',
            'question_one_answer': 'answer one',
            'question_two': 'what is the second answer?',
            'question_two_answer': 'answer two',
        }
        response = self.client.post(url, dict(data, question_one=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 on bad question')
        response = self.client.post(url, dict(data, question_two=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 on bad question')
        response = self.client.post(url, dict(data, question_one_answer=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 on bad question answer')
        response = self.client.post(url, dict(data, question_two_answer=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 on bad question answer')

        # With a valid token, get a valid user
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Register a valid invitation is 200 OK')
        self.assertNotEqual(response.data['id'], None,
                            msg='Registering an invitation should give valid user_id')
        self.assertEqual(response.data['email'], invite.email)

        lookup_invite = FirmEmailInvite.objects.get(pk=invite.pk)
        self.assertEqual(response.data['email'], invite.email,
                         msg='New users email should match invitation')
        self.assertEqual(response.data['id'], lookup_invite.user.id,
                         msg='New users id should match invitation')
        self.assertEqual(FirmEmailInvite.STATUS_ACCEPTED, lookup_invite.status)
        self.assertEqual(lookup_invite.onboarding_data['login']['steps'][0]['password'], '')
        self.assertEqual(lookup_invite.onboarding_data['login']['steps'][0]['passwordConfirmation'], '')
        self.assertEqual(lookup_invite.onboarding_data['login']['steps'][0]['primarySecurityQuestion'], '')
        self.assertEqual(lookup_invite.onboarding_data['login']['steps'][0]['primarySecurityAnswer'], '')
        self.assertEqual(lookup_invite.onboarding_data['login']['steps'][0]['secondarySecurityQuestion'], '')
        self.assertEqual(lookup_invite.onboarding_data['login']['steps'][0]['secondarySecurityAnswer'], '')

    def test_register_answers_validate(self):
        self.client.logout()

        invite = FirmEmailInviteFactory.create(status=FirmEmailInvite.STATUS_SENT)

        url = reverse('api:v1:firm:register-user')
        data = {
            'first_name': invite.first_name,
            'last_name': invite.last_name,
            'invite_key': invite.invite_key,
            'password': 'test',
            'question_one': 'what is the first answer?',
            'question_one_answer': 'answer one',
            'question_two': 'what is the second answer?',
            'question_two_answer': 'answer two',
        }

        # 400 no such token=123
        response = self.client.post(url, dict(data, invite_key='123'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 for registrations from nonexistant email invite')

        # 400 on bad securityquestions
        response = self.client.post(url, dict(data, question_one=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 on bad question')
        response = self.client.post(url, dict(data, question_two=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 on bad question')
        response = self.client.post(url, dict(data, question_one_answer=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 on bad question answer')
        response = self.client.post(url, dict(data, question_two_answer=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 on bad question answer')

        # With a valid token, get a valid user
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Register a valid invitation is 200 OK')
        self.assertNotEqual(response.data['id'], None,
                            msg='Registering an invitation should give valid user_id')
        self.assertEqual(response.data['email'], invite.email)

        lookup_invite = FirmEmailInvite.objects.get(pk=invite.pk)
        self.assertEqual(response.data['email'], invite.email,
                         msg='New users email should match invitation')
        self.assertEqual(response.data['id'], lookup_invite.user.id,
                         msg='New users id should match invitation')
        self.assertEqual(FirmEmailInvite.STATUS_ACCEPTED, lookup_invite.status)

        questions_url = reverse('api:v1:user-security-question')
        response = self.client.get(questions_url)
        test_question_id1 = response.data[0]['id']
        test_question_id2 = response.data[1]['id']
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        check_answer_url = reverse('api:v1:user-check-answer', args=[test_question_id1])
        # question/answer combo 1
        data = {
            'answer': 'answer one',
        }
        response = self.client.post(check_answer_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # question/answer combo 2
        check_answer_url = reverse('api:v1:user-check-answer', args=[test_question_id2])
        data = {
            'answer': 'answer two',
        }
        response = self.client.post(check_answer_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_register_with_invite_key(self):
        # Bring an invite key, get logged in as a new user
        invite = FirmEmailInviteFactory.create(status=FirmEmailInvite.STATUS_SENT)

        url = reverse('api:v1:firm:register-user')
        data = {
            'first_name': invite.first_name,
            'last_name': invite.last_name,
            'invite_key': invite.invite_key,
            'password': 'test',
            'question_one': 'what is the first answer?',
            'question_one_answer': 'answer one',
            'question_two': 'what is the second answer?',
            'question_two_answer': 'answer two',
        }

        # 400 no such token=123
        response = self.client.post(url, dict(data, invite_key='123'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 for registrations from nonexistant email invite')

        # 400 on bad securityquestions
        response = self.client.post(url, dict(data, question_one=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 on bad question')
        response = self.client.post(url, dict(data, question_two=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 on bad question')
        response = self.client.post(url, dict(data, question_one_answer=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 on bad question answer')
        response = self.client.post(url, dict(data, question_two_answer=''))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg='400 on bad question answer')

        # With a valid token, get a valid user
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Register a valid invitation is 200 OK')
        self.assertNotEqual(response.data['id'], None,
                            msg='Registering an invitation should give valid user_id')
        self.assertEqual(response.data['email'], invite.email)

        lookup_invite = FirmEmailInvite.objects.get(pk=invite.pk)
        self.assertEqual(response.data['email'], invite.email,
                         msg='New users email should match invitation')
        self.assertEqual(response.data['id'], lookup_invite.user.id,
                         msg='New users id should match invitation')
        self.assertEqual(FirmEmailInvite.STATUS_ACCEPTED, lookup_invite.status)


        # New user must be logged in too
        self.assertIn('sessionid', response.cookies)

        # Make sure /api/v1/me has invitation info
        response = self.client.get(reverse('api:v1:user-me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='/api/v1/me should be valid during invitation')
        self.assertEqual(response.data['invitation']['invite_key'], invite.invite_key,
                         msg='/api/v1/me should have invitation data')
        self.assertEqual(response.data['invitation']['status'],
                         FirmEmailInvite.STATUS_ACCEPTED,
                         msg='/api/v1/me should have invitation status ACCEPTED')

        # GET: /api/v1/invites/:key
        # If a session is not logged in, return 200 with data
        self.client.logout()

        response = self.client.get(reverse('api:v1:firm:invite-detail',
                                           kwargs={'invite_key': invite.invite_key} ))
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='/api/v1/firm/invites/:key should be valid during invitation')
        self.assertEqual(response.data['invite_key'], invite.invite_key,
                         msg='/api/v1/firm/invites/:key should have invitation data')
        self.assertEqual(response.data['status'], FirmEmailInvite.STATUS_ACCEPTED,
                         msg='/api/v1/firm/invites/:key should have invitation status ACCEPTED')
        self.assertEqual('onboarding_data' in response.data, False,
                         msg='/api/v1/firm/invites/:key should not show onboarding_data to anonymous')
        self.assertEqual(response.data['email'], lookup_invite.email)

    def test_register_logout_then_login(self):
        # Bring an invite key, get logged in as a new user
        PW = 'testpassword'
        invite = FirmEmailInviteFactory.create(status=FirmEmailInvite.STATUS_SENT)

        url = reverse('api:v1:firm:register-user')
        data = {
            'first_name': invite.first_name,
            'last_name': invite.last_name,
            'invite_key': invite.invite_key,
            'password': PW,
            'question_one': 'what is the first answer?',
            'question_one_answer': 'answer one',
            'question_two': 'what is the second answer?',
            'question_two_answer': 'answer two',
        }

        # Accept an invitation and create a user
        response = self.client.post(url, data)
        lookup_invite = FirmEmailInvite.objects.get(pk=invite.pk)
        invite_detail_url = reverse('api:v1:firm:invite-detail', kwargs={'invite_key': invite.invite_key} )
        me_url = reverse('api:v1:user-me')
        self.assertEqual(FirmEmailInvite.STATUS_ACCEPTED, lookup_invite.status)

        # New user must be logged in and able to see invite data
        self.assertIn('sessionid', response.cookies)
        response = self.client.get(me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='/api/v1/me should be valid during invitation')

        # If a session is not logged in, return 200 with data
        self.client.logout()
        response = self.client.get(me_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='/api/v1/me denies unauthenticated user')

        # But this user can still log in again
        # through non-api url, user prob not using api to login
        # in this scenario
        # POST ing to the backup login url FAILS here:
        self.client = DjangoClient()  # django
        url = reverse('login')
        data = {
            'username': lookup_invite.user.email,
            'password': PW,
        }
        response = self.client.post(url, data)
        # redirects to frontend client onboarding
        self.assertRedirects(response, lookup_invite.firm_onboarding_url, fetch_redirect_response=False)
        self.assertIn('sessionid', response.cookies, msg='A user still onboarding can log in')

        response = self.client.get(me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='/api/v1/me works for newly authenticated user')

    def test_onboard_after_register(self):
        self.client.logout()

        # Bring an invite key, get logged in as a new user
        invite = FirmEmailInviteFactory.create(status=FirmEmailInvite.STATUS_SENT)

        url = reverse('api:v1:firm:register-user')
        data = {
            'first_name': invite.first_name,
            'last_name': invite.last_name,
            'invite_key': invite.invite_key,
            'password': 'test',
            'question_one': 'what is the first answer?',
            'question_one_answer': 'answer one',
            'question_two': 'what is the second answer?',
            'question_two_answer': 'answer two',
        }

        # Accept an invitation and create a user
        response = self.client.post(url, data)
        lookup_invite = FirmEmailInvite.objects.get(pk=invite.pk)
        invite_detail_url = reverse('api:v1:firm:invite-detail', kwargs={'invite_key': invite.invite_key} )

        self.assertEqual(FirmEmailInvite.STATUS_ACCEPTED, lookup_invite.status)

        # New user must be logged in too
        self.assertIn('sessionid', response.cookies)

        # GET: /api/v1/invites/:key
        # If a session is logged in, return 200 with data
        response = self.client.get(invite_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='/api/v1/firm/invites/:key should be valid during invitation')
        self.assertEqual(response.data['invite_key'], invite.invite_key,
                         msg='/api/v1/firm/invites/:key should have invitation data')
        self.assertEqual(response.data['status'], FirmEmailInvite.STATUS_ACCEPTED,
                         msg='/api/v1/firm/invites/:key should have invitation status ACCEPTED')
        self.assertEqual('onboarding_data' in response.data, True,
                         msg='/api/v1/firm/invites/:key should show onboarding_data to user')

        # PUT: /api/v1/firm/invites/:key
        # Submit with onboarding_data
        onboarding = {'onboarding_data': {'foo': 'bar'}}
        response = self.client.put(invite_detail_url, data=onboarding)

        lookup_invite = FirmEmailInvite.objects.get(pk=invite.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Onboarding must accept json objects')
        self.assertEqual(response.data['status'], FirmEmailInvite.STATUS_ACCEPTED,
                         msg='invitation status ACCEPTED')
        self.assertEqual(lookup_invite.onboarding_data['foo'], 'bar',
                         msg='should save onboarding_file')

        lookup_invite = FirmEmailInvite.objects.get(pk=invite.pk)
        self.assertEqual(response.data['status'], FirmEmailInvite.STATUS_ACCEPTED,
                         msg='invitation status ACCEPTED')

    def test_complete_invitation(self):

        self.client.logout()
        # Bring an invite key, get logged in as a new user
        invite = FirmEmailInviteFactory.create(status=FirmEmailInvite.STATUS_SENT)

        url = reverse('api:v1:firm:register-user')
        data = {
            'first_name': invite.first_name,
            'last_name': invite.last_name,
            'invite_key': invite.invite_key,
            'password': 'test',
            'question_one': 'what is the first answer?',
            'question_one_answer': 'answer one',
            'question_two': 'what is the second answer?',
            'question_two_answer': 'answer two',
        }

        # Accept an invitation and create a user
        response = self.client.post(url, data)
        invite = FirmEmailInvite.objects.get(pk=invite.pk)
        user = invite.user
        invite_detail_url = reverse('api:v1:firm:invite-detail', kwargs={'invite_key': invite.invite_key} )

        self.assertEqual(FirmEmailInvite.STATUS_ACCEPTED, invite.status)

        # New user must be logged in too
        self.assertIn('sessionid', response.cookies)

        # PUT: /api/v1/invites/:key
        # Submit with onboarding_data
        onboarding = {'onboarding_data': json.dumps({'foo': 'bar'})}
        response = self.client.put(invite_detail_url, data=onboarding)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Onboarding must accept json')

        # betasmartz_client = ClientFactory.create(user=user)
        # betasmartz_client_account = ClientAccountFactory(primary_owner=betasmartz_client, account_type=ACCOUNT_TYPE_PERSONAL, confirmed=False)
        # betasmartz_client_account.confirmed = True
        # betasmartz_client_account.save()

        # invite = FirmEmailInvite.objects.get(pk=invite.pk)
        # self.assertEqual(invite.status, FirmEmailInvite.STATUS_COMPLETE)
        # self.assertEqual(invite.onboarding_data, None)

    def test_resend_firm_invite(self):
        """
        Allow authenticated users to resend email invites for onboarding
        """
        invite = FirmEmailInviteFactory.create(status=FirmEmailInvite.STATUS_SENT)
        url = reverse('api:v1:firm:register-user')
        data = {
            'first_name': invite.first_name,
            'last_name': invite.last_name,
            'invite_key': invite.invite_key,
            'password': 'test',
            'question_one': 'what is the first answer?',
            'question_one_answer': 'answer one',
            'question_two': 'what is the second answer?',
            'question_two_answer': 'answer two',
        }

        # Accept an invitation and create a user
        response = self.client.post(url, data)
        invite = FirmEmailInvite.objects.get(pk=invite.pk)

        self.client.logout()
        url = reverse('api:v1:firm:resend-invite', args=[invite.invite_key])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(invite.user)
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        site = Site.objects.get_current()
        self.assertEqual(mail.outbox[-1].subject, "Welcome to {}".format(site.name),
                         msg='Email outbox has email with expected resend email subject')
        lookup_invite = FirmEmailInvite.objects.get(pk=invite.pk)
        self.assertEqual(lookup_invite.send_count, 1)
