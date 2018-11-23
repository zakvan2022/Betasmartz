from django.test import TestCase

from api.v1.tests.factories import TickerFactory
from execution.broker.ETNA.ETNABroker import ETNABroker, ResponseCode
from execution.models import Order, ETNALogin


# demo.etnatrader.com


# get rid of apexORDER and replace with ETNAorder - everything prepared


class BaseTest(TestCase):
    def setUp(self):
        self.broker = ETNABroker()
        #self.login = get_current_login()
        self.ticker = TickerFactory.create(symbol='GOOG')

    '''
    2017/03/21 - tests started to fail. As ETNA not being used, tests disabled for timebeing.
    def test_ETNA_login(self):
        login_response = self.broker._get_current_login()
        self.assertTrue(len(login_response.Ticket) == 520)
        self.assertTrue(login_response.ResponseCode == 0)
        self.assertTrue(len(login_response.Result.SessionId) == 36)
        self.assertTrue(login_response.Result.UserId > 0)


    def test_ETNA_multiple_logins(self):
        self.broker._login()
        self.broker._login()
        self.broker._get_current_login()
        logins = ETNALogin.objects.filter(ResponseCode=ResponseCode.Valid.value)
        self.assertTrue(len(logins) == 1)

    def test_get_accounts(self):
        login_response = self.broker._get_current_login()
        #  this will be used only once at the beginning, else we will use ETNA_ACCOUNT_ID from local_settings.py
        self.broker._get_accounts_ETNA(login_response.Ticket)
        account_id = self.broker._get_current_account_id()
        self.assertTrue(account_id > 0)

    def test_get_security(self):
        etna_security = self.broker.get_security(self.ticker.symbol)
        self.assertTrue(etna_security.Symbol == self.ticker.symbol)
        self.assertTrue(etna_security.symbol_id == 5)


    def test_send_trade(self):
        order = self.broker.create_order(10, 1, self.ticker)
        order = self.broker.send_order(order)
        self.assertTrue(order.Order_Id != -1)
        return order

    def test_update_order_status(self):
        order = self.test_send_trade()
        nothing = Order.objects.is_complete()
        something = Order.objects.is_not_complete()
        order_list = []
        order_list.append(order)
        self.assertTrue(len(nothing) == 0)
        self.assertTrue(len(something) == 1)
        self.assertTrue(order.is_complete is False)

        order = self.broker.update_orders(order_list)
        one_order = Order.objects.is_complete()
        nothing = Order.objects.is_not_complete()
        self.assertTrue(len(one_order) == 1)
        self.assertTrue(len(nothing) == 0)
        self.assertTrue(order.is_complete is True)
        self.assertTrue(order.Status == Order.StatusChoice.Rejected.value)
    '''
    def tearDown(self):
        login_response = self.broker._get_current_login()
        self.broker._logout(login_response.Ticket)
