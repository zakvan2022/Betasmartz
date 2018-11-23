import math
import pandas as pd
from dateutil.relativedelta import relativedelta
from rest_framework.exceptions import ValidationError
from main import constants
from main import inflation
import pdb

inflation_level = inflation.inflation_level

def get_account_balance(balance_start, capital_growth, contribution, distribution):
    '''
    returns balance given starting balance, capital growth, contribution and distributions
    '''
    return max(0, balance_start + capital_growth + contribution - distribution)


def get_account_growth(balance_start, rate):
    '''
    returns growth given starting balance and growth rate
    '''
    return (balance_start * rate)


def get_account_proportion(period, accnt_balance, class_balance):
    '''
    returns proportion of total balance of account class represented
    by the given account for the given period
    '''
    return (accnt_balance.iloc[period]/class_balance.iloc[period])


def get_age(dob):
    '''
    returns current age today based on dob
    '''
    return ((pd.Timestamp('today') - pd.Timestamp(dob)).days)/365.25


def get_annual_sum(intra_year_series, year_list):
    '''
    returns series of annualized quantities for each year in year_list, obtained by summing all values in intra_year_series for each year
    '''
    year_series_elements = []
    for yr in year_list:
        annual_sum = 0
        for element in intra_year_series.loc[pd.Timestamp(str(yr) + '0101').date():pd.Timestamp(str(yr) + '1231').date()]:
            annual_sum = annual_sum + element
        year_series_elements.append(annual_sum)
    return year_series_elements


def get_annual_year_end_value(intra_year_series, year_list):
    '''
    returns series of year_end quantities for each year in year_list, obtained by taking the last (i.e. latest)
    value in the intra_year_series for each year
    '''
    year_series_elements = []
    for yr in year_list:
        latest_value = 0
        for element in intra_year_series.loc[pd.Timestamp(str(yr) + '0101').date():pd.Timestamp(str(yr) + '1231').date()]:
            latest_value = element
        year_series_elements.append(latest_value)
    return year_series_elements
            

def get_deflator_from_period(period):
    '''
    returns dataframe of 'period-based' deflation factors for each period back from period, from now out to period
    '''
    return get_inflator_to_period(period)/get_inflator_to_period(period)[len(get_inflator_to_period(period)) - 1]


def get_inflator_to_period(period):
    '''
    returns dataframe of inflation rates and 'now-based' inflation factors for each period out to period
    '''
    inflation_df = pd.DataFrame(index=get_retirement_model_projection_index(pd.Timestamp('today').date(), period))
    inflation_df['Inflation_Rate'] = [inflation_level[i]/12. for i in range(period)]
    inflation_df['Inflator'] = (1 + inflation_df['Inflation_Rate']).cumprod()
    return inflation_df 

    
def get_miscellaneous_base(total_income, sum_expenses, monthly_contrib_employee_base):
    '''
    returns amount of undisclosed miscellaneous items implied by
    total_income - expenses - employee_contributions != 0
    '''
    tot_contrib = 0
    for contrib in monthly_contrib_employee_base:
        tot_contrib = tot_contrib + contrib

    abs_contrib = tot_contrib * total_income/12.
    return total_income - abs_contrib - sum_expenses


def get_nontaxable_distribution(ret_certain_inc_gap, reqd_min_dist, balance_start_nontaxable):
    '''
    returns nontaxable distribution given retirement certain income gap, required minimum
    distribution, nontaxable starting balance
    '''
    if ret_certain_inc_gap > reqd_min_dist:
        if balance_start_nontaxable > 0:
            return min(ret_certain_inc_gap - reqd_min_dist, balance_start_nontaxable)
        else:
            return 0.
    else:
        return 0.


def get_period_as_age(dob, period):
    '''
    returns age corresponding to period
    '''
    if period < 0:
        raise Exception('period < 0')
    return get_age(dob) + (period/12.)


def get_period_of_age(age_now, future_age):
    '''
    given age now, returns retirement model period last period in which TaxUser is younger than age
    '''
    if age_now > future_age:
        raise ValidationError("age_now > future_age")      
        
    return math.ceil((future_age - age_now) * 12)


def get_portfolio_return_above_cpi(desired_risk):
    return desired_risk * 10.0 * 0.005


def get_pre_retirement_years(dob, desired_retirement_age):
    '''
    returns number of years between now and start of retirement
    '''
    return round(desired_retirement_age - get_age(dob))


def get_reqd_min_distribution(age, balance_start_taxable, ira_rmd_factor):
    '''
    returns required minimumn distribution given starting balance of taxable accounts and age
    '''
    if balance_start_taxable > 0.:
        if age > 70.5:
            return balance_start_taxable/(ira_rmd_factor * 12.)
        else:
            return 0.
    else:
        return 0.
            

