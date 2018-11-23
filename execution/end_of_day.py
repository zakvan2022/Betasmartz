
import logging
import types
from collections import defaultdict
from datetime import timedelta
from functools import partial
from execution.broker.InteractiveBrokers.IBOrder import IBOrder
from logging import DEBUG, INFO, WARN, ERROR
from time import sleep
import time
import numpy as np
from django.db import transaction
from django.db.models import Sum, F, Case, When, Value, FloatField
from django.utils import timezone
from portfolios.providers.execution.django import ExecutionProviderDjango
from portfolios.models import Ticker
from portfolios.calculation import build_instruments, calculate_portfolio, \
    calculate_portfolios, get_instruments
from portfolios.providers.data.django import DataProviderDjango
from client.models import ClientAccount
from goal.models import Goal, Transaction
from execution.market_data.InteractiveBrokers.IBProvider import IBProvider
from execution.broker.ETNA.ETNABroker import ETNABroker
from execution.broker.InteractiveBrokers.IBBroker import IBBroker
from execution.account_groups.create_account_groups import FAAccountProfile
from main.management.commands.rebalance import TAX_BRACKET_LESS1Y, TAX_BRACKET_MORE1Y, rebalance, create_request, build_positions, get_position_lots_by_tax_lot
from execution.models import MarketOrderRequest, ExecutionRequest, Execution, MarketOrderRequestAPEX, \
    Fill, ExecutionFill, ExecutionDistribution, PositionLot, Sale, Order
from main import settings
# TODO remove obsolete functionality
from api.v1.tests.factories import MarkowitzScaleFactory

short_sleep = partial(sleep, 1)
long_sleep = partial(sleep, 10)

tax_bracket_egt1Y = 0.2
tax_bracket_lt1Y = 0.3

verbose_levels = {
    3 : DEBUG,
    2 : INFO,
    1 : WARN,
    0 : ERROR,
    }

ib_account_list = list()
ib_account_cash = dict()

logger = logging.getLogger('betasmartz.daily_process')
logger.setLevel(logging.INFO)


class BrokerManager(object):
    _brokers = dict()
    def get(self, broker_name):
        if broker_name not in self._brokers:
            if broker_name == "IB":
                broker = IBBroker()
            elif broker_name == "ETNA":
                broker = ETNABroker()
            broker.connect()
            self._brokers[broker_name] = broker
        return self._brokers[broker_name]


broker_manager =  BrokerManager()

class ProviderManager(object):
    _providers = dict()
    def get(self, provider_name):
        if provider_name not in self._providers:
            if provider_name == "IB":
                provider = IBProvider()
                provider.connect()
            self._providers[provider_name] = provider
        return self._providers[provider_name]


provider_manager =  ProviderManager()

def get_options():
    opts = types.SimpleNamespace()
    opts.verbose = 0
    return opts


@transaction.atomic()
def reconcile_cash_client_account(account):
    account_cash = account.cash_balance
    goals = account.goals.all()

    goals_cash = 0
    for goal in goals:
        goals_cash += goal.cash_balance

    # obtaining account_info object. This represents info as of with real brokers account
    account_info = broker_manager.get(account.broker).get_account_info(account.broker_account)


    difference = account_info.cash - (account_cash + goals_cash)
    if difference > 0:
        #there was deposit
        account_cash += difference
    elif difference < 0:
        #withdrawals
        if abs(difference) < account_cash:
            account_cash -= abs(difference)
        else:
            logger.exception("cash < sum of goals cashes for " + str(account.broker_account))
            raise Exception("cash < sum of goals cashes for " + str(account.broker_account))
            # we have a problem - we should not be able to withdraw more than account_cash
    account.cash_balance = account_cash
    account.save()
    return difference


def reconcile_cash_client_accounts():
    client_accounts = ClientAccount.objects.all()
    with transaction.atomic():
        for account in client_accounts:
            try:
                reconcile_cash_client_account(account)
            except:
                print("exception")


def get_execution_requests():
    ers = ExecutionRequest.objects.all().filter(order__state=MarketOrderRequest.State.APPROVED.value)
    return ers


