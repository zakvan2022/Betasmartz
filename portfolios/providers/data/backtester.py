from collections import defaultdict
from datetime import date, timedelta
from django.core.cache import cache
from django.utils import timezone
from main import redis
from django_pandas.io import read_frame
from .abstract import DataProviderAbstract
from main.tests.fixture import Fixture1
from portfolios.exceptions import OptimizationException
from portfolios.models import AssetFeatureValue, DailyPrice, MarketCap, MarketIndex, \
    PortfolioSet, Ticker, MarkowitzScale, InvestmentCycleObservation, InvestmentCyclePrediction
from portfolios.returns import get_prices
import os
from api.v1.tests.factories import InvestmentCyclePredictionFactory
import pandas as pd
import numpy as np


class DataProviderBacktest(DataProviderAbstract):
    def __init__(self, sliding_window_length, dir=None):
        self.cache = None
        self.sliding_window_length = sliding_window_length
        self.__current_date = self.sliding_window_length
        self.dir = os.getcwd() + dir

        cycles = '111222000334440001122200111222000334440001122200111222000334440001122200' * 31
        dates = Fixture1.populate_observations(cycles, date(2011, 1, 1))

        self.time_constrained_tickers = []
        self._populate_probabilities()
        self.fund_price_matrix = None
        self.benchmark_marketweight_matrix = None
        self._create_tickers()
        self.dates = self._get_dates()

    def initialize_tickers(self):
        self._initial_fill_ticker_prices()

    def _get_dates(self):
        timedates = self.fund_price_matrix.index.to_pydatetime()
        dates = [timedate.date() for timedate in timedates]
        return dates

    def _create_tickers(self):
        self.fund_price_matrix = pd.read_csv(self.dir + 'fundPrices_mock.csv',
                                             index_col='Date',
                                             infer_datetime_format=True,
                                             parse_dates=True)
        self.fund_price_matrix.index.name = 'date'

        self.benchmark_marketweight_matrix = pd.read_csv(self.dir + 'capitalization_mock.csv',
                                                         index_col='Date',
                                                         infer_datetime_format=True,
                                                         parse_dates=True)
        self.benchmark_marketweight_matrix.name = 'date'

    @staticmethod
    def _populate_probabilities():
        vals = [
            [0.08089787, 0.167216193, 0.007325566, 0.143641463, 0.733230633],
            [0.080636192, 0.151937142, 0.187936638, 0.39640021, 0.420692639],
            [0.087140048, 0.122145455, 0.043799137, 0.508127278, 0.412764823],
            [0.086595196, 0.163545905, 0.029313429, 0.329095078, 0.370009886],
            [0.087243834, 0.19905742, 0.00229681, 0.09144718, 0.390732573],
            [0.081566295, 0.277402407, 0.080812535, 0.045212519, 0.360884538],
            [0.07358428, 0.117376517, 0.001417166, 0.143329684, 0.395081559],
            [0.073802749, 0.133804588, 0.000635776, 0.394104881, 0.39465102],
            [0.075446787, 0.082311401, 0.000812869, 0.271816537, 0.69018451],
            [0.078041426, 0.244725389, 0.014591784, 0.049618232, 0.472784413],
            [0.076303139, 0.115293179, 0.176512979, 0.07634871, 0.375165155],
            [0.073802749, 0.133804588, 0.000635776, 0.394104881, 0.39465102],
        ]
        dt = date(2011, 1, 1)
        for p in vals:
            InvestmentCyclePredictionFactory.create(as_of=dt, eq=p[0], eq_pk=p[1], pk_eq=p[2], eq_pit=p[3], pit_eq=p[4])
            dt += timedelta(days=31)

    def move_date_forward(self):
        # this function is only used in backtesting
        self.cache = None
        success = False

        self._remove_ticker_prices(self.get_start_date())

        if len(self.dates) > self.__current_date + 1:
            self.__current_date += 1
            success = True
        else:
            print("cannot move date forward")

        self._add_ticker_prices(self.get_current_date())
        return success

    def _add_ticker_prices(self, dt):
        tickers = Ticker.objects.all()
        prices = list()
        market_indexes = list()

        for t in tickers:
            data = self.fund_price_matrix[t.symbol]
            prices.append(DailyPrice(instrument=t, date=dt, price=data[dt]))
            market_indexes.append(DailyPrice(instrument=t, date=dt, price=data[dt]))
        DailyPrice.objects.bulk_create(prices)

    def _remove_ticker_prices(self, dt):
        DailyPrice.objects.filter(date=dt).delete()

    def _initial_fill_ticker_prices(self):
        tickers = Ticker.objects.all()
        prices = list()
        market_caps = list()
        for t in tickers:
            data = self.fund_price_matrix[t.symbol]
            data = data[self.get_start_date():self.get_current_date()]

            market_cap = self.benchmark_marketweight_matrix[t.symbol]
            market_cap = market_cap[self.get_start_date():self.get_current_date()]

            for day, market_cap_day in zip(data.index, market_cap.index):
                prices.append(DailyPrice(instrument=t, date=day, price=data[day]))
                prices.append(DailyPrice(instrument=t.benchmark, date=day, price=data[day]))
                if not np.isnan(market_cap[market_cap_day]):
                    market_caps.append(
                        MarketCap(instrument=t.benchmark, date=market_cap_day, value=market_cap[market_cap_day]))
        DailyPrice.objects.bulk_create(prices)
        MarketCap.objects.bulk_create(market_caps)

    def get_instrument_daily_prices(self, ticker):
        prices = get_prices(ticker, self.get_start_date(), self.get_current_date())
        return prices

    def get_current_date(self):
        date = self.dates[self.__current_date]
        return date

    def get_start_date(self):
        date = self.dates[self.__current_date - self.sliding_window_length]
        return date

    def get_fund_price_latest(self, ticker):
        latest_ticker = ticker.daily_prices.order_by('-date').first()
        if latest_ticker:
            return latest_ticker.price
        return None

    def get_instrument_daily_prices(self, ticker):
        return ticker.daily_prices.order_by('-date')

    def get_features(self, ticker):
        return ticker.features.values_list('id', flat=True)

    def get_asset_class_to_portfolio_set(self):
        ac_ps = defaultdict(list)
        # Build the asset_class -> portfolio_sets mapping
        for ps in PortfolioSet.objects.all():
            for ac in ps.asset_classes.all():
                ac_ps[ac.id].append(ps.id)
        return ac_ps

    def get_tickers(self):
        return Ticker.objects.all()

    def get_ticker(self, tid):
        return Ticker.objects.get(id=tid)

    def get_market_weight_latest(self, ticker):
        mp = MarketCap.objects.filter(instrument_content_type__id=ticker.benchmark_content_type.id,
                                      instrument_object_id=ticker.benchmark_object_id).order_by('-date').first()
        return None if mp is None else mp.value

    def get_portfolio_sets_ids(self):
        return PortfolioSet.objects.values_list('id', flat=True)

    def get_asset_feature_values_ids(self):
        return AssetFeatureValue.objects.values_list('id', flat=True)

    def get_goals(self):
        return

    def get_markowitz_scale(self):
        return MarkowitzScale.objects.order_by('-date').first()

    def set_markowitz_scale(self, dt, mn, mx, a, b, c):
        MarkowitzScale.objects.create(date=dt,
                                      min=mn,
                                      max=mx,
                                      a=a,
                                      b=b,
                                      c=c)

    def get_instrument_cache(self):
        return self.cache

    def set_instrument_cache(self, data):
        self.cache = data

    def get_investment_cycles(self):
        # Populate the cache as we'll be hitting it a few times. Boolean evaluation causes full cache population
        obs = InvestmentCycleObservation.objects.all().filter(as_of__lt=self.get_current_date()).order_by('as_of')
        if not obs:
            raise OptimizationException("There are no historic observations available")
        return obs

    def get_last_cycle_start(self):
        obs = self.get_investment_cycles()

        current_cycle = obs.last().cycle

        # Get the end date and value of the last non-current full cycle before the current one
        pre_dt = obs.exclude(cycle=current_cycle).last().as_of
        previous_cycle = obs.filter(as_of=pre_dt).last().cycle

        # Get the end date of the cycle before the previous full cycle
        if current_cycle == InvestmentCycleObservation.Cycle.EQ.value:
            pre_dt_start = obs.filter(as_of__lte=pre_dt).exclude(cycle=previous_cycle).last().as_of
            pre_on_dt = obs.filter(as_of__lt=pre_dt_start).filter(cycle=previous_cycle).last().as_of
        else:
            pre_dt_start = obs.filter(as_of__lt=pre_dt).filter(cycle=current_cycle).last().as_of
            pre_on_dt = obs.filter(as_of__lt=pre_dt_start).exclude(cycle=current_cycle).last().as_of

        # Now get the first date after this when the full previous cycle was on
        return obs.filter(as_of__gt=pre_on_dt).first().as_of

    def get_cycle_obs(self, begin_date):
        qs = self.get_investment_cycles().filter(as_of__gte=begin_date)
        return read_frame(qs, fieldnames=['cycle'], index_col='as_of', verbose=False)['cycle']

    def get_investment_cycle_predictions(self):
        return InvestmentCyclePrediction.objects.all().filter(as_of__lt=self.get_current_date()).order_by('as_of')

    def get_probs_df(self, begin_date):
        qs = self.get_investment_cycle_predictions().filter(as_of__gt=begin_date)
        probs_df = read_frame(qs,
                              fieldnames=['eq', 'eq_pk', 'pk_eq', 'eq_pit', 'pit_eq'],
                              index_col='as_of')
        return probs_df