def get_retirement_account_index(acnt_type):
    '''
    Returns index of retirement account (using index rather than name,
    as can have multiple accounts of same type, so name would not uniqueley identify them)
    '''
    for i in range(len(constants.US_RETIREMENT_ACCOUNT_TYPES)):
        if acnt_type['acc_type'] == constants.US_RETIREMENT_ACCOUNT_TYPES[i]:
            return i
    raise Exception('unrecognized account type')
    

def get_retirement_model_projection_index(start_date, period):
    '''
    returns retirement model dataframe index from given start date and for given period
    '''
    return [start_date + relativedelta(months=1) + relativedelta(months=+i) for i in range(period)]


def get_retirement_years(life_exp, desired_retirement_age):
    '''
    returns the number of years between retirement and life expectancy
    '''
    return round(math.ceil(life_exp) - desired_retirement_age)


def get_soc_sec_factor(desired_retirement_age):
    '''
    returns factor by which to multiply ss_fra_retirement based on desired retirement age
    '''

    if desired_retirement_age <= 62:
        factor = 0.75

    elif desired_retirement_age > 62 and desired_retirement_age <= 63:
        factor = 0.80

    elif desired_retirement_age > 63 and desired_retirement_age <= 64:
        factor = 0.867

    elif desired_retirement_age > 64 and desired_retirement_age <= 65:
        factor = 0.933

    elif desired_retirement_age > 65 and desired_retirement_age <= 66:
        factor = 1.0

    elif desired_retirement_age > 66 and desired_retirement_age <= 67:
        factor = 1.08

    elif desired_retirement_age > 67 and desired_retirement_age <= 68:
        factor = 1.16

    elif desired_retirement_age > 68 and desired_retirement_age <= 69:
        factor = 1.24

    elif desired_retirement_age > 69:
        factor = 1.32

    return factor


def get_ss_benefit_future_dollars(ss_fra_todays, dob, future_age):
    '''
    returns soc sec benefit payment for the first period in which user is over a given future age
    in inflated future dollars, for a given date of birth and given ss_fra_todays
    '''
    period_of_age = get_period_of_age(get_age(dob), future_age)
    return get_ss_fra_future_dollars(ss_fra_todays, (period_of_age + 1))[period_of_age] * get_soc_sec_factor(future_age)


def get_ss_fra_future_dollars(ss_fra_todays, period):
    '''
    returns ss_fra_future_dollars series, i.e. the value of soc sec benefit for given
    period, in inflated, future dollars, for a given ss_fra_todays
    '''
    return ss_fra_todays * get_inflator_to_period(period)['Inflator']    


def get_start_year():
    '''
    returns start year
    '''
    return pd.Timestamp('today').year


def get_sum_expenses(expenses):
    '''
    returns sum of expenses
    '''
    sum_expenses = 0
    if expenses is not None:
        for exp in expenses:
            if exp['amt'] < 0:
                raise Exception("exp['amt'] < 0")
            else:
                sum_expenses = sum_expenses + exp['amt']                         
    return sum_expenses


def get_taxable_distribution(balance_start_taxable, ret_certain_inc_gap, nontaxable_distribution):
    '''
    returns taxable distribution given taxable account starting balance, retirement
    certain income gap, nontaxable distributions
    '''
    if balance_start_taxable > 0:
        return min(ret_certain_inc_gap - nontaxable_distribution, balance_start_taxable)
    else:
        return 0.


def get_years(dob, life_exp):
    '''
    retuns a list of the years between now and end of projection
    '''
    start_year = get_start_year()
    years = [i for i in range(start_year, start_year + get_years_to_project(dob, life_exp))]
    return years


def get_years_post(dob, desired_retirement_age, life_exp):
    '''
    retuns a list of the years between retirement ... and DEATH
    '''
    start_year = get_start_year()
    years = [i for i in range(start_year + get_pre_retirement_years(dob, desired_retirement_age), start_year + get_years_to_project(dob, life_exp))]
    return years


def get_years_pre(dob, desired_retirement_age, life_exp):
    '''
    retuns a list of the years between now and start of retirement
    '''
    start_year = get_start_year()
    years = [i for i in range(start_year, start_year + get_pre_retirement_years(dob, desired_retirement_age))]
    return years


def get_years_to_project(dob, life_exp):
    '''
    returns the number of years to be projected
    '''
    return round(math.ceil(life_exp) - get_age(dob)) # i.e. assume user dies at the start of the year of their life expectancy, rather than at the end


