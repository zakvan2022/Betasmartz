from functools import reduce
from main import constants, tax_helpers
from client.models import ClientAccount
from retiresmartz.models import RetirementPlan
from django.core.exceptions import ObjectDoesNotExist
import math
import numpy as np
from tzlocal import get_localzone
from pytz import timezone
import requests
from random import random
from portfolios.models import MarketIndex
import datetime
# import matplotlib.pyplot as plt

def get_lifestyle_box(client):
    return [
        {
            'target': True,
            'title': 'No.1: Doing OK',
            'stars': range(3),
            'subtitle': 'Lifestyle 1',
            'description': 'Largely Social Security',
            'income': round(client.income * constants.LIFESTYLE_DOING_OK_MULTIPLIER),
            'image': 'statements/retirement/lifestyle_01.png'
        },
        {
            'target': True,
            'title': 'No.2: Comfortable',
            'stars': range(4),
            'subtitle': 'Lifestyle 2',
            'description': 'Social Security + supplement',
            'income': round(client.income * constants.LIFESTYLE_COMFORTABLE_MULTIPLIER),
            'image': 'statements/retirement/lifestyle_02.png'
        },
        {
            'target': True,
            'title': 'No.3: Doing Well',
            'stars': range(5),
            'subtitle': 'Lifestyle 3',
            'description': 'Self-funded + some social security',
            'income': round(client.income * constants.LIFESTYLE_DOING_WELL_MULTIPLIER),
            'image': 'statements/retirement/lifestyle_03.png'
        },
        {
            'target': True,
            'title': 'No.4: Luxury',
            'stars': range(6),
            'subtitle': 'Lifestyle 4',
            'description': 'Self funded',
            'income': round(client.income * constants.LIFESTYLE_LUXURY_MULTIPLIER),
            'image': 'statements/retirement/lifestyle_04.png'
        }
    ]

expense_groups = [
    {
      'label': 'Expenditures',
      'color': '#d47877'
    },
    {
      'label': 'Retirement contributions',
      'color': '#add5ff'
    },
    {
      'label': 'Savings & Investments',
      'color': '#83ad5d'
    },
    {
      'label': 'Social security & Medicare (FCIA)',
      'color': '#8a6d3b'
    },
    {
      'label': 'Tax',
      'color': '#5f9ea0'
    }
]

def get_waterfall_chart(plan, has_partner):
    expenses = plan.expenses if plan.expenses else []
    ExpenseCategory = RetirementPlan.ExpenseCategory
    sum_expenses = reduce(lambda acc, item: acc + item['amt'], expenses, 0)

    expenses_group_mapping = {
        ExpenseCategory.ALCOHOLIC_BEVERAGE.value: 0,
        ExpenseCategory.APPAREL_SERVICES.value: 0,
        ExpenseCategory.EDUCATION.value: 0,
        ExpenseCategory.ENTERTAINMENT.value: 0,
        ExpenseCategory.FOOD.value: 0,
        ExpenseCategory.HEALTHCARE.value: 0,
        ExpenseCategory.HOUSING.value: 0,
        ExpenseCategory.INSURANCE_PENSIONS_SOCIAL_SECURITY.value: 3,
        ExpenseCategory.PERSONAL_CARE.value: 0,
        ExpenseCategory.READING.value: 0,
        ExpenseCategory.SAVINGS.value: 2,
        ExpenseCategory.TAXES.value: 4,
        ExpenseCategory.TOBACCO.value: 0,
        ExpenseCategory.TRANSPORTATION.value: 0,
        ExpenseCategory.MISCELLANEOUS.value: 0
    }

    btc = (plan.btc + (plan.partner_data['btc'] if has_partner else 0)) / 12
    sum_expenses += btc

    btc_bar = {
        'color': expense_groups[1]['color'],
        'amt': round(btc),
        'height': btc / max(1, sum_expenses) * 100,
        'left': 0
    }

    x_axis = [expense_groups[1]['label']] + list(map(lambda item: RetirementPlan.get_expense_category_text(item['cat']), expenses))
    y_axis = range(int(math.ceil(sum_expenses / 1000.0)) * 1000, 0, -1000)

    # TODO: Group by categories and sort by alphabetical order of x_axis
    bars = [btc_bar] + [{
        'color': expense_groups[expenses_group_mapping[item['cat']]]['color'],
        'amt': round(item['amt']),
        'height': item['amt'] / sum_expenses * 100,
        'left': (i + 1) * 100 / max(1, len(x_axis))
    } for i, item in enumerate(expenses)]

    return {
        'x_axis': x_axis,
        'x_unit_width': int(100 / max(1, len(x_axis)) * 100) / 100,
        'y_axis': y_axis,
        'y_unit_width': 100 / max(1, len(y_axis)),
        'legends': expense_groups,
        'bars': bars
    }

