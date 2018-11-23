import pandas as pd
import numpy as np
import json
from main import state_tax_engine
from main import tax_sheet
from main import abstract
from main import constants
 

class FederalTax(object):
    '''
    Model for projected federal tax calculation; based on 'Projected Federal Tax Calc' tab in 'Retirement Modelling v3.xlsx' 
    '''

    def __init__(self, filing_status, years, inflation, taxable_income):

        '''
        checks
        '''
        self.validate_inputs(filing_status, years, inflation, taxable_income)
            
        
        '''
        variables
        '''
        self.fed_tax_filing_status   = self.get_federal_tax_filing_status(filing_status)
        self.years                  = years
        self.inflation              = inflation
        self.taxable_income         = taxable_income

        
    def create_tax_engine(self):

        '''
        tax engine
        '''
        
        self.tax_bracket = [0., 0.1, 0.15, 0.25, 0.28, 0.33, 0.35, 0.396]

        self.tax_engine = pd.DataFrame(index=self.tax_bracket[1:])
        
        self.tax_engine['Bracket_Rate_Differential'] = [self.tax_bracket[i] - self.tax_bracket[i - 1] for i in range(1, len(self.tax_bracket))]
        
        self.tax_engine['Single']                        = [0.       , 9225.    , 37450.    , 90750.    , 189300.   , 411500.   , 413200.   ]
        self.tax_engine['Married_Fil_Joint']             = [0.       , 18450.   , 74900.    , 151200.   , 230450.   , 411500.   , 464850.   ]    
        self.tax_engine['Married_Fil_Sep']               = [0.       , 9225.    , 37450.    , 75600.    , 115225.   , 205750.   , 232425.   ]  
        self.tax_engine['Head_Of_House']                 = [0.       , 13150.   , 50200.    , 129600.   , 209850.   , 411500.   , 439000    ]   
        self.tax_engine['Qual_Widow_Dep_Child']          = [0.       , 18450.   , 74900.    , 151200.   , 230450.   , 411500.   , 464850    ]   
        self.tax_engine['Married_Fil_Sep_Live_Apart']    = [0.       , 9225.    , 37450.    , 90750.    , 189300.   , 411500.   , 413200.   ]   

        self.stand_deduct = {'Single':                      6300. ,
                             'Married_Fil_Joint':           12600. ,
                             'Married_Fil_Sep':             6300. ,
                             'Head_Of_House':               9250. ,
                             'Qual_Widow_Dep_Child':        12600. ,
                             'Married_Fil_Sep_Live_Apart':  6300. }


    def get_federal_tax_filing_status(self, filing_status):
        '''
        returns one of 'Single', 'Married_Fil_Joint', 'Married_Fil_Sep', 'Head_Of_House', 'Qual_Widow_Dep_Child',
        'Married_Fil_Sep_Live_Apart' (or raising exception) depending on filing_status
        '''
        if filing_status == abstract.PersonalData.CivilStatus['SINGLE']:
            return 'Single'

        elif filing_status == abstract.PersonalData.CivilStatus['MARRIED_FILING_SEPARATELY_LIVED_TOGETHER']:
            return 'Married_Fil_Sep'

        elif filing_status == abstract.PersonalData.CivilStatus['MARRIED_FILING_SEPARATELY_NOT_LIVED_TOGETHER']:
            return 'Married_Fil_Sep_Live_Apart'

        elif filing_status == abstract.PersonalData.CivilStatus['HEAD_OF_HOUSEHOLD']:
            return 'Head_Of_House'
              
        elif filing_status == abstract.PersonalData.CivilStatus['QUALIFYING_WIDOWER']:
            return 'Qual_Widow_Dep_Child'

        elif filing_status == abstract.PersonalData.CivilStatus['MARRIED_FILING_JOINTLY']:
            return 'Married_Fil_Joint'

        else:
            raise Exception('filing_status not handled')


    def get_federal_tax(self, inflation, income):
        '''
        returns federal tax for given income, inflation amd fed tax filing status 
        '''
        # Names could be improved ... am not familiar with the correct tax terminology
        # also, deductions are not included in calculation ...
        self.tax_engine['Is_Greater_Than'] = np.where(float(income) > (self.tax_engine[self.fed_tax_filing_status]  * (1 + inflation)), 1, 0)
        self.tax_engine['Excess'] = income - self.tax_engine[self.fed_tax_filing_status]  * (1 + inflation)
        self.tax_engine['Bracket_Component'] = self.tax_engine['Bracket_Rate_Differential'] * self.tax_engine['Excess'] * self.tax_engine['Is_Greater_Than']
        result = self.tax_engine['Bracket_Component'].sum()
        return result
    

    def create_tax_projected(self):
        '''
        projected federal tax
        '''
        self.tax_projected = pd.DataFrame(index = self.years)
        self.tax_projected['Ann_Avg_Inflation'] = self.inflation
        self.tax_projected['Annual_Taxable_Income'] = self.taxable_income

        self.tax_projected['Projected_Fed_Tax'] = [self.get_federal_tax(self.tax_projected['Ann_Avg_Inflation'].iloc[j],
                                                                    self.tax_projected['Annual_Taxable_Income'].iloc[j]) for j in range(len(self.years))]


    def validate_inputs(self, filing_status, years, inflation, taxable_income):

        if not years:
            raise Exception('years not provided')

        if not inflation:
            raise Exception('inflation not provided')

        if len(years) == 0:
            raise Exception('length of years is zero')

        if len(inflation) == 0:
            raise Exception('length of inflation is zero')

        if len(taxable_income) == 0:
            raise Exception('length of taxable_income is zero')
        
        if len(inflation) != len(years):
            raise Exception('len(inflation) != len(years)')
        
        if len(taxable_income) != len(years):
            raise Exception('len(taxable_income) != len(years)')
        

