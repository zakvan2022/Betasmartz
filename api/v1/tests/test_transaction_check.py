import os
import json
from decimal import Decimal
from django.core.urlresolvers import reverse
from datetime import date, timedelta, datetime
from unittest import mock, skip
from unittest.mock import MagicMock
from django.utils import timezone
from pinax.eventlog.models import Log
from rest_framework import status
from rest_framework.test import APITestCase
from .factories import MarkowitzScaleFactory, GoalTypeFactory, \
    ExecutionDistributionFactory, RecurringTransactionFactory, \
    ContentTypeFactory, TransactionFactory, PositionLotFactory
from activitylog.models import ActivityLog, ActivityLogEvent
from activitylog.event import Event
from common.constants import GROUP_SUPPORT_STAFF
from main.constants import ACCOUNT_TYPE_PERSONAL
from goal.models import GoalMetric, Transaction, Goal, EventMemo
from main.management.commands.populate_test_data import populate_prices, populate_cycle_obs, populate_cycle_prediction
from execution.models import Execution, MarketOrderRequest
from main.risk_profiler import max_risk, MINIMUM_RISK
from user.models import User
from portfolios.models import InvestmentType
from main import constants
from main.tests.fixture import Fixture1
from .factories import GroupFactory, GoalFactory, ClientAccountFactory, GoalSettingFactory, TickerFactory, \
    AssetClassFactory, PortfolioSetFactory, MarketIndexFactory, GoalMetricFactory, AssetFeatureValueFactory, \
    PlaidUserFactory, StripeUserFactory, EmailInviteFactory, RegionFactory, AddressFactory, \
    RiskProfileGroupFactory, AccountTypeRiskProfileGroupFactory, AdvisorFactory, SecurityQuestionFactory, \
    ClientFactory
from api.v1.goals.serializers import GoalSettingSerializer, GoalCreateSerializer, RecurringTransactionCreateSerializer
from main.plaid import create_public_token, get_accounts
from client.models import EmailInvite, Client, ClientAccount
from goal.models import RecurringTransaction
from main.constants import EMPLOYMENT_STATUS_EMMPLOYED, GENDER_MALE
from django.conf import settings
from main.management.commands.transactions_check import execute_recurring_transactions_today
from main.plaid import get_stripe_account_token

mocked_now = datetime(2016, 1, 1)


