import logging
import pandas as pd
import numpy as np
import json
import math
from main import inflation
from main import us_tax
from main import tax_helpers as helpers
from main import test_tax_sheet as tst_tx
from main import abstract
from main import constants
from dateutil.relativedelta import relativedelta
from main import zip2state
from ssa import ssa as ssa
from rest_framework.exceptions import ValidationError
import pdb

logger = logging.getLogger('taxsheet')
inflation_level = inflation.inflation_level

NUM_US_RETIREMENT_ACCOUNT_TYPES = len(constants.US_RETIREMENT_ACCOUNT_TYPES)

class TaxUser(object):
    '''
    Contains a list of inputs and functions for Andrew's Excel tax sheet (Retirement Modelling v4.xlsx).
    '''
    def __init__(self,
                 plan,
                 life_exp,
                 is_partner,
                 plans):

        #initialize from single plan object
        if not is_partner:
            dob = plan.client.date_of_birth
            total_income = plan.income
            reverse_mort = plan.reverse_mortgage

        else:
            dob = plan.partner_data['dob']
            total_income = plan.partner_data['income']
            reverse_mort = False
            
        desired_retirement_age = plan.retirement_age
        retirement_lifestyle = plan.lifestyle
        house_value = plan.client.home_value
        desired_risk = plan.desired_risk
        filing_status = plan.client.civil_status
        tax_transcript_data = plan.client.regional_data.get('tax_transcript_data', None)
        income_growth = plan.income_growth
        employment_status = plan.client.employment_status
        ss_fra_todays = plan.client.ss_fra_todays
        paid_days = plan.paid_days
        retirement_accounts = plan.retirement_accounts

        if not plan.retirement_postal_code:
            try:
                zip_code = int(plan.client.residential_address.post_code)
            except:
                raise Exception("no valid zip code provided")
        else:
            zip_code = int(plan.retirement_postal_code)
            
        expenses = plan.expenses
        btc = plan.btc

        # show inputs
        self.debug = False
        if (self.debug):
            helpers.show_inputs(dob,
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
                             btc)

        adj_gross_income, total_payments, taxable_income = self.get_tax_transcript_data(tax_transcript_data)
        # adj_gross_income cannot be less than total_income
        adj_gross_income = helpers.validate_adj_gross_income(adj_gross_income, total_income)
  
        if not house_value:
            house_value = 0.
            
        if not ss_fra_todays:
            ss_fra_todays = 0.

        helpers.validate_inputs(dob,
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
                                 btc)
        '''
        set variables
        '''
        self.dob = dob
        self.desired_retirement_age = desired_retirement_age
        self.life_exp = life_exp
        self.retirement_lifestyle = retirement_lifestyle
        self.reverse_mort = reverse_mort
        self.house_value = house_value
        self.desired_risk = desired_risk
        self.filing_status = abstract.PersonalData.CivilStatus(filing_status)
        self.total_income = total_income
        self.taxable_income = taxable_income
        self.plans = plans
        self.total_payments = total_payments
        self.other_income = max(0, adj_gross_income - total_income)
        self.income_growth = income_growth/100.
        self.employment_status = constants.EMPLOYMENT_STATUSES[employment_status]
        self.ss_fra_todays = ss_fra_todays
        self.paid_days = paid_days
        self.retirement_accounts = retirement_accounts
        self.ira_rmd_factor = 26.5
        self.state = zip2state.get_state(zip_code)
        self.sum_expenses = helpers.get_sum_expenses(expenses)
        self.btc = btc # this is an ANNUAL quantity

        '''
        age
        '''
        self.age = helpers.get_age(self.dob)
        self.validate_age()
        '''
        retirememt period
        '''
        self.validate_life_exp_and_des_retire_age()
        self.pre_retirement_end = helpers.get_period_of_age(self.age, self.desired_retirement_age)  # i.e. last period in which TaxUser is younger than desired retirement age                                                                                  # NB this period has index self.pre_retirement_end - 1
        self.retirement_start = self.pre_retirement_end + 1                                 # i.e. first period in which TaxUser is older than desired retirement age                                                                                   # NB this period has index self.retirement_start - 1

        '''
        years
        '''
        self.start_year = helpers.get_start_year()
        self.years_to_project = helpers.get_years_to_project(self.dob, self.life_exp)
        self.retirement_years = helpers.get_retirement_years(self.life_exp, self.desired_retirement_age)
        self.pre_retirement_years = helpers.get_pre_retirement_years(self.dob, self.desired_retirement_age)
        self.years = helpers.get_years(self.dob, self.life_exp)
        self.years_pre = helpers.get_years_pre(self.dob, self.desired_retirement_age, self.life_exp)
        self.years_post = helpers.get_years_post(self.dob, self.desired_retirement_age, self.life_exp)

        '''
        remenant
        period to retirement may not be a whole number of years.
        'remenant' = periods representing this 'gap'
        '''
        self.remenant_periods = self.pre_retirement_end - (12 * len(self.years_pre))   
        self.remenant_start_index = (self.pre_retirement_years * 12) - 1 + 1 # i.e. we need the period AFTER the last pre-retirement period (so +1)
 
        '''
        rows
        '''
        self.total_rows = self.pre_retirement_end + (self.retirement_years * 12)
        
        '''
        annual inflation
        '''
        self.indices_for_inflation = [(11 + (i * 12)) for i in range(self.years_to_project)]
        if len(inflation_level) < self.indices_for_inflation[len(self.indices_for_inflation) - 1]:
            raise Exception("supplied inflation data does not cover the full period required")        
        self.annual_inflation = [sum(inflation_level[j*12:(j*12)+12])/12. for j in range(len(self.indices_for_inflation))]

        '''
        retirement_accounts
        '''
        self.init_balance, self.monthly_contrib_employee_base, self.monthly_contrib_employer_base = self.get_retirement_accounts()
        self.miscellaneous_base = helpers.get_miscellaneous_base(self.total_income, self.sum_expenses, self.monthly_contrib_employee_base)
        self.btc_factor = self.get_btc_factor(self.get_employee_monthly_contrib_monthly_view(), self.monthly_contrib_employee_base)

        '''
        dataframe indices
        '''
        self.dateind = helpers.get_retirement_model_projection_index(pd.Timestamp('today').date(), self.total_rows)
        self.dateind_pre = helpers.get_retirement_model_projection_index(pd.Timestamp('today').date(), self.pre_retirement_end)
        self.dateind_post = helpers.get_retirement_model_projection_index(self.dateind_pre[len(self.dateind_pre)-1], (self.total_rows - len(self.dateind_pre)))
        
        '''
        data frame
        '''
        self.maindf = pd.DataFrame(index=self.dateind)

                
    def create_maindf(self):
        '''
        create the main data frame
        '''
        self.maindf['Person_Age'] = [self.age + (1./12.)*(i+1) for i in range(self.total_rows)]

        # MONTHLY GROWTH RATE ASSUMPTIONS
        self.pre_proj_inc_growth_monthly = [self.income_growth/12. for i in range(self.pre_retirement_end)]
        self.post_proj_inc_growth_monthly = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.maindf['Proj_Inc_Growth_Monthly'] = self.set_full_series(self.pre_proj_inc_growth_monthly, self.post_proj_inc_growth_monthly)

        self.maindf['Proj_Inflation_Rate'] = helpers.get_inflator_to_period(self.total_rows)['Inflation_Rate']
        self.pre_proj_inflation_rate = [inflation_level[i]/12. for i in range(self.pre_retirement_end)] 
        self.post_proj_inflation_rate = [inflation_level[self.retirement_start + i]/12. for i in range(self.total_rows - self.pre_retirement_end)] 

        self.maindf['Portfolio_Return'] = self.maindf['Proj_Inflation_Rate'] + helpers.get_portfolio_return_above_cpi(self.desired_risk)/12.
        self.pre_portfolio_return = [inflation_level[i]/12. + helpers.get_portfolio_return_above_cpi(self.desired_risk)/12. for i in range(self.pre_retirement_end)]
        self.post_portfolio_return = [inflation_level[self.retirement_start + i]/12. + helpers.get_portfolio_return_above_cpi(self.desired_risk)/12.
                                      for i in range(self.total_rows - self.pre_retirement_end)]

        self.maindf['Retire_Work_Inc_Daily_Rate'] = [116*(1+self.income_growth/12.)**i for i in range(self.total_rows)]

        '''
        get the 'flators'
        '''
        self.pre_deflator = [0. for i in range(self.pre_retirement_end)]
        self.pre_deflator[self.pre_retirement_end - 1] = 1. * (1 - self.pre_proj_inflation_rate[self.pre_retirement_end - 1])                                                                                          
        for i in range (1, self.pre_retirement_end):
            self.pre_deflator[self.pre_retirement_end - 1 - i] = self.pre_deflator[self.pre_retirement_end - 1 - i + 1] * (1 - self.pre_proj_inflation_rate[self.pre_retirement_end - 1 - i])                                                                                         

        self.pre_inflator = [0. for i in range(self.pre_retirement_end)]
        self.pre_inflator[0] = 1. * (1 + self.pre_proj_inflation_rate[0])
        for i in range (1, self.pre_retirement_end):
            self.pre_inflator[i] = self.pre_inflator[i-1] * (1 + self.pre_proj_inflation_rate[i])

        self.post_inflator = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.post_inflator[0] = 1. * (1 + self.post_proj_inflation_rate[0])
        for i in range (1, self.total_rows - self.pre_retirement_end):
            self.post_inflator[i] = self.post_inflator[i - 1] * (1 + self.post_proj_inflation_rate[i])

        self.post_inflator_continuous = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.post_inflator_continuous[0] = self.pre_inflator[len(self.pre_inflator) -1] * (1 + self.post_proj_inflation_rate[0])
        for i in range (1, self.total_rows - self.pre_retirement_end):
            self.post_inflator_continuous[i] = self.post_inflator_continuous[i - 1] * (1 + self.post_proj_inflation_rate[i])
        
        self.maindf['Deflator'] = self.set_full_series(self.pre_deflator, [1. for i in range(self.total_rows - self.pre_retirement_end)])     # for pre-retirement
        self.maindf['Inflator'] = self.set_full_series([1. for i in range(self.pre_retirement_end)], self.post_inflator)                      # for post-retirement
        self.maindf['Flator'] = self.maindf['Deflator'] * self.maindf['Inflator']                                                             # deserves a pat on the back

        # INCOME RELATED - WORKING PERIOD
        '''
        get pre-retirement  income flator
        '''
        self.pre_df = pd.DataFrame(index=self.dateind_pre)
        self.pre_df['Inc_Growth_Monthly_Pre'] = self.maindf['Proj_Inc_Growth_Monthly'][0:self.pre_retirement_end]
        self.pre_df['Inc_Inflator_Pre'] = (1 + self.pre_df['Inc_Growth_Monthly_Pre']).cumprod()
        
        '''
        get pre-retirement inflation flator
        '''
        self.pre_df['Inf_Inflator_Pre'] = helpers.get_inflator_to_period(self.pre_retirement_end)['Inflator']

        self.pre_total_income = self.total_income/12. * self.pre_df['Inc_Inflator_Pre']
        self.post_total_income  = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.maindf['Total_Income'] = self.set_full_series(self.pre_total_income, self.post_total_income)
        
        self.pre_other_income = self.other_income/12. * self.pre_df['Inf_Inflator_Pre']
        self.post_other_income  = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.maindf['Other_Income'] = self.set_full_series(self.pre_other_income, self.post_other_income)                                

        self.maindf['Adj_Gross_Income'] = self.maindf['Total_Income'] + self.maindf['Other_Income']
        
        self.pre_fed_regular_tax = self.total_payments/12. * self.pre_df['Inf_Inflator_Pre']
        self.post_fed_regular_tax  = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        self.maindf['Fed_Regular_Tax_Est'] = self.set_full_series(self.pre_fed_regular_tax, self.post_fed_regular_tax)
        
        self.maindf['Fed_Taxable_Income'] = self.maindf['Adj_Gross_Income'] - self.maindf['Fed_Regular_Tax_Est']
        
        self.state_tax = us_tax.StateTax(self.state, self.filing_status, self.total_income)
        self.state_tax_after_credits = self.state_tax.get_state_tax()
        self.state_effective_rate_to_agi = self.state_tax_after_credits/self.total_income

        self.pre_state_tax_after_credits = self.state_tax_after_credits/12. * self.pre_df['Inf_Inflator_Pre']      
        self.post_state_tax_after_credits = [0. for i in range(self.total_rows - self.pre_retirement_end)]

        self.maindf['State_Tax_After_Credits'] = self.set_full_series(self.pre_state_tax_after_credits, self.post_state_tax_after_credits)
            
        self.maindf['After_Tax_Income_Est'] = self.maindf['Adj_Gross_Income'] - self.maindf['Fed_Regular_Tax_Est'] - self.maindf['State_Tax_After_Credits']
    
        fica_tx = us_tax.Fica(self.employment_status, self.total_income)
        self.fica_ss = fica_tx.get_for_ss()
        self.fica_medicare = fica_tx.get_for_medicare()
        self.fica = self.fica_ss + self.fica_medicare
        
        self.pre_fica = self.fica/12. * self.pre_df['Inf_Inflator_Pre']       
        self.post_fica = [0. for i in range(self.total_rows - self.pre_retirement_end)] 
        self.maindf['FICA'] = self.set_full_series(self.pre_fica, self.post_fica)

        self.maindf['Home_Value'] = self.house_value * (1+self.maindf['Proj_Inflation_Rate']).cumprod()

        # CERTAIN INCOME
        if self.retirement_lifestyle == 1:
            self.lifestyle_factor = 0.66

        elif self.retirement_lifestyle == 2:
            self.lifestyle_factor = 0.81

        elif self.retirement_lifestyle == 3:
            self.lifestyle_factor = 1

        elif self.retirement_lifestyle == 4:
            self.lifestyle_factor = 1.5

        self.pre_des_ret_inc_pre_tax = self.lifestyle_factor * self.maindf['Adj_Gross_Income'][0:self.pre_retirement_end]
        self.post_des_ret_inc_pre_tax = [self.pre_des_ret_inc_pre_tax[len(self.pre_des_ret_inc_pre_tax) - 1] for i in range(self.total_rows - self.pre_retirement_end)] 
        self.maindf['Des_Ret_Inc_Pre_Tax_Post_Nominal'] = self.set_full_series(self.pre_des_ret_inc_pre_tax, self.post_des_ret_inc_pre_tax)
        self.maindf['Des_Ret_Inc_Pre_Tax'] = self.maindf['Des_Ret_Inc_Pre_Tax_Post_Nominal'] * self.maindf['Inflator']

        '''
        use the 'flators'
        '''
        self.maindf['Soc_Sec_Benefit'] = helpers.get_ss_fra_future_dollars(self.ss_fra_todays, self.total_rows) * helpers.get_soc_sec_factor(self.desired_retirement_age)
        
        self.maindf['Soc_Sec_Ret_Ear_Tax_Exempt'] = self.maindf['Soc_Sec_Benefit']

        self.maindf['Nominal_Ret_Working_Inc'] = np.where(self.maindf['Person_Age'] < 80, self.maindf['Retire_Work_Inc_Daily_Rate'] * 4 * self.paid_days, 0)
        self.maindf['Ret_Working_Inc'] = self.maindf['Deflator'] * self.maindf['Nominal_Ret_Working_Inc']
        
        self.maindf['Nominal_Pension_Payments'] = [0. for i in range(self.total_rows)]
        self.maindf['Pension_Payments'] = self.maindf['Deflator'] * self.maindf['Nominal_Pension_Payments']

        self.maindf['Annuity_Payments'] = self.get_all_retirement_income()

        # REVERSE MORTGAGE
        if self.reverse_mort:
            self.post_reverse_mortgage = np.where(self.age > 0,
                                                        np.where(self.maindf['Total_Income'] == 0,
                                                                 np.where(self.maindf['Person_Age'] > 62,
                                                                          self.maindf['Home_Value'][self.retirement_start - 1] * (0.9/(self.retirement_years * 12.)),
                                                                          0),
                                                                 0),
                                                        0)[self.pre_retirement_end:]

        else:
            self.post_reverse_mortgage = [0. for i in range(self.total_rows - self.pre_retirement_end)]
            
        self.pre_reverse_mortgage = [self.post_reverse_mortgage[0] for i in range (self.pre_retirement_end)]
        self.maindf['Reverse_Mortgage_Nominal'] = self.set_full_series(self.pre_reverse_mortgage, self.post_reverse_mortgage)
        self.maindf['Reverse_Mortgage'] = self.maindf['Deflator'] * self.maindf['Reverse_Mortgage_Nominal']

        # INCOME GAP
        self.maindf['Certain_Ret_Inc'] = self.get_full_post_retirement_and_pre_deflated(self.maindf['Soc_Sec_Benefit']
                                                                                        + self.maindf['Ret_Working_Inc']
                                                                                        + self.maindf['Pension_Payments']
                                                                                        + self.maindf['Annuity_Payments']
                                                                                        + self.maindf['Reverse_Mortgage'])
                                      
        self.maindf['Ret_Certain_Inc_Gap'] = self.get_full_post_retirement_and_pre_deflated(np.where(self.maindf['Des_Ret_Inc_Pre_Tax']- self.maindf['Certain_Ret_Inc'] > 0. ,
                                                                                                     self.maindf['Des_Ret_Inc_Pre_Tax']- self.maindf['Certain_Ret_Inc'], 0. ))
        
        # ACCOUNTS
        self.maindf['Nontaxable_Accounts'] = 0
        self.maindf['All_Accounts_Pre'] = 0
        self.maindf['Taxable_Accounts'] = 0
        
        if self.retirement_accounts is not None:
            for acnt in self.retirement_accounts:
                k = helpers.get_retirement_account_index(acnt)
                self.maindf[str(k) + '_Employee'] = self.maindf['Total_Income'] * self.monthly_contrib_employee_base[k] * self.btc_factor
                self.maindf[str(k) + '_Employer'] = self.maindf['Total_Income'] * self.monthly_contrib_employer_base[k] * self.btc_factor
                pre_capital_growth, pre_balance = self.get_capital_growth_and_balance_series(self.pre_retirement_end, str(k), self.init_balance[k] )       
                post_balance = [0. for i in range(self.total_rows - self.pre_retirement_end)]
                post_capital_growth = [0. for i in range(self.total_rows - self.pre_retirement_end)]
                        
                self.maindf[str(k) + '_Capital_Growth'] = self.set_full_series(pre_capital_growth, post_capital_growth)
                self.maindf[str(k) + '_Balance'] = self.set_full_series(pre_balance, post_balance)
                self.maindf['All_Accounts_Pre'] = self.maindf['All_Accounts_Pre'] + self.maindf[str(k) + '_Balance']
 
        # FOLLOWING NEEDS RE-WRITE; VERY FRAGILE ... WHAT IF ORDER OF THE ACCOUNTS IN constants:US_RETIREMENT_ACCOUNT_TYPES IS CHANGED?
        self.maindf['Nontaxable_Accounts'] = 0

        if '9_Balance' in self.maindf:
            self.maindf['Nontaxable_Accounts'] = self.maindf['Nontaxable_Accounts'] + self.maindf['9_Balance']  # Ind Roth 401K

        if '19_Balance' in self.maindf:
            self.maindf['Nontaxable_Accounts'] = self.maindf['Nontaxable_Accounts'] + self.maindf['19_Balance'] # Roth IRA

        if '18_Balance' in self.maindf:
            self.maindf['Nontaxable_Accounts'] = self.maindf['Nontaxable_Accounts'] + self.maindf['18_Balance'] # Roth 401k

        self.maindf['Taxable_Accounts'] = self.maindf['All_Accounts_Pre'] - self.maindf['Nontaxable_Accounts']

        self.pre_zeros = [0. for i in range(self.pre_retirement_end)] 
        self.reqd_min_dist = []
        self.capital_growth_nontaxable = []
        self.capital_growth_taxable = []
        self.distribution_nontaxable = []
        self.distribution_taxable = []
        self.balance_nontaxable = []
        self.balance_taxable = []

        for i in range(0, self.total_rows - self.pre_retirement_end):
            start_balance_taxable = 0.
            start_balance_nontaxable = 0.
            
            if i == 0:
                start_balance_taxable = self.maindf['Taxable_Accounts'].iloc[self.pre_retirement_end - 1]
                start_balance_nontaxable = self.maindf['Nontaxable_Accounts'].iloc[self.pre_retirement_end - 1]
            else:
                start_balance_taxable = self.balance_taxable[len(self.balance_taxable)-1]
                start_balance_nontaxable = self.balance_nontaxable[len(self.balance_nontaxable)-1]
            
            rmd = helpers.get_reqd_min_distribution(self.maindf['Person_Age'].iloc[self.pre_retirement_end - 1 + i],
                                                                        start_balance_taxable,
                                                                        self.ira_rmd_factor)
            if rmd < 0.01:
                rmd = 0.
            self.reqd_min_dist.append(rmd)

            ag_nt = helpers.get_account_growth(start_balance_nontaxable, self.post_portfolio_return[i])
            if ag_nt < 0.01:
                ag_nt = 0.
            self.capital_growth_nontaxable.append(ag_nt)

            ag_t = helpers.get_account_growth(start_balance_taxable, self.post_portfolio_return[i])
            if ag_t < 0.01:
                ag_t = 0.
            self.capital_growth_taxable.append(ag_t)

            nt_d = helpers.get_nontaxable_distribution(self.maindf['Ret_Certain_Inc_Gap'].iloc[self.pre_retirement_end + i],
                                                       self.reqd_min_dist[len(self.reqd_min_dist)-1],
                                                       start_balance_nontaxable)
            if nt_d < 0.01:
                nt_d = 0.
            self.distribution_nontaxable.append(nt_d)
            
            t_d = helpers.get_taxable_distribution(start_balance_taxable,
                                                   self.maindf['Ret_Certain_Inc_Gap'].iloc[self.pre_retirement_end + i],
                                                   self.distribution_nontaxable[len(self.distribution_nontaxable)-1])
            if t_d < 0.01:
                t_d = 0.
            self.distribution_taxable.append(t_d)
            
            b_nt = helpers.get_account_balance(start_balance_nontaxable,
                                              self.capital_growth_nontaxable[len(self.capital_growth_nontaxable)-1],
                                              0.,
                                              self.distribution_nontaxable[len(self.distribution_nontaxable)-1])
            if b_nt < 0.01:
                b_nt = 0.
            self.balance_nontaxable.append(b_nt)
            
            b_t = helpers.get_account_balance(start_balance_taxable,
                                               self.capital_growth_taxable[len(self.capital_growth_taxable)-1],
                                               0.,
                                               self.distribution_taxable[len(self.distribution_taxable)-1])
            if b_t < 0.01:
                b_t = 0.
            self.balance_taxable.append(b_t)

        self.maindf['Reqd_Min_Dist'] = self.set_full_series(self.pre_zeros, self.reqd_min_dist)
        self.maindf['Capital_Growth_Nontaxable'] = self.set_full_series(self.pre_zeros, self.capital_growth_nontaxable)
        self.maindf['Capital_Growth_Taxable'] = self.set_full_series(self.pre_zeros, self.capital_growth_taxable)
        self.maindf['Tot_Nontaxable_Dist'] = self.set_full_series(self.pre_zeros, self.distribution_nontaxable)
        self.maindf['Tot_Taxable_Dist'] = self.set_full_series(self.pre_zeros, self.distribution_taxable)
        self.maindf['Balance_Nontaxable'] = self.set_full_series(self.pre_zeros, self.balance_nontaxable)
        self.maindf['Balance_Taxable'] = self.set_full_series(self.pre_zeros, self.balance_taxable)

        self.maindf['Taxable_Accounts'] = self.maindf['Taxable_Accounts'] + self.maindf['Balance_Taxable']
        
        self.maindf['Nontaxable_Accounts'] = self.maindf['Nontaxable_Accounts'] + self.maindf['Balance_Nontaxable']

        self.maindf['Taxable_And_Nontaxable_Accounts'] = self.maindf['Taxable_Accounts'] + self.maindf['Nontaxable_Accounts'] 

        self.maindf['Ret_Inc_Gap'] = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Ret_Certain_Inc_Gap']
                                                                                     - self.maindf['Tot_Nontaxable_Dist']
                                                                                     - self.maindf['Tot_Taxable_Dist'])
        
        # TRACK ACCOUNT BALANCES PER ACCOUNT TYPE
        account_proportion = {}
        if self.retirement_accounts is not None:
            for acnt in self.retirement_accounts:
                k = helpers.get_retirement_account_index(acnt)
                if k == 9 or k == 19 or k == 18:
                    account_proportion[str(k)] = helpers.get_account_proportion(self.pre_retirement_end - 1,
                                                                                      self.maindf[str(k) + '_Balance'],
                                                                                      self.maindf['Nontaxable_Accounts'])
                    multiplier = self.maindf['Balance_Nontaxable']
                    
                else:
                    account_proportion[str(k)] = helpers.get_account_proportion(self.pre_retirement_end - 1,
                                                                                      self.maindf[str(k) + '_Balance'],
                                                                                      self.maindf['Taxable_Accounts'])
                    multiplier = self.maindf['Balance_Taxable']
                self.maindf[str(k) + '_Balance'] = self.maindf[str(k) + '_Balance'] * account_proportion[str(k)]   

                # CALCULATION OF AFTER TAX INCOME
        self.maindf['Non_Taxable_Inc'] = self.maindf['Tot_Nontaxable_Dist'] + self.maindf['Reverse_Mortgage']
        
        self.maindf['Taxable_Soc_Sec'] = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Soc_Sec_Benefit']
                                                                                        + self.maindf['Ret_Working_Inc']
                                                                                        + self.maindf['Pension_Payments']
                                                                                        + self.maindf['Annuity_Payments']
                                                                                        + self.maindf['Tot_Taxable_Dist']
                                                                                        - self.maindf['Soc_Sec_Ret_Ear_Tax_Exempt'])

        self.maindf['Tot_Inc'] = self.get_full_post_retirement_and_pre_set_zero(self.maindf['Non_Taxable_Inc']
                                                                                + self.maindf['Tot_Taxable_Dist']
                                                                                + self.maindf['Annuity_Payments']
                                                                                + self.maindf['Pension_Payments']
                                                                                + self.maindf['Ret_Working_Inc']
                                                                                + self.maindf['Soc_Sec_Benefit'])

        self.taxable_inc_pre = (self.maindf['Soc_Sec_Benefit']
                                + self.maindf['Ret_Working_Inc']
                                + self.maindf['Pension_Payments']
                                + self.maindf['Annuity_Payments']
                                + self.maindf['Tot_Taxable_Dist'])[:self.pre_retirement_end]

        self.taxable_inc_post = (self.maindf['Taxable_Soc_Sec']
                                 + self.maindf['Ret_Working_Inc']
                                 + self.maindf['Pension_Payments']
                                 + self.maindf['Annuity_Payments']
                                 + self.maindf['Tot_Taxable_Dist'])[self.pre_retirement_end:]
        
        self.maindf['Taxable_Inc'] = self.set_full_series(self.taxable_inc_pre, self.taxable_inc_post)

        self.maindf['Adj_Gross_Inc'] = self.maindf['Tot_Inc']

        '''
        federal tax
        '''
        self.maindf['Fed_Taxable_Inc'] = self.set_full_series([0. for i in range(self.pre_retirement_end)], self.maindf['Taxable_Inc'][self.pre_retirement_end:])

        self.annual_taxable_income_pre = [self.maindf['Fed_Taxable_Income'][(i * 12)]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 1]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 2]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 3]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 4]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 5]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 6]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 7]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 8]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 9]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 10]
                                          + self.maindf['Fed_Taxable_Income'][(i * 12) + 11] for i in range(self.pre_retirement_years)]

        for i in range(self.remenant_periods):
            self.annual_taxable_income_pre = self.maindf['Fed_Taxable_Income'][self.remenant_start_index -1 + i]
        
        self.annual_taxable_income_post = [self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12)]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 1]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 2]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 3]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 4]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 5]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 6]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 7]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 8]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 9]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 10]
                                           + self.maindf['Taxable_Inc'][self.retirement_start - 1 + (i * 12) + 11] for i in range(self.retirement_years)]
       
        self.annual_taxable_income = self.set_full_series_with_indices(self.annual_taxable_income_pre,
                                                                       self.annual_taxable_income_post,
                                                                       self.years_pre,
                                                                       self.years_post)

        taxFed = us_tax.FederalTax(self.filing_status,
                                   self.years,
                                   self.annual_inflation,
                                   self.annual_taxable_income)
        taxFed.create_tax_engine()
        taxFed.create_tax_projected()

        self.annual_projected_tax = taxFed.tax_projected['Projected_Fed_Tax'] 
        self.post_projected_tax = pd.Series()
        
        for i in range(len(self.years_post)):
            self.post_projected_tax = self.post_projected_tax.append(pd.Series([self.annual_projected_tax.iloc[self.pre_retirement_years - 1  + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1  + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1  + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years- 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years- 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.,
                                                                                self.annual_projected_tax.iloc[self.pre_retirement_years - 1 + 1 + i]/12.],
                                                                               index = [self.dateind_post[i * 12],
                                                                               self.dateind_post[(i * 12) + 1],
                                                                               self.dateind_post[(i * 12) + 2],
                                                                               self.dateind_post[(i * 12) + 3],
                                                                               self.dateind_post[(i * 12) + 4],
                                                                               self.dateind_post[(i * 12) + 5],
                                                                               self.dateind_post[(i * 12) + 6],
                                                                               self.dateind_post[(i * 12) + 7],
                                                                               self.dateind_post[(i * 12) + 8],
                                                                               self.dateind_post[(i * 12) + 9],
                                                                               self.dateind_post[(i * 12) + 10],
                                                                               self.dateind_post[(i * 12) + 11]]))

        
        full_post = pd.Series(self.post_projected_tax, index=self.dateind_post) 
        self.maindf['Fed_Regular_Tax'] = self.set_full_series([0. for i in range(self.pre_retirement_end)], self.post_projected_tax )
        self.maindf['State_Tax_After_Credits'] = self.maindf['Adj_Gross_Inc'] * self.state_effective_rate_to_agi
        self.maindf['After_Tax_Income'] = self.maindf['Adj_Gross_Inc'] - self.maindf['Fed_Regular_Tax'] - self.maindf['State_Tax_After_Credits']

        # ACTUAL INCOME
        self.maindf['Actual_Inc'] = self.maindf['Total_Income'] + self.maindf['Tot_Inc']

        # DESIRED INCOME
        self.pre_0 = [0 for i in range(self.pre_retirement_end)]
        self.maindf['Desired_Inc'] = self.set_full_series(self.pre_0, self.post_des_ret_inc_pre_tax) * self.maindf['Inflator']

        # MONTHLY INPUTS FOR RETIRESMARTZ PLAN GRAPH
        self.income_actual_monthly = self.maindf['Actual_Inc']
        self.income_desired_monthly = self.maindf['Desired_Inc']
        self.taxable_assets_monthly = self.maindf['Taxable_Accounts']
        self.nontaxable_assets_monthly = self.maindf['Nontaxable_Accounts']

        # DEFLATION FACTOR AT RETIREMENT IN TODAYS
        self.deflation_factor_retirement_in_todays = helpers.get_inflator_to_period(self.retirement_start)['Inflator'][self.retirement_start - 1]

        # PROJECTED BALANCE AT RETIREMENT IN TODAYS
        self.proj_balance_at_retire_in_todays = self.maindf['Taxable_Accounts'][self.retirement_start]/self.deflation_factor_retirement_in_todays

        # PROJECTED INCOME ACTUAL AT RETIREMENT IN TODAYS
        self.proj_inc_actual_at_retire_in_todays = self.maindf['Tot_Inc'][self.retirement_start]/self.deflation_factor_retirement_in_todays

        # PROJECTED INCOME DESIRED AT RETIREMENT IN TODAYS
        self.proj_inc_desired_at_retire_in_todays = self.maindf['Desired_Inc'][self.retirement_start]/self.deflation_factor_retirement_in_todays

        # SAVINGS END DATE AS AGE 
        self.savings_end_date_as_age = self.get_savings_end_date_as_age()

        # SOA DOLLAR BILL PERCENTAGES CURRENT
        self.current_percent_soc_sec, self.current_percent_medicare, self.current_percent_fed_tax, self.current_percent_state_tax = self.get_soa_dollar_bill_percentages()

        # COMPONENTS OF TAXABLE INCOME
        self.annual_df = pd.DataFrame(index=self.years)
        
        self.annual_df['Non_Taxable_Inc'] = helpers.get_annual_sum(self.get_full_post_retirement_and_pre_set_zero(self.maindf['Non_Taxable_Inc']), self.years)
        self.annual_df['Tot_Taxable_Dist'] = helpers.get_annual_sum(self.get_full_post_retirement_and_pre_set_zero(self.maindf['Tot_Taxable_Dist']), self.years)
        self.annual_df['Annuity_Payments'] = helpers.get_annual_sum(self.get_full_post_retirement_and_pre_set_zero(self.maindf['Annuity_Payments']), self.years)
        self.annual_df['Pension_Payments'] = helpers.get_annual_sum(self.get_full_post_retirement_and_pre_set_zero(self.maindf['Pension_Payments']), self.years)
        self.annual_df['Ret_Working_Inc'] = helpers.get_annual_sum(self.get_full_post_retirement_and_pre_set_zero(self.maindf['Ret_Working_Inc']), self.years)
        self.annual_df['Soc_Sec_Benefit'] = helpers.get_annual_sum(self.get_full_post_retirement_and_pre_set_zero(self.maindf['Soc_Sec_Benefit']), self.years)

        self.non_taxable_inc = self.annual_df['Non_Taxable_Inc']
        self.tot_taxable_dist = self.annual_df['Tot_Taxable_Dist']
        self.annuity_payments = self.annual_df['Annuity_Payments']
        self.pension_payments = self.annual_df['Pension_Payments']
        self.ret_working_inc = self.annual_df['Ret_Working_Inc']
        self.soc_sec_benefit = self.annual_df['Soc_Sec_Benefit']

        # COMPONENTS OF ACCOUNTS
        self.annual_df['Taxable_Accounts'] = helpers.get_annual_year_end_value(self.get_full_post_retirement_and_pre_set_zero(self.maindf['Taxable_Accounts']), self.years)
        self.annual_df['Nontaxable_Accounts'] = helpers.get_annual_year_end_value(self.get_full_post_retirement_and_pre_set_zero(self.maindf['Nontaxable_Accounts']), self.years)
        
        self.taxable_accounts = self.annual_df['Taxable_Accounts']
        self.non_taxable_accounts = self.annual_df['Nontaxable_Accounts']

        # ... BY ACCOUNT TYPE

        self.accounts_401a = None
        self.accounts_401k = None
        self.accounts_403b = None
        self.accounts_403k = None
        self.accounts_409a = None
        self.accounts_457 = None
        self.accounts_esop = None
        self.accounts_gov = None
        self.accounts_ind_401k = None
        self.accounts_ind_roth_401k= None 
        self.accounts_ira = None
        self.accounts_mon_purch = None
        self.accounts_pay_deduct_ira = None 
        self.accounts_prof_sharing = None
        self.accounts_qual_annuity = None
        self.accounts_qual_np = None
        self.accounts_qual_np_roth = None
        self.accounts_priv_457 = None 
        self.accounts_roth_401k = None
        self.accounts_roth_ira = None  
        self.accounts_sarsep_ira = None
        self.accounts_sep_ira = None
        self.accounts_simple_ira = None
        self.accounts_tax_def_annuity = None
        
        if '0_Balance' in self.maindf:
            self.annual_df['401A'] = helpers.get_annual_year_end_value(self.maindf['0_Balance'], self.years)
            self.accounts_401a = self.annual_df['401A']

        if '1_Balance' in self.maindf:
            self.annual_df['401K'] = helpers.get_annual_year_end_value(self.maindf['1_Balance'], self.years)
            self.accounts_401k = self.annual_df['401K']

        if '2_Balance' in self.maindf:
            self.annual_df['403B'] = helpers.get_annual_year_end_value(self.maindf['2_Balance'], self.years)
            self.accounts_403b = self.annual_df['403B']
            
        if '3_Balance' in self.maindf:
            self.annual_df['403K'] = helpers.get_annual_year_end_value(self.maindf['3_Balance'], self.years)
            self.accounts_403k = self.annual_df['403K']

        if '4_Balance' in self.maindf:
            self.annual_df['409A'] = helpers.get_annual_year_end_value(self.maindf['4_Balance'], self.years)
            self.accounts_409a = self.annual_df['409A']

        if '5_Balance' in self.maindf:    
            self.annual_df['457'] = helpers.get_annual_year_end_value(self.maindf['5_Balance'], self.years)
            self.accounts_457 = self.annual_df['457']
            
        if '6_Balance' in self.maindf:
            self.annual_df['ESOP'] = helpers.get_annual_year_end_value(self.maindf['6_Balance'], self.years)
            self.accounts_esop = self.annual_df['ESOP']
            
        if '7_Balance' in self.maindf:
            self.annual_df['GOVERNMENTAL'] = helpers.get_annual_year_end_value(self.maindf['7_Balance'], self.years)
            self.accounts_gov = self.annual_df['GOVERNMENTAL']

        if '8_Balance' in self.maindf:
            self.annual_df['INDIVIDUAL401K'] = helpers.get_annual_year_end_value(self.maindf['8_Balance'], self.years)
            self.accounts_ind_401k = self.annual_df['INDIVIDUAL401K']
            
        if '9_Balance' in self.maindf:
            self.annual_df['INDROTH401K'] = helpers.get_annual_year_end_value(self.maindf['9_Balance'], self.years)
            self.accounts_ind_roth_401k = self.annual_df['INDROTH401K']
            
        if '10_Balance' in self.maindf:
            self.annual_df['IRA'] = helpers.get_annual_year_end_value(self.maindf['10_Balance'], self.years)
            self.accounts_ira = self.annual_df['IRA']
            
        if '11_Balance' in self.maindf:
            self.annual_df['MONEYPURCHASE'] = helpers.get_annual_year_end_value(self.maindf['11_Balance'], self.years)
            self.accounts_mon_purch = self.annual_df['MONEYPURCHASE']
            
        if '12_Balance' in self.maindf:
            self.annual_df['PAYROLLDEDUCTIRA'] = helpers.get_annual_year_end_value(self.maindf['12_Balance'], self.years)
            self.accounts_pay_deduct_ira = self.annual_df['PAYROLLDEDUCTIRA']
            
        if '13_Balance' in self.maindf:
            self.annual_df['PROFITSHARING'] = helpers.get_annual_year_end_value(self.maindf['13_Balance'], self.years)
            self.accounts_prof_sharing = self.annual_df['PROFITSHARING']

        if '14_Balance' in self.maindf:
            self.annual_df['QUALIFIEDANNUITY'] = helpers.get_annual_year_end_value(self.maindf['14_Balance'], self.years)
            self.accounts_qual_annuity = self.annual_df['QUALIFIEDANNUITY']

        if '15_Balance' in self.maindf:
            self.annual_df['QUALIFIEDNPPLAN'] = helpers.get_annual_year_end_value(self.maindf['15_Balance'], self.years)
            self.accounts_qual_np = self.annual_df['QUALIFIEDNPPLAN']

        if '16_Balance' in self.maindf:
            self.annual_df['QUALIFIEDNPROTHPLAN'] = helpers.get_annual_year_end_value(self.maindf['16_Balance'], self.years)
            self.accounts_qual_np_roth = self.annual_df['QUALIFIEDNPROTHPLAN']

        if '17_Balance' in self.maindf:
            self.annual_df['QUALIFIEDPRIV457PLAN'] = helpers.get_annual_year_end_value(self.maindf['17_Balance'], self.years)
            self.accounts_priv_457 = self.annual_df['QUALIFIEDPRIV457PLAN']
            
        if '18_Balance' in self.maindf:
            self.annual_df['ROTH401K'] = helpers.get_annual_year_end_value(self.maindf['18_Balance'], self.years)
            self.accounts_roth_401k = self.annual_df['ROTH401K']

        if '19_Balance' in self.maindf:
            self.annual_df['ROTHIRA'] = helpers.get_annual_year_end_value(self.maindf['19_Balance'], self.years)
            self.accounts_roth_ira = self.annual_df['ROTHIRA']

        if '20_Balance' in self.maindf:
            self.annual_df['SARSEPIRA'] = helpers.get_annual_year_end_value(self.maindf['20_Balance'], self.years)
            self.accounts_sarsep_ira = self.annual_df['SARSEPIRA']
            
        if '21_Balance' in self.maindf:
            self.annual_df['SEPIRA'] = helpers.get_annual_year_end_value(self.maindf['21_Balance'], self.years)
            self.accounts_sep_ira = self.annual_df['SEPIRA']
            
        if '22_Balance' in self.maindf:
            self.annual_df['SIMPLEIRA'] = helpers.get_annual_year_end_value(self.maindf['22_Balance'], self.years)
            self.accounts_simple_ira = self.annual_df['SIMPLEIRA']
            
        if '23_Balance' in self.maindf:
            self.annual_df['TAXDEFERRED_ANNUITY'] = helpers.get_annual_year_end_value(self.maindf['23_Balance'], self.years)
            self.accounts_tax_def_annuity = self.annual_df['TAXDEFERRED_ANNUITY']

        # REVERSE MORT
        self.house_value_at_retire_in_todays = self.maindf['Home_Value'][self.retirement_start]/self.deflation_factor_retirement_in_todays
        self.reverse_mort_pymnt_at_retire_in_todays = self.maindf['Reverse_Mortgage'][self.retirement_start]/self.deflation_factor_retirement_in_todays
        
        if(self.debug):
            self.show_outputs()
        

    def get_a_retirement_income(self, begin_date, amount):
        '''
        returns self.maindf['This_Annuity_Payments'] determined from retirement income.
        '''
        self.maindf['This_Annuity_Payments_Nominal'] = 0
        try:
            months_to_annuity_start = max(1, math.ceil(((pd.Timestamp(begin_date) - pd.Timestamp('today')).days) * (12./365.25)))
            if months_to_annuity_start > 0 and months_to_annuity_start < self.total_rows:
                pre_ret_inc = [0. for i in range(months_to_annuity_start)]
                post_ret_inc_nominal = [amount for i in range(self.total_rows - months_to_annuity_start)]
                dateind_pre_annuity = [pd.Timestamp('today').date() + relativedelta(months=1) + relativedelta(months=+i) for i in range(months_to_annuity_start)]
                dateind_post_annuity = [dateind_pre_annuity[len(dateind_pre_annuity)-1] + relativedelta(months=1) + relativedelta(months=+i) for i in range(self.total_rows - months_to_annuity_start)]
            return self.set_full_series_with_indices(pre_ret_inc, post_ret_inc_nominal, dateind_pre_annuity, dateind_post_annuity) * (1 + self.maindf['Proj_Inflation_Rate']).cumprod()
        except:
            return 0


    def get_all_retirement_income(self):
        '''
        returns self.maindf['Annuity_Payments'], the sum of all retirment incomes.
        '''
        self.maindf['All_Annuity_Payments'] = 0
        retirement_income_details = []
        retirement_income_details = self.get_retirement_income_details_from_plans()
        for detail in retirement_income_details:
            self.maindf['All_Annuity_Payments'] = self.get_a_retirement_income(detail[0], detail[1])
        return self.maindf['All_Annuity_Payments']


    def get_btc_factor(self, employee_monthly_contrib_monthly_view, monthly_contrib_employee_base):
        '''
        'btc factor' is multiplied by all retirement account contributions to incorporate effect of varying proportions in Monthly View pie chart. 
        '''
        if self.retirement_accounts is not None:
            contribs = 0
            for acnt in self.retirement_accounts:
                k = helpers.get_retirement_account_index(acnt)
                contribs = contribs + monthly_contrib_employee_base[k]
            if contribs > 0:
                btc_factor = employee_monthly_contrib_monthly_view/contribs
            else:
                btc_factor = 0
        return btc_factor


    def get_capital_growth_and_balance_series(self, period, account_type, starting_balance):
        '''
        returns capital growth and balance series over period for account_tyconstants.US_RETIREMENT_ACCOUNT_TYPEpe
        '''
        '''
        for now can't think of a more 'pythonic' way to do this next bit ... may need re-write ...
        '''
        balance = [starting_balance for i in range(period)]
        capital_growth = [0. for i in range(period)]
        for i in range(1, period):
            capital_growth[i] = self.maindf['Portfolio_Return'][i] * balance[i - 1]
            balance[i] = self.maindf[account_type + '_Employee'][i] + self.maindf[account_type + '_Employer'][i] + capital_growth[i] + balance[i - 1]
        return capital_growth, balance


    def get_employee_monthly_contrib_monthly_view(self):
        '''
        returns monthly contribution for employee based on monthly view pie chart
        '''
        # return max(0, (self.total_income/12. - self.sum_expenses - self.miscellaneous_base)/(self.total_income/12.))
        # NB - both following quantities are annual
        return (self.btc/self.total_income) 
    

    def get_full_post_retirement_and_pre_deflated(self, temp_df_column):
        '''
        returns data frame column having 'real' (c.f. 'nominal') vales, where post retirement is calculated
        from other columns, and pre-retirement is the deflated retirement value
        '''
        nominal_pre = [temp_df_column[self.pre_retirement_end - 1] for i in range(self.pre_retirement_end)]
        real_post = [temp_df_column[self.retirement_start - 1 + i] for i in range(self.total_rows - self.pre_retirement_end)]
        result = self.maindf['Deflator'] * self.set_full_series(nominal_pre, real_post)
        return result
    

    def get_full_post_retirement_and_pre_set_zero(self, temp_df_column):
        '''
        returns data frame column having 'real' (c.f. 'nominal') values, where post retirement is calculated
        from other columns, and pre-retirement is set to zero
        '''
        nominal_pre = [0. for i in range(self.pre_retirement_end)]
        real_post = [temp_df_column[self.retirement_start - 1 + i] for i in range(self.total_rows - self.pre_retirement_end)]
        result = self.set_full_series(nominal_pre, real_post)
        return result
    

    def get_full_pre_retirement_and_post_set_zero(self, temp_df_column):
        '''
        returns data frame column having 'real' (c.f. 'nominal') values, where pre retirement is calculated
        from other columns, and post-retirement is set to zero
        '''
        nominal_pre = [temp_df_column[self.pre_retirement_end - 1] for i in range(self.pre_retirement_end)]
        real_post = [0. for i in range(self.total_rows - self.pre_retirement_end)]
        result = self.set_full_series(nominal_pre, real_post)
        return result
    

    def set_full_series(self, series_pre, series_post):
        '''
        returns full series by appending pre-retirement and post-retirement series
        '''
        full_pre = pd.Series(series_pre, index=self.dateind_pre)
        full_post = pd.Series(series_post, index=self.dateind_post)
        result = full_pre.append(full_post)
        return result
            
    
    def get_retirement_accounts(self):
        '''
        returns lists of initial balances and monthly employee and employer contribution percentages, indexed according to constants.US_RETIREMENT_ACCOUNT_TYPES
        '''
        init_balance = [0. for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)]
        monthly_contrib_amt_employee = [0. for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)]
        employer_match_contributions = [0. for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)]
        employer_match_income = [0. for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)]
        
        if self.retirement_accounts is not None:
            for acnt in self.retirement_accounts:
                i = helpers.get_retirement_account_index(acnt)
                init_balance[i] = init_balance[i] + acnt['balance']

                if acnt['contrib_amt'] > 0:
                    if acnt['contrib_period'] == 'monthly':
                        monthly_contrib_amt_employee[i] = monthly_contrib_amt_employee[i] + acnt['contrib_amt']
                    else:
                        monthly_contrib_amt_employee[i] = monthly_contrib_amt_employee[i] + acnt['contrib_amt']/12.

                if acnt['employer_match_type'] == 'contributions':
                    employer_match_contributions[i] = employer_match_contributions[i] + acnt['employer_match']
                else:
                    employer_match_income[i] = employer_match_income[i] + acnt['employer_match']
                    
        monthly_contrib_employee_base = [(monthly_contrib_amt_employee[i]/(self.total_income/12.)) for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)]           
        monthly_contrib_employer_base = [(employer_match_income[i] + (employer_match_contributions[i] * monthly_contrib_employee_base[i])) for i in range(NUM_US_RETIREMENT_ACCOUNT_TYPES)] 
        return init_balance, monthly_contrib_employee_base, monthly_contrib_employer_base
        

    def get_retirement_income_details_from_plans(self):
        '''
        returns a list of tuples (begin_date, monthly amount) for each source of external_income in plans  
        '''
        external_income = []

        for plan in self.plans:
            try:
                if plan.external_income.all() != []:
                    begin_date = plan.external_income.all()[0].begin_date
                    amount = plan.external_income.all()[0].amount
                    detail = (begin_date, amount)
                    external_income.append(detail)
            except:
                if (self.debug):
                    print(str(plan) + " not of expected form")

        return external_income 


    def get_savings_end_date_as_period(self):
        '''
        returns period post retirement when taxable assets first deplete to zero
        '''
        for i in range(self.retirement_start, self.total_rows):
            if self.maindf['Taxable_Accounts'][i] == 0:
                return i
        return self.total_rows
                

    def get_savings_end_date_as_age(self):
        '''
        returns age post retirement when taxable assets first deplete to zero
        '''
        age = helpers.get_period_as_age(self.dob, self.get_savings_end_date_as_period())
        if age < self.desired_retirement_age:
            raise Exception('age < self.desired_retirement_age')
        return age


    def get_soa_dollar_bill_percentages(self):
        '''
        returns current day social security payment, medicare payment, federal income
        tax payment, and state income tax payment all as a percentrage of current income
        '''
        if not self.total_income:
            raise Exception('self.total_income is None')

        if self.total_income == 0:
            return 0, 0, 0, 0
            
        if not self.fica_ss \
           and (self.employment_status[0] != constants.EMPLOYMENT_STATUS_UNEMPLOYED \
                and self.employment_status[0] == constants.EMPLOYMENT_STATUS_RETIRED \
                and self.employment_status[0] == constants.EMPLOYMENT_STATUS_NOT_LABORFORCE):
            raise Exception('self.fica_ss is None')
        soc_sec_percent = self.fica_ss/self.total_income
        
        if not self.fica_medicare \
           and (self.employment_status[0] != constants.EMPLOYMENT_STATUS_UNEMPLOYED \
                and self.employment_status[0] == constants.EMPLOYMENT_STATUS_RETIRED \
                and self.employment_status[0] == constants.EMPLOYMENT_STATUS_NOT_LABORFORCE):
            raise Exception('self.fica_medicare is None')
        medicare_percent = self.fica_medicare/self.total_income
        
        fed_tax_percent = self.annual_projected_tax.iloc[0]/self.total_income

        # self.pre_state_tax_after_credits is a monthly figure
        state_tax_percent = (12 * self.pre_state_tax_after_credits.iloc[0])/self.total_income

        if soc_sec_percent + medicare_percent + fed_tax_percent + state_tax_percent <= 1:
            return soc_sec_percent, medicare_percent, fed_tax_percent, state_tax_percent

        else:
            raise Exception('soc_sec_percent + medicare_percent + fed_tax_percent + state_tax_percent > 1')
        return age
    

    def get_tax_transcript_data(self, tax_transcript_data):
        '''
        returns adj_gross_income, total_payments, taxable_income
        '''
        try:
            adj_gross_income = tax_transcript_data['adjusted_gross_income']
        except:
            adj_gross_income = 0

        try:
            total_payments = tax_transcript_data['total_payments']
        except:
            total_payments = 0

        try:
            taxable_income = tax_transcript_data['taxable_income']
        except:
            taxable_income = 0

        return adj_gross_income, total_payments, taxable_income


    def set_full_series_with_indices(self, series_pre, series_post, index_pre, index_post):
        '''
        returns full series by appending pre-retirement series (with index2) and post-retirement
        series (with index2) 
        '''       
        full_pre = pd.Series(series_pre, index_pre)
        full_post = pd.Series(series_post, index_post)
        result = full_pre.append(full_post)
        return result

    
    def show_outputs(self):
        
        self.check_acc_df = pd.DataFrame(index=self.dateind)
        self.check_inc_df = pd.DataFrame(index=self.dateind)
        
        self.check_acc_df['Person_Age'] = self.maindf['Person_Age']
        self.check_acc_df['Taxable_Accounts'] = self.maindf['Taxable_Accounts']
        self.check_acc_df['Nontaxable_Accounts'] = self.maindf['Nontaxable_Accounts']
        
        self.check_inc_df['Person_Age'] = self.maindf['Person_Age']
        self.check_inc_df['Actual_Inc'] = self.maindf['Actual_Inc']
        self.check_inc_df['Desired_Inc'] = self.maindf['Desired_Inc']
        self.check_inc_df['Ret_Certain_Inc_Gap'] = self.maindf['Ret_Certain_Inc_Gap']
        self.check_inc_df['Ret_Inc_Gap'] = self.maindf['Ret_Inc_Gap']
        self.check_inc_df['Reqd_Min_Dist'] = self.maindf['Reqd_Min_Dist']
        self.check_inc_df['Non_Taxable_Inc'] = self.maindf['Non_Taxable_Inc']
        self.check_inc_df['Tot_Taxable_Dist'] = self.maindf['Tot_Taxable_Dist']
        self.check_inc_df['Annuity_Payments'] = self.maindf['Annuity_Payments']
        self.check_inc_df['Pension_Payments'] = self.maindf['Pension_Payments']
        self.check_inc_df['Ret_Working_Inc'] = self.maindf['Ret_Working_Inc']
        self.check_inc_df['Soc_Sec_Benefit'] = self.maindf['Soc_Sec_Benefit']
        
        start = max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age) - 10)
        end = min(max(helpers.get_period_of_age(self.age, 71) , start + 1) ,self.total_rows)
        print("--------------------------------------ALL MONTHLY--------------------------------------------------")
        print(self.maindf)
        print("--------------------------------------Retirement projection OUTPUTS by row yr 1 -------------------")
        print(self.maindf.ix[0][0:30])
        print(self.maindf.ix[0][31:60])
        print(self.maindf.ix[0][61:90])
        print(self.maindf.ix[0][91:120])
        print("--------------------------------------Retirement projection OUTPUTS by row yr 2-------------------")
        print(self.maindf.ix[1][0:30])
        print(self.maindf.ix[1][31:60])
        print(self.maindf.ix[1][61:90])
        print(self.maindf.ix[1][91:120])
        print("--------------------------------------Retirement projection OUTPUTS by row @ pre-retirement-------------------")
        print(self.maindf.ix[max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age) - 2)][0:30])
        print(self.maindf.ix[max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age) - 2)][31:60])
        print(self.maindf.ix[max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age) - 2)][61:90])
        print(self.maindf.ix[max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age) - 2)][91:120])
        print("--------------------------------------Retirement projection OUTPUTS by row @ retirement-------------------")
        print(self.maindf.ix[max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age) - 1)][0:30])
        print(self.maindf.ix[max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age) - 1)][31:60])
        print(self.maindf.ix[max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age) - 1)][61:90])
        print(self.maindf.ix[max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age) - 1)][91:120])
        print("--------------------------------------Retirement projection OUTPUTS by row @ retirement + 1-------------------")
        print(self.maindf.ix[max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age))][0:30])
        print(self.maindf.ix[max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age))][31:60])
        print(self.maindf.ix[max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age))][61:90])
        print(self.maindf.ix[max(1, helpers.get_period_of_age(self.age, self.desired_retirement_age))][91:120])
        print()
        print("--------------------------------------Retirement model OUTPUTS -------------------")
        print("--------------------------------------At start - Taxable_Accounts ---------------------------")
        print(self.check_acc_df[:12])
        print("--------------------------------------At start - Income ---------------------------")
        print(self.check_inc_df[:12])
        print("--------------------------------------Taxable_Accounts ---------------------------")
        print(self.check_acc_df[start:end])
        print("--------------------------------------Income ---------------------------")
        print(self.check_inc_df[start:end])
        print("--------------------------------------Various ---------------------------")
        print('self.age:                    ' + str(self.age))
        print('self.savings_end_date_as_age:' + str(self.savings_end_date_as_age))
        print('self.current_percent_soc_sec ' + str(self.current_percent_soc_sec))
        print('self.current_percent_medicare' + str(self.current_percent_medicare))
        print('self.current_percent_fed_tax ' + str(self.current_percent_fed_tax))
        print('self.current_percent_state_tax:' + str(self.current_percent_state_tax))
        print('ss_fra_retirement:           ' + str(helpers.get_ss_benefit_future_dollars(self.ss_fra_todays, self.dob, self.desired_retirement_age)))
        print('self.get_employee_monthly_contrib_monthly_view():' + str(self.get_employee_monthly_contrib_monthly_view()))
        print('self.monthly_contrib_employee_base:' + str(self.monthly_contrib_employee_base))
        print('self.get_btc_factor(self.get_employee_monthly_contrib_monthly_view(), monthly_contrib_employee_base):' + str(self.get_btc_factor(self.get_employee_monthly_contrib_monthly_view(), self.monthly_contrib_employee_base)))
        print("--------------------------------------Annualized for SOA ---------------------------")
        print(self.annual_df)
        print("[Set self.debug=False to hide these]")
        print("")
            

    def validate_age(self):
        if self.age >= self.desired_retirement_age:
            raise Exception("age greater than or equal to desired retirement age")

        if self.age <= 0:
            raise Exception("age less than or equal to 0")


    def validate_life_exp_and_des_retire_age(self):
        if self.life_exp > 100:
            raise Exception("self.life_exp > 100")
            
        if self.life_exp < 65:
            raise Exception("self.life_exp < 65")
        '''
        model requires at least one period (i.e. one month) between retirement_age and life_expectancy
        '''
        if self.life_exp == self.desired_retirement_age:
            self.life_exp = self.life_exp + 1
