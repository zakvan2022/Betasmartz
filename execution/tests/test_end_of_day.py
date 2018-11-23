from datetime import datetime
from unittest.mock import Mock
from tests.test_settings import IB_TESTING, IB_ACC_1, IB_ACC_2, IB_ACC_SUM
from django.test import TestCase
from execution.Obsolete.interactive_brokers.end_of_day.end_of_day import create_django_executions
from execution.account_groups.account_allocations import AccountAllocations
from execution.account_groups.account_allocations import Execution as ExecutionClass
from execution.data_structures.market_depth import MarketDepth, SingleLevelMarketDepth
from execution.end_of_day import *
from execution.end_of_day import get_execution_requests, transform_execution_requests
from portfolios.models import ExternalInstrument, InvestmentType
from main.tests.fixture import Fixture1
from main.management.commands.rebalance import reduce_cash
from api.v1.tests.factories import TickerFactory
from execution.broker.BaseBroker import BaseBroker
from unittest import skipIf,skip




class BaseTest(TestCase):

    def setUp(self):
        self.bonds_type = InvestmentType.Standard.BONDS.get()
        self.stocks_type = InvestmentType.Standard.STOCKS.get()
        self.con = Mock(BaseBroker)
        self.con.connect.return_value = True

        #self.con.requesting_market_depth.return_value = False

        self.market_data = dict()
        self.market_data['GOOG'] = MarketDepth()

        single_level = SingleLevelMarketDepth()
        single_level.bid = 1
        single_level.ask = 2
        single_level.bid_volume = 50
        single_level.ask_volume = 100
        self.market_data['GOOG'].add_level(0, single_level)

        Fixture1.personal_account1()
        Fixture1.personal_account2()

        request1 = MarketOrderRequest.objects.create(state=MarketOrderRequest.State.APPROVED.value,
                                                     account=Fixture1.personal_account1())

        request2 = MarketOrderRequest.objects.create(state=MarketOrderRequest.State.APPROVED.value,
                                                     account=Fixture1.personal_account2())
        Fixture1.ib_account1()
        Fixture1.ib_account2()

        params = {
            'reason': ExecutionRequest.Reason.DRIFT.value,
            'goal': Fixture1.goal1(),
            'asset': Fixture1.fund3(),
            'volume': 5,
            'order': request1
        }
        ExecutionRequest.objects.get_or_create(id=1, defaults=params)
        params = {
            'reason': ExecutionRequest.Reason.DRIFT.value,
            'goal': Fixture1.goal1(),
            'asset': Fixture1.fund4(),
            'volume': 5,
            'order': request1
        }
        ExecutionRequest.objects.get_or_create(id=2, defaults=params)

        #Client2
        params = {
            'reason': ExecutionRequest.Reason.DRIFT.value,
            'goal': Fixture1.goal2(),
            'asset': Fixture1.fund3(),
            'volume': 10,
            'order': request2
        }
        ExecutionRequest.objects.get_or_create(id=3, defaults=params)
        params = {
            'reason': ExecutionRequest.Reason.DRIFT.value,
            'goal': Fixture1.goal2(),
            'asset': Fixture1.fund4(),
            'volume': 10,
            'order': request2
        }
        ExecutionRequest.objects.get_or_create(id=4, defaults=params)

    @skip("Turtned off due to consecutive IB message limits.")
    @skipIf(not IB_TESTING, "IB Testing is manually turned off.")
    def test_change_account_cash(self):
        goal1 = Fixture1.goal1()

        account = Fixture1.personal_account1()
        account.all_goals.return_value = [goal1]

        #no difference
        account.cash_balance = 0
        ib_account = account.ib_account

        ib_account_cash[ib_account.ib_account] = 0
        difference = reconcile_cash_client_account(account)
        self.assertNotAlmostEqual(0, difference)

        self.assertEqual(ib_account.ib_account, IB_ACC_1)

        #deposit - transferred to account.cash_balance
        ib_account_cash[ib_account.ib_account] = 1100
        reconcile_cash_client_account(account)
        self.assertNotAlmostEqual(0, account.cash_balance)

        #withdrawal - from account.cash_balance
        ib_account_cash[ib_account.ib_account] = 900
        reconcile_cash_client_account(account)
        self.assertAlmostEqual(900, account.cash_balance)

        #exception - sum of goal cash balances > ib_account_cash
        goal1.cash_balance = 1000
        goal1.save()
        account.cash_balance = 100
        ib_account_cash[ib_account.ib_account] = 900

        with self.assertRaises(Exception) as cm:
            reconcile_cash_client_account(account)
        self.assertTrue(ib_account.ib_account in cm.exception.args[0])

    def test_market_depth(self):
        self.assertAlmostEquals(self.market_data['GOOG'].levels[0].get_mid(), 1.5)
        self.assertEqual(self.market_data['GOOG'].depth, 10)
        self.assertAlmostEquals(self.market_data['GOOG'].levels[0].bid_volume, 50)
        self.assertAlmostEquals(self.market_data['GOOG'].levels[0].ask_volume, 100)

    def test_get_execution_requests(self):
        execution_requests = get_execution_requests()
        self.assertTrue(len(execution_requests) == 4)

    def test_transform_execution_requests(self):
        execution_requests = get_execution_requests()
        allocations = transform_execution_requests(execution_requests)
        self.assertTrue(allocations['SPY'][IB_ACC_1] == 5)
        self.assertTrue(allocations['SPY'][IB_ACC_2] == 10)
        self.assertTrue(allocations['TLT'][IB_ACC_1] == 5)
        self.assertTrue(allocations['TLT'][IB_ACC_2] == 10)

    def test_allocations(self):
        execution = ExecutionClass(10, IB_ACC_1, 5, timezone.now(), 1, "IB")

        allocation = AccountAllocations()

        allocation.add_execution_allocation(execution)

        self.assertTrue(allocation.allocations[1][IB_ACC_1].price == 10)
        self.assertTrue(allocation.allocations[1][IB_ACC_1].shares == 5)

        execution = ExecutionClass(20, IB_ACC_1, 5, timezone.now(), 1, "IB")
        allocation.add_execution_allocation(execution)

        self.assertTrue(allocation.allocations[1][IB_ACC_1].price == 15)
        self.assertTrue(allocation.allocations[1][IB_ACC_1].shares == 10)

    def test_create_account_groups(self):
        account_profile = FAAccountProfile()

        account_dict = {
            IB_ACC_1: 5,
            IB_ACC_2: 10,
        }
        account_profile.append_share_allocation('MSFT', account_dict)
        profile = account_profile.get_profile()

        profile_should_be1 = r'<?xml version="1.0" encoding="UTF-8"?><ListOfAllocationProfiles><AllocationProfile><name>MSFT</name><type>3</type><ListOfAllocations varName="listOfAllocations"><Allocation><acct>'+IB_ACC_2+'</acct><amount>10.0</amount></Allocation><Allocation><acct>'+IB_ACC_1+'</acct><amount>5.0</amount></Allocation></ListOfAllocations></AllocationProfile></ListOfAllocationProfiles>'
        profile_should_be2 = r'<?xml version="1.0" encoding="UTF-8"?><ListOfAllocationProfiles><AllocationProfile><name>MSFT</name><type>3</type><ListOfAllocations varName="listOfAllocations"><Allocation><acct>'+IB_ACC_1+'</acct><amount>5.0</amount></Allocation><Allocation><acct>'+IB_ACC_2+'</acct><amount>10.0</amount></Allocation></ListOfAllocations></AllocationProfile></ListOfAllocationProfiles>'
        self.assertTrue(profile == profile_should_be1 or profile == profile_should_be2)

    '''  Obsolete
    def test_order(self):
        ib_contract = types.SimpleNamespace()
        ib_contract.m_symbol = 'SPY'

        ib_order = types.SimpleNamespace()
        ib_order.m_totalQuantity = 1

        order = Order(contract=ib_contract,
                      order=ib_order,
                      symbol=ib_contract.m_symbol,
                      remaining=ib_order.m_totalQuantity)
        self.assertTrue(order.symbol == 'SPY')
        self.assertTrue(order.status == Order.OrderStatus.New)
        self.assertTrue(order.remaining == 1)
        self.assertTrue(order.fill_price is None)
        self.assertTrue(order.filled == 0)
    '''

    def test_create_django_executions(self):
        fills = dict()
        order = Order()
        order.Symbol = "SPY"
        order.filled = 5
        order.status = Order.StatusChoice.Filled
        fills[1] = order

        execution = ExecutionClass(10, IB_ACC_1, 5, timezone.now(), 1, "IB")
        allocation = AccountAllocations()
        allocation.add_execution_allocation(execution)

        create_django_executions(fills, allocation.allocations)

        executionDjango = Execution.objects.get(asset=Ticker.objects.get(symbol='SPY'), volume=5)

        self.assertTrue(executionDjango.price == 10)
        self.assertTrue(executionDjango.volume == 5)
        self.assertTrue(executionDjango.amount == 50)
        self.assertTrue(executionDjango.executed == execution.time[-1])

    def test_external_instrument(self):
        Fixture1.external_instrument1()
        Fixture1.external_instrument2()
        instrument1 = ExternalInstrument.objects.get(institution=ExternalInstrument.Institution.APEX.value,
                                                     ticker__symbol='SPY')
        instrument2 = ExternalInstrument.objects.get(institution=ExternalInstrument.Institution.INTERACTIVE_BROKERS.value,
                                                     ticker__symbol='SPY')
        self.assertTrue(instrument1.instrument_id == 'SPY_APEX')
        self.assertTrue(instrument2.instrument_id == 'SPY_IB')

    def test_reduce_cash(self):
        goal1 = Fixture1.goal1()
        goal1.cash_balance = 1000
        cash_available = goal1.cash_balance
        ticker = TickerFactory.create()
        ticker.latest_tick = 2
        volume = 2000
        cash_available, volume = reduce_cash(volume, ticker, cash_available)
        self.assertAlmostEqual(cash_available, 1.03)
        self.assertTrue(volume == 497)