tax_engine = []
class StateTax(object):

    '''
    Most individual U.S. states collect a state income tax in addition to federal income tax.
    The two are separate entities. State income tax is imposed at a fixed or graduated rate on
    taxable income of individuals. The rates vary by state. Taxable income conforms closely to
    federal taxable income in most states, with limited modifications. Many states allow a standard
    deduction or some form of itemized deductions. 
    '''


    def __init__(self, state, filing_status, income):

        self.validate_inputs(state, filing_status, income)

        self.state = state
        self.filing_status = filing_status
        self.income = income


    def get_state_tax(self):
        '''
        return state tax for given state, income and filing_status
        '''
        tax_engine = self.get_tax_engine()
        idx = self.get_index(tax_engine)
        df = pd.DataFrame(index=idx)
        df['Rate'] = self.get_rates(tax_engine)
        df['Bracket'] = self.get_brackets(tax_engine)  
        df['Excess'] = [0. for i in range(len(idx))]
        try:
            if len(tax_engine) != 2 or tax_engine[0] != 'rate':
                for i in range(1, len(idx)):
                    if self.income > df['Bracket'].iloc[i]:
                        df['Excess'].iloc[i-1] = df['Bracket'].iloc[i] - df['Bracket'].iloc[i - 1]
                    else:
                        df['Excess'].iloc[i-1] = max(self.income - df['Bracket'].iloc[i-1], 0)
                        
        except KeyError as e:
            df['Excess'].iloc[0] = max(self.income, 0)

        # Names could be improved ... am not familiar with the correct tax terminology
        # also, deductions are not included in calculation ...
        df['Is_Greater_Than'] = np.where(float(self.income) > df['Bracket'], 1, 0)
        df['Bracket_Component'] = df['Rate'] * df['Excess'] * df['Is_Greater_Than']
        result = df['Bracket_Component'].sum()
        return result


    def get_tax_engine(self):
        '''
        sets json with tax_engine for state and filing status
        '''
        found = False
        for i in range(len(state_tax_engine.tax_engine)):
            json_st_tx = json.loads(state_tax_engine.tax_engine[i])
            if json_st_tx['state'] == self.state:
                json_state_tax = json_st_tx
                found = True

        if found:
            return json_state_tax[self.get_state_tax_filing_status()]

        else:
            raise Exception('state not handled')


    def get_index(self, tx_eng):
        '''
        returns index for rates and brackets for state and filing status
        '''
        try:
            if len(tx_eng) != 2 or tx_eng[0] != 'rate':
                result = [i for i in range(len(tx_eng))]
        except KeyError as e:
                result = [0,]
        return result
    
    
    def get_rates(self, tx_eng):
        '''
        returns list with rates for state and filing status
        '''
        try:
            if len(tx_eng) != 2 or tx_eng[0] != 'rate':
                result = [tx_eng[i]["rate"] for i in range(len(tx_eng))]
        except KeyError as e:
                result = [tx_eng["rate"]]
        return result


    def get_brackets(self, tx_eng):
        '''
        returns list with brackets for state and filing status
        '''
        try:
            if len(tx_eng) != 2 or tx_eng[0] != 'rate':
                result = [tx_eng[i]["bracket"] for i in range(len(tx_eng))]
        except KeyError as e:
                result = [tx_eng["bracket"]]
        return result
    

    def get_state_tax_filing_status(self):
        '''
        returns either 'Single' or 'Married_Filing_Joint' (or raises exception) based on overloaded filing_status 
        '''
        if self.filing_status == abstract.PersonalData.CivilStatus['SINGLE']:
            return 'Single'

        elif self.filing_status == abstract.PersonalData.CivilStatus['MARRIED_FILING_SEPARATELY_LIVED_TOGETHER']:
            return 'Single'

        elif self.filing_status == abstract.PersonalData.CivilStatus['MARRIED_FILING_SEPARATELY_NOT_LIVED_TOGETHER']:
            return 'Single'

        elif self.filing_status == abstract.PersonalData.CivilStatus['HEAD_OF_HOUSEHOLD']:
            return 'Single'

        elif self.filing_status == abstract.PersonalData.CivilStatus['QUALIFYING_WIDOWER']:
            return 'Single'

        elif self.filing_status == abstract.PersonalData.CivilStatus['MARRIED_FILING_JOINTLY']:
            return 'Married Filing Jointly'

        else:
            raise Exception('filing_status not handled')
        

    def validate_inputs(self, state, filing_status, income):

        if not state:
            raise Exception('state not provided')

        if len(state) != 2:
            raise Exception('state does not have two characters, so not of correct format for US states')
        
        if income < 0:
            raise Exception('income < 0')

