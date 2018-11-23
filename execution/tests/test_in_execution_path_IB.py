from django.db.models import Sum
from django.test import TestCase
import time
from api.v1.tests.factories import ExecutionRequestFactory, MarketOrderRequestFactory, \
    ClientAccountFactory, IBAccountFactory, GoalFactory, TickerFactory, FillFactory
from goal.models import Goal
from execution.broker.InteractiveBrokers.IBBroker import IBBroker
from execution.broker.InteractiveBrokers.IBOrder import IBOrder
from execution.models import Fill, Order, Execution
from datetime import datetime
from execution.end_of_day import broker_manager, create_orders, create_pre_trade_allocation, send_pre_trade, send_order,\
    process_fills, mark_order_as_complete, update_orders, process
from unittest import skipIf
from tests.test_settings import IB_TESTING, IB_ACC_1, IB_ACC_2, IB_ACC_SUM
from execution.account_groups.create_account_groups import FAAccountProfile
from main.management.commands.populate_test_data import populate_prices, populate_cycle_obs, populate_cycle_prediction

mocked_now = datetime(year=2016,month=6,day=1)

@skipIf(not IB_TESTING,"IB Testing is manually turned off.")
class BaseTest(TestCase):
    def setUp(self):
        self.account1 = ClientAccountFactory.create()
        self.broker_acc1 = IBAccountFactory.create(bs_account=self.account1, ib_account=IB_ACC_1)
        self.goal1 = GoalFactory.create(account=self.account1)

        self.account2 = ClientAccountFactory.create()
        self.goal2 = GoalFactory.create(account=self.account2)
        self.broker_acc2 = IBAccountFactory.create(bs_account=self.account2, ib_account=IB_ACC_2)

        self.ticker1 = TickerFactory.create(symbol='GOOG')
        self.ticker2 = TickerFactory.create(symbol='AAPL')


    def test_partial_in_and_out_path1(self):
        #1 market_order_request, 1 execution_request, 2 fills
        #out
        mor = MarketOrderRequestFactory.create(account=self.account1)
        mor2 = MarketOrderRequestFactory.create(account=self.account2)
        er = ExecutionRequestFactory.create(goal=self.goal1, asset=self.ticker1, volume=100, order=mor)
        er2 = ExecutionRequestFactory.create(goal=self.goal2, asset=self.ticker2, volume=10, order=mor2)
        er3 = ExecutionRequestFactory.create(goal=self.goal1, asset=self.ticker1, volume=50, order=mor)

        allocations = create_pre_trade_allocation()

        create_orders()

        account_profile = FAAccountProfile()
        account_profile.append_share_allocation(self.ticker1.symbol, allocations[self.ticker1.symbol])
        profile = account_profile.get_profile()
        send_pre_trade("IB",profile)
        order1_ib = Order.objects.get(ticker=self.ticker1)
        order1_ib.__class__ = IBOrder
        order1_ib.m_faProfile = self.ticker1.symbol
        send_order(order1_ib, True)

        account_profile = FAAccountProfile()
        account_profile.append_share_allocation(self.ticker2.symbol, allocations[self.ticker2.symbol])
        profile = account_profile.get_profile()
        send_pre_trade("IB", profile)
        order2_ib = Order.objects.get(ticker=self.ticker2)
        order2_ib.__class__ = IBOrder
        order2_ib.m_faProfile = self.ticker2.symbol

        send_order(order2_ib, True)
        orders = []
        orders.append(order1_ib)
        orders.append(order2_ib)
        time.sleep(1*60)
        distributions = update_orders(orders)
        mark_order_as_complete(order1_ib)
        mark_order_as_complete(order2_ib)


        process_fills(distributions)

        sum_volume = Execution.objects.filter(distributions__execution_request__goal=self.goal1)\
            .aggregate(sum=Sum('volume'))
        self.assertTrue(sum_volume['sum'] == 150)
        sum_volume = Execution.objects.filter(distributions__execution_request__goal=self.goal2) \
            .aggregate(sum=Sum('volume'))
        self.assertTrue(sum_volume['sum'] == 10)