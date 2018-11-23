from unittest.case import skip

import numpy as np
import pandas as pd
from django.test import TestCase
from backtesting.backtester import TestSetup, Backtester
from statsmodels.stats.correlation_tools import cov_nearest

from execution.models import MarketOrderRequest
from goal.models import GoalMetric, Portfolio, PortfolioItem
from main.management.commands.rebalance import rebalance, create_request, build_positions
from main.tests.fixture import Fixture1
from portfolios.calculation import build_instruments, calculate_portfolio, \
     calculate_portfolios, get_instruments
from portfolios.models import AssetClass, InvestmentType, MarketIndex, MarkowitzScale, Region, Ticker
from portfolios.providers.data.django import DataProviderDjango
from portfolios.providers.execution.django import ExecutionProviderDjango
from unittest import skip

class BaseTest(TestCase):
    # @skip('not yet working - need to figure out how to make bl work')
    @skip("refactoring in progress")
    def test_backtest(self):
        setup = TestSetup()

        # actually tickers are created here - we need to set proper asset class for each ticker
        self.create_goal()

        setup.create_goal(self.goal)
        setup.data_provider.initialize_tickers()
        setup.data_provider.move_date_forward()

        backtester = Backtester()

        print("backtesting " + str(setup.data_provider.get_current_date()))
        build_instruments(setup.data_provider)

        # optimization fails due to
        portfolios_stats = calculate_portfolios(setting=setup.goal.selected_settings,
                                                data_provider=setup.data_provider,
                                                execution_provider=setup.execution_provider)
        portfolio_stats = calculate_portfolio(settings=setup.goal.selected_settings,
                                              data_provider=setup.data_provider,
                                              execution_provider=setup.execution_provider)

        weights, instruments, reason = rebalance(idata=get_instruments(setup.data_provider),
                                                 goal=setup.goal,
                                                 data_provider=setup.data_provider,
                                                 execution_provider=setup.execution_provider)

        new_positions = build_positions(setup.goal, weights, instruments)

        # create sell requests first
        mor, requests = create_request(setup.goal, new_positions, reason,
                                       execution_provider=setup.execution_provider,
                                       data_provider=setup.data_provider,
                                       allowed_side=-1)
        # process sells
        backtester.execute(mor)

        # now create buys - but only use cash to finance proceeds of buys
        mor, requests = create_request(setup.goal, new_positions, reason,
                                       execution_provider=setup.execution_provider,
                                       data_provider=setup.data_provider,
                                       allowed_side=1)

        backtester.execute(mor)

        transaction_cost = np.sum([abs(r.volume) for r in requests]) * 0.005
        # So, the rebalance could not be in place if the excecution algo might not determine how much it will cost to rebalance.

        # this does not work - make it work with Django execution provider - use EtnaOrders
        #performance = backtester.calculate_performance(execution_provider=setup.execution_provider)

        self.assertTrue(True)

    def create_goal(self):
        self.goal = Fixture1.initialize_backtest(['DIA', 'DLN', 'DOG', 'DRIP', 'DSLV', 'DUST', 'DVY', 'DWTI', 'DXD',
       'DXJ', 'EDC', 'EDZ', 'EEM', 'EEMV', 'EFA'])
        #self.goal = Fixture1.goal1()