def transform_execution_requests(execution_requests):
    '''
    transform django ExecutionRequests into allocation object, which we will use to keep track of allocation fills
    :param execution_requests: list of ExecutionRequest
    :return:
    '''
    allocations = defaultdict(lambda: defaultdict(float))
    for e in execution_requests.select_related('order__account__ib_account__ib_account', 'asset__symbol'):
        allocations[e.asset.symbol][e.order.account.ib_account.ib_account] += e.volume
    return allocations


def approve_mor(mor):
    mor.state = MarketOrderRequest.State.APPROVED.value
    mor.save()

def create_orders():
    '''
    from outstanding MOR and ER create MorApex and ApexOrder
    '''
    x=1
    ers_temp = ExecutionRequest.objects.all().filter(order__state=MarketOrderRequest.State.APPROVED.value)\
        .annotate(ticker_id=F('asset__id'))\
        .values('ticker_id', 'order__account')\
        .annotate(volume=Sum('volume'))
    ers = list()

    class ERSkey:
        def __init__(self):
            self.broker = ""
            self.broker_acc_id = ""
            self.ticker_id = ""
            self.volume = 0

        def __eq__(self, other):
            if self.broker == other.broker and self.ticker_id == other.ticker_id and self.broker_acc_id == other.broker_acc_id:
                return True
            return False
        def increment_volume(self, vol):
            self.volume += vol


    for er in ers_temp:
        er_obj = ERSkey()
        acc = ClientAccount.objects.get(pk=er['order__account'])
        er_obj.broker = acc.broker
        er_obj.broker_acc_id = acc.broker_acc_id
        er_obj.ticker_id = er['ticker_id']
        er_obj.volume = er['volume']

        if er_obj in ers:
            ers[ers.index(er_obj)].increment_volume(er['volume'])
        else:
            ers.append(er_obj)
    for grouped_volume_per_share in ers:
        if not grouped_volume_per_share.volume == 0:
            ticker = Ticker.objects.get(id=grouped_volume_per_share.ticker_id)

            provider = provider_manager.get("IB")
            md = provider.get_market_depth_L1(ticker.symbol)
            order = broker_manager.get(grouped_volume_per_share.broker).create_order(price=round(md.get_mid()*1.005 if grouped_volume_per_share.volume > 0 else md.get_mid()*0.995,2), quantity=grouped_volume_per_share.volume, ticker=ticker)
            order.save()
            mor_ids = MarketOrderRequest.objects.all().filter(state=MarketOrderRequest.State.APPROVED.value,
                                                              execution_requests__asset_id=ticker.id).\
                values_list('id', flat=True).distinct()

            for id in mor_ids:
                mor = MarketOrderRequest.objects.get(id=id)
                MarketOrderRequestAPEX.objects.create(market_order_request=mor, ticker=ticker, order=order)

# should not get mix of two brokers
def update_orders(orders):
    distributions = {}
    orders_by_broker = {}
    for order in orders:
        if order.Broker not in orders_by_broker:
            orders_by_broker[order.Broker] = []
        orders_by_broker[order.Broker].append(order)
    for broker in orders_by_broker:
        if broker not in distributions:
            distributions[broker] = broker_manager.get(broker).update_orders(orders_by_broker[broker])
    return distributions

def send_pre_trade(broker,profile):
    broker_manager.get(broker).send_pre_trade(profile)

def send_order(order, execute = False):
    order.Status = Order.StatusChoice.Sent.value
    order.save()
    distributions = None
    if execute:
        broker_manager.get(order.Broker).send_order(order)
    mors = MarketOrderRequest.objects.filter(morsAPEX__order=order).distinct()
    for m in mors:
        m.state = MarketOrderRequest.State.SENT.value
        m.save()
    return distributions


def mark_order_as_complete(order):
    order.Status = Order.StatusChoice.Filled.value
    order.save()


@transaction.atomic
def create_pre_trade_allocation():
    allocation = {}
    ers = ExecutionRequest.objects.all().filter(order__state=MarketOrderRequest.State.APPROVED.value)
    for er in ers:
        if er.asset.symbol not in allocation:
            allocation[er.asset.symbol] = {}
        mor = MarketOrderRequest.objects.get(execution_requests__id=er.id)
        if mor.account.broker_acc_id not in allocation[er.asset.symbol]:
            allocation[er.asset.symbol][mor.account.broker_acc_id] = 0
        allocation[er.asset.symbol][mor.account.broker_acc_id] += abs(er.volume)
    return allocation