def get_zip_code(retirement_zip_code, residential_zip_code):
    '''
    Returns retirement_zip_code if not None, otherwise returns residential_zip_code
    '''
    if not retirement_zip_code:
        return residential_zip_code
    else:
        return retirement_zip_code


def show_inputs(dob,
            desired_retirement_age,
            life_exp,
            retirement_lifestyle,
            total_income,
            reverse_mort,
            house_value,
            desired_risk,
            filing_status,
            tax_transcript_data,
            plans,
            income_growth,
            employment_status,
            ss_fra_todays,
            paid_days,
            retirement_accounts,
            inflation_level,
            zip_code,
            expenses,
            btc):
    print("-----------------------------Retirement model INPUTS -------------------")
    print('dob:                         ' + str(dob))
    print('desired_retirement_age:      ' + str(desired_retirement_age))
    print('life_exp:                    ' + str(life_exp))
    print('retirement_lifestyle:        ' + str(retirement_lifestyle))
    print('total_income:                ' + str(total_income))
    print('reverse_mort:                ' + str(reverse_mort))
    print('house_value:                 ' + str(house_value))
    print('desired_risk:                ' + str(desired_risk))
    print('filing_status:               ' + str(filing_status))
    print('tax_transcript_data          ' + str(tax_transcript_data))
    print('plans:                       ' + str(plans))
    print('income_growth:               ' + str(income_growth))
    print('employment_status:           ' + str(employment_status))
    print('ss_fra_todays:               ' + str(ss_fra_todays))
    print('paid_days:                   ' + str(paid_days))
    print('zip_code:                    ' + str(zip_code))
    print('retirement_accounts:         ' + str(retirement_accounts))
    print('expenses:                    ' + str(expenses))
    print('btc:                         ' + str(btc))
    print("[Set self.debug=False to hide these]")


def validate_inputs(dob,
                     desired_retirement_age,
                     life_exp,
                     retirement_lifestyle,
                     total_income,
                     reverse_mort,
                     house_value,
                     desired_risk,
                     filing_status,
                     adj_gross_income,
                     total_payments,
                     taxable_income,
                     plans,
                     income_growth,
                     employment_status,
                     ss_fra_todays,
                     paid_days,
                     retirement_accounts,
                     inflation_level,
                     zip_code,
                     expenses,
                     btc):

    # Null checks
    if not dob:
        raise Exception('dob not provided')

    if not desired_retirement_age:
        raise Exception('desired_retirement_age not provided')

    if not life_exp:
        raise Exception('life_exp no provided')

    if not retirement_lifestyle:
        raise Exception('retirement_lifestyle not provided')

    if not inflation_level:
        raise Exception('inflation_level not provided')

    if not zip_code:
        raise Exception('state not provided')

    # other checks
    if life_exp < desired_retirement_age:
        raise Exception('life_exp less than desired_retirement_age')

    if retirement_lifestyle != 1 and retirement_lifestyle != 2 and retirement_lifestyle != 3 and retirement_lifestyle != 4:
        raise Exception('unhandled value of retirement_lifestyle')

    if desired_risk < 0 or desired_risk > 1:
        raise Exception('desired_risk outside 0 <= desired_risk <= 1')
        self.client = TestClient(regional_data,
                                 date_of_birth,
                                 home_value,
                                 civil_status,
                                 employment_status,
                                 ss_fra_todays)

        self.retirement_age = retirement_age
        self.lifestyle = lifestyle
        self.income = income
        self.reverse_mortgage = reverse_mortgage
        self.desired_risk = desired_risk
        self.income_growth = income_growth
        self.paid_days = paid_days
        self.retirement_postal_code = retirement_postal_code
        self.retirement_accounts = retirement_accounts
        self.expenses = expenses
        self.btc = btc

    if house_value < 0:
        raise Exception('house_value less than 0')

    if ss_fra_todays < 0:
        raise Exception('ss_fra_todays less than 0')

    if total_income < 0:
        raise Exception('total_income less than 0')

    if adj_gross_income < 0:
        raise Exception('adj_gross_income less than 0')

    if taxable_income < 0:
        raise Exception('taxable_income less than 0')

    if total_payments < 0:
        raise Exception('total_payments less than 0')

    if paid_days < 0:
        raise Exception('paid_days less than 0')

    if paid_days > 30:
        raise Exception('paid_days greater than 30 per month')

    if type(zip_code) != int:
        raise Exception("zip_code must be integer")
    '''
    if zip_code < 10000 or zip_code > 99999:
        raise Exception("zip_code not of correct form")
    '''


def validate_adj_gross_income(tot_inc, adj_gr_inc):
    '''
    adjusted_gross_income must be at least as large as total_income.
    returns adjusted_total_income at least as large as total income.
    '''
    return max(adj_gr_inc, tot_inc)

    

