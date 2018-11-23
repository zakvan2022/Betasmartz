import datetime

from dateutil.relativedelta import relativedelta
from django.test import TestCase

from common.utils import months_between
from portfolios.models import Inflation
from retiresmartz.calculator.assets import TaxPaidAccount, TaxDeferredAccount
import pandas as pd
from retiresmartz.tests.test_cashflows import get_time_series


class AssetTests(TestCase):
    def setUp(self):
        self.dob = datetime.date(1960, 3, 14)
        self.today = datetime.date(2016, 2, 1)
        self.retirement = datetime.date(2029, 2, 1)
        self.death = datetime.date(2054, 6, 1)

        # Populate some inflation figures.
        dt = datetime.date(1950, 1, 1)
        inflations = []
        while dt <= self.death:
            inflations.append(Inflation(year=dt.year, month=dt.month, value=0.001))
            dt += relativedelta(months=1)
        if hasattr(Inflation, '_cum_data'):
            del Inflation._cum_data
        Inflation.objects.bulk_create(inflations)
        self.get_balances = lambda asset: get_time_series(asset, self.today, self.death, 'balance')
        self.get_cash_flows = lambda asset: get_time_series(asset, self.today, self.death, 'on')

    def test_tax_paid_account(self):
        ac = TaxPaidAccount(name="Test Account",
                            today=self.today,
                            opening_balance=50000,
                            growth=0.05,
                            retirement_date=self.retirement,
                            end_date=self.death,
                            contributions=400)

        # Make sure we can use the calculator as of today, but attempted withdrawals fail until retirement date
        self.assertEqual(ac.balance(self.today), 50000)
        self.assertEqual(ac.withdraw(self.today, 1000), 0)
        self.assertEqual(ac.balance(self.today), 50000)

        # Make sure withdrawal before start_date is zero, but balance is inflated correctly
        r_minus_1 = self.retirement - relativedelta(days=1)
        def get_pred(months):
            pred = 50000 * (((1.05 ** (1 / 12)) + 0.001) ** months)
            for m in range(1, months + 1):
                pred += (400 * (1.001 ** m)) * ((1.05 ** (1 / 12)) + 0.001) ** (months - m)
            return pred

        predicted = get_pred(months_between(self.today, r_minus_1))

        self.assertAlmostEqual(ac.balance(r_minus_1), predicted, 6)
        self.assertEqual(ac.withdraw(r_minus_1, 1000), 0)
        # Make sure the withdrawal didn't actually withdraw.
        self.assertAlmostEqual(ac.balance(r_minus_1), predicted, 6)

        # Make sure withdrawal can happen on start date, and withdrawal actually happens.
        predicted = get_pred(months_between(self.today, self.retirement))
        self.assertAlmostEqual(ac.balance(self.retirement), predicted, 6)
        self.assertEqual(ac.withdraw(self.retirement, 1000), 1000)
        self.assertAlmostEqual(ac.balance(self.retirement), predicted - 1000, 6)

        # Make sure we can get end date
        self.assertEqual(ac.withdraw(self.death, 1000), 1000)

        # Make sure after end date it returns zero
        self.assertEqual(ac.withdraw(self.death + relativedelta(days=1), 1000), 0)

        # Make sure backwards dates raise a value error
        with self.assertRaises(ValueError):
            ac.balance(self.retirement)

        # Make sure a reset allows previous dates again, and we get the same result
        ac.reset()
        self.assertAlmostEqual(ac.balance(self.retirement), predicted, 6)
        time_series = self.get_balances(ac)
        self.assertTrue(isinstance(time_series, pd.DataFrame))

    def test_tax_deferred_account_as_asset(self):
        ac = TaxDeferredAccount(name='Example plan',
                                today=self.today,
                                dob=self.dob,
                                tax_rate=0.2,
                                opening_balance=50000,
                                growth=0.05,
                                retirement_date=self.retirement,
                                end_date=self.death,
                                contributions=400)
        time_series = self.get_balances(ac)
        self.assertTrue(isinstance(time_series, pd.DataFrame))

    def test_tax_deferred_as_cf(self):
        #self.today = datetime.date(2031, 2, 1)
        self.retirement = datetime.date(2050, 2, 1)

        ac = TaxDeferredAccount(name='Example plan',
                                today=self.today,
                                dob=self.dob,
                                tax_rate=0.2,
                                opening_balance=50000,
                                growth=0.05,
                                retirement_date=self.retirement,
                                end_date=self.death,
                                contributions=400)
        time_series = self.get_cash_flows(ac)
        self.assertTrue(isinstance(time_series, pd.DataFrame))
