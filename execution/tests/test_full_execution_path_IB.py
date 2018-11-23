from django.db.models import Sum
from django.test import TestCase
from datetime import datetime, date
import time
from api.v1.tests.factories import GoalFactory, PositionLotFactory, TickerFactory, \
    TransactionFactory, GoalSettingFactory, IBAccountFactory, GoalMetricFactory, AssetFeatureValueFactory, \
    PortfolioSetFactory, MarkowitzScaleFactory, PortfolioFactory
from goal.models import Goal, GoalMetric
from execution.models import Fill, Order, Execution
from execution.broker.InteractiveBrokers.IBBroker import IBBroker
from execution.broker.InteractiveBrokers.IBOrder import IBOrder
from execution.end_of_day import broker_manager, create_orders, create_pre_trade_allocation, send_pre_trade, send_order,\
    process_fills, mark_order_as_complete, update_orders, process
from unittest import skipIf
from tests.test_settings import IB_TESTING, IB_ACC_1, IB_ACC_2, IB_ACC_SUM
from execution.account_groups.create_account_groups import FAAccountProfile
from main.management.commands.populate_test_data import populate_prices, populate_cycle_obs, populate_cycle_prediction
from unittest.mock import patch
from django.utils import timezone
from portfolios.providers.execution.django import ExecutionProviderDjango
from portfolios.providers.data.django import DataProviderDjango
from main.management.commands.rebalance import get_held_weights
from portfolios.calculation import get_instruments
from main.tests.fixture import Fixture1
from unittest.mock import MagicMock
from unittest import mock

mocked_now = datetime.now()

@skipIf(not IB_TESTING,"IB Testing is manually turned off.")
class BaseTest(TestCase):
    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def setUp(self):
        self.t1 = TickerFactory.create(symbol='SPY', unit_price=5)
        self.t2 = TickerFactory.create(symbol='VEA', unit_price=5)
        self.t3 = TickerFactory.create(symbol='TIP', unit_price=100)
        self.t4 = TickerFactory.create(symbol='IEV', unit_price=100)
        #self.t5 = TickerFactory.create(symbol='IEV2', unit_price=100, asset_class=self.t4.asset_class)


        self.equity = AssetFeatureValueFactory.create(name='equity', assets=[self.t1, self.t2])
        self.bond = AssetFeatureValueFactory.create(name='bond', assets=[self.t3, self.t4])

        self.goal_settings = GoalSettingFactory.create()
        asset_classes = [self.t1.asset_class, self.t2.asset_class, self.t3.asset_class, self.t4.asset_class]
        portfolio_set = PortfolioSetFactory.create(name='set', risk_free_rate=0.01, asset_classes=asset_classes)
        self.goal = GoalFactory.create(approved_settings=self.goal_settings, active_settings=self.goal_settings,
                                       cash_balance=100, portfolio_set=portfolio_set)
        self.broker_acc = IBAccountFactory.create(bs_account=self.goal.account, ib_account=IB_ACC_1)
        self.tickers = [self.t1, self.t2, self.t3, self.t4, self.t4]
        self.prices = [4, 4, 90, 90, 95]
        self.quantities = [5, 5, 5, 5, 5]
        self.executed = [date(2015, 1, 1), date(2016, 1, 1), date(2015, 1, 1), date(2016, 1, 1), date(2016, 1, 1)]

        self.execution_details = []
        for i in range(5):
            execution = Fixture1.create_execution_details(self.goal,
                                                          self.tickers[i],
                                                          self.quantities[i],
                                                          self.prices[i],
                                                          self.executed[i])
            self.execution_details.append(execution)

        self.data_provider = DataProviderDjango(mocked_now.date())
        self.execution_provider = ExecutionProviderDjango()
        MarkowitzScaleFactory.create()
        self.setup_performance_history()
        self.idata = get_instruments(self.data_provider)

        self.portfolio = PortfolioFactory.create(setting=self.goal_settings)
        self.current_weights = get_held_weights(self.goal)


    def setup_performance_history(self):
        populate_prices(400, asof=mocked_now)
        populate_cycle_obs(400, asof=mocked_now)
        populate_cycle_prediction(asof=mocked_now)

    def test_full_in_execution_path_IB(self):
        GoalMetricFactory.create(group=self.goal_settings.metric_group, feature=self.equity,
                                 type=GoalMetric.METRIC_TYPE_PORTFOLIO_MIX,
                                 rebalance_type=GoalMetric.REBALANCE_TYPE_ABSOLUTE,
                                 rebalance_thr=0.05, configured_val=0.3,
                                 comparison=GoalMetric.METRIC_COMPARISON_MINIMUM)
        GoalMetricFactory.create(group=self.goal_settings.metric_group, feature=self.bond,
                                 type=GoalMetric.METRIC_TYPE_PORTFOLIO_MIX,
                                 rebalance_type=GoalMetric.REBALANCE_TYPE_ABSOLUTE,
                                 rebalance_thr=0.05, configured_val=0.7,
                                 comparison=GoalMetric.METRIC_COMPARISON_MAXIMUM)

        GoalMetricFactory.create(group=self.goal_settings.metric_group, feature=self.equity,
                                 type=GoalMetric.METRIC_TYPE_RISK_SCORE,
                                 rebalance_type=GoalMetric.REBALANCE_TYPE_ABSOLUTE,
                                 rebalance_thr=0.5, configured_val=0.5)

        goals = Goal.objects.all()

        process(self.data_provider, self.execution_provider, 5)
        for goal in goals:
            sum_volume = Execution.objects.filter(distributions__execution_request__goal=goal) \
                .aggregate(sum=Sum('volume'))
            sum_amount = Execution.objects.filter(distributions__execution_request__goal=goal) \
                .aggregate(sum=Sum('volume'))
            self.assertTrue(sum_volume['sum'] == sum_amount['sum'])