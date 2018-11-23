from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from common.constants import GROUP_SUPPORT_STAFF
from main.constants import ACCOUNT_TYPES
from advisor.models import Advisor
from user.models import User
from firm.models import AuthorisedRepresentative, Firm, FirmEmailInvite, generate_token
from .factories import AccountTypeRiskProfileGroupFactory, ClientFactory, \
    GroupFactory, UserFactory, FirmFactory, AuthorisedRepresentativeFactory, \
    AdvisorFactory, SupervisorFactory, FirmEmailInviteFactory
import json
from datetime import date
from main.constants import EMPLOYMENT_STATUS_EMMPLOYED, GENDER_MALE
from django.test import Client as DjangoClient


class FirmTests(APITestCase):
    def setUp(self):
        self.support_group = GroupFactory(name=GROUP_SUPPORT_STAFF)

        self.firm = FirmFactory.create()

        # having to manually set the private attributes here, some problem with
        # factory_boy not triggering the hasattr checks properly otherwise
        self.authorised_rep = AuthorisedRepresentativeFactory.create(firm=self.firm)
        self.authorised_rep.user._is_authorised_representative = True
        self.authorised_rep.user.save()
        self.advisor = AdvisorFactory.create(firm=self.firm)
        self.advisor.user._is_advisor = True
        self.advisor.user.save()
        self.betasmartz_client = ClientFactory.create(advisor=self.advisor)
        self.betasmartz_client.user._is_client = True
        self.betasmartz_client.user.save()
        self.supervisor = SupervisorFactory.create(firm=self.firm)
        self.supervisor.user._is_supervisor = True
        self.supervisor.user.save()

        self.other_firm = FirmFactory.create()

    def test_get_firm_unauthenticated(self):
        url = reverse('api:v1:firm:single', args=[self.firm.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_firm_as_authorised_representative(self):
        url = reverse('api:v1:firm:single', args=[self.firm.pk])
        self.client.force_authenticate(self.authorised_rep.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Can retrieve /api/v1/firm/<pk> as a firm authorised representative')
        self.assertEqual(self.firm.id, response.data.get('id'))

    def test_get_firm_as_advisor(self):
        url = reverse('api:v1:firm:single', args=[self.firm.pk])
        self.client.force_authenticate(self.advisor.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        msg='Can retrieve /api/v1/firm/<pk> as a firm advisor')
        self.assertEqual(self.firm.id, response.data.get('id'))

    def test_get_firm_as_supervisor(self):
        url = reverse('api:v1:firm:single', args=[self.firm.pk])
        self.client.force_authenticate(self.supervisor.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        msg='Can retrieve /api/v1/firm/<pk> as a firm supervisor')
        self.assertEqual(self.firm.id, response.data.get('id'))

    def test_get_firm_as_client(self):
        url = reverse('api:v1:firm:single', args=[self.firm.pk])
        self.client.force_authenticate(self.betasmartz_client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Can retrieve /api/v1/firm/<pk> as a firm client')
        self.assertEqual(self.firm.id, response.data.get('id'))

    def test_get_other_firm(self):
        """
        Test that attempts to retrieve firm info that an
        authorised representative, advisor, supervisor
        and/or client is not a part of fails.
        """
        url = reverse('api:v1:firm:single', args=[self.other_firm.pk])
        self.client.force_authenticate(self.authorised_rep.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Attempt to get firm info fails as authorised representative of another firm')

        self.client.force_authenticate(self.advisor.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Attempt to get firm info fails as advisor of another firm')

        self.client.force_authenticate(self.supervisor.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Attempt to get firm info fails as supervisor of another firm')

        self.client.force_authenticate(self.betasmartz_client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         msg='Attempt to get firm info fails as client of another firm')

    def test_create_authorised_representative(self):
        # We need an accepted invitation to be able to create a client
        usr = UserFactory.create()
        FirmEmailInviteFactory.create(user=usr, status=FirmEmailInvite.STATUS_ACCEPTED)
        url = reverse('api:v1:firm:authorisedrepresentative-list')
        address = {
            "address": "123 My Street\nSome City",
            "post_code": "112233",
            "region": {
                "name": "California",
                "country": "US",
                "code": "CA",
            }
        }
        regional_data = {
            'ssn': '555-55-5555',
        }
        firm_details = {
            'office_address': address,
            'postal_address': address,
            'daytime_phone_num': '+1-234-234-2342',
            'alternate_email_address': usr.email,
            'site_url': 'http://firm.example.com',
        }
        advisors = [
            {
                'first_name': 'Advisor',
                'last_name': 'Example1',
                'email': 'advisor1@email.com',
                'work_phone_num': '+1-234-234-2342',
            },
            {
                'first_name': 'Advisor',
                'last_name': 'Example2',
                'email': 'advisor2@email.com',
                'work_phone_num': '+1-234-234-2342',
            }
        ]
        firm = {
            'name': 'Test Firm',
            'slug': 'test-firm',
            'token': generate_token(),
            'details': firm_details,
        }
        data = {
            "betasmartz_agreement": True,
            "date_of_birth": date(2016, 9, 21),
            "gender": GENDER_MALE,
            "phone_num": "+1-234-234-2342",
            "residential_address": address,
            "regional_data": json.dumps(regional_data),
            "firm": firm,
            'advisors': advisors
        }
        self.client.force_authenticate(usr)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Ensure it is created approved and accepted.
        self.assertEqual(response.data['is_confirmed'], True)
        self.assertEqual(response.data['is_accepted'], True)
        self.assertEqual(response.data['phone_num'], "+12342342342")
        self.assertEqual(response.data['residential_address']['address'], address['address'])
        self.assertEqual(response.data['residential_address']['post_code'], address['post_code'])
        self.assertEqual(response.data['betasmartz_agreement'], True)
        regional_data_load = json.loads(response.data['regional_data'])
        self.assertEqual(regional_data_load['ssn'], regional_data['ssn'])

        # check onboarding status is complete
        lookup_invite = FirmEmailInvite.objects.get(user=usr)
        self.assertEqual(lookup_invite.status, FirmEmailInvite.STATUS_COMPLETE)

        lookup_firm = Firm.objects.get(pk=response.data['firm']['id'])
        self.assertEqual(lookup_firm.name, 'Test Firm')
        self.assertEqual(lookup_firm.details.daytime_phone_num, '+12342342342')

        # can login with new firm
        self.client = DjangoClient()  # django
        url = reverse('login')
        data = {
            'username': usr.email,
            'password': 'test',
        }
        response = self.client.post(url, data)
        # redirect to firm application
        self.assertRedirects(response, reverse('firm:overview'))

        # can retrieve profile info ok
        url = reverse('api:v1:user-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # advisors created
        advisors = Advisor.objects.filter(firm=lookup_firm, )
        self.assertEqual(len(advisors), 2, msg='Created all advisors')
        user1 = User.objects.filter(email='advisor1@email.com')
        self.assertEqual(len(user1), 1, msg='Advisor User 1 exists')
        user2 = User.objects.filter(email='advisor2@email.com')
        self.assertEqual(len(user2), 1, msg='Advisor User 2 exists')
