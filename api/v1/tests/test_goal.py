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
from execution.models import Execution, MarketOrderRequest
from goal.models import GoalMetric, EventMemo, Transaction, Goal
from main import constants
from main.constants import ACCOUNT_TYPE_PERSONAL
from main.management.commands.populate_test_data import populate_prices, populate_cycle_obs, populate_cycle_prediction
from main.risk_profiler import max_risk, MINIMUM_RISK
from main.tests.fixture import Fixture1
from portfolios.models import InvestmentType, PortfolioProvider
from user.models import User
from .factories import GroupFactory, GoalFactory, ClientAccountFactory, GoalSettingFactory, TickerFactory, \
    AssetClassFactory, PortfolioSetFactory, MarketIndexFactory, GoalMetricFactory, AssetFeatureValueFactory, \
    PlaidUserFactory, StripeUserFactory, EmailInviteFactory, RegionFactory, AddressFactory, \
    RiskProfileGroupFactory, AccountTypeRiskProfileGroupFactory, AdvisorFactory, SecurityQuestionFactory, \
    ClientFactory
from api.v1.goals.serializers import GoalSettingSerializer, GoalCreateSerializer, RecurringTransactionCreateSerializer
from main.plaid import create_public_token, get_accounts
from client.models import EmailInvite, Client, ClientAccount
from main.constants import EMPLOYMENT_STATUS_EMMPLOYED, GENDER_MALE
from statements.models import RecordOfAdvice
from django.conf import settings

mocked_now = datetime(2016, 1, 1)


