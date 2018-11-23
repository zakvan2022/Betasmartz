from django.test import TestCase

from api.v1.tests.factories import ExecutionRequestFactory, APEXAccountFactory, MarketOrderRequestFactory, ClientAccountFactory, GoalFactory, TickerFactory
from execution.end_of_day import *
from execution.models import Order
from unittest import skipIf
from tests.test_settings import IB_TESTING, ETNA_TESTING

ib_testing = False
@skipIf(not ETNA_TESTING,"ETNA Testing is manually turned off.")
@skipIf(not IB_TESTING,"IB Testing is manually turned off.")
class BaseTest(TestCase):
    def setUp(self):
        self.account = ClientAccountFactory.create()
        self.goal = GoalFactory.create(account=self.account)
        self.mor = MarketOrderRequestFactory.create(account=self.account)
        self.broker_acc1 = APEXAccountFactory.create(bs_account=self.account)

        self.asset = TickerFactory.create(symbol='GOOG')
        self.asset2 = TickerFactory.create(symbol='AAPL')
        er1 = ExecutionRequestFactory.create(goal=self.goal, asset=self.asset, volume=5, order=self.mor)
        er2 = ExecutionRequestFactory.create(goal=self.goal, asset=self.asset, volume=10, order=self.mor)
        er3 = ExecutionRequestFactory.create(goal=self.goal, asset=self.asset2, volume=10, order=self.mor)

    def test_execution_requests_with_market_order_request(self):
        requests = ExecutionRequest.objects.all().filter(order=self.mor)
        self.assertTrue(requests[0].volume == 5)
        self.assertTrue(requests[1].volume == 10)

    def test_apex_order1(self):
        create_orders()
        orders = Order.objects.all()

        self.assertTrue(orders[0].ticker.id == self.asset.id)
        self.assertTrue(orders[0].Quantity == 15)
        self.assertTrue(orders[1].ticker.id == self.asset2.id)
        self.assertTrue(orders[1].Quantity == 10)

    def test_apex_order2(self):
        self.account2 = ClientAccountFactory.create()
        self.broker_acc2 = APEXAccountFactory.create(bs_account=self.account2)
        self.goal2 = GoalFactory.create(account=self.account2)
        self.mor2 = MarketOrderRequestFactory.create(account=self.account2)
        self.asset3 = TickerFactory.create(symbol='MSFT')
        er4 = ExecutionRequestFactory.create(goal=self.goal2, asset=self.asset3, volume=20, order=self.mor2)
        create_orders()
        order = Order.objects.all()
        self.assertTrue(len(order) == 3)
        self.assertTrue(order[2].Quantity == 20)

    def test_apex_order3(self):
        self.account3 = ClientAccountFactory.create()
        self.broker_acc3 = APEXAccountFactory.create(bs_account=self.account3)
        self.goal3 = GoalFactory.create(account=self.account3)
        self.mor3 = MarketOrderRequestFactory.create(account=self.account3)
        er5 = ExecutionRequestFactory.create(goal=self.goal3, asset=self.asset, volume=20, order=self.mor3)
        create_orders()
        orders = Order.objects.all()
        self.assertTrue(len(orders) == 2)
        self.assertTrue(orders[0].Quantity == 35)