FICA_RATE_SS_EMPLOYED = 0.062
FICA_RATE_SS_SELF_EMPLOYED = 0.124
FICA_RATE_MEDICARE_EMPLOYED = 0.0145
FICA_RATE_MEDICARE_SELF_EMPLOYED = 0.029
FICA_INC_CEILING_SS = 118500.

class Fica(object):

    '''
    Federal Insurance Contributions Act (FICA) tax is a United States
    federal payroll (or employment) tax imposed on both employees and employers
    to fund Social Security and Medicare
    '''


    def __init__(self, employment_status, total_income):

        self.validate_inputs(employment_status, total_income)

        self.employment_status = employment_status
        self.total_income = total_income



    def get_fica(self):
        '''
        FICA = Social Security contribution + Medicare con
        '''

        result = self.get_for_ss() + self.get_for_medicare()

        return result
    

    def get_for_ss(self):
        
        if self.employment_status[0] == constants.EMPLOYMENT_STATUS_EMMPLOYED:
            '''
            For social security = IF employment_status is employed then multiply wages,
            salaries, tips etc (Line 7 of Form 1040) up to a maximum amount of $118,500
            by 6.2%
            '''
            
            result = min(self.total_income, FICA_INC_CEILING_SS) * FICA_RATE_SS_EMPLOYED
            

        elif self.employment_status[0] == constants.EMPLOYMENT_STATUS_SELF_EMPLOYED:
            '''
            For social security = IF employment_status is self employed then multiply
            business income (Line 12 of Form 1040) less SE_tax  (Line 57 of Form 1040)
            up to a maximum amount of $118,500 by 12.4%
            '''            
            # NB - assuming here that 'business income (Line 12 of Form 1040) less SE_tax
            # (Line 57 of Form 1040)' is equal to total_income
            
            result = min(self.total_income, FICA_INC_CEILING_SS) * FICA_RATE_SS_SELF_EMPLOYED

        elif self.employment_status[0] == constants.EMPLOYMENT_STATUS_UNEMPLOYED:
            result = 0

        elif self.employment_status[0] == constants.EMPLOYMENT_STATUS_RETIRED:
            result = 0

        elif self.employment_status[0] == constants.EMPLOYMENT_STATUS_NOT_LABORFORCE:
            result = 0

        else: 
            raise Exception('employment_status not handled')

        return result


    def get_for_medicare(self):

        if self.employment_status[0] == constants.EMPLOYMENT_STATUS_EMMPLOYED:
            '''
            For medicare = IF employment_status is employed then multiply wages, salaries,
            tips etc (Line 7 of Form 1040)  by 1.45%F
            '''
            
            result = self.total_income * FICA_RATE_MEDICARE_EMPLOYED
            

        elif self.employment_status[0] == constants.EMPLOYMENT_STATUS_SELF_EMPLOYED:
            '''
            For medicare = IF employment_status is self employed then multiply business
            income (Line 12 of Form 1040) less SE_tax  (Line 57 of Form 1040) by 2.9%
            '''
            # NB - assuming here that 'business income (Line 12 of Form 1040) less SE_tax
            # (Line 57 of Form 1040)' is equal to total_income
            
            result = self.total_income * FICA_RATE_MEDICARE_SELF_EMPLOYED

        elif self.employment_status[0] == constants.EMPLOYMENT_STATUS_UNEMPLOYED:
            result = 0

        elif self.employment_status[0] == constants.EMPLOYMENT_STATUS_RETIRED:
            result = 0

        elif self.employment_status[0] == constants.EMPLOYMENT_STATUS_NOT_LABORFORCE:
            result = 0

        else: 
            raise Exception('employment_status not handled')

        return result


    def validate_inputs(self, employment_status, total_income):

        if not total_income:
            raise Exception('total_income not provided')
        
        if total_income < 0:
            raise Exception('total_income < 0')








