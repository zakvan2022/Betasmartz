import pandas as pd
import pandas.io.data as web

from portfolios.providers.data.backtester import DataProviderBacktest
from portfolios.providers.dummy_models import GoalFactory, PositionLot
from portfolios.providers.execution.django import ExecutionProviderDjango
from portfolios.models import Ticker
from portfolios.calculation import build_instruments, \
    calculate_portfolio, calculate_portfolios, get_instruments
from api.v1.tests.factories import MarkowitzScaleFactory, FillFactory
from execution.end_of_day import create_orders, process_fills, send_order, \
    mark_order_as_complete, approve_mor
from execution.models import Order
from main.management.commands.rebalance import rebalance


class GetETFTickers(object):
    def __init__(self, filePath):
        self.__filePath = filePath
        self.__data = None

    def loadCsv(self):
        self.__data = pd.read_csv(self.__filePath)

    def filterETFs(self):
        self.__data = self.__data.ix[self.__data['Industry'] == 'Exchange Traded Fund']
        self.__data = self.__data.ix[self.__data['Country'] == 'USA']
        self.__data = self.__data.sort('Volume', ascending=False)
        self.__data = self.__data.head(n=300)

    def returnData(self):
        return self.__data['Ticker'].tolist()


class DownloadDataYahoo(object):
    def __init__(self, start, end, tickerList):
        self.__tickerList = tickerList
        self.__start = start
        self.__end = end
        self.__data = None

    def download(self):
        self.__data = web.DataReader(self.__tickerList, 'yahoo', self.__start, self.__end)

    def returnData(self):
        return self.__data


class Backtester(object):
    def execute_order(self, settings, order, data_provider, execution_provider):
        for request in order[0].execution_requests:
            ticker = data_provider.get_ticker(request.asset.symbol)
            share_value = ticker.daily_prices.last() * request.volume
            settings.current_balance -= share_value
            settings.cash_balance -= share_value
            #position = PositionMock(ticker=ticker, share=request.volume)

            positionLot = PositionLot(ticker=ticker,
                                      price=ticker.daily_prices.last(),
                                      quantity=request.volume,executed=data_provider.get_current_date())
            positionLot.data_provider = data_provider
            settings.position_lots.append(positionLot)
            execution_provider.order_executed(execution_request=request,
                                              price=ticker.daily_prices.last(),
                                              time=data_provider.get_current_date())
            execution_provider.attribute_sell(execution_request=request, goal=settings,
                                              data_provider=data_provider)
        execution_provider.cancel_pending_orders()
        execution_provider.cash_left(cash=settings.cash_balance, time=data_provider.get_current_date())

    def execute(self, mor):
        approve_mor(mor)
        create_orders()
        orders_etna = Order.objects.is_not_complete()
        for order in orders_etna:
            send_order(order)
            mark_order_as_complete(order)

            ticker = Ticker.objects.get(id=order.ticker.id)
            price = ticker.daily_prices.order_by('-date').first().price

            FillFactory.create(volume=order.FillQuantity, price=price, etna_order=order)
        process_fills()

    def calculate_performance(self, execution_provider):
        return execution_provider.calculate_portfolio_returns()


class TestSetup(object):
    def __init__(self):
        self._covars = self._samples = self._instruments = self._masks = None
        self.data_provider = DataProviderBacktest(sliding_window_length=250 * 5, dir='/backtesting/')
        self.execution_provider = ExecutionProviderDjango()
        MarkowitzScaleFactory.create()
        self.data_provider.get_goals()

        self.goal = None

    def create_goal(self, goal):
        self.goal = goal

    def instruments_setup(self):
        self._covars, self._samples, self._instruments, self._masks = build_instruments(self.data_provider)


if __name__ == "__main__":
    '''
    tickers = GetETFTickers('finviz.csv')
    tickers.loadCsv()
    tickers.filterETFs()
    etfTickers = tickers.returnData()
    yahoo = DownloadDataYahoo(datetime.datetime(2005,1,1), datetime.datetime(2016,7,30), etfTickers)
    yahoo.download()
    dataClose = yahoo.returnData()['Close']
    dataClose[dataClose == 0] = np.nan
    dataClose.fillna('ffill')

    capitalization = yahoo.returnData()['Close'] * yahoo.returnData()['Volume']
    capitalization[capitalization==0]=np.nan
    capitalization.fillna('ffill')

    dataClose.to_csv('fundPrices.csv')
    capitalization.to_csv('capitalization.csv')
    '''

    setup = TestSetup()

    backtester = Backtester()
    requests = [setup.execution_provider.create_empty_market_order()]

    while setup.data_provider.move_date_forward():
        print("backtesting "+str(setup.data_provider.get_current_date()))

        build_instruments(setup.data_provider)

        '''

        # execute orders from yesterday
        backtester.place_order(settings=setup.goal,
                               order=requests,
                               data_provider=setup.data_provider,
                               execution_provider=setup.execution_provider)
        '''

        # calculate current portfolio stats
        portfolios_stats = calculate_portfolios(setting=setup.goal.active_settings,
                                                data_provider=setup.data_provider,
                                                execution_provider=setup.execution_provider)
        portfolio_stats = calculate_portfolio(settings=setup.goal.active_settings,
                                              data_provider=setup.data_provider,
                                              execution_provider=setup.execution_provider)

        # generate orders for tomorrow
        #try:
        requests = rebalance(idata=get_instruments(setup.data_provider),
                             goal=setup.goal,
                             data_provider=setup.data_provider,
                             execution_provider=setup.execution_provider)
        #except:
        #    print("reblance not succesful")
        #    requests = [setup.execution_provider.create_empty_market_order()]

        #backtester.execute_order(settings=setup.goal,
        #                         order=requests,
        #                         data_provider=setup.data_provider,
        #                         execution_provider=setup.execution_provider)
        backtester.execute()

    performance = backtester.calculate_performance(execution_provider=setup.execution_provider)

    print('finished correctly')
