import pandas as pd
from main import abstract
from main import constants
from datetime import date
import pdb


# define the objects needed
class TestClient(object):
    
    def __init__(self,
                 regional_data,
                 date_of_birth,
                 home_value,
                 civil_status,
                 employment_status,
                 ss_fra_todays):
        
        self.regional_data = regional_data
        self.date_of_birth = date_of_birth
        self.home_value = home_value
        self.civil_status = civil_status
        self.employment_status = employment_status
        self.ss_fra_todays = ss_fra_todays

class TestPlan(object):
    
    def __init__(self,
                 regional_data,
                 date_of_birth,
                 home_value,
                 civil_status,
                 employment_status,
                 ss_fra_todays,
                 retirement_age,
                 lifestyle,
                 income,
                 reverse_mortgage,
                 desired_risk,
                 income_growth,
                 paid_days,
                 retirement_postal_code,
                 retirement_accounts,
                 expenses,
                 btc):

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

# first, the plan
retirement_age = 37
lifestyle = 1
income = 150000
reverse_mortgage = False
desired_risk = 0.07
income_growth = 5.0
paid_days = 0
retirement_postal_code = 90058

retirement_accounts = [{'contrib_amt': 487, 'id': 1, 'cat': 5, 'balance_efdt': '2017-03-30', 'employer_match_type': 'none', 'name': 'Test', 'acc_type': 5, 'contrib_period': 'monthly', 'balance': 1000, 'owner': 'self', 'employer_match': 0}]

expenses = [{'amt': 203.41666666666666, 'id': 11, 'cat': 11, 'desc': 'Savings', 'who': 'self'}, {'amt': 24.833333333333332, 'id': 13, 'cat': 13, 'desc': 'Tobacco', 'who': 'self'}, {'amt': 1440.1666666666667, 'id': 14, 'cat': 14, 'desc': 'Transportation', 'who': 'self'}, {'amt': 153.58333333333334, 'id': 15, 'cat': 15, 'desc': 'Miscellaneous', 'who': 'self'}, {'amt': 110.75, 'id': 1, 'cat': 1, 'desc': 'Alcoholic Beverage', 'who': 'self'}, {'amt': 354.1666666666667, 'id': 2, 'cat': 2, 'desc': 'Apparel & Services', 'who': 'self'}, {'amt': 172.83333333333334, 'id': 3, 'cat': 3, 'desc': 'Education', 'who': 'self'}, {'amt': 455.75, 'id': 4, 'cat': 4, 'desc': 'Entertainment', 'who': 'self'}, {'amt': 1110.75, 'id': 5, 'cat': 5, 'desc': 'Food', 'who': 'self'}, {'amt': 461.6666666666667, 'id': 6, 'cat': 6, 'desc': 'Healthcare', 'who': 'self'}, {'amt': 3111.3333333333335, 'id': 7, 'cat': 7, 'desc': 'Housing', 'who': 'self'}, {'amt': 1368.9166666666667, 'id': 8, 'cat': 8, 'desc': 'Insuarance, Pensions & Social Security', 'who': 'self'}, {'amt': 109.33333333333333, 'id': 9, 'cat': 9, 'desc': 'Personal Care', 'who': 'self'}, {'amt': 15.416666666666666, 'id': 10, 'cat': 10, 'desc': 'Reading', 'who': 'self'}, {'amt': 2478.25, 'id': 12, 'cat': 12, 'desc': 'Taxes', 'who': 'self'}]

btc = 5844

# second, the client
#regional_data =  {'tax_transcript_data' : {'se_tax': 0, 'total_tax': 0, 'SSN': '134-12-3413', 'std_deduction': 0, 'address': {'address2': '', 'post_code': '00001', 'state': 'USA', 'address1': '123 MAIN STREET', 'city': 'ANYWHERE'}, 'total_adjustments': 0, 'taxable_income': 0, 'combat_credit': 0, 'filing_status': 1, 'total_income': 0, 'earned_income_credit': 0, 'excess_ss_credit': 0, 'SSN_spouse': '123-45-6789\n987-65-4321', 'tentative_tax': 0, 'blind': False, 'exemption_amount': 0, 'add_child_tax_credit': 0, 'premium_tax_credit': 0, 'adjusted_gross_income': 1376, 'refundable_credit': 0, 'blind_spouse': False, 'total_credits': 0, 'name': 'THOMAS E TAXPAYER', 'total_payments': 0, 'tax_period': '2011-12-31', 'name_spouse': 'TAMARA B TAXPAYER', 'exemptions': 3}}
regional_data =  {'tax_transcript_data' : {'se_tax': 0, 'total_tax': 0, 'SSN': '134-12-3413', 'std_deduction': 0, 'address': {'address2': '', 'post_code': '00001', 'state': 'USA', 'address1': '123 MAIN STREET', 'city': 'ANYWHERE'}, 'total_adjustments': 0, 'taxable_income': 0, 'combat_credit': 0, 'filing_status': 1, 'total_income': 0, 'earned_income_credit': 0, 'excess_ss_credit': 0, 'SSN_spouse': '123-45-6789\n987-65-4321', 'tentative_tax': 0, 'blind': False, 'exemption_amount': 0, 'add_child_tax_credit': 0, 'premium_tax_credit': 0, 'adjusted_gross_income': 0, 'refundable_credit': 0, 'blind_spouse': False, 'total_credits': 0, 'name': 'THOMAS E TAXPAYER', 'total_payments': 0, 'tax_period': '2011-12-31', 'name_spouse': 'TAMARA B TAXPAYER', 'exemptions': 3}}


date_of_birth = pd.Timestamp('2016-09-28')
home_value = 100000.0
civil_status = abstract.PersonalData.CivilStatus['SINGLE'].value
employment_status = constants.EMPLOYMENT_STATUS_SELF_EMPLOYED
ss_fra_todays = 1000.0

# third, the rest
plans = []
life_exp = 80
is_partner = False

# now set up the plan
plan = TestPlan(regional_data,
                 date_of_birth,
                 home_value,
                 civil_status,
                 employment_status,
                 ss_fra_todays,
                 retirement_age,
                 lifestyle,
                 income,
                 reverse_mortgage,
                 desired_risk,
                 income_growth,
                 paid_days,
                 retirement_postal_code,
                 retirement_accounts,
                 expenses,
                 btc)

