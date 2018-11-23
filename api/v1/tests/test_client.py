import os
import json
from datetime import date
from django.core.urlresolvers import reverse
from django.test import Client as DjangoClient
from rest_framework import status
from rest_framework.test import APITestCase
from django.conf import settings
from address.models import Region
from api.v1.tests.factories import AdvisorFactory, EmailInviteFactory
from activitylog.event import Event
from client.models import Client, EmailInvite, ExternalAsset
from common.constants import GROUP_SUPPORT_STAFF
from main.constants import ACCOUNT_TYPE_PERSONAL, GENDER_MALE, EMPLOYMENT_STATUS_EMMPLOYED, \
    CLIENT_FULL_ACCESS, CLIENT_READONLY_ACCESS
from brokers.interactive_brokers.onboarding.constants import IB_EMPLOY_STAT_EMPLOYED, \
     SOURCE_OF_FUNDS_TYPE_CONSULTING
from user.models import User
from activitylog.models import ActivityLogEvent
from main import abstract
from .factories import AccountTypeRiskProfileGroupFactory, AddressFactory, \
    ClientAccountFactory, ClientFactory, ExternalAssetFactory, GoalFactory, \
    GroupFactory, RegionFactory, RiskProfileGroupFactory, UserFactory, \
    SecurityAnswerFactory, RiskProfileAnswerFactory
from main.tests.fixture import Fixture1


