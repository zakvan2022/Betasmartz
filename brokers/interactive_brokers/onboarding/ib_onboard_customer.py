from main import constants
from main import abstract

class IbOnboardCustomer(object):

    def __init__(self,
                 user,
                 plan,
                 region,
                 address,
                 ibaccount):


        self.country_of_birth = 'Spain'
        self.num_dependents = '17'
        self.residence_street_2 = ''
        self.phone_type = 'Home'
        self.phone_number = '916345678'
        self.identification_legal_residence_state = 'MADRID'
        self.identification_legal_citizenship = 'Spain'
        self.identification_legal_residence_country = 'Spain'
        self.identification_ssn = '1112223456'
        self.gender = 'M'
        self.employer = 'ABC Corp'
        self.occupation = 'Accounting' 
        self.employer_business = 'Accounting' 
        self.employer_address_state = 'MADRID' 
        self.employer_address_street_2 = '' 
        self.employer_address_postal_code = '28660' 
        self.employer_address_country = 'Spain' 
        self.employer_address_street_1 = '936 Calle Negro' 
        self.employer_address_city = 'Madrid' 
        self.employment_ownership = '0%' 
        self.employment_title = 'Jefe' 
        self.fin_info_tot_assets = '5'
        self.fin_info_liq_net_worth = '6'
        self.fin_info_ann_net_inc = '7'
        self.fin_info_net_worth = '8'
        self.asset_exp_0_knowledge = 'Limited'
        self.asset_exp_0_yrs  = '1'
        self.asset_exp_0_trds_per_yr = '1'
        self.asset_exp_1_knowledge = 'Limited'
        self.asset_exp_1_yrs = '2'
        self.asset_exp_1_trds_per_yr = '2'
        self.reg_status_broker_deal = 'false'
        self.reg_status_exch_memb = 'false'
        self.reg_status_disp = 'false'
        self.reg_status_investig = 'false'
        self.reg_status_stk_cont = 'false'
        self.tax_resid_0_country = 'Spain'
        self.tax_resid_0_tin_type = 'NonUS_NationalIID'
        self.tax_resid_0_tin = '1112223456' 
        self.doc_exec_ts = '20170309140030'
        self.doc_exec_login_ts = '20170309140000'
        self.signature = 'Juan Lopez'