class TransactionsCheckTests(APITestCase):
    def setUp(self):
        self.support_group = GroupFactory(name=GROUP_SUPPORT_STAFF)
        self.bonds_asset_class = AssetClassFactory.create(name='US_TOTAL_BOND_MARKET')
        self.stocks_asset_class = AssetClassFactory.create(name='HEDGE_FUNDS')
        self.portfolio_set = PortfolioSetFactory.create()
        self.portfolio_set.asset_classes.add(self.bonds_asset_class, self.stocks_asset_class)

        self.maxDiff = None
        # client with some personal assets, cash balance and goals
        self.region = RegionFactory.create()
        self.betasmartz_client_address = AddressFactory(region=self.region)
        self.risk_group = RiskProfileGroupFactory.create(name='Personal Risk Profile Group')
        self.personal_account_type = AccountTypeRiskProfileGroupFactory.create(account_type=ACCOUNT_TYPE_PERSONAL,
                                                                               risk_profile_group=self.risk_group)
        self.advisor = AdvisorFactory.create()
        self.question_one = SecurityQuestionFactory.create()
        self.question_two = SecurityQuestionFactory.create()

        self.risk_score_metric = {
            "type": GoalMetric.METRIC_TYPE_RISK_SCORE,
            "comparison": GoalMetric.METRIC_COMPARISON_EXACTLY,
            "configured_val": MINIMUM_RISK,
            "rebalance_type": GoalMetric.REBALANCE_TYPE_RELATIVE,
            "rebalance_thr": 0.1
        }

        self.expected_tax_transcript_data = {
            'name_spouse': 'MELISSA',
            'SSN_spouse': '477-xx-xxxx',
            'address': {
                'address1': '200 SAMPLE RD',
                'address2': '',
                'city': 'HOT SPRINGS',
                'post_code': '33XXX',
                'state': 'AR'
            },
            'name': 'DAMON M MELISSA',
            'SSN': '432-xx-xxxx',
            'filing_status': 'Married Filing Joint',
            'total_income': '67,681.00',
            'total_payments': '7,009.00',
            'earned_income_credit': '0.00',
            'combat_credit': '0.00',
            'add_child_tax_credit': '0.00',
            'excess_ss_credit': '0.00',
            'refundable_credit': '2,422.00',
            'premium_tax_credit': '',
            'adjusted_gross_income': '63,505.00',
            'taxable_income': '40,705.00',
            'blind': 'N',
            'blind_spouse': 'N',
            'exemptions': '4',
            'exemption_amount': '12,800.00',
            'tentative_tax': '5,379.00',
            'std_deduction': '10,000.00',
            'total_adjustments': '4,176.00',
            'tax_period': 'Dec. 31, 2005',
            'se_tax': '6,052.00',
            'total_tax': '9,431.00',
            'total_credits': '2,000.00',
        }

        self.expected_social_security_statement_data = {
            'EmployerPaidThisYearMedicare': '1,177',
            'EmployerPaidThisYearSocialSecurity': '5,033',
            'EstimatedTaxableEarnings': '21,807',
            'LastYearMedicare': '21,807',
            'LastYearSS': '21,807',
            'PaidThisYearMedicare': '1,177',
            'PaidThisYearSocialSecurity': '4,416',
            'RetirementAtAge62': '759',
            'RetirementAtAge70': '1,337',
            'RetirementAtFull': '1,078',
            'SurvivorsChild': '808',
            'SurvivorsSpouseAtFull': '1,077',
            'SurvivorsSpouseWithChild': '808',
            'SurvivorsTotalFamilyBenefitsLimit': '1,616',
            'date_of_estimate': 'January 2, 2016',
        }

    def test_transactions_check(self):
        """
        Create an Goal with RecurringTransaction
        Execute transactions_check and make sure Transactions are
        created for the Recurring Transactions.
        """
        # Bring an invite key, get logged in as a new user
        invite = EmailInviteFactory.create(status=EmailInvite.STATUS_SENT)

        url = reverse('api:v1:client-user-register')
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
        lookup_invite = EmailInvite.objects.get(pk=invite.pk)
        invite_detail_url = reverse('api:v1:invite-detail', kwargs={'invite_key': invite.invite_key} )

        self.assertEqual(EmailInvite.STATUS_ACCEPTED, lookup_invite.status)

        # New user must be logged in too
        self.assertIn('sessionid', response.cookies)

        # GET: /api/v1/invites/:key
        # If a session is logged in, return 200 with data
        response = self.client.get(invite_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='/api/v1/invites/:key should be valid during invitation')
        self.assertEqual(response.data['invite_key'], invite.invite_key,
                         msg='/api/v1/invites/:key should have invitation data')
        self.assertEqual(response.data['status'], EmailInvite.STATUS_ACCEPTED,
                         msg='/api/v1/invites/:key should have invitation status ACCEPTED')
        self.assertEqual('onboarding_data' in response.data, True,
                         msg='/api/v1/invites/:key should show onboarding_data to user')
        self.assertEqual(response.data['risk_profile_group'], self.risk_group.id)

        # Make sure the user now has access to the risk-profile-groups endpoint
        rpg_url = reverse('api:v1:settings-risk-profile-groups-list')
        response = self.client.get(rpg_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['id'], self.risk_group.id)

        # PUT: /api/v1/invites/:key
        # Submit with onboarding_data
        onboarding = {'onboarding_data': {'foo': 'bar'}}
        response = self.client.put(invite_detail_url, data=onboarding)

        lookup_invite = EmailInvite.objects.get(pk=invite.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Onboarding must accept json objects')
        self.assertEqual(response.data['status'], EmailInvite.STATUS_ACCEPTED,
                         msg='invitation status ACCEPTED')
        self.assertEqual(lookup_invite.onboarding_data['foo'], 'bar',
                         msg='should save onboarding_file')

        # PUT: /api/v1/invites/:key
        # Tax transcript upload and parsing
        with open(os.path.join(settings.BASE_DIR, 'pdf_parsers', 'samples', 'sample_2006.pdf'), mode="rb") as tax_transcript:
            data = {
                'tax_transcript': tax_transcript
            }
            response = self.client.put(invite_detail_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Updating onboarding with tax_transcript PDF returns OK')
        self.assertNotEqual(response.data['tax_transcript_data'], None,
                            msg='tax_transcript_data is in the response and not None')
        self.assertEqual(response.data['tax_transcript_data'], self.expected_tax_transcript_data,
                         msg='Parsed tax_transcript_data matches expected')

        with open(os.path.join(settings.BASE_DIR, 'pdf_parsers', 'samples', 'ssa-7005-sm-si_wanda_worker_young.pdf'), mode="rb") as ss_statement:
            data = {
                'social_security_statement': ss_statement
            }
            response = self.client.put(invite_detail_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Updating onboarding with tax_transcript PDF returns OK')
        self.assertNotEqual(response.data['social_security_statement'], None,
                            msg='social_security_statement_data is in the response and not None')
        self.assertEqual(response.data['social_security_statement_data'], self.expected_social_security_statement_data,
                         msg='Parsed social_security_statement_data matches expected')

        with open(os.path.join(settings.BASE_DIR, 'pdf_parsers', 'samples', 'ssa-7005-sm-si_wanda_worker_young.pdf'), mode="rb") as ss_statement:
            data = {
                'partner_social_security_statement': ss_statement
            }
            response = self.client.put(invite_detail_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Updating onboarding with tax_transcript PDF returns OK')
        self.assertNotEqual(response.data['partner_social_security_statement'], None,
                            msg='partner_social_security_statement_data is in the response and not None')
        self.assertEqual(response.data['partner_social_security_statement_data'], self.expected_social_security_statement_data,
                         msg='Parsed partner_social_security_statement_data matches expected')

        self.assertEqual(response._headers['content-type'], ('Content-Type', 'application/json'),
                         msg='Response content type is application/json after upload')

        lookup_invite = EmailInvite.objects.get(pk=invite.pk)
        self.assertEqual(response.data['status'], EmailInvite.STATUS_ACCEPTED,
                         msg='invitation status ACCEPTED')

        # re-upload tax transcript
        with open(os.path.join(settings.BASE_DIR, 'pdf_parsers', 'samples', 'sample_2006.pdf'), mode="rb") as tax_transcript:
            data = {
                'tax_transcript': tax_transcript
            }
            response = self.client.put(invite_detail_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Updating onboarding with tax_transcript PDF returns OK')
        self.assertNotEqual(response.data['tax_transcript_data'], None,
                            msg='tax_transcript_data is in the response and not None')
        self.assertEqual(response.data['tax_transcript_data'], self.expected_tax_transcript_data,
                         msg='Parsed tax_transcript_data matches expected')

        # test stripe photo_verification upload goes through ok
        with open(os.path.join(settings.BASE_DIR, 'tests', 'success.png'), mode="rb") as photo_verification:
            data = {
                'photo_verification': photo_verification
            }
            response = self.client.put(invite_detail_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Updating onboarding with photo verification returns OK')
        self.assertNotEqual(response.data['photo_verification'], None,
                            msg='photo_verification is in the response and not None')

        # create client and make sure tax_transcript data is carried over properly
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
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        regional_data_load = json.loads(response.data['regional_data'])
        self.assertNotEqual(regional_data_load['tax_transcript'], None)
        self.assertEqual(regional_data_load['tax_transcript_data']['filing_status'],
                         self.expected_tax_transcript_data['filing_status'],
                         msg='Parsed tax_transcript_data filing_status parsed successfully')

        lookup_invite = EmailInvite.objects.get(pk=invite.pk)

        # create goal
        self.bonds_index = MarketIndexFactory.create()
        self.stocks_index = MarketIndexFactory.create()

        self.bonds_asset_class = AssetClassFactory.create(investment_type=InvestmentType.Standard.BONDS.get())
        self.stocks_asset_class = AssetClassFactory.create(investment_type=InvestmentType.Standard.STOCKS.get())
        # Add the asset classes to the portfolio set
        self.portfolio_set = PortfolioSetFactory.create()
        self.portfolio_set.asset_classes.add(self.bonds_asset_class, self.stocks_asset_class)
        self.bonds_ticker = TickerFactory.create(asset_class=self.bonds_asset_class,
                                                 benchmark=self.bonds_index)
        self.stocks_ticker = TickerFactory.create(asset_class=self.stocks_asset_class,
                                                  benchmark=self.stocks_index)

        # Set the markowitz bounds for today
        self.m_scale = MarkowitzScaleFactory.create()
        # populate the data needed for the optimisation
        # We need at least 500 days as the cycles go up to 70 days and we need at least 7 cycles.
        populate_prices(500, asof=mocked_now.date())
        populate_cycle_obs(500, asof=mocked_now.date())
        populate_cycle_prediction(asof=mocked_now.date())
        account = ClientAccount.objects.get(primary_owner=lookup_invite.user.client)
        # setup some inclusive goal settings
        goal_settings = GoalSettingFactory.create()
        goal = GoalFactory.create(selected_settings=goal_settings)

        # plaid user with access_token needed for deposits
        plaid_user = PlaidUserFactory.create(user=account.primary_owner.user)
        resp = create_public_token()
        plaid_user.access_token = resp['access_token']
        plaid_user.save()
        accounts = get_accounts(plaid_user.user)

        tx1 = self.rt = RecurringTransactionFactory.create(
            setting=goal_settings,
            begin_date=timezone.now().date(),
            amount=10,
            growth=0.0005,
            schedule='RRULE:FREQ=DAILY;INTERVAL=1',
            account_id=accounts[0]['account_id'],
            enabled=True,
        )
        lookup_transactions = Transaction.objects.all()
        self.assertEqual(len(lookup_transactions), 0)
        tx1.setting.goal.approve_selected()

        execute_recurring_transactions_today()

        lookup_transactions = Transaction.objects.all()
        self.assertEqual(len(lookup_transactions), 1)

        trans = Transaction.objects.first()
        self.assertEqual(trans.to_goal.state, Goal.State.ACTIVE.value)
        self.assertEqual(trans.status, Transaction.STATUS_PENDING)