@transaction.atomic
def process_fills(volume_distribution=None):
    '''
    from existing apex fills create executions, execution distributions, transactions and positionLots - pro rata all fills
    :return:
    '''
    fills = Fill.objects\
        .filter(order__Status__in=Order.StatusChoice.complete_statuses())\
        .annotate(ticker_id=F('order__ticker__id'))\
        .values('id', 'ticker_id', 'price', 'volume','executed')

    complete_mor_ids = set()
    complete_order_ids = set()
    for fill in fills:
        ers = ExecutionRequest.objects\
            .filter(asset_id=fill['ticker_id'], order__morsAPEX__order__Status__in=Order.StatusChoice.complete_statuses())
        sum_ers = np.sum([er.volume for er in ers])

        for er in ers:
            apex_fill = Fill.objects.get(id=fill['id'])
            ticker = Ticker.objects.get(id=fill['ticker_id'])
            mor = MarketOrderRequest.objects.get(execution_requests__id=er.id)
            if mor.id not in complete_mor_ids:
                complete_mor_ids.add(mor.id)
            # now volume is directly obtained, if it's provided under volume distribution
            pro_rata = er.volume / float(sum_ers)
            if volume_distribution is None:
                volume = fill['volume'] * pro_rata
            else:
                volume = 0
                for broker in volume_distribution:
                    if broker in volume_distribution and er.asset.symbol in volume_distribution[broker] and mor.account.broker_acc_id in volume_distribution[broker][er.asset.symbol]:
                        volume += volume_distribution[broker][er.asset.symbol][mor.account.broker_acc_id] * pro_rata

            orders = list(Order.objects.filter(morsAPEX__market_order_request__execution_requests__id=er.id))
            for order in orders:
                if order.id not in complete_order_ids:
                    complete_order_ids.add(order.id)

            execution = Execution.objects.create(asset=ticker, volume=volume, price=fill['price'],
                                                 amount=volume*fill['price'], order=mor, executed=fill['executed'])
            ExecutionFill.objects.create(fill=apex_fill, execution=execution)
            trans = Transaction.objects.create(reason=Transaction.REASON_ORDER,
                                               amount=volume*fill['price'],
                                               to_goal=er.goal, executed=fill['executed'])
            ed = ExecutionDistribution.objects.create(execution=execution, transaction=trans, volume=volume,
                                                      execution_request=er)

            if volume > 0:
                PositionLot.objects.create(quantity=volume, execution_distribution=ed)
            else:
                create_sale(ticker.id, volume, fill['price'], ed)

    for mor_id in complete_mor_ids:
        mor = MarketOrderRequest.objects.get(id=mor_id)
        mor.state = MarketOrderRequest.State.COMPLETE.value
        mor.save()

    for order_id in complete_order_ids:
        order = Order.objects.get(id=order_id)
        order.Status = Order.StatusChoice.Archived.value

        sum_fills = Fill.objects.filter(order_id=order_id).aggregate(sum=Sum('volume'))
        if sum_fills['sum'] == order.Quantity:
            order.fill_info = Order.FillInfo.FILLED.value
        elif sum_fills['sum'] == 0:
            order.fill_info = Order.FillInfo.UNFILLED.value
        else:
            order.fill_info = Order.FillInfo.PARTIALY_FILLED.value
        order.save()

def create_sale(ticker_id, volume, current_price, execution_distribution):
    # start selling PositionLots from 1st until quantity sold == volume
    position_lots = get_position_lots_by_tax_lot(ticker_id,
                                                 current_price,
                                                 execution_distribution.execution_request.goal_id)

    left_to_sell = abs(volume)
    for lot in position_lots:
        if left_to_sell == 0:
            break

        new_quantity = max(lot.quantity - left_to_sell, 0)
        left_to_sell -= lot.quantity - new_quantity
        lot.quantity = new_quantity
        lot.save()
        if new_quantity == 0:
            lot.delete()

        Sale.objects.create(quantity=- (lot.quantity - new_quantity),
                            sell_execution_distribution=execution_distribution,
                            buy_execution_distribution=lot.execution_distribution)