class ClientTests(APITestCase):

    def setUp(self):
        self.support_group = GroupFactory(name=GROUP_SUPPORT_STAFF)
        # client with some personal assets, cash balance and goals
        self.region = RegionFactory.create()
        self.betasmartz_client_address = AddressFactory(region=self.region)
        self.risk_group = RiskProfileGroupFactory.create(name='Personal Risk Profile Group')
        self.personal_account_type = AccountTypeRiskProfileGroupFactory.create(account_type=0,
                                                                               risk_profile_group=self.risk_group)
        self.user = UserFactory.create()
        self.user.groups_add(User.GROUP_CLIENT)
        self.betasmartz_client = ClientFactory.create(user=self.user)

        self.sa1 = SecurityAnswerFactory.create(user=self.user, question='question one')
        self.sa2 = SecurityAnswerFactory.create(user=self.user, question='question two')

        self.betasmartz_client_account = ClientAccountFactory(primary_owner=self.betasmartz_client, account_type=ACCOUNT_TYPE_PERSONAL)
        self.external_asset1 = ExternalAssetFactory.create(owner=self.betasmartz_client)
        self.external_asset2 = ExternalAssetFactory.create(owner=self.betasmartz_client)

        self.goal1 = GoalFactory.create(account=self.betasmartz_client_account)
        self.goal2 = GoalFactory.create(account=self.betasmartz_client_account)

        self.betasmartz_client2 = ClientFactory.create()

    def tearDown(self):
        self.client.logout()

    def test_create_external_asset(self):
        url = '/api/v1/clients/%s/external-assets' % self.betasmartz_client.id
        old_count = ExternalAsset.objects.count()
        self.client.force_authenticate(user=self.betasmartz_client.user)

        # First input details about the loan.
        loan_data = {
            'type': ExternalAsset.Type.PROPERTY_LOAN.value,
            'name': 'My Home Loan',
            'owner': self.betasmartz_client.id,
            # description intentionally omitted to test optionality
            'valuation': -145000,
            'valuation_date': '2016-07-05',
            'growth': 0.03,
            'transfer_plan': {
                'begin_date': '2016-07-05',
                'amount': 1000,
                'growth': 0.0,
                'schedule': 'RRULE:FREQ=MONTHLY;BYMONTHDAY=1'
            },
            'acquisition_date': '2016-07-03',
        }
        response = self.client.post(url, loan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure the object was returned correctly
        self.assertTrue('id' in response.data)
        self.assertEqual(response.data['name'], 'My Home Loan')

        # Make sure the object was added to the DB, along with it's transfer plan
        self.assertEqual(ExternalAsset.objects.count(), old_count + 1)
        debt = ExternalAsset.objects.get(id=response.data['id'])
        self.assertEqual(debt.name, 'My Home Loan')
        self.assertEqual(debt.transfer_plan.amount, 1000)

        # Now submit details about the asset
        data = {
            'type': ExternalAsset.Type.FAMILY_HOME.value,
            'name': 'My Home',
            'owner': self.betasmartz_client.id,
            'description': 'This is my beautiful home',
            'valuation': 345000.01,
            'valuation_date': '2016-07-05',
            'growth': 0.01,
            # trasfer_plan intentionally omitted as there isn't one
            'acquisition_date': '2016-07-03',
            'debt': debt.id
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure the object was added to the DB
        self.assertEqual(ExternalAsset.objects.count(), old_count + 2)
        house = ExternalAsset.objects.get(id=response.data['id'])
        self.assertEqual(house.name, 'My Home')

    def test_update_asset(self):
        asset = self.external_asset1
        url = '/api/v1/clients/%s/external-assets/%s' % (self.betasmartz_client.id, asset.id)
        test_name = 'Holy Pingalicious Test Asset'
        self.assertNotEqual(asset.name, test_name)
        data = {
            'name': test_name,
        }
        old_count = ExternalAsset.objects.count()
        self.client.force_authenticate(user=self.betasmartz_client.user)
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ExternalAsset.objects.count(), old_count)  # No extra asset created
        self.assertTrue('id' in response.data)  # Correct response serializer used
        self.assertEqual(response.data['name'], test_name)  # New value returned
        asset.refresh_from_db()
        self.assertEqual(asset.name, test_name)  # Value in db actually changed

    def test_update_asset_no_id(self):
        """
        Make sure we can't update or set the id.
        """
        self.client.force_authenticate(user=self.betasmartz_client.user)

        # Try for update
        asset = self.external_asset1
        self.assertNotEqual(asset.id, 999)
        url = '/api/v1/clients/%s/external-assets/%s' % (self.betasmartz_client.id, asset.id)
        data = {'id': 999}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], asset.id)

        # Try for create
        url = '/api/v1/clients/%s/external-assets' % (self.betasmartz_client.id)
        data = {
            'id': 999,
            'type': ExternalAsset.Type.FAMILY_HOME.value,
            'name': 'My Home 2',
            'owner': self.betasmartz_client.id,
            'description': 'This is my beautiful home',
            'valuation': 345000.01,
            'valuation_date': '2016-07-05',
            'growth': 0.01,
            # trasfer_plan intentionally omitted as there isn't one
            'acquisition_date': '2016-07-03'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response.data['id'], 999)

    def test_get_all_assets(self):
        url = '/api/v1/clients/%s/external-assets' % (self.betasmartz_client.id)
        self.client.force_authenticate(user=self.betasmartz_client.user)

        # First check when there are none, we get the appropriate response
        ExternalAsset.objects.all().delete()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assets_count = ExternalAsset.objects.filter(owner=self.betasmartz_client).count()
        self.assertEqual(len(response.data), assets_count)

        # Then add one and make sure it is returned
        asset = ExternalAssetFactory.create(owner=self.betasmartz_client)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), assets_count + 1)
        self.assertEqual(response.data[0]['name'], asset.name)

    def test_get_asset_detail(self):
        asset = self.external_asset1
        url = '/api/v1/clients/%s/external-assets/%s' % (self.betasmartz_client.id, asset.id)
        self.client.force_authenticate(user=self.betasmartz_client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type'], asset.type)
        self.assertEqual(response.data['name'], asset.name)
        self.assertEqual(response.data['owner'], self.betasmartz_client.id)
        self.assertEqual(response.data['description'], asset.description)
        self.assertEqual(response.data['valuation'], asset.valuation)
        self.assertEqual(response.data['valuation_date'], str(asset.valuation_date))
        self.assertEqual(response.data['acquisition_date'], str(asset.acquisition_date))
        self.assertEqual(response.data['growth'], asset.growth)
        self.assertEqual(response.data['debt'], asset.debt)

    def test_delete_asset(self):
        asset1 = self.external_asset1
        url = '/api/v1/clients/%s/external-assets/%s' % (self.betasmartz_client.id, asset1.id)
        self.client.force_authenticate(user=self.betasmartz_client.user)

        old_count = ExternalAsset.objects.count()
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)  # Correct code received
        self.assertEqual(response.data, None)  # Nothing returned

        # Check Item no longer in DB
        self.assertEqual(ExternalAsset.objects.count(), old_count - 1)  # Asset removed
        self.assertIsNone(ExternalAsset.objects.filter(id=asset1.id).first())

    def test_asset_access(self):
        """
        test that users cannot see assets they are not authorised to
        :return:
        """
        # asset1 = self.external_asset1
        url = '/api/v1/clients/%s/external-assets' % self.betasmartz_client.id
        self.client.force_authenticate(user=self.betasmartz_client2.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Correct code received
        self.assertEqual(response.data, [])  # No assets available.

        # Now change to the authorised user, and we should get stuff.
        self.client.logout()
        self.client.force_authenticate(user=self.betasmartz_client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Correct code received
        self.assertEqual(len(response.data), 2)  # Assets available.

    def test_update_client_address(self):
        url = '/api/v1/clients/%s' % self.betasmartz_client.id

        # residential_address should be self.client3.residential_address.pk
        self.client.force_authenticate(self.betasmartz_client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='200 for authenticated put request to get user settings to check address')
        self.assertEqual(response.data['residential_address']['address'],
                         self.betasmartz_client.residential_address.address)
        old_regions = Region.objects.count()

        # Lets change the address
        new_add = '1 over there\nsomewhere'
        data = {
            "residential_address": response.data['residential_address'],
            'question_one': self.sa1.pk,
            'answer_one': 'test',
            'question_two': self.sa2.pk,
            'answer_two': 'test',
        }
        data['residential_address']['address'] = new_add

        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='200 for authenticated put request to update user address')
        self.assertEqual(response.data['residential_address']['address'], new_add)
        self.betasmartz_client.refresh_from_db()
        self.assertEqual(self.betasmartz_client.residential_address.address, new_add)
        # Make sure a new region was not created, as it was the same as the old one.
        self.assertEqual(Region.objects.count(), old_regions)

    def test_update_client_details(self):
        url = '/api/v1/clients/%s' % self.betasmartz_client.id
        # lets test income update
        old_income = self.betasmartz_client.income
        new_income = old_income + 5000.0
        old_other_income = self.betasmartz_client.other_income
        new_other_income = old_other_income + 1000.0
        new_occupation = '11-0000'
        new_industry_sector = 'NAICS 11'
        new_student_loan = True
        new_employer = 'League of Extraordinary Gentlemen'
        new_civil_status = 1  # 0 single, 1 married
        new_date_of_birth = date(1990, 1, 1)
        data = {
            'income': new_income,
            'other_income': new_other_income,
            'occupation': new_occupation,
            'industry_sector': new_industry_sector,
            'student_loan': new_student_loan,
            'employer': new_employer,
            'civil_status': new_civil_status,
            'date_of_birth': new_date_of_birth,
            'question_one': self.sa1.pk,
            'answer_one': 'test',
            'question_two': self.sa2.pk,
            'answer_two': 'test',
        }
        self.client.force_authenticate(self.user)
        response = self.client.put(url, data)
        self.betasmartz_client.refresh_from_db()  # Refresh after the put.
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='200 for authenticated put request to update client income, occupation, industry_sector, student_loan, employer, and civil status')
        self.assertTrue(response.data['id'] == self.betasmartz_client.id)
        self.assertTrue(response.data['income'] == new_income)
        self.assertTrue(response.data['occupation'] == new_occupation)
        self.assertTrue(response.data['industry_sector'] == new_industry_sector)
        self.assertTrue(response.data['student_loan'] == new_student_loan)
        self.assertTrue(self.betasmartz_client.occupation == new_occupation)
        self.assertTrue(self.betasmartz_client.industry_sector == new_industry_sector)
        self.assertTrue(self.betasmartz_client.student_loan == new_student_loan)
        self.assertTrue(response.data['employer'] == new_employer)
        self.assertTrue(response.data['civil_status'] == new_civil_status)
        self.assertEqual(response.data['date_of_birth'], str(new_date_of_birth))
        self.assertEqual(self.betasmartz_client.date_of_birth, new_date_of_birth)

    def test_create_client(self):
        # We need an accepted invitation to be able to create a client
        usr = UserFactory.create()
        EmailInviteFactory.create(user=usr, status=EmailInvite.STATUS_ACCEPTED)
        url = reverse('api:v1:client-list')
        address = {
            "address": "123 My Street\nSome City",
            "post_code": "112233",
            "region": {
                "name": "New South Wales",
                "country": "AU",
                "code": "NSW",
            }
        }
        regional_data = {
            'ssn': '555-55-5555',
        }
        data = {
            "advisor_agreement": True,
            "betasmartz_agreement": True,
            "date_of_birth": date(2016, 9, 21),
            "employment_status": EMPLOYMENT_STATUS_EMMPLOYED,
            "gender": GENDER_MALE,
            "income": 1234,
            "politically_exposed": True,
            "phone_num": "+1-234-234-2342",
            "residential_address": address,
            "regional_data": json.dumps(regional_data)
        }
        self.client.force_authenticate(usr)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Ensure it is created approved and accepted.
        self.assertEqual(response.data['is_confirmed'], True)
        self.assertEqual(response.data['is_accepted'], True)
        self.assertEqual(response.data['politically_exposed'], True)
        self.assertEqual(response.data['phone_num'], "+12342342342")
        self.assertEqual(response.data['residential_address']['address'], address['address'])
        self.assertEqual(response.data['residential_address']['post_code'], address['post_code'])
        self.assertEqual(response.data['betasmartz_agreement'], True)
        self.assertEqual(response.data['advisor_agreement'], True)
        regional_data_load = json.loads(response.data['regional_data'])
        self.assertEqual(regional_data_load['ssn'], regional_data['ssn'])

        self.assertEqual(usr.client.accounts_all.count(), 1)
        self.assertTrue(usr.client.accounts_all.get().confirmed)

        # check onboarding status is complete
        lookup_invite = EmailInvite.objects.get(user=usr)
        self.assertEqual(lookup_invite.status, EmailInvite.STATUS_COMPLETE)

        lookup_client = Client.objects.get(id=usr.client.id)
        self.assertNotEqual(lookup_client.agreement_time, None)
        self.assertNotEqual(lookup_client.agreement_ip, None)

        # can login with new client
        self.client = DjangoClient()  # django
        url = reverse('login')
        data = {
            'username': usr.email,
            'password': 'test',
        }
        response = self.client.post(url, data)
        # redirect to application
        self.assertRedirects(response, reverse('client:page', args=[usr.client.id, ]))

        # can retrieve profile info ok
        url = reverse('api:v1:user-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_client_no_address(self):
        # We need an accepted invitation to be able to create a client
        usr = UserFactory.create()
        EmailInviteFactory.create(user=usr, status=EmailInvite.STATUS_ACCEPTED)

        url = reverse('api:v1:client-list')
        regional_data = {
            'ssn': '555-55-5555',
        }
        data = {
            "advisor_agreement": True,
            "betasmartz_agreement": True,
            "date_of_birth": date(2016, 9, 21),
            "employment_status": EMPLOYMENT_STATUS_EMMPLOYED,
            "gender": GENDER_MALE,
            "income": 1234,
            "politically_exposed": True,
            "phone_num": "+1-234-234-2342",
            'regional_data': regional_data,
        }
        self.client.force_authenticate(usr)
        response = self.client.post(url, data)
        # Check client created with default address.
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['residential_address'] is not None)

    def test_create_client_no_regional_data(self):
        """
        regional_data is a required field, needs ssn field at a minimum
        """
        usr = UserFactory.create()
        EmailInviteFactory.create(user=usr, status=EmailInvite.STATUS_ACCEPTED)
        url = reverse('api:v1:client-list')
        address = {
            "address": "123 My Street\nSome City",
            "post_code": "112233",
            "region": {
                "name": "New South Wales",
                "country": "AU",
                "code": "NSW",
            }
        }
        data = {
            "advisor_agreement": True,
            "betasmartz_agreement": True,
            "date_of_birth": date(2016, 9, 21),
            "employment_status": EMPLOYMENT_STATUS_EMMPLOYED,
            "gender": GENDER_MALE,
            "income": 1234,
            "politically_exposed": True,
            "phone_num": "+1-234-234-2342",
            "residential_address": address,
        }
        self.client.force_authenticate(usr)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        regional_data = {
            'ssn': '555-55-5555',
        }
        data['regional_data'] = json.dumps(regional_data)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_client_with_advisor(self):
        """
        Test advisor is ignored, as advisor comes from invite.
        """
        # We need an accepted invitation to be able to create a client
        usr = UserFactory.create()
        invite = EmailInviteFactory.create(user=usr, status=EmailInvite.STATUS_ACCEPTED)

        url = reverse('api:v1:client-list')
        advisor = AdvisorFactory.create()
        regional_data = {
            'ssn': '555-55-5555',
        }
        data = {
            "advisor_agreement": True,
            "betasmartz_agreement": True,
            "date_of_birth": date(2016, 9, 21),
            "employment_status": EMPLOYMENT_STATUS_EMMPLOYED,
            "gender": GENDER_MALE,
            "income": 1234,
            "politically_exposed": True,
            "phone_num": "+1-234-234-2342",
            "residential_address": {
                "address": "123 My Street\nSome City",
                "post_code": "112233",
                "region": {
                    "name": "New South Wales",
                    "country": "AU",
                    "code": "NSW",
                }
            },
            "advisor": advisor.id,
            'regional_data': regional_data,
        }
        self.client.force_authenticate(usr)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(invite.advisor.id, advisor.id)
        self.assertEqual(response.data['advisor']['id'], invite.advisor.id)

    def test_create_client_with_confirmed(self):
        """
        Test is_confirmed is ignored, as client cannot set is_confirmed
        """
        # We need an accepted invitation to be able to create a client
        usr = UserFactory.create()
        EmailInviteFactory.create(user=usr, status=EmailInvite.STATUS_ACCEPTED)

        url = reverse('api:v1:client-list')
        regional_data = {
            'ssn': '555-55-5555',
        }
        data = {
            "advisor_agreement": True,
            "betasmartz_agreement": True,
            "date_of_birth": date(2016, 9, 21),
            "employment_status": EMPLOYMENT_STATUS_EMMPLOYED,
            "gender": GENDER_MALE,
            "income": 1234,
            "phone_num": "+1-234-234-2342",
            "politically_exposed": True,
            "residential_address": {
                "address": "123 My Street\nSome City",
                "post_code": "112233",
                "region": {
                    "name": "New South Wales",
                    "country": "AU",
                    "code": "NSW",
                }
            },
            "is_confirmed": False,
            'regional_data': regional_data,
        }
        self.client.force_authenticate(usr)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['is_confirmed'], True)

    def test_create_client_with_user(self):
        """
        Test user_id is ignored, as user must be logged in to create client, and the user will always be the logged in.
        """
        # We need an accepted invitation to be able to create a client
        usr = UserFactory.create()
        EmailInviteFactory.create(user=usr, status=EmailInvite.STATUS_ACCEPTED)

        url = reverse('api:v1:client-list')
        regional_data = {
            'ssn': '555-55-5555',
        }
        data = {
            "advisor_agreement": True,
            "betasmartz_agreement": True,
            "date_of_birth": date(2016, 9, 21),
            "employment_status": EMPLOYMENT_STATUS_EMMPLOYED,
            "gender": GENDER_MALE,
            "income": 1234,
            "politically_exposed": True,
            "phone_num": "+1-234-234-2342",
            "residential_address": {
                "address": "123 My Street\nSome City",
                "post_code": "112233",
                "region": {
                    "name": "New South Wales",
                    "country": "AU",
                    "code": "NSW",
                }
            },
            "user_id": 44,
            'regional_data': regional_data,
        }
        self.client.force_authenticate(usr)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(usr.id, 44)
        self.assertEqual(response.data['user']['id'], usr.id)

    def test_create_client_with_ib_onboard(self):
        """
        Test ib_onboard is created.
        """
        # We need an accepted invitation to be able to create a client
        usr = UserFactory.create()
        EmailInviteFactory.create(user=usr, status=EmailInvite.STATUS_ACCEPTED)
        url = reverse('api:v1:client-list')
        regional_data = {
            'ssn': '555-55-5555',
        }
        address = {
            "address": "123 My Street\nSome City",
            "post_code": "112233",
            "region": {
                "name": "New South Wales",
                "country": "AU",
                "code": "NSW",
            }
        }
        ib_onboard = {
           "account_number": "U1234567",
           "account_type" : ACCOUNT_TYPE_PERSONAL,
           "asset_exp_0_knowledge": 1,
           "asset_exp_0_trds_per_yr": 1,
           "asset_exp_0_yrs": 1,
           "asset_exp_1_knowledge": 1,
           "asset_exp_1_trds_per_yr": 1,
           "asset_exp_1_yrs": 1,
           "country_of_birth": "VE",
           "date_of_birth": "1986-03-21",
           "doc_exec_login_ts": "87987987987",
           "doc_exec_ts": "87987987987",
           "signature": "Fred Bloggs",
           "fin_info_ann_net_inc": 4,
           "fin_info_liq_net_worth": 5,
           "fin_info_net_worth": 3,
           "fin_info_tot_assets": 7,
           "ib_employment_status": IB_EMPLOY_STAT_EMPLOYED,
           "identif_leg_citizenship": "CA",
           "identif_ssn=": "111-111-11111",
           "other_income_source": SOURCE_OF_FUNDS_TYPE_CONSULTING,
           "num_dependents": 47,
           "phone_type": "Home",
           "reg_status_broker_deal": "False",
           "reg_status_disp": "False",
           "reg_status_exch_memb": "False",
           "reg_status_investig": "False",
           "reg_status_stk_cont": 1,
           "salutation": "Mr.",
           "suffix": "I",
           "tax_resid_0_tin": "111-111-1234",
           "tax_resid_0_tin_type": "SSN",
           "employer_address": address,
           "tax_address": address,
        }
        data = {
            "advisor_agreement": True,
            "betasmartz_agreement": True,
            "civil_status": abstract.PersonalData.CivilStatus['SINGLE'].value,
            "date_of_birth": date(2016, 9, 21),
            "employer": "Good Company, Inc.",
            "gender": GENDER_MALE,
            "income": 123467,
            "industry_sector": "NAICS 11",
            "occupation": "11-0000",
            "other_income": 1234,
            "politically_exposed": True,
            "phone_num": "+1-234-234-2342",
            "residential_address": address,
            "regional_data": regional_data,
            "ib_onboard": ib_onboard,
            "user_id": usr.id
        }
        self.client.force_authenticate(usr)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        client = Client.objects.get(id=response.data.get('id'))
        client_ib_onboard = client.ib_onboard
        client_ib_account = client.accounts[0].ib_account
        self.assertEqual(client_ib_onboard.account_number, ib_onboard['account_number'])
        self.assertEqual(client_ib_onboard.employer_address.address, ib_onboard['employer_address']['address'])
        self.assertEqual(client_ib_onboard.employer_address.post_code, ib_onboard['employer_address']['post_code'])
        self.assertEqual(client_ib_account.ib_account, 'U1234567')

    def test_create_client_with_readonly_access(self):
        """
        Test readonly_access is set.
        """
        # We need an accepted invitation to be able to create a client
        usr = UserFactory.create()
        EmailInviteFactory.create(user=usr, status=EmailInvite.STATUS_ACCEPTED, access_level=CLIENT_FULL_ACCESS)

        url = reverse('api:v1:client-list')

        regional_data = {
            'ssn': '555-55-5555',
        }
        address = {
            "address": "123 My Street\nSome City",
            "post_code": "112233",
            "region": {
                "name": "New South Wales",
                "country": "AU",
                "code": "NSW",
            }
        }
        data = {
            "advisor_agreement": True,
            "betasmartz_agreement": True,
            "date_of_birth": date(2016, 9, 21),
            "employment_status": EMPLOYMENT_STATUS_EMMPLOYED,
            "gender": GENDER_MALE,
            "income": 1234,
            "politically_exposed": True,
            "phone_num": "+1-234-234-2342",
            "residential_address": address,
            "regional_data": regional_data
        }
        self.client.force_authenticate(usr)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        client = Client.objects.get(id=response.data.get('id'))
        self.assertEqual(client.readonly_access, False)
        
        usr2 = UserFactory.create()
        EmailInviteFactory.create(user=usr2, status=EmailInvite.STATUS_ACCEPTED, access_level=CLIENT_READONLY_ACCESS)
        self.client.force_authenticate(usr2)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        client = Client.objects.get(id=response.data.get('id'))
        self.assertEqual(client.readonly_access, True)

    def test_advisor_invite_states_displayed(self):
        usr_accepted = UserFactory.create()
        invite_accepted = EmailInviteFactory.create(user=usr_accepted, status=EmailInvite.STATUS_ACCEPTED)
        self.assertEqual(invite_accepted.get_status_display(),'Accepted')

        usr_completed = UserFactory.create()
        invite_completed = EmailInviteFactory.create(user=usr_completed, status=EmailInvite.STATUS_COMPLETE)
        self.assertEqual(invite_completed.get_status_display(),'Complete')

        usr_created = UserFactory.create()
        invite_created = EmailInviteFactory.create(user=usr_created, status=EmailInvite.STATUS_CREATED)
        self.assertEqual(invite_created.get_status_display(),'Created')

        usr_expired = UserFactory.create()
        invite_expired = EmailInviteFactory.create(user=usr_expired, status=EmailInvite.STATUS_EXPIRED)
        self.assertEqual(invite_expired.get_status_display(),'Expired')

        usr_sent = UserFactory.create()
        invite_sent = EmailInviteFactory.create(user=usr_sent, status=EmailInvite.STATUS_SENT)
        self.assertEqual(invite_sent.get_status_display(),'Sent')

    def test_update_client_tax_filing_status(self):
        invite = EmailInviteFactory.create(status=EmailInvite.STATUS_ACCEPTED)
        url = reverse('api:v1:client-list')
        usr = UserFactory.create()
        EmailInviteFactory.create(user=usr, status=EmailInvite.STATUS_ACCEPTED)

        url = reverse('api:v1:client-list')
        regional_data = {
            'ssn': '555-55-5555',
            'tax_transcript': 'some.random.url',
            'tax_transcript_data': {"filing_status":"test"},
        }
        data = {
            "advisor_agreement": True,
            "betasmartz_agreement": True,
            "date_of_birth": date(2016, 9, 21),
            "employment_status": EMPLOYMENT_STATUS_EMMPLOYED,
            "gender": GENDER_MALE,
            "income": 1234,
            "politically_exposed": True,
            "phone_num": "+1-234-234-2342",
            "residential_address": {
                "address": "123 My Street\nSome City",
                "post_code": "112233",
                "region": {
                    "name": "New South Wales",
                    "country": "AU",
                    "code": "NSW",
                }
            },
            "user_id": 44,
            'regional_data': regional_data,
        }
        self.client.force_authenticate(usr)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(usr.id, 44)
        self.assertEqual(response.data['user']['id'], usr.id)
        regional_data_load = response.data.get('regional_data')
        self.assertEqual(regional_data_load['tax_transcript_data']['filing_status'], 'test')

    def test_update_client_drinks(self):
        url = '/api/v1/clients/%s' % self.betasmartz_client.id
        # lets test income update
        data = {
            'drinks': 5,
            'question_one': self.sa1.pk,
            'answer_one': 'test',
            'question_two': self.sa2.pk,
            'answer_two': 'test',
        }
        self.client.force_authenticate(self.user)
        response = self.client.put(url, data)
        self.betasmartz_client.refresh_from_db()  # Refresh after the put.
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='200 for authenticated put request to update client drinks')
        self.assertEqual(response.data['id'], self.betasmartz_client.id)
        self.assertEqual(response.data['drinks'], 5)

    def test_update_client_smoker(self):
        url = '/api/v1/clients/%s' % self.betasmartz_client.id
        # lets test income update
        data = {
            'smoker': True,
            'question_one': self.sa1.pk,
            'answer_one': 'test',
            'question_two': self.sa2.pk,
            'answer_two': 'test',
        }
        self.client.force_authenticate(self.user)
        response = self.client.put(url, data)
        self.betasmartz_client.refresh_from_db()  # Refresh after the put.
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='200 for authenticated put request to update client smoker field')
        self.assertEqual(response.data['id'], self.betasmartz_client.id)
        self.assertEqual(response.data['smoker'], True)

    def test_get_all_client_goals(self):
        """
        should list all goals from all accounts
        """
        # goal from another account
        second_account = ClientAccountFactory.create(primary_owner=self.betasmartz_client)
        goal = GoalFactory.create(account=second_account)

        url = '/api/v1/clients/{}/goals'.format(self.betasmartz_client.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.user)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # make sure goals are listed in data
        self.assertEqual(response.data[0]['id'], self.goal1.id)
        self.assertEqual(response.data[1]['id'], self.goal2.id)
        self.assertEqual(response.data[2]['id'], goal.id)

    def test_update_client_employer_type(self):
        """


        """
        url = '/api/v1/clients/%s' % self.betasmartz_client.id
        # lets test income update
        data = {
            'employer_type': 3,
            'question_one': self.sa1.pk,
            'answer_one': 'test',
            'question_two': self.sa2.pk,
            'answer_two': 'test',
        }
        self.client.force_authenticate(self.user)
        response = self.client.put(url, data)
        self.betasmartz_client.refresh_from_db()  # Refresh after the put.
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='200 for authenticated put request to update client employer type field')
        self.assertEqual(response.data['id'], self.betasmartz_client.id)
        self.assertEqual(response.data['employer_type'], 3)

    def test_get_no_activity(self):
        url = '/api/v1/clients/{}/activity'.format(Fixture1.personal_account1().primary_owner.id)
        self.client.force_authenticate(user=Fixture1.personal_account1().primary_owner.user)
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

        url = '/api/v1/clients/{}/activity'.format(Fixture1.personal_account1().primary_owner.id)
        self.client.force_authenticate(user=Fixture1.personal_account1().primary_owner.user)
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

    def test_quovo_get_accounts(self):
        url = '/api/v1/quovo/get-accounts'
        self.client.force_authenticate(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code,status.HTTP_200_OK)
        self.assertContains(response,'data')

    def test_quovo_get_iframe_token(self):
        url = '/api/v1/quovo/get-iframe-token'
        self.client.force_authenticate(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code,status.HTTP_200_OK)
        self.assertContains(response,'data')

    def test_update_risk_profile_responses(self):
        url = reverse('api:v1:client-risk-profile-responses', args=[self.betasmartz_client.id])
        self.client.force_authenticate(self.user)
        risk_profile_response = RiskProfileAnswerFactory.create()
        data=[risk_profile_response.id]
        response = self.client.put(url, data)
        self.assertEqual(response.status_code,status.HTTP_200_OK)
        self.assertEqual(response.data, data)

        other_advisor = AdvisorFactory.create()
        self.client.force_authenticate(other_advisor.user)
        response = self.client.put(url, data)
        self.assertEqual(response.status_code,status.HTTP_403_FORBIDDEN)

        other_client = ClientFactory.create()
        self.client.force_authenticate(other_client.user)
        response = self.client.put(url, data)
        self.assertEqual(response.status_code,status.HTTP_403_FORBIDDEN)