class GoalTests(APITestCase):
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
        RecordOfAdvice.send_roa_generated_email = MagicMock()
        RecordOfAdvice.save_pdf = MagicMock()

    def tearDown(self):
        self.client.logout()

    def test_get_list(self):
        goal = Fixture1.goal1()
        goal.approve_selected()
        url = '/api/v1/goals'
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        # Make sure for the list endpoint, selected settings is an object, but active and approved are null or integer.
        self.assertNotEqual(response.data[0]['active_settings'], None)
        self.assertEqual(response.data[0]['approved_settings'], response.data[0]['selected_settings']['id'])

    def test_get_detail(self):
        goal = Fixture1.goal1()
        url = '/api/v1/goals/{}'.format(goal.id)
        goal.approve_selected()
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], Fixture1.goal1().id)
        # Make sure for the detail endpoint, selected settings is an object, but active and approved are null or integer.
        self.assertNotEqual(response.data['active_settings'], None)
        self.assertEqual(response.data['approved_settings'], response.data['selected_settings']['id'])

    def test_get_no_activity(self):
        url = '/api/v1/goals/{}/activity'.format(Fixture1.goal1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_all_activity(self):
        # First add some transactions, balances and eventlogs, and make sure the ActivityLogs are set.
        Fixture1.settings_event1()
        Fixture1.transaction_event1()
        Fixture1.populate_balance1()  # 2 Activity lines
        # We also need to activate the activity logging for the desired event types.
        ActivityLogEvent.get(Event.APPROVE_SELECTED_SETTINGS)
        ActivityLogEvent.get(Event.GOAL_BALANCE_CALCULATED)
        ActivityLogEvent.get(Event.GOAL_DEPOSIT_EXECUTED)

        url = '/api/v1/goals/{}/activity'.format(Fixture1.goal1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        # Note the Goal not included in response as it is in request.
        self.assertEqual(response.data[3], {'time': 946684800,
                                            'type': ActivityLogEvent.get(Event.APPROVE_SELECTED_SETTINGS).activity_log.id})  # Setting change approval
        self.assertEqual(response.data[2], {'balance': 0.0,
                                            'time': 978220800,
                                            'type': ActivityLogEvent.get(Event.GOAL_BALANCE_CALCULATED).activity_log.id})  # Balance
        self.assertEqual(response.data[1], {'balance': 3000.0,
                                            'time': 978307200,
                                            'type': ActivityLogEvent.get(Event.GOAL_BALANCE_CALCULATED).activity_log.id})  # Balance
        # Deposit. Note inclusion of amount, as we're looking at it from the goal perspective.
        self.assertEqual(response.data[0], {'amount': 3000.0,
                                            'data': [3000.0],
                                            'time': 978307200,
                                            'type': ActivityLogEvent.get(Event.GOAL_DEPOSIT_EXECUTED).activity_log.id})

    def test_event_memo(self):
        '''
        Tests event memos and assigning multiple events to one activity log item.
        :return:
        '''
        # Add a public settings event with a memo
        se = Fixture1.settings_event1()
        EventMemo.objects.create(event=se, comment='A memo for e1', staff=False)
        # Add a staff settings event with a memo
        se2 = Fixture1.settings_event2()
        EventMemo.objects.create(event=se2, comment='A memo for e2', staff=True)
        # Add a transaction event without a memo
        Fixture1.transaction_event1()
        # We also need to activate the activity logging for the desired event types.
        # We add selected and update to the same une to test that too
        al = ActivityLog.objects.create(name="Settings Funk", format_str='Settings messed with')
        ActivityLogEvent.objects.create(id=Event.APPROVE_SELECTED_SETTINGS.value, activity_log=al)
        ActivityLogEvent.objects.create(id=Event.UPDATE_SELECTED_SETTINGS.value, activity_log=al)
        ActivityLogEvent.get(Event.GOAL_DEPOSIT_EXECUTED)

        url = '/api/v1/goals/{}/activity'.format(Fixture1.goal1().id)
        # Log in as a client and make sure I see the public settings event, and the transaction, not the staff entry.
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[2]['memos'], ['A memo for e1'])
        self.assertFalse('memos' in response.data[0])
        self.assertFalse('memos' in response.data[1])

        # Log in as the advisor and make sure I see all three events.
        self.client.force_authenticate(user=Fixture1.advisor1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[2]['memos'], ['A memo for e1'])
        self.assertEqual(response.data[1]['memos'], ['A memo for e2'])
        self.assertFalse('memos' in response.data[0])

    def test_performance_history_empty(self):
        url = '/api/v1/goals/{}/performance-history'.format(Fixture1.goal1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_performance_history(self):
        goal = GoalFactory.create()
        prices = (
            (Fixture1.fund1(), '20160101', 10),
            (Fixture1.fund1(), '20160102', 10.5),
            (Fixture1.fund1(), '20160103', 10.6),
            (Fixture1.fund1(), '20160104', 10.3),
            (Fixture1.fund1(), '20160105', 10.1),
            (Fixture1.fund1(), '20160106', 9.9),
            (Fixture1.fund1(), '20160107', 10.5),
            (Fixture1.fund2(), '20160101', 50),
            (Fixture1.fund2(), '20160102', 51),
            (Fixture1.fund2(), '20160103', 53),
            (Fixture1.fund2(), '20160104', 53.5),
            (Fixture1.fund2(), '20160105', 51),
            (Fixture1.fund2(), '20160106', 52),
            (Fixture1.fund2(), '20160107', 51.5),
        )
        Fixture1.set_prices(prices)

        order_details = (
            (Fixture1.personal_account1(), MarketOrderRequest.State.COMPLETE),
            (Fixture1.personal_account1(), MarketOrderRequest.State.COMPLETE),
            (Fixture1.personal_account1(), MarketOrderRequest.State.COMPLETE),
            (Fixture1.personal_account1(), MarketOrderRequest.State.COMPLETE),
            (Fixture1.personal_account1(), MarketOrderRequest.State.COMPLETE),
            (Fixture1.personal_account1(), MarketOrderRequest.State.COMPLETE),
        )

        orders = Fixture1.add_orders(order_details)

        execution_details = (
            (Fixture1.fund1(), orders[0], 3, 10.51, -75, '20160102'),
            (Fixture1.fund1(), orders[0], 4, 10.515, -75.05, '20160102'),
            (Fixture1.fund1(), orders[1], -1, 10.29, 10, '20160104'),
            (Fixture1.fund2(), orders[2], 2, 53.49, -110, '20160104'),
            (Fixture1.fund2(), orders[2], 8, 53.5, -430, '20160104'),
            (Fixture1.fund1(), orders[3], -3, 10.05, 30, '20160105'),
            (Fixture1.fund2(), orders[4], -3, 50.05, 145, '20160105'),
            (Fixture1.fund2(), orders[4], -2, 50.04, 98, '20160105'),
            (Fixture1.fund2(), orders[5], -5, 52, 255, '20160106'),
        )
        executions = Fixture1.add_executions(execution_details)
        execution_requests = Fixture1.add_execution_requests(goal, execution_details, executions)

        # We distribute the entire executions to one goal.
        distributions = (
            (executions[0], 3, Fixture1.goal1()),
            (executions[1], 4, Fixture1.goal1()),
            (executions[2], -1, Fixture1.goal1()),
            (executions[3], 2, Fixture1.goal1()),
            (executions[4], 8, Fixture1.goal1()),
            (executions[5], -3, Fixture1.goal1()),
            (executions[6], -3, Fixture1.goal1()),
            (executions[7], -2, Fixture1.goal1()),
            (executions[8], -5, Fixture1.goal1()),
        )
        Fixture1.add_execution_distributions(distributions, execution_requests)

        url = '/api/v1/goals/{}/performance-history'.format(Fixture1.goal1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0], (16802, 0))  # 20160102
        self.assertEqual(response.data[1], (16803, Decimal('0.009524')))
        self.assertEqual(response.data[2], (16804, Decimal('-0.028302')))
        self.assertEqual(response.data[3], (16805, Decimal('-0.043901')))
        self.assertEqual(response.data[4], (16806, Decimal('-0.019802')))
        self.assertEqual(response.data[5], (16807, Decimal('0.060606')))
        self.assertEqual(response.data[6], (16808, 0))

    def test_put_settings_recurring_transactions(self):
        # Test PUT with good transaction data
        tx1 = RecurringTransactionFactory.create()
        tx2 = RecurringTransactionFactory.create()
        url = '/api/v1/goals/{}/selected-settings'.format(Fixture1.goal1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        serializer = RecurringTransactionCreateSerializer(tx1)
        serializer2 = RecurringTransactionCreateSerializer(tx2)
        settings_changes = {
            'recurring_transactions': [serializer.data, serializer2.data, ],
        }
        response = self.client.put(url, settings_changes)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # bad transaction missing enabled field
        data = serializer.data
        del data['enabled']
        settings_changes = {
            'recurring_transactions': [data, serializer2.data, ],
        }
        response = self.client.put(url, settings_changes)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_settings_no_record_of_advice(self):
        # Test PUT with no memo
        old_events = Log.objects.count()
        old_memos = EventMemo.objects.count()
        url = '/api/v1/goals/{}/selected-settings'.format(Fixture1.goal1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        settings_changes = {"target": 1928355}
        response = self.client.put(url, settings_changes)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Make sure an event log was written
        self.assertEqual(old_events + 1, Log.objects.count())
        # Make sure no event memo was written
        self.assertEqual(old_memos, EventMemo.objects.count())

    def test_put_settings_with_record_of_advice_by_advisor(self):
        # Test with a memo and true staff
        old_events = Log.objects.count()
        old_roas = RecordOfAdvice.objects.count()
        url = '/api/v1/goals/{}/selected-settings'.format(Fixture1.goal1().id)
        advisor = Fixture1.client1().advisor
        self.client.force_authenticate(user=advisor.user)
        record_of_advice = {
            'circumstances': 'Changes in the client\'s circumstances',
            'basis': 're-weighting of a portfolio',
            'details': 'rebalance of portfolio back to original asset allocation'
        }
        settings_changes = {
            "target": 1928355,
            "record_of_advice": record_of_advice
        }
        response = self.client.put(url, settings_changes)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Make sure an event log was written
        self.assertEqual(old_events + 2, Log.objects.count())
        # Make sure an record of advice was written
        self.assertEqual(old_roas + 1, RecordOfAdvice.objects.count())
        # Make sure the record of advice was the same as what I passed.
        roa = RecordOfAdvice.objects.order_by('-id')[0]
        self.assertTrue(roa.basis, record_of_advice['basis'])
        self.assertTrue(roa.circumstances, record_of_advice['circumstances'])
        self.assertTrue(roa.details, record_of_advice['details'])

    def test_put_settings_with_record_of_advice_by_client(self):
        # Test with a memo and true staff
        old_events = Log.objects.count()
        old_roas = RecordOfAdvice.objects.count()
        url = '/api/v1/goals/{}/selected-settings'.format(Fixture1.goal1().id)
        advisor = Fixture1.client1().advisor
        self.client.force_authenticate(user=Fixture1.client1().user)
        record_of_advice = {
            'circumstances': 'Changes in the client\'s circumstances',
            'basis': 're-weighting of a portfolio',
            'details': 'rebalance of portfolio back to original asset allocation'
        }
        settings_changes = {
            "target": 1928355,
            "record_of_advice": record_of_advice
        }
        response = self.client.put(url, settings_changes)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_settings_with_risk_too_high(self):
        url = '/api/v1/goals/{}/selected-settings'.format(Fixture1.goal1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        rsm = self.risk_score_metric.copy()
        rsm['configured_val'] = 0.9
        new_settings = {
            "metric_group": {"metrics": [rsm]},
        }
        self.assertLess(max_risk(Fixture1.goal1().selected_settings), 0.9)
        response = self.client.put(url, new_settings)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_pending_transfers(self):
        # Populate an executed deposit and make sure no pending transfers are returned
        tx1 = Fixture1.transaction1()
        url = '/api/v1/goals/{}/pending-transfers'.format(Fixture1.goal1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        # Populate 2 pending transfers (a deposit and withdrawal) and make sure they are both returned.
        tx2 = Fixture1.pending_deposit1()
        tx3 = Fixture1.pending_withdrawal1()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = [
            {
                "id": 3,
                "time": 946652400,
                "amount": -3500.0
            },
            {
                "id": 2,
                "time": 946648800,
                "amount": 4000.0
            }
        ]
        self.assertEqual(response.data, data)

    def test_recommended_risk_scores(self):
        """
        expects the years parameter for the span of risk scores
        """
        url = '/api/v1/goals/{}/risk-score-data'.format(Fixture1.goal1().id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['max'], MINIMUM_RISK)
        self.assertEqual(response.data['recommended'], MINIMUM_RISK)

    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_calculate_all_portfolios(self):
        """
        expects the setting parameter to be a json dump
        of the goal settings to use for the portfolio calculation
        """
        # tickers for testing portfolio calculations in goals endpoint
        # otherwise, No valid instruments found

        TickerFactory.create(symbol='IAGG', asset_class=self.bonds_asset_class)
        TickerFactory.create(symbol='AGG', asset_class=self.bonds_asset_class)
        TickerFactory.create(symbol='ITOT', asset_class=self.stocks_asset_class)
        TickerFactory.create(symbol='GRFXX', asset_class=self.stocks_asset_class)
        TickerFactory.create(symbol='IPO')
        fund = TickerFactory.create(symbol='rest')
        self.portfolio_set.asset_classes.add(fund.asset_class)

        # Set the markowitz bounds for today
        self.m_scale = MarkowitzScaleFactory.create()

        # populate the data needed for the optimisation
        # We need at least 500 days as the cycles go up to 70 days and we need at least 7 cycles.
        populate_prices(500, asof=mocked_now.date())
        populate_cycle_obs(500, asof=mocked_now.date())
        populate_cycle_prediction(asof=mocked_now.date())

        account = ClientAccountFactory.create(primary_owner=Fixture1.client1())
        # setup some inclusive goal settings
        goal_settings = GoalSettingFactory.create()
        # Create a risk score metric for the settings
        GoalMetricFactory.create(group=goal_settings.metric_group, type=GoalMetric.METRIC_TYPE_RISK_SCORE)
        goal = GoalFactory.create(account=account,
                                  selected_settings=goal_settings,
                                  portfolio_set=self.portfolio_set,
                                  state=Goal.State.ACTIVE.value)
        goal_settings.completion_date = timezone.now().date() - timedelta(days=365)
        serializer = GoalSettingSerializer(goal_settings)
        url = '/api/v1/goals/{}/calculate-all-portfolios?setting={}'.format(goal.id, json.dumps(serializer.data))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_calculate_portfolio(self):
        """
        expects the setting parameter to be a json dump
        of the goal settings to use for the portfolio calculation
        """
        # tickers for testing portfolio calculations in goals endpoint
        # otherwise, No valid instruments found

        TickerFactory.create(symbol='IAGG', asset_class=self.bonds_asset_class)
        TickerFactory.create(symbol='AGG', asset_class=self.bonds_asset_class)
        TickerFactory.create(symbol='ITOT', asset_class=self.stocks_asset_class)
        TickerFactory.create(symbol='GRFXX', asset_class=self.stocks_asset_class)
        TickerFactory.create(symbol='IPO')
        fund = TickerFactory.create(symbol='rest')

        self.portfolio_set.asset_classes.add(fund.asset_class)

         # Set the markowitz bounds for today
        self.m_scale = MarkowitzScaleFactory.create()

        # populate the data needed for the optimisation
        # We need at least 500 days as the cycles go up to 70 days and we need at least 7 cycles.
        populate_prices(500, asof=mocked_now.date())
        populate_cycle_obs(500, asof=mocked_now.date())
        populate_cycle_prediction(asof=mocked_now.date())

        account = ClientAccountFactory.create(primary_owner=Fixture1.client1())
        # setup some inclusive goal settings
        goal_settings = GoalSettingFactory.create()
        # Create a risk score metric for the settings
        GoalMetricFactory.create(group=goal_settings.metric_group, type=GoalMetric.METRIC_TYPE_RISK_SCORE)

        goal = GoalFactory.create(account=account,
                                  selected_settings=goal_settings,
                                  portfolio_set=self.portfolio_set,
                                  state=Goal.State.ACTIVE.value)
        serializer = GoalSettingSerializer(goal_settings)
        url = '/api/v1/goals/{}/calculate-portfolio?setting={}'.format(goal.id, json.dumps(serializer.data))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_calculate_portfolio_complete(self):
        # tickers for testing portfolio calculations in goals endpoint
        # otherwise, No valid instruments found
        TickerFactory.create(symbol='IAGG', asset_class=self.bonds_asset_class)
        TickerFactory.create(symbol='AGG', asset_class=self.bonds_asset_class)
        TickerFactory.create(symbol='ITOT', asset_class=self.stocks_asset_class)
        TickerFactory.create(symbol='GRFXX', asset_class=self.stocks_asset_class)
        TickerFactory.create(symbol='IPO')
        fund = TickerFactory.create(symbol='rest')

        self.portfolio_set.asset_classes.add(fund.asset_class)

        # Set the markowitz bounds for today
        self.m_scale = MarkowitzScaleFactory.create()

        # populate the data needed for the optimisation
        # We need at least 500 days as the cycles go up to 70 days and we need at least 7 cycles.
        populate_prices(500, asof=mocked_now.date())
        populate_cycle_obs(500, asof=mocked_now.date())
        populate_cycle_prediction(asof=mocked_now.date())

        account = ClientAccountFactory.create(primary_owner=Fixture1.client1())
        # setup some inclusive goal settings
        goal_settings = GoalSettingFactory.create()
        # Create a risk score metric for the settings
        GoalMetricFactory.create(group=goal_settings.metric_group, type=GoalMetric.METRIC_TYPE_RISK_SCORE)
        goal = GoalFactory.create(account=account, selected_settings=goal_settings, portfolio_set=self.portfolio_set,
                                  active_settings=goal_settings, state=Goal.State.ACTIVE.value)
        goal_settings.completion_date = timezone.now().date() - timedelta(days=365)
        serializer = GoalSettingSerializer(goal_settings)
        url = '/api/v1/goals/{}/calculate-all-portfolios?setting={}'.format(goal.id, json.dumps(serializer.data))
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_goal_metric(self):
        t1 = TickerFactory.create(symbol='SPY', unit_price=5)
        t2 = TickerFactory.create(symbol='QQQ', unit_price=5)

        equity = AssetFeatureValueFactory.create(name='equity', assets=[t1,t2])

        goal_settings = GoalSettingFactory.create()

        GoalMetricFactory.create(group=goal_settings.metric_group, feature=equity, type=GoalMetric.METRIC_TYPE_PORTFOLIO_MIX, rebalance_thr=0.05,
                                 configured_val=0.5, rebalance_type=GoalMetric.REBALANCE_TYPE_ABSOLUTE)

        goal = GoalFactory.create(active_settings=goal_settings)

        Fixture1.create_execution_details(goal, t1, 1, 2, date(2014, 6, 1))
        Fixture1.create_execution_details(goal, t2, 1, 2, date(2014, 6, 1))

        metric = GoalMetric.objects.get(group__settings__goal_active=goal)

        self.assertTrue(10.0 / goal.available_balance == metric.measured_val)

        self.assertTrue((metric.measured_val - metric.configured_val) / metric.rebalance_thr == metric.drift_score)

        metric.rebalance_type = GoalMetric.REBALANCE_TYPE_RELATIVE
        self.assertTrue(((metric.measured_val - metric.configured_val) / metric.configured_val) / metric.rebalance_thr \
                        == metric.drift_score)


    def test_sum_stocks_for_goal(self):
        self.content_type = ContentTypeFactory.create()

    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_add_goal_0_target(self):
        # tickers for testing portfolio calculations in goals endpoint
        # otherwise, No valid instruments found
        self.bonds_index = MarketIndexFactory.create()
        self.stocks_index = MarketIndexFactory.create()
        self.bonds_ticker = TickerFactory.create(asset_class=self.bonds_asset_class, benchmark=self.bonds_index)
        self.stocks_ticker = TickerFactory.create(asset_class=self.stocks_asset_class, benchmark=self.stocks_index)

        # Set the markowitz bounds for today
        self.m_scale = MarkowitzScaleFactory.create()

        # populate the data needed for the optimisation
        # We need at least 500 days as the cycles go up to 70 days and we need at least 7 cycles.
        populate_prices(500, asof=mocked_now.date())
        populate_cycle_obs(500, asof=mocked_now.date())
        populate_cycle_prediction(asof=mocked_now.date())

        url = '/api/v1/goals'
        self.client.force_authenticate(user=Fixture1.client1().user)
        account = ClientAccountFactory.create(primary_owner=Fixture1.client1())
        goal_settings = GoalSettingFactory.create()
        goal_metric = GoalMetricFactory.create(group=goal_settings.metric_group)
        ser = GoalCreateSerializer(data={
            'account': account.id,
            'name': 'Zero Goal Target',
            'type': GoalTypeFactory().id,
            'target': 0,
            'completion': timezone.now().date() + timedelta(days=7),
            'initial_deposit': 0,
            'ethical': True,
            'portfolio_set': self.portfolio_set.id
        })

        self.assertEqual(ser.is_valid(), True, msg="Serializer has errors %s"%ser.errors)
        response = self.client.post(url, ser.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['selected_settings']['target'], 0)
        self.assertEqual(response.data['on_track'], True)

    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_add_goal_complete(self):
        # tickers for testing portfolio calculations in goals endpoint
        # otherwise, No valid instruments found
        self.bonds_index = MarketIndexFactory.create()
        self.stocks_index = MarketIndexFactory.create()
        self.bonds_ticker = TickerFactory.create(asset_class=self.bonds_asset_class, benchmark=self.bonds_index)
        self.stocks_ticker = TickerFactory.create(asset_class=self.stocks_asset_class, benchmark=self.stocks_index)

        # Set the markowitz bounds for today
        self.m_scale = MarkowitzScaleFactory.create()

        # populate the data needed for the optimisation
        # We need at least 500 days as the cycles go up to 70 days and we need at least 7 cycles.
        populate_prices(500, asof=mocked_now.date())
        populate_cycle_obs(500, asof=mocked_now.date())
        populate_cycle_prediction(asof=mocked_now.date())

        url = '/api/v1/goals'
        self.client.force_authenticate(user=Fixture1.client1().user)
        account = ClientAccountFactory.create(primary_owner=Fixture1.client1())
        goal_settings = GoalSettingFactory.create()
        goal_metric = GoalMetricFactory.create(group=goal_settings.metric_group)
        ser = GoalCreateSerializer(data={
            'account': account.id,
            'name': 'Zero Goal Target',
            'type': GoalTypeFactory().id,
            'target': 500,
            'completion': timezone.now().date(),
            'initial_deposit': 0,
            'ethical': True,
            'portfolio_set': self.portfolio_set.id
        })

        self.assertEqual(ser.is_valid(), True, msg="Serializer has errors %s"%ser.errors)
        response = self.client.post(url, ser.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['selected_settings']['target'], 500)
        # "OnTrack" is false because the 500 deposit is still pending
        self.assertEqual(response.data['on_track'], False)

        goal = Goal.objects.get(pk=response.data['id'])
        goal.cash_balance += 500
        goal.save()

        response = self.client.get('%s/%s'%(url, goal.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['selected_settings']['target'], 500)
        self.assertEqual(response.data['on_track'], True)

    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_create_goal(self):
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
        account = ClientAccountFactory.create(primary_owner=Fixture1.client1())
        # setup some inclusive goal settings
        goal_settings = GoalSettingFactory.create()
        goal_type = GoalTypeFactory.create()
        url = '/api/v1/goals'
        data = {
            'account': account.id,
            'name': 'Fancy new goal',
            'type': goal_type.id,
            'target': 15000.0,
            'completion': "2016-01-01",
            'initial_deposit': 5000,
            'ethical': True,
            'portfolio_set': self.portfolio_set.id
        }

        # unauthenticated 403
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # authenticated 200
        self.client.force_authenticate(account.primary_owner.user)
        response = self.client.post(url, data)
        lookup_goal = Goal.objects.get(id=response.data['id'])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(response.data['portfolio_set'],
                             {'id': self.portfolio_set.id,
                              'name': self.portfolio_set.name,
                              'portfolio_provider': self.portfolio_set.portfolio_provider.id})
        self.assertEqual(response.data['has_deposit_transaction'], True)

    def test_get_goal_positions(self):
        goal = GoalFactory.create()

        url = '/api/v1/goals/{}/positions'.format(goal.pk)
        self.client.force_authenticate(goal.account.primary_owner.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Goal positions endpoint returns ok for Goal with no positions')

        # Create a 6 month old execution, transaction and a distribution that caused the transaction
        fund = TickerFactory.create(unit_price=2.1)
        fund2 = TickerFactory.create(unit_price=4)

        Fixture1.create_execution_details(goal, fund, 10, 2, date(2014, 6, 1))
        Fixture1.create_execution_details(goal, fund, 5, 2, date(2014, 6, 1))
        Fixture1.create_execution_details(goal, fund2, 1, 2, date(2014, 6, 1))

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Goal positions endpoint returns ok for Goal with positions')
        self.assertEqual(len(response.data), 2)
        self.assertDictEqual(response.data[0], {'ticker': fund.id, 'quantity': 15.0})  # Sum of the two fills
        self.assertDictEqual(response.data[1], {'ticker': fund2.id, 'quantity': 1.0})

    def test_archive_goal(self):
        client = Fixture1.client1()
        account = ClientAccountFactory.create(primary_owner=client)
        goal = GoalFactory.create(account=account)
        url = '/api/v1/goals/{}/archive'.format(goal.pk)

        # First login as client and flag the goal as archive-requested
        self.client.force_authenticate(client.user)
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Goal.objects.get(id=goal.id).state, Goal.State.ARCHIVE_REQUESTED.value)

        # Then login as Advisor and actually archive it
        self.client.force_authenticate(client.advisor.user)
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Goal.objects.get(id=goal.id).state, Goal.State.CLOSING.value)

    def test_get_goal_settings_by_id(self):
        goal = Fixture1.goal1()
        setting = goal.selected_settings
        url = '/api/v1/goals/{}/settings/{}'.format(goal.id, setting.id)

        # unauthenticated
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # authenticated
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data, [])
        self.assertEqual(response.data.get('id'), setting.id)

        # 404 check
        url = '/api/v1/goals/{}/settings/{}'.format(goal.id, 99999)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Unauthorized user check
        self.client.force_authenticate(user=Fixture1.client2().user)
        url = '/api/v1/goals/{}/settings/{}'.format(goal.id, setting.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_goal_deposit(self):
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
        account = ClientAccountFactory.create(primary_owner=Fixture1.client1())
        # setup some inclusive goal settings
        goal_settings = GoalSettingFactory.create()
        goal_type = GoalTypeFactory.create()
        url = '/api/v1/goals'
        data = {
            'account': account.id,
            'name': 'Fancy new goal',
            'type': goal_type.id,
            'target': 15000.0,
            'completion': "2016-01-01",
            'initial_deposit': 5000,
            'ethical': True,
            'portfolio_set': self.portfolio_set.id
        }

        # unauthenticated 403
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # authenticated 200
        self.client.force_authenticate(account.primary_owner.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(response.data['portfolio_set'],
                             {'id': self.portfolio_set.id,
                              'name': self.portfolio_set.name,
                              'portfolio_provider': self.portfolio_set.portfolio_provider.id})
        plaid_user = PlaidUserFactory.create(user=account.primary_owner.user)
        resp = create_public_token()
        plaid_user.access_token = resp['access_token']
        plaid_user.save()
        accounts = get_accounts(plaid_user.user)
        goal_id = response.data['id']
        url = '/api/v1/goals/{}/deposit'.format(goal_id)
        data = {
            'amount': 50.00,
            'account_id': accounts[0]['account_id'],
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        transaction_id = response.data['id']

        # Get goal and check if awaiting_deposit field is populated
        url = '/api/v1/goals/{}'.format(goal_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['awaiting_deposit']['id'], transaction_id)
        self.assertEqual(response.data['awaiting_deposit']['amount'], data['amount'])
        self.assertEqual(response.data['awaiting_deposit']['account_id'], data['account_id'])

    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_goal_withdraw(self):
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
        goal_type = GoalTypeFactory.create()
        url = '/api/v1/goals'
        data = {
            'account': account.id,
            'name': 'Fancy new goal',
            'type': goal_type.id,
            'target': 15000.0,
            'completion': "2016-01-01",
            'initial_deposit': 5000,
            'ethical': True,
            'portfolio_set': self.portfolio_set.id
        }

        # authenticated 200
        self.client.force_authenticate(account.primary_owner.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertDictEqual(response.data['portfolio_set'],
                             {'id': self.portfolio_set.id,
                              'name': self.portfolio_set.name,
                              'portfolio_provider': self.portfolio_set.portfolio_provider.id})

        # plaid user with access_token needed for deposits
        plaid_user = PlaidUserFactory.create(user=account.primary_owner.user)
        resp = create_public_token()
        plaid_user.access_token = resp['access_token']
        plaid_user.save()
        accounts = get_accounts(plaid_user.user)
        goal_create_response = response

        # execute the actual withdrawal now that the onboarding has been secured
        self.client.force_authenticate(user=account.primary_owner.user)
        url = '/api/v1/goals/{}/withdraw'.format(goal_create_response.data['id'])
        data = {
            'amount': 1.00,
            'account_id': accounts[2]['account_id'],
        }
        response = self.client.post(url, data)

        # goal needs to be approved before a withdraw attempt can be made
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        lookup_goal = Goal.objects.get(id=goal_create_response.data['id'])
        lookup_goal.approve_selected()

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_get_update_goal_awaiting_deposit(self):
        goal = GoalFactory.create()
        account = goal.account
        user = account.primary_owner.user
        # authenticated 200
        self.client.force_authenticate(user)
        plaid_user = PlaidUserFactory.create(user=user)
        resp = create_public_token()
        plaid_user.access_token = resp['access_token']
        plaid_user.save()
        accounts = get_accounts(plaid_user.user)
        url = '/api/v1/goals/{}/deposit'.format(goal.id)
        data = {
            'amount': 50.00,
            'account_id': accounts[0]['account_id'],
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        url = '/api/v1/goals/{}/awaiting-deposit/{}'.format(goal.id, response.data['id'])

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], data['amount'])
        self.assertEqual(response.data['account_id'], data['account_id'])

        data = {
            'amount': 55.00,
            'account_id': accounts[0]['account_id'],
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], data['amount'])

    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_inactive_goal_to_active_executes_transactions(self):
        goal = Fixture1.goal1()
        self.assertEqual(goal.state, Goal.State.INACTIVE.value)

        # plaid user with access_token needed for deposits
        plaid_user = PlaidUserFactory.create(user=goal.account.primary_owner.user)
        resp = create_public_token()
        plaid_user.access_token = resp['access_token']
        plaid_user.save()
        accounts = get_accounts(plaid_user.user)

        url = '/api/v1/goals/{}/deposit'.format(goal.id)
        data = {
            'amount': 1.00,
            'account_id': accounts[0]['account_id'],
        }
        self.client.force_authenticate(user=goal.account.primary_owner.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        lookup_trans = Transaction.objects.filter(to_goal=goal).first()
        self.assertEqual(lookup_trans.status, Transaction.STATUS_AWAITING_APPROVAL)

        goal.approve_selected()
        lookup_trans = Transaction.objects.get(pk=lookup_trans.id)
        self.assertEqual(lookup_trans.status, Transaction.STATUS_PENDING)

    def test_default_goal_has_deposit_transaction(self):
        goal = GoalFactory.create()
        self.assertEqual(goal.has_deposit_transaction, False)
        trans = TransactionFactory.create(to_goal=goal)
        lookup_goal = Goal.objects.get(id=goal.id)
        self.assertEqual(lookup_goal.has_deposit_transaction, True)