def execute(delay):
    # 1 market_order_request, 1 execution_request, 2 fills
    # out
    create_orders()
    allocations = create_pre_trade_allocation()
    orders = []
    for order in Order.objects.all().filter(Status=Order.StatusChoice.New.value):
        account_profile = FAAccountProfile()
        account_profile.append_share_allocation(order.Symbol, allocations[order.Symbol])
        profile = account_profile.get_profile()
        send_pre_trade(order.Broker, profile)
        if order.Broker == "IB":
            order.__class__ = IBOrder
            order.m_faProfile = order.Symbol
        send_order(order, True)


        orders.append(order)
    time.sleep(delay)
    distributions = update_orders(orders)
    for order in orders:
        mark_order_as_complete(order)

    process_fills(distributions)


def process(data_provider, execution_provider, delay, goals=None):
    # actually tickers are created here - we need to set proper asset class for each ticker
    if goals is None:
        goals = Goal.objects.filter(state=Goal.State.ACTIVE.value)

    #get_markowitz_scale(self)
    #MarkowitzScaleFactory.create()
    data_provider.get_goals()

    build_instruments(data_provider)

    # optimization fails due to
    #portfolios_stats = calculate_portfolios(setting=goal.selected_settings,
    #                                       data_provider=data_provider,
    #                                       execution_provider=execution_provider)
    #portfolio_stats = calculate_portfolio(settings=goal.selected_settings,
    #                                      data_provider=data_provider,
    #                                      execution_provider=execution_provider)
    goals_list = []
    for goal in goals:
        weights, instruments, reason = rebalance(idata=get_instruments(data_provider),
                                                goal=goal,
                                                data_provider=data_provider,
                                                execution_provider=execution_provider)

        new_positions = build_positions(goal, weights, instruments)

        goals_list.append({
            'goal': goal,
            'new_positions': new_positions
        })

        if settings.DEBUG:
            print('---------------------------------------------------')
            print('weights:', weights)
            print('instruments:', instruments)

    for item in goals_list:
        goal = item['goal']
        new_positions = item['new_positions']

        mor, requests = create_request(goal, new_positions, reason,
                                        execution_provider=execution_provider,
                                        data_provider=data_provider,
                                        allowed_side=-1)
        if settings.DEBUG:
            print('---------------------------------------------------')
            print(requests)
            print('>>>>>>>>>>>>', 'goal:',
              'state->', goal.state,
              'account->', goal.account,
              'name->', goal.name,
              'portfolio_set->', goal.portfolio_set,
              'cash_balance->', goal.cash_balance)
            print('new_positions:', new_positions)
        approve_mor(mor)
    # process sells
    execute(delay)

    for item in goals_list:
        goal = item['goal']
        new_positions = item['new_positions']

        # now create buys - but only use cash to finance proceeds of buys
        mor, requests = create_request(goal, new_positions, reason,
                                        execution_provider=execution_provider,
                                        data_provider=data_provider,
                                        allowed_side=1)
        approve_mor(mor)
    # process buys
    execute(delay)


# obsolete - delete
def example_usage_with_IB():
    options = get_options()
    logging.root.setLevel(verbose_levels.get(options.verbose, ERROR))
    con = InteractiveBrokers()
    con.connect()
    con.request_account_summary()

    con.request_market_depth('GOOG')
    while con.requesting_market_depth():
        short_sleep()

    long_sleep()
    long_sleep()
    long_sleep()

    account_dict = dict()
    account_dict['DU493341'] = 40
    account_dict['DU493342'] = 60
    profile = FAAccountProfile()
    profile.append_share_allocation('AAPL', account_dict)

    account_dict['DU493341'] = 60
    account_dict['DU493342'] = 40
    profile.append_share_allocation('MSFT', account_dict)
    con.replace_profile(profile.get_profile())

    #con.request_profile()
    short_sleep()

    order_id = con.make_order(ticker='MSFT', limit_price=57.57, quantity=100)
    con.place_order(order_id)

    order_id = con.make_order(ticker='AAPL', limit_price=107.59, quantity=-100)
    con.place_order(order_id)

    long_sleep()
    con.current_time()

    con.request_market_depth('GOOG')
    while con.requesting_market_depth():
        short_sleep()

    short_sleep()

    long_sleep()
    long_sleep()


'''
class Command(BaseCommand):
    help = 'execute orders'

    def handle(self, *args, **options):
        logger.setLevel(logging.DEBUG)
'''