def get_tax_situation(plan):
    try:
        p = plan.projection
        client = {
            'state_income_tax': round(p.current_percent_state_tax * 100, 2),
            'federal_income_tax': round(p.current_percent_fed_tax * 100, 2),
            'medicare': round(p.current_percent_medicare * 100, 2),
            'social_security': round(p.current_percent_soc_sec * 100, 2)
        }
        client['yours_to_keep'] = 100 - (client['state_income_tax'] + \
                                         client['federal_income_tax'] + \
                                         client['medicare'] + \
                                         client['social_security'])

        partner = {
            'state_income_tax': round(p.part_current_percent_state_tax * 100, 2),
            'federal_income_tax': round(p.part_current_percent_fed_tax * 100, 2),
            'medicare': round(p.part_current_percent_medicare * 100, 2),
            'social_security': round(p.part_current_percent_soc_sec * 100, 2)
        }
        partner['yours_to_keep'] = 100 - (partner['state_income_tax'] + \
                                          partner['federal_income_tax'] + \
                                          partner['medicare'] + \
                                          partner['social_security'])
        return {
            'client': client,
            'partner': partner
        }
    except ObjectDoesNotExist:
        return {
            'client': {
                'yours_to_keep': 58.05,
                'state_income_tax': 9.3,
                'federal_income_tax': 25,
                'medicare': 1.45,
                'social_security': 6.2
            },
            'partner': {
                'yours_to_keep': 58.05,
                'state_income_tax': 9.3,
                'federal_income_tax': 25,
                'medicare': 1.45,
                'social_security': 6.2
            }
        }

def get_pensions_annuities(plan):
    pa = plan.external_income.all()
    # TODO: return all the external incomes added or restrict to have only one external income
    if pa.count():
        return pa[0]
    else:
        return {
            'name': 'N/A',
            'account_type': None,
            'begin_date': None,
            'amount': None
        }

def value_at(lst, index):
    try:
        return lst[index]
    except:
        return 0

def get_retirement_income_chart(plan, has_partner):
    try:
        p = plan.projection

        base_idx = tax_helpers.get_pre_retirement_years(plan.client.date_of_birth, plan.retirement_age)
        last_idx = base_idx + tax_helpers.get_retirement_years(plan.selected_life_expectancy, plan.retirement_age) - 1

        max_limit = plan.desired_income
        for idx in range(base_idx, last_idx):
            sum_value = value_at(p.non_taxable_inc, idx) + \
                        value_at(p.tot_taxable_dist, idx) + \
                        value_at(p.annuity_payments, idx) + \
                        value_at(p.pension_payments, idx) + \
                        value_at(p.ret_working_inc, idx) + \
                        value_at(p.soc_sec_benefit, idx)
            if has_partner:
                sum_value += value_at(p.part_non_taxable_inc, idx) + \
                             value_at(p.part_tot_taxable_dist, idx) + \
                             value_at(p.part_annuity_payments, idx) + \
                             value_at(p.part_pension_payments, idx) + \
                             value_at(p.part_ret_working_inc, idx) + \
                             value_at(p.part_soc_sec_benefit, idx)
            max_limit = max(max_limit, sum_value)

        colors = ['#b4b4b4', '#6faddb', '#ffc82c', '#ae5b1d', '#335989', '#83b75e']
        partner_colors = ['#767676', '#a98419', '#3273a0', '#54783c', '#7da2d7', '#f4a872']
        legends = [
            'Nontaxable Income',
            'Total Taxable Distributions',
            'Annuity Payments',
            'Pension Payments',
            'Retirement Working Income',
            'Social Security Benefit'
        ]
        partner_legends = [
            'Spouse - Nontaxable Income',
            'Spouse - Total Taxable Distributions',
            'Spouse - Annuity Payments',
            'Spouse - Pension Payments',
            'Spouse - Retirement Working Income',
            'Spouse - Social Security Benefit'
        ]
        if has_partner:
            partner_age = int(tax_helpers.get_age(plan.partner_data['dob']))
            legends += partner_legends
            colors += partner_colors
        legends += ['Desired Income']
        colors += ['#ff0000']

        values = []
        if max_limit > 0:
            y_interval_0 = max_limit / 10
            y_interval = pow(10, np.floor(np.log10(y_interval_0)))
            y_interval = y_interval * 5 if y_interval_0 < y_interval * 5 else y_interval * 10
            max_limit = int(np.ceil(max_limit / y_interval) * y_interval)
        else:
            y_interval = 1
            max_limit = 1
        y_axis = range(0, max_limit + 1, int(y_interval))
        y_axis = list(reversed(list(y_axis)))
        y_height = y_interval / max_limit * 100
        x_num = last_idx - base_idx
        x_interval = min(40, 560 / x_num)
        x_width = x_interval * x_num + 42

        for idx in range(base_idx, last_idx):
            y_values = [
                value_at(p.non_taxable_inc, idx) / max_limit * 100,
                value_at(p.tot_taxable_dist, idx) / max_limit * 100,
                value_at(p.annuity_payments, idx) / max_limit * 100,
                value_at(p.pension_payments, idx) / max_limit * 100,
                value_at(p.ret_working_inc, idx) / max_limit * 100,
                value_at(p.soc_sec_benefit, idx) / max_limit * 100,
            ]
            x_label = str(plan.client.age + 1 + idx)
            if has_partner:
                y_values += [
                    value_at(p.part_non_taxable_inc, idx) / max_limit * 100,
                    value_at(p.part_tot_taxable_dist, idx) / max_limit * 100,
                    value_at(p.part_annuity_payments, idx) / max_limit * 100,
                    value_at(p.part_pension_payments, idx) / max_limit * 100,
                    value_at(p.part_ret_working_inc, idx) / max_limit * 100,
                    value_at(p.part_soc_sec_benefit, idx) / max_limit * 100,
                ]
                x_label += ' / ' + str(partner_age + 1 + idx)
            values += [{
                'x_label': x_label,
                'y_values': y_values,
                'y_offset': 100 - sum(y_values)
            }]
        return {
            'values': values,
            'colors': colors,
            'legends': legends,
            'y_axis': list(y_axis),
            'y_height': y_height,
            'desired_income': (1 - plan.desired_income / max_limit) * 100,
            'x_interval': x_interval,
            'x_width': x_width
        }
    except ObjectDoesNotExist:
        return None


