from django.test import TestCase
from api.v1.tests.factories import TickerFactory
from execution.market_data.InteractiveBrokers.IBProvider import IBProvider
from unittest import skip, skipIf
from tests.test_settings import IB_TESTING


@skipIf(not IB_TESTING,"IB Testing is manually turned off.")
class BaseTest(TestCase):
    def setUp(self):
        self.con = IBProvider()
        self.con.connect()
        self.ticker = TickerFactory.create(symbol='GOOG')

    def test_IB_connect(self):
        self.assertTrue(self.con._connection.isConnected())

    def test_IB_disconnect(self):
        self.assertTrue(self.con._connection.isConnected())
        self.con.disconnect()
        self.assertFalse(self.con._connection.isConnected())

    def test_IB_get_best_bid_ask(self):
        result = self.con.get_market_depth_L1('SPY')
        self.assertTrue(result.ask >0)
        print(result)

    def tearDown(self):
        self.con.disconnect()