import datetime

from dateutil.relativedelta import relativedelta
from django.test import TestCase

from common.utils import months_between
from portfolios.models import Inflation
from retiresmartz.calculator.cashflows import InflatedCashFlow, ReverseMortgage, EmploymentIncome
from retiresmartz.calculator.desired_cashflows import RetiresmartzDesiredCashFlow
import pandas as pd
from retiresmartz.calculator.social_security import calculate_payments


def get_time_series(cf, today, death, function_name):
    cf.reset()
    date = today
    cash_flows = dict()
    f = getattr(cf, function_name)
    while date <= death:
        cash_flows[date] = f(date)
        date += relativedelta(years=1)
    time_series = pd.DataFrame.from_dict(cash_flows, orient='index')
    time_series.sort_index(inplace=True)
    return time_series


class CashFlowTests(TestCase):
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
        self.get_cash_flow = (lambda cf: get_time_series(cf, self.today, self.death, 'on'))

    def test_inflated_cash_flow(self):
        cf = InflatedCashFlow(amount=116,
                              today=self.today,
                              start_date=self.retirement,
                              end_date=self.dob + relativedelta(years=85))

        # Make sure we can use the calculator as of today
        self.assertEqual(cf.on(self.today), 0)

        # Make sure before start_date is zero
        self.assertEqual(cf.on(self.retirement - relativedelta(days=1)), 0)

        # Make sure it starts on start date, and was inflated correctly
        ret_val = cf.on(self.retirement)
        self.assertAlmostEqual(ret_val, 116 * 1.001 ** months_between(self.today, self.retirement), 4)

        # Make sure we can get end date and it is inflated correctly
        self.assertAlmostEqual(cf.on(self.dob + relativedelta(years=85)),
                               116 * 1.001 ** months_between(self.today, self.dob + relativedelta(years=85)),
                               4)

        # Make sure after end date it returns zero
        self.assertEqual(cf.on(self.dob + relativedelta(years=85, days=1)), 0)

        # Make sure backwards dates raise a value error
        with self.assertRaises(ValueError):
            cf.on(self.retirement)

        # Make sure a reset allows previous dates again, and we get the same result
        cf.reset()
        self.assertEqual(ret_val, cf.on(self.retirement))
        time_series = self.get_cash_flow(cf)
        self.assertTrue(isinstance(time_series, pd.DataFrame))

    def test_reverse_mortgage(self):
        cf = ReverseMortgage(home_value=200000,
                             value_date=self.today,
                             start_date=self.retirement,
                             end_date=self.death)

        # Make sure we can use the calculator as of today
        self.assertEqual(cf.on(self.today), 0)

        # Make sure before start_date is zero
        self.assertEqual(cf.on(self.retirement - relativedelta(days=1)), 0)

        # Make sure it starts on start date, and was inflated correctly
        ret_val = cf.on(self.retirement)
        payments = months_between(self.retirement, self.death)
        self.assertAlmostEqual(ret_val,
                               200000 * 1.001 ** months_between(self.today, self.retirement) / payments * 0.9,
                               4)

        # Make sure we can get end date and it is the same payment
        self.assertAlmostEqual(cf.on(self.death), ret_val, 4)

        # Make sure after end date it returns zero
        self.assertEqual(cf.on(self.death + relativedelta(days=1)), 0)

        # Make sure backwards dates raise a value error
        with self.assertRaises(ValueError):
            cf.on(self.retirement)

        # Make sure a reset allows previous dates again, and we get the same result
        cf.reset()
        self.assertEqual(ret_val, cf.on(self.retirement))
        time_series = self.get_cash_flow(cf)
        self.assertTrue(isinstance(time_series, pd.DataFrame))

    def test_employment_income(self):
        cf = EmploymentIncome(income=150000,
                              growth=0.01,
                              today=self.today,
                              end_date=self.retirement)

        # Make sure we can use the calculator as of today
        self.assertEqual(cf.on(self.today), 150000)

        # Make sure we can get it on the end date and it is inflated correctly
        predicted = 150000 * ((1+(0.01/12)) ** months_between(self.today, self.retirement))
        self.assertAlmostEqual(cf.on(self.retirement), predicted, 4)

        # Make sure after end date it returns zero
        self.assertEqual(cf.on(self.death + relativedelta(days=1)), 0)

        # Make sure backwards dates raise a value error
        with self.assertRaises(ValueError):
            cf.on(self.retirement)

        # Make sure a reset allows previous dates again, and we get the same result
        cf.reset()
        self.assertAlmostEqual(predicted, cf.on(self.retirement), 4)
        time_series = self.get_cash_flow(cf)
        self.assertTrue(isinstance(time_series, pd.DataFrame))

    def test_ss(self):
        ss_all = calculate_payments(self.dob, 4000)
        ss_income = ss_all.get(self.retirement, None)
        if ss_income is None:
            ss_income = ss_all[sorted(ss_all)[0]]
        ss_payments = InflatedCashFlow(ss_income, self.today, self.retirement, self.death)
        time_series = self.get_cash_flow(ss_payments)
        self.assertTrue(isinstance(time_series, pd.DataFrame))

    def test_desired_cash_flow(self):
        income = EmploymentIncome(income=4000,
                                  growth=0.01,
                                  today=self.today,
                                  end_date=self.retirement)

        cf = RetiresmartzDesiredCashFlow(current_income=income,
                                         retirement_income=1000,
                                         retirement_date=self.retirement,
                                         today=self.today,
                                         end_date=self.death,
                                         replacement_ratio=1)
        cash_flows = dict()
        for date, desired_amount in cf:
            cash_flows[date] = desired_amount
        time_series = pd.DataFrame.from_dict(cash_flows, orient='index')
        time_series.sort_index(inplace=True)
        self.assertTrue(isinstance(time_series, pd.DataFrame))