def get_random_colors(len):
    colors = []
    letters = list('0123456789ABCDEF')
    for num in range(0, len):
        color = '#'
        for i in list(range(0, 6)):
            color += letters[int(math.floor(random() * 16))]
        colors += [color]
    return colors

def get_account_balance_chart(plan, has_partner):
    try:
        p = plan.projection

        base_idx = 0
        last_idx = plan.selected_life_expectancy - plan.client.age - 1

        max_limit = 0
        sum_value = [0] * (last_idx - base_idx + 1)
        if p.list_of_account_balances is not None:
            list_of_account_balances = list(filter(lambda item: item['data'] is not None, p.list_of_account_balances))
        else:
            list_of_account_balances = []
        if has_partner:
            part_list_of_account_balances = list(filter(lambda item: item['data'] is not None, p.part_list_of_account_balances))

        for idx in range(base_idx, last_idx):
            for acc in list_of_account_balances:
                sum_value[idx] += value_at(acc['data'], idx)
            if has_partner:
                for acc in part_list_of_account_balances:
                    sum_value[idx] += value_at(acc['data'], idx)
        max_limit = max(sum_value)

        colors = get_random_colors(len(list_of_account_balances))
        legends = list(map(lambda item: ClientAccount.get_account_type_text(item['account_type']), list_of_account_balances))

        if has_partner:
            partner_colors = get_random_colors(len(part_list_of_account_balances))
            partner_legends = list(map(lambda item: 'Partner ' + ClientAccount.get_account_type_text(item['account_type']), part_list_of_account_balances))
            colors += partner_colors
            legends += partner_legends
            partner_age = int(tax_helpers.get_age(plan.partner_data['dob']))

        values = []
        if max_limit > 0:
            y_interval_0 = max_limit / 10
            y_interval = pow(10, np.floor(np.log10(y_interval_0)))
            y_interval = y_interval * 5 if y_interval_0 < y_interval * 5 else y_interval * 10
            max_limit = int(np.ceil(max_limit / y_interval) * y_interval)
        else:
            y_interval = 1
            max_limit = 1
        y_axis = range(0, max_limit + 1, int(y_interval))
        y_axis = list(reversed(list(y_axis)))
        y_height = y_interval / max_limit * 100
        x_num = last_idx - base_idx
        x_interval = min(40, 560 / x_num)
        x_width = x_interval * x_num + 42

        for idx in range(base_idx, last_idx):
            y_values = []
            for acc in list_of_account_balances:
                y_values.append(value_at(acc['data'], idx) / max_limit * 100)
            x_label = str(plan.client.age + 1 + idx)
            if has_partner:
                for acc in part_list_of_account_balances:
                    y_values.append(value_at(acc['data'], idx) / max_limit * 100)
                x_label += ' / ' + str(partner_age + 1 + idx)

            values += [{
                'x_label': x_label,
                'y_values': y_values,
                'y_offset': 100 - sum(y_values)
            }]
        return {
            'values': values,
            'colors': colors,
            'legends': legends,
            'y_axis': list(y_axis),
            'y_height': y_height,
            'x_interval': x_interval,
            'x_width': x_width
        }
    except ObjectDoesNotExist:
        return None

def get_timezone(client_ip):
    tz_info = get_localzone()
    try:
        res = requests.get(url='http://ip-api.com/json/{}'.format(client_ip))
        res = res.json()
        if 'timezone' in res:
            tz_info = timezone(res['timezone'])
    except:
        pass
    return tz_info

def get_price_from_index(index, daydelta):
    today = datetime.date.today()
    this_day = today - datetime.timedelta(days=daydelta)

    firstDay = this_day.replace(day=1)
    last_date_of_prev_month = firstDay - datetime.timedelta(days=1)

    try:
        last_date_object = MarketIndex.objects.get(data_api_param__iexact=index)
    except MarketIndex.DoesNotExist:
        last_date_object = []

    if last_date_object:
        last_date_object_query = last_date_object.daily_prices.filter(date__lte=last_date_of_prev_month)
    
        if last_date_object_query:
            return last_date_object_query.latest('date').price
        else:
            return 0
    else:
        return 0