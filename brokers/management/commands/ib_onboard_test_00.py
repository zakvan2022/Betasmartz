from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        '''
        runs test of IB onboarding, i.e. creates xml files, zips it, encrypts
        it and posts it to IB FTP site
        '''

        from brokers.interactive_brokers.onboarding import onboarding as onb
        from brokers.interactive_brokers.onboarding import onboarding_helpers as onb_help
        from main.constants import ACCOUNT_TYPE_PERSONAL, ACCOUNT_TYPE_JOINT, ACCOUNT_TYPE_TRUST, JOINT_ACCOUNT_TYPE_JOINT_TENANTS, \
             OCCUPATION_TYPES, INDUSTRY_TYPES
        from brokers.interactive_brokers.onboarding.constants import IB_EMPLOY_STATUSES, SOURCE_OF_FUNDS_TYPES, \
             IB_EMPLOY_STAT_AT_HOME_TRADER, SOURCE_OF_FUNDS_TYPE_CONSULTING, SOURCE_OF_FUNDS_TYPE_INHERITANCE
        from main import abstract
        import pandas as pd
        import pdb
        import os
        import datetime

        class TestIBOnboard(object):

            def __init__ (self,
                          client,
                          account_number,
                          account_type,
                          asset_exp_0_knowledge,
                          asset_exp_0_trds_per_yr,
                          asset_exp_0_yrs,
                          asset_exp_1_knowledge,
                          asset_exp_1_trds_per_yr,
                          asset_exp_1_yrs,
                          country_of_birth,
                          date_of_birth,
                          doc_exec_login_ts,
                          doc_exec_ts,
                          signature,
                          employer_address,
                          fin_info_ann_net_inc,
                          fin_info_liq_net_worth,
                          fin_info_net_worth,
                          fin_info_tot_assets,
                          ib_employment_status,
                          identif_leg_citizenship,
                          identif_ssn,
                          joint_type,
                          num_dependents,
                          other_income_source,
                          phone_type,
                          reg_status_broker_deal,
                          reg_status_disp,
                          reg_status_exch_memb,
                          reg_status_investig,
                          reg_status_stk_cont,
                          residential_address,
                          salutation,
                          suffix,
                          tax_address,
                          tax_resid_0_tin,
                          tax_resid_0_tin_type):

                self.client = client
                self.account_number=account_number
                self.account_type=account_type
                self.asset_exp_0_knowledge = asset_exp_0_knowledge
                self.asset_exp_0_trds_per_yr = asset_exp_0_trds_per_yr
                self.asset_exp_0_yrs = asset_exp_0_yrs
                self.asset_exp_1_knowledge = asset_exp_1_knowledge
                self.asset_exp_1_trds_per_yr = asset_exp_1_trds_per_yr
                self.asset_exp_1_yrs = asset_exp_1_yrs
                self.country_of_birth = country_of_birth
                self.date_of_birth = date_of_birth
                self.doc_exec_login_ts = doc_exec_login_ts
                self.doc_exec_ts = doc_exec_ts
                self.signature = signature
                self.employer_address = employer_address
                self.fin_info_ann_net_inc = fin_info_ann_net_inc
                self.fin_info_liq_net_worth = fin_info_liq_net_worth
                self.fin_info_net_worth = fin_info_net_worth
                self.fin_info_tot_assets = fin_info_tot_assets
                self.ib_employment_status = ib_employment_status
                self.identif_leg_citizenship = identif_leg_citizenship
                self.identif_ssn = identif_ssn
                self.joint_type = joint_type
                self.num_dependents = num_dependents
                self.other_income_source = other_income_source
                self.phone_type = phone_type
                self.reg_status_broker_deal = reg_status_broker_deal
                self.reg_status_disp =reg_status_disp
                self.reg_status_exch_memb = reg_status_exch_memb
                self.reg_status_investig = reg_status_investig
                self.reg_status_stk_cont = reg_status_stk_cont
                self.residential_address = residential_address
                self.salutation = salutation
                self.suffix = suffix
                self.tax_address = tax_address
                self.tax_resid_0_tin = tax_resid_0_tin
                self.tax_resid_0_tin_type = tax_resid_0_tin_type

        class TestRegion(object):

            def __init__ (self,
                          code,
                          country):

                self.code = code
                self.country = country

        class TestAddress(object):

            def __init__ (self,
                          address1,
                          address2,
                          city,
                          region,
                          post_code):

                self.address1 = address1
                self.address2 = address2
                self.city = city
                self.region = region
                self.post_code = post_code

        class TestClient(object):

            class TestUser(object):

                def __init__(self,
                             email,
                             first_name,
                             last_name):

                    self.email = email
                    self.first_name = first_name
                    self.last_name = last_name

            def __init__ (self,
                          civil_status,
                          email,
                          employer,
                          first_name,
                          gender,
                          id,
                          income,
                          industry_sector,
                          last_name,
                          occupation,
                          other_income,
                          phone_num):

                self.civil_status = civil_status
                self.employer = employer
                self.gender = gender
                self.id = id
                self.income = income
                self.industry_sector=industry_sector
                self.occupation = occupation
                self.other_income = other_income
                self.phone_num = phone_number
                self.user = self.TestUser(email=email,
                                         first_name=first_name,
                                         last_name=last_name)

        class TestIBTrustOnboard(object):

            def __init__ (self,
                          client,
                          account_number,
                          account_type,
                          trst_third_party_mgmt,
                          trst_type_of_trust,
                          trst_date_formed,
                          trst_name,
                          trst_reg_num,
                          trst_reg_type,
                          trst_same_mail_address,
                          trst_address,
                          trst_reg_country,
                          trst_form_state,
                          trst_form_country,
                          fin_info_ann_net_inc,
                          fin_info_liq_net_worth,
                          fin_info_net_worth,
                          fin_info_tot_assets,
                          asset_exp_0_trds_per_yr,
                          asset_exp_0_yrs,
                          asset_exp_0_knowledge,
                          asset_exp_1_trds_per_yr,
                          asset_exp_1_yrs,
                          asset_exp_1_knowledge,
                          source_inc_percentage,
                          source_inc_type,
                          reg_status_affil,
                          reg_status_memb,
                          reg_status_disp,
                          reg_status_investig,
                          reg_status_stk_cont,
                          reg_status_ib_accounts,
                          reg_status_criminal,
                          reg_status_reg_control,
                          reg_status_broker_deal,
                          reg_status_exch_memb,
                          trustee_same_address,
                          trustee_address,
                          trustee_ext_id,
                          trustee_last_name,
                          trustee_first_name,
                          trustee_salutation,
                          trustee_date_of_birth,
                          trustee_phone,
                          trustee_email,
                          trustee_occupation,
                          trustee_employee_title,
                          trustee_is_nfa_reg,
                          trustee_citizenship,
                          trustee_ssn,
                          trustee_leg_res_country,
                          trustee_leg_res_state,
                          trustee_issuing_country,
                          benef_same_address,
                          benef_address,
                          benef_ext_id,
                          benef_last_name,
                          benef_first_name,
                          benef_salutation,
                          grantors_same_address,
                          grantors_address,
                          grantors_ext_id,
                          grantors_last_name,
                          grantors_first_name,
                          grantors_salutation,
                          grantors_date_of_birth,
                          grantors_citizenship,
                          grantors_ssn,
                          grantors_leg_res_country,
                          grantors_leg_res_state,
                          grantors_issuing_country,
                          tax_address,
                          tax_resid_0_tin,
                          tax_resid_0_tin_type,
                          doc_exec_login_ts,
                          doc_exec_ts,
                          signature):

                self.client = client
                self.account_number = account_number
                self.account_type = account_type
                self.trst_third_party_mgmt = trst_third_party_mgmt
                self.trst_type_of_trust = trst_type_of_trust
                self.trst_date_formed = trst_date_formed
                self.trst_name = trst_name
                self.trst_reg_num = trst_reg_num
                self.trst_reg_type = trst_reg_type
                self.trst_same_mail_address = trst_same_mail_address
                self.trst_address = trst_address
                self.trst_reg_country = trst_reg_country
                self.trst_form_state = trst_form_state
                self.trst_form_country = trst_form_country
                self.fin_info_ann_net_inc = fin_info_ann_net_inc
                self.fin_info_liq_net_worth = fin_info_liq_net_worth
                self.fin_info_net_worth = fin_info_net_worth
                self.fin_info_tot_assets = fin_info_tot_assets
                self.asset_exp_0_trds_per_yr = asset_exp_0_trds_per_yr
                self.asset_exp_0_yrs = asset_exp_0_yrs
                self.asset_exp_0_knowledge = asset_exp_0_knowledge
                self.asset_exp_1_trds_per_yr = asset_exp_1_trds_per_yr
                self.asset_exp_1_yrs = asset_exp_1_yrs
                self.asset_exp_1_knowledge = asset_exp_1_knowledge
                self.source_inc_percentage = source_inc_percentage
                self.source_inc_type = source_inc_type
                self.reg_status_affil = reg_status_affil
                self.reg_status_memb = reg_status_memb
                self.reg_status_disp = reg_status_disp
                self.reg_status_investig = reg_status_investig
                self.reg_status_stk_cont = reg_status_stk_cont
                self.reg_status_ib_accounts = reg_status_ib_accounts
                self.reg_status_criminal = reg_status_criminal
                self.reg_status_reg_control = reg_status_reg_control
                self.reg_status_broker_deal = reg_status_broker_deal
                self.reg_status_exch_memb = reg_status_exch_memb
                self.trustee_same_address = trustee_same_address
                self.trustee_address = trustee_address
                self.trustee_ext_id = trustee_ext_id
                self.trustee_last_name = trustee_last_name
                self.trustee_first_name = trustee_first_name
                self.trustee_salutation = trustee_salutation
                self.trustee_date_of_birth = trustee_date_of_birth
                self.trustee_phone = trustee_phone
                self.trustee_email = trustee_email
                self.trustee_occupation = trustee_occupation
                self.trustee_employee_title = trustee_employee_title
                self.trustee_is_nfa_reg = trustee_is_nfa_reg
                self.trustee_citizenship = trustee_citizenship
                self.trustee_ssn = trustee_ssn
                self.trustee_leg_res_country = trustee_leg_res_country
                self.trustee_leg_res_state = trustee_leg_res_state
                self.trustee_issuing_country = trustee_issuing_country
                self.benef_same_address = benef_same_address
                self.benef_address = benef_address
                self.benef_ext_id = benef_ext_id
                self.benef_last_name = benef_last_name
                self.benef_first_name = benef_first_name
                self.benef_salutation = benef_salutation
                self.grantors_same_address = grantors_same_address
                self.grantors_address = grantors_address
                self.grantors_ext_id = grantors_ext_id
                self.grantors_last_name = grantors_last_name
                self.grantors_first_name = grantors_first_name
                self.grantors_salutation = grantors_salutation
                self.grantors_date_of_birth = grantors_date_of_birth
                self.grantors_citizenship = grantors_citizenship
                self.grantors_ssn = grantors_ssn
                self.grantors_leg_res_country = grantors_leg_res_country
                self.grantors_leg_res_state = grantors_leg_res_state
                self.grantors_issuing_country = grantors_issuing_country
                self.tax_address = tax_address
                self.tax_resid_0_tin = tax_resid_0_tin
                self.tax_resid_0_tin_type = tax_resid_0_tin_type
                self.doc_exec_login_ts = doc_exec_login_ts
                self.doc_exec_ts = doc_exec_ts
                self.signature = signature

        # USER
        account_number = '656764798610877'
        account_type = ACCOUNT_TYPE_PERSONAL
        address1 = '1, La Calle, Pueblo'
        city = 'Thistown'
        civil_status = abstract.PersonalData.CivilStatus['SINGLE'].value
        country = 'US'
        country_of_birth = 'US'
        date_of_birth = pd.Timestamp('1972-09-28')
        email = 'corte_el_carnicero@captainhaddock.com'
        empl_add_country = 'GB'
        empl_add_city = 'Benavente'
        empl_add_post_code = '28660A'
        empl_add_state = 'NY'
        empl_add_street_1 = '1, the Road'
        empl_add_street_2 = ''
        empl_business = 'Finance'
        empl_title = 'Jefe'
        employer = 'ABC Corp'
        first_name = 'Juan'
        gender = 'M'
        id = 12345
        identif_leg_citizenship = 'US'
        identif_ssn = '111-22-2333'
        income = 75432
        industry_sector = INDUSTRY_TYPES[0][0]
        last_name = 'Lopez'
        num_dependents = 17
        occupation = OCCUPATION_TYPES[0][0]
        other_income = 10000
        other_income_source = SOURCE_OF_FUNDS_TYPE_CONSULTING
        phone_number = '+12125861234'
        phone_type = 'Home'
        postal_code = '12345'
        retirement_postal_code = 28660
        salutation = 'Mr.'
        street_2 = 'Anyborough'
        suffix = None
        state = 'AL'
        zip_code = '45624'

        # FINANCIAL INFO
        asset_exp_0_knowledge = 5
        asset_exp_0_yrs  = '1'
        asset_exp_0_trds_per_yr = '1'
        asset_exp_1_knowledge = 8
        asset_exp_1_yrs = '2'
        asset_exp_1_trds_per_yr = '2'
        fin_info_tot_assets = '5'
        fin_info_liq_net_worth = '6'
        fin_info_ann_net_inc = '7'
        fin_info_net_worth = '8'

        # REGULATORY INFO
        reg_status_broker_deal = 'false'
        reg_status_exch_memb = 'false'
        reg_status_disp = 'false'
        reg_status_investig = 'false'
        reg_status_stk_cont = '1'
        tax_resid_0_country = 'Spain'
        tax_resid_0_tin_type = 'SSN'
        tax_resid_0_tin = '111-22-23456'

        # DOCUMENTS
        doc_exec_ts = datetime.datetime.now()
        doc_exec_login_ts = datetime.datetime.now()
        signature = 'Juan Lopez'
        date_of_birth = pd.Timestamp('1990-04-05').date()

        region = TestRegion(code=state,
                            country=country)

        residential_address = TestAddress(address1=address1,
                                          address2=street_2,
                                          city=city,
                                          region=region,
                                          post_code=zip_code)

        employer_region = TestRegion(code=empl_add_state,
                                     country=empl_add_country)

        employer_address = TestAddress(address1=empl_add_street_1,
                                       address2=empl_add_street_2,
                                       city=empl_add_city,
                                       region=employer_region,
                                       post_code=empl_add_post_code)

        tax_address = residential_address

        client = TestClient(civil_status=civil_status,
                            email=email,
                            employer=employer,
                            first_name=first_name,
                            gender=gender,
                            id=id,
                            income=income,
                            industry_sector=industry_sector,
                            last_name=last_name,
                            occupation=occupation,
                            other_income=other_income,
                            phone_num=phone_number)

        # TEST EMPLOYMENT_STATUSES
        for empl_stat in IB_EMPLOY_STATUSES:
            ib_employment_status = empl_stat[0]

            ib_onboard = TestIBOnboard(client=client,
                                       employer_address=employer_address,
                                       residential_address=residential_address,
                                       tax_address=tax_address,
                                       account_number=account_number,
                                       account_type=account_type,
                                       asset_exp_0_knowledge=asset_exp_0_knowledge,
                                       asset_exp_0_trds_per_yr=asset_exp_0_trds_per_yr,
                                       asset_exp_0_yrs=asset_exp_0_yrs,
                                       asset_exp_1_knowledge=asset_exp_1_knowledge,
                                       asset_exp_1_trds_per_yr=asset_exp_1_trds_per_yr,
                                       asset_exp_1_yrs=asset_exp_1_yrs,
                                       country_of_birth=country_of_birth,
                                       date_of_birth=date_of_birth,
                                       doc_exec_login_ts=doc_exec_login_ts,
                                       doc_exec_ts=doc_exec_ts,
                                       signature=signature,
                                       fin_info_ann_net_inc=fin_info_ann_net_inc,
                                       fin_info_liq_net_worth=fin_info_liq_net_worth,
                                       fin_info_net_worth=fin_info_net_worth,
                                       fin_info_tot_assets=fin_info_tot_assets,
                                       ib_employment_status=ib_employment_status,
                                       identif_leg_citizenship=identif_leg_citizenship,
                                       identif_ssn=identif_ssn,
                                       joint_type='',
                                       other_income_source=other_income_source,
                                       num_dependents=num_dependents,
                                       phone_type=phone_type,
                                       reg_status_broker_deal=reg_status_broker_deal,
                                       reg_status_disp=reg_status_disp,
                                       reg_status_exch_memb=reg_status_exch_memb,
                                       reg_status_investig=reg_status_investig,
                                       reg_status_stk_cont=reg_status_stk_cont,
                                       salutation=salutation,
                                       suffix=suffix,
                                       tax_resid_0_tin=tax_resid_0_tin,
                                       tax_resid_0_tin_type=tax_resid_0_tin_type)

            success = onb.onboard('INDIVIDUAL', ib_onboard)

        # TEST COUNTRIES
        country = 'US'
        region = TestRegion(code=state,
                            country=country)

        residential_address = TestAddress(address1=address1,
                                          address2=street_2,
                                          city=city,
                                          region=region,
                                          post_code=zip_code)

        tax_address = residential_address

        ib_onboard = TestIBOnboard(client=client,
                                   employer_address=employer_address,
                                   residential_address=residential_address,
                                   tax_address=tax_address,
                                   account_number=account_number,
                                   account_type=account_type,
                                   asset_exp_0_knowledge=asset_exp_0_knowledge,
                                   asset_exp_0_trds_per_yr=asset_exp_0_trds_per_yr,
                                   asset_exp_0_yrs=asset_exp_0_yrs,
                                   asset_exp_1_knowledge=asset_exp_1_knowledge,
                                   asset_exp_1_trds_per_yr=asset_exp_1_trds_per_yr,
                                   asset_exp_1_yrs=asset_exp_1_yrs,
                                   country_of_birth=country_of_birth,
                                   date_of_birth=date_of_birth,
                                   doc_exec_login_ts=doc_exec_login_ts,
                                   doc_exec_ts=doc_exec_ts,
                                   signature=signature,
                                   fin_info_ann_net_inc=fin_info_ann_net_inc,
                                   fin_info_liq_net_worth=fin_info_liq_net_worth,
                                   fin_info_net_worth=fin_info_net_worth,
                                   fin_info_tot_assets=fin_info_tot_assets,
                                   ib_employment_status=ib_employment_status,
                                   identif_leg_citizenship=identif_leg_citizenship,
                                   identif_ssn=identif_ssn,
                                   joint_type='',
                                   other_income_source=other_income_source,
                                   num_dependents=num_dependents,
                                   phone_type=phone_type,
                                   reg_status_broker_deal=reg_status_broker_deal,
                                   reg_status_disp=reg_status_disp,
                                   reg_status_exch_memb=reg_status_exch_memb,
                                   reg_status_investig=reg_status_investig,
                                   reg_status_stk_cont=reg_status_stk_cont,
                                   salutation=salutation,
                                   suffix=suffix,
                                   tax_resid_0_tin=tax_resid_0_tin,
                                   tax_resid_0_tin_type=tax_resid_0_tin_type)

        success = onb.onboard('INDIVIDUAL', ib_onboard)

        # JOINT FILING
        joint_account_type = ACCOUNT_TYPE_JOINT
        joint_type = JOINT_ACCOUNT_TYPE_JOINT_TENANTS

        ret_client = TestClient(civil_status=civil_status,
                            email=email,
                            employer=employer,
                            first_name=first_name,
                            gender=gender,
                            id=id,
                            income=income,
                            industry_sector=industry_sector,
                            last_name=last_name,
                            occupation=occupation,
                            other_income=other_income,
                            phone_num=phone_number)

        ib_onboard = TestIBOnboard(client=ret_client,
                                   employer_address=employer_address,
                                   residential_address=residential_address,
                                   tax_address=tax_address,
                                   account_number=account_number,
                                   account_type=joint_account_type,
                                   asset_exp_0_knowledge=asset_exp_0_knowledge,
                                   asset_exp_0_trds_per_yr=asset_exp_0_trds_per_yr,
                                   asset_exp_0_yrs=asset_exp_0_yrs,
                                   asset_exp_1_knowledge=asset_exp_1_knowledge,
                                   asset_exp_1_trds_per_yr=asset_exp_1_trds_per_yr,
                                   asset_exp_1_yrs=asset_exp_1_yrs,
                                   country_of_birth=country_of_birth,
                                   date_of_birth=date_of_birth,
                                   doc_exec_login_ts=doc_exec_login_ts,
                                   doc_exec_ts=doc_exec_ts,
                                   signature=signature,
                                   fin_info_ann_net_inc=fin_info_ann_net_inc,
                                   fin_info_liq_net_worth=fin_info_liq_net_worth,
                                   fin_info_net_worth=fin_info_net_worth,
                                   fin_info_tot_assets=fin_info_tot_assets,
                                   ib_employment_status=ib_employment_status,
                                   identif_leg_citizenship=identif_leg_citizenship,
                                   identif_ssn=identif_ssn,
                                   joint_type = joint_type,
                                   other_income_source=other_income_source,
                                   num_dependents=num_dependents,
                                   phone_type=phone_type,
                                   reg_status_broker_deal=reg_status_broker_deal,
                                   reg_status_disp=reg_status_disp,
                                   reg_status_exch_memb=reg_status_exch_memb,
                                   reg_status_investig=reg_status_investig,
                                   reg_status_stk_cont=reg_status_stk_cont,
                                   salutation=salutation,
                                   suffix=suffix,
                                   tax_resid_0_tin=tax_resid_0_tin,
                                   tax_resid_0_tin_type=tax_resid_0_tin_type)

        # PARTNER
        part_account_number = '123464798610877'
        part_account_type = ACCOUNT_TYPE_JOINT
        part_address1 = '2 Strasse, Pico'
        part_asset_exp_0_knowledge = 1
        part_asset_exp_0_yrs  = '2'
        part_asset_exp_0_trds_per_yr = '3'
        part_asset_exp_1_knowledge = 9
        part_asset_exp_1_yrs = '5'
        part_asset_exp_1_trds_per_yr = '20'
        part_city = 'Pozuelo'
        part_civil_status = abstract.PersonalData.CivilStatus['MARRIED_FILING_JOINTLY'].value
        part_country = 'US'
        part_country_of_birth = 'US'
        part_date_of_birth = pd.Timestamp('1983-04-05').date()
        part_doc_exec_ts = datetime.datetime.now()
        part_doc_exec_login_ts = datetime.datetime.now()
        part_signature = 'Juana Gonzalez'
        part_date_of_birth = pd.Timestamp('1990-04-05').date()
        part_email = 'cortana@captainhaddock.com'
        part_empl_add_street_1 = '2, La Calle'
        part_empl_add_street_2 = ''
        part_empl_add_city = 'Zamorra'
        part_empl_add_country = 'US'
        part_empl_add_post_code = 'SW7 3JP'
        part_empl_add_state = 'Sussex'
        part_empl_business = 'Mining'
        part_employer = 'WXY Mines'
        part_employment_status = IB_EMPLOY_STAT_AT_HOME_TRADER
        part_empl_title = 'CEO'
        part_fin_info_tot_assets = '5'
        part_fin_info_liq_net_worth = '6'
        part_fin_info_ann_net_inc = '7'
        part_fin_info_net_worth = '8'
        part_first_name = 'Juana'
        part_gender = 'F'
        part_id = 87654
        part_identif_leg_citizenship = 'US'
        part_identif_ssn = '111-22-2233'
        part_income = 754320
        part_industry_sector = INDUSTRY_TYPES[1][0]
        part_last_name = 'Gonzalez'
        part_num_dependents = 3
        part_occupation = OCCUPATION_TYPES[1][0]
        part_other_income = '2500'
        part_other_income_source = SOURCE_OF_FUNDS_TYPE_INHERITANCE
        part_phone_number = '9876543654'
        part_phone_type = 'Home'
        part_reg_status_broker_deal = 'false'
        part_reg_status_exch_memb = 'false'
        part_reg_status_disp = 'false'
        part_reg_status_investig = 'false'
        part_reg_status_stk_cont = '3'
        part_retirement_postal_code = 28655
        part_salutation = 'Mrs.'
        part_street_2 = 'Greenborough'
        part_suffix = None
        part_state = 'AL'
        part_ssn = '1111111111111'
        part_tax_resid_0_country = 'VE'
        part_tax_resid_0_tin_type = 'NonUS_NationalIID'
        part_tax_resid_0_tin = '111-22-3456'
        part_zip_code = '78964'

        part_region = TestRegion(code=part_state,
                                 country=part_country)

        part_residential_address = TestAddress(address1=part_address1,
                                               address2=part_street_2,
                                               city=part_city,
                                               region=part_region,
                                               post_code=part_zip_code)

        part_employer_region = TestRegion(code=part_empl_add_state,
                                          country=part_empl_add_country)

        part_employer_address = TestAddress(address1=part_empl_add_street_1,
                                            address2=part_empl_add_street_2,
                                            city=part_empl_add_city,
                                            region=part_employer_region,
                                            post_code=part_empl_add_post_code)

        part_tax_address = part_residential_address

        part_client = TestClient(civil_status=part_civil_status,
                                 email=part_email,
                                 employer=part_employer,
                                 first_name=part_first_name,
                                 gender=part_gender,
                                 id=part_id,
                                 income=part_income,
                                 industry_sector=part_industry_sector,
                                 last_name=part_last_name,
                                 occupation=part_occupation,
                                 other_income=part_other_income,
                                 phone_num=part_phone_number)

        # TEST EMPLOYMENT_STATUSES pd.Timestamp('1990-04-05').date()
        for empl_stat in IB_EMPLOY_STATUSES:
            part_ib_employment_status = empl_stat[0]

            part_ib_onboard = TestIBOnboard(client=part_client,
                                            employer_address=part_employer_address,
                                            residential_address=part_residential_address,
                                            tax_address=part_tax_address,
                                            account_number=part_account_number,
                                            account_type=part_account_type,
                                            asset_exp_0_knowledge=part_asset_exp_0_knowledge,
                                            asset_exp_0_trds_per_yr=part_asset_exp_0_trds_per_yr,
                                            asset_exp_0_yrs=part_asset_exp_0_yrs,
                                            asset_exp_1_knowledge=part_asset_exp_1_knowledge,
                                            asset_exp_1_trds_per_yr=part_asset_exp_1_trds_per_yr,
                                            asset_exp_1_yrs=part_asset_exp_1_yrs,
                                            country_of_birth=part_country_of_birth,
                                            date_of_birth=part_date_of_birth,
                                            doc_exec_login_ts=part_doc_exec_login_ts,
                                            doc_exec_ts=part_doc_exec_ts,
                                            signature=part_signature,
                                            fin_info_ann_net_inc=part_fin_info_ann_net_inc,
                                            fin_info_liq_net_worth=part_fin_info_liq_net_worth,
                                            fin_info_net_worth=part_fin_info_net_worth,
                                            fin_info_tot_assets=part_fin_info_tot_assets,
                                            ib_employment_status=part_employment_status,
                                            identif_leg_citizenship=part_identif_leg_citizenship,
                                            joint_type=joint_type,
                                            identif_ssn=part_identif_ssn,
                                            num_dependents=part_num_dependents,
                                            other_income_source=part_other_income_source,
                                            phone_type=part_phone_type,
                                            reg_status_broker_deal=part_reg_status_broker_deal,
                                            reg_status_disp=part_reg_status_disp,
                                            reg_status_exch_memb=part_reg_status_exch_memb,
                                            reg_status_investig=part_reg_status_investig,
                                            reg_status_stk_cont=part_reg_status_stk_cont,
                                            salutation=part_salutation,
                                            suffix=part_suffix,
                                            tax_resid_0_tin=part_tax_resid_0_tin,
                                            tax_resid_0_tin_type=part_tax_resid_0_tin_type)

            success = onb.onboard('JOINT', ib_onboard, part_ib_onboard)

        # COUNTRIES
        country = 'ES'
        region = TestRegion(code=state,
                            country=country)

        residential_address = TestAddress(address1=address1,
                                          address2=street_2,
                                          city=city,
                                          region=region,
                                          post_code=zip_code)

        tax_address = residential_address

        ib_onboard = TestIBOnboard(client=ret_client,
                                   employer_address=employer_address,
                                   residential_address=residential_address,
                                   tax_address=tax_address,
                                   account_number=account_number,
                                   account_type=joint_account_type,
                                   asset_exp_0_knowledge=asset_exp_0_knowledge,
                                   asset_exp_0_trds_per_yr=asset_exp_0_trds_per_yr,
                                   asset_exp_0_yrs=asset_exp_0_yrs,
                                   asset_exp_1_knowledge=asset_exp_1_knowledge,
                                   asset_exp_1_trds_per_yr=asset_exp_1_trds_per_yr,
                                   asset_exp_1_yrs=asset_exp_1_yrs,
                                   country_of_birth=country_of_birth,
                                   date_of_birth=date_of_birth,
                                   doc_exec_login_ts=doc_exec_login_ts,
                                   doc_exec_ts=doc_exec_ts,
                                   signature=signature,
                                   fin_info_ann_net_inc=fin_info_ann_net_inc,
                                   fin_info_liq_net_worth=fin_info_liq_net_worth,
                                   fin_info_net_worth=fin_info_net_worth,
                                   fin_info_tot_assets=fin_info_tot_assets,
                                   ib_employment_status=ib_employment_status,
                                   identif_leg_citizenship=identif_leg_citizenship,
                                   identif_ssn=identif_ssn,
                                   joint_type=joint_type,
                                   other_income_source=other_income_source,
                                   num_dependents=num_dependents,
                                   phone_type=phone_type,
                                   reg_status_broker_deal=reg_status_broker_deal,
                                   reg_status_disp=reg_status_disp,
                                   reg_status_exch_memb=reg_status_exch_memb,
                                   reg_status_investig=reg_status_investig,
                                   reg_status_stk_cont=reg_status_stk_cont,
                                   salutation=salutation,
                                   suffix=suffix,
                                   tax_resid_0_tin=tax_resid_0_tin,
                                   tax_resid_0_tin_type=tax_resid_0_tin_type)

        part_ib_onboard = TestIBOnboard(client=part_client,
                                           employer_address=part_employer_address,
                                           residential_address=part_residential_address,
                                           tax_address=part_tax_address,
                                           account_number=part_account_number,
                                           account_type=part_account_type,
                                           asset_exp_0_knowledge=part_asset_exp_0_knowledge,
                                           asset_exp_0_trds_per_yr=part_asset_exp_0_trds_per_yr,
                                           asset_exp_0_yrs=part_asset_exp_0_yrs,
                                           asset_exp_1_knowledge=part_asset_exp_1_knowledge,
                                           asset_exp_1_trds_per_yr=part_asset_exp_1_trds_per_yr,
                                           asset_exp_1_yrs=part_asset_exp_1_yrs,
                                           country_of_birth=part_country_of_birth,
                                           date_of_birth=part_date_of_birth,
                                           doc_exec_login_ts=part_doc_exec_login_ts,
                                           doc_exec_ts=part_doc_exec_ts,
                                           signature=part_signature,
                                           fin_info_ann_net_inc=part_fin_info_ann_net_inc,
                                           fin_info_liq_net_worth=part_fin_info_liq_net_worth,
                                           fin_info_net_worth=part_fin_info_net_worth,
                                           fin_info_tot_assets=part_fin_info_tot_assets,
                                           ib_employment_status=part_ib_employment_status,
                                           identif_leg_citizenship=part_identif_leg_citizenship,
                                           identif_ssn=part_identif_ssn,
                                           joint_type=joint_type,
                                           num_dependents=part_num_dependents,
                                           other_income_source=part_other_income_source,
                                           phone_type=part_phone_type,
                                           reg_status_broker_deal=part_reg_status_broker_deal,
                                           reg_status_disp=part_reg_status_disp,
                                           reg_status_exch_memb=part_reg_status_exch_memb,
                                           reg_status_investig=part_reg_status_investig,
                                           reg_status_stk_cont=part_reg_status_stk_cont,
                                           salutation=part_salutation,
                                           suffix=part_suffix,
                                           tax_resid_0_tin=part_tax_resid_0_tin,
                                           tax_resid_0_tin_type=part_tax_resid_0_tin_type)

        success = onb.onboard('JOINT', ib_onboard, part_ib_onboard)
'''
        # TRUST FILING
        account_number = account_number
        account_type = ACCOUNT_TYPE_TRUST
        trst_third_party_mgmt = 'False'
        trst_type_of_trust = 'Revocable'
        trst_date_formed = pd.Timestamp('2000-01-02').date()
        trst_name = 'William D. Conqueror'
        trst_reg_num = '111-22-3333'
        trst_reg_type = 'SSN'
        trst_same_mail_address = 'True'
        trst_address = residential_address
        trst_reg_country = 'US'
        trst_form_state = 'ME'
        trst_form_country = 'US'
        fin_info_ann_net_inc = '6'
        fin_info_liq_net_worth = '7'
        fin_info_net_worth = '7'
        fin_info_tot_assets = '3100000'
        asset_exp_0_trds_per_yr = '1'
        asset_exp_0_yrs = '2'
        asset_exp_0_knowledge = 'Limited'
        asset_exp_1_trds_per_yr = '3'
        asset_exp_1_yrs = '4'
        asset_exp_1_knowledge = 'Low'
        source_inc_percentage = '100'
        source_inc_type = 'INTEREST'
        reg_status_affil = 'False'
        reg_status_memb = 'True'
        reg_status_disp = 'False'
        reg_status_investig = 'True'
        reg_status_stk_cont = 'False'
        reg_status_ib_accounts = 'True'
        reg_status_criminal = 'False'
        reg_status_reg_control = 'True'
        reg_status_broker_deal = 'False'
        reg_status_exch_memb = 'True'
        trustee_same_address = False
        trustee_address = residential_address
        trustee_ext_id = 'ABCD3001TASP1'
        trustee_last_name = 'Conqueror'
        trustee_first_name = 'William'
        trustee_salutation = 'Mr.'
        trustee_date_of_birth = pd.Timestamp('1980-01-02').date()
        trustee_phone = '207-555-5555'
        trustee_email = 'wdcon@acme.com'
        trustee_occupation = 'Employed'
        trustee_employee_title = 'Employed'
        trustee_is_nfa_reg = 'False'
        trustee_citizenship = 'US'
        trustee_ssn = '111223333'
        trustee_leg_res_country = 'US'
        trustee_leg_res_state = 'MA'
        trustee_issuing_country = 'US'
        benef_same_address = False
        benef_address = residential_address
        benef_ext_id = 'ABCD3001TASP2'
        benef_last_name = 'Conqueror'
        benef_first_name = 'William'
        benef_salutation = 'Mr.'
        grantors_same_address = False
        grantors_address = residential_address
        grantors_ext_id = 'ABCD3001TASP3'
        grantors_last_name = 'Conqueror'
        grantors_first_name = 'William'
        grantors_salutation = 'Mr.'
        grantors_date_of_birth = pd.Timestamp('1980-01-02').date()
        grantors_citizenship = 'US'
        grantors_ssn = '111223333'
        grantors_leg_res_country = 'US'
        grantors_leg_res_state = 'MA'
        grantors_issuing_country = 'US'
        tax_address = residential_address
        tax_resid_0_tin_type = 'SSN'
        tax_resid_0_tin = '1112223456'
        doc_exec_ts = datetime.datetime.now()
        doc_exec_login_ts = datetime.datetime.now()
        signature = 'Juan Lopez'

        trust_client = TestClient(civil_status=civil_status,
                            email=email,
                            employer=employer,
                            first_name=first_name,
                            gender=gender,
                            id=id,
                            income=income,
                            industry_sector=industry_sector,
                            last_name=last_name,
                            occupation=occupation,
                            other_income=other_income,
                            phone_num=phone_number)

        trust_ib_onboard = TestIBTrustOnboard(client=trust_client,
                                account_number=account_number,
                                account_type=account_type,
                                trst_third_party_mgmt=trst_third_party_mgmt,
                                trst_type_of_trust=trst_type_of_trust,
                                trst_date_formed=trst_date_formed,
                                trst_name=trst_name,
                                trst_reg_num=trst_reg_num,
                                trst_reg_type=trst_reg_type,
                                trst_same_mail_address=trst_same_mail_address,
                                trst_address=trst_address,
                                trst_reg_country=trst_reg_country,
                                trst_form_state=trst_form_state,
                                trst_form_country=trst_form_country,
                                fin_info_ann_net_inc=fin_info_ann_net_inc,
                                fin_info_liq_net_worth=fin_info_liq_net_worth,
                                fin_info_net_worth=fin_info_net_worth,
                                fin_info_tot_assets=fin_info_tot_assets,
                                asset_exp_0_trds_per_yr=asset_exp_0_trds_per_yr,
                                asset_exp_0_yrs=asset_exp_0_yrs,
                                asset_exp_0_knowledge=asset_exp_0_knowledge,
                                asset_exp_1_trds_per_yr=asset_exp_1_trds_per_yr,
                                asset_exp_1_yrs=asset_exp_1_yrs,
                                asset_exp_1_knowledge=asset_exp_1_knowledge,
                                source_inc_percentage=source_inc_percentage,
                                source_inc_type=source_inc_type,
                                reg_status_affil=reg_status_affil,
                                reg_status_memb=reg_status_memb,
                                reg_status_disp=reg_status_disp,
                                reg_status_investig=reg_status_investig,
                                reg_status_stk_cont=reg_status_stk_cont,
                                reg_status_ib_accounts=reg_status_ib_accounts,
                                reg_status_criminal=reg_status_criminal,
                                reg_status_reg_control=reg_status_reg_control,
                                reg_status_broker_deal=reg_status_broker_deal,
                                reg_status_exch_memb=reg_status_exch_memb,
                                trustee_same_address=trustee_same_address,
                                trustee_address=trustee_address,
                                trustee_ext_id=trustee_ext_id,
                                trustee_last_name=trustee_last_name,
                                trustee_first_name=trustee_first_name,
                                trustee_salutation=trustee_salutation,
                                trustee_date_of_birth=trustee_date_of_birth,
                                trustee_phone=trustee_phone,
                                trustee_email=trustee_email,
                                trustee_occupation=trustee_occupation,
                                trustee_employee_title=trustee_employee_title,
                                trustee_is_nfa_reg=trustee_is_nfa_reg,
                                trustee_citizenship=trustee_citizenship,
                                trustee_ssn=trustee_ssn,
                                trustee_leg_res_country=trustee_leg_res_country,
                                trustee_leg_res_state=trustee_leg_res_state,
                                trustee_issuing_country=trustee_issuing_country,
                                benef_same_address=benef_same_address,
                                benef_address=benef_address,
                                benef_ext_id=benef_ext_id,
                                benef_last_name=benef_last_name,
                                benef_first_name=benef_first_name,
                                benef_salutation=benef_salutation,
                                grantors_same_address=grantors_same_address,
                                grantors_address=grantors_address,
                                grantors_ext_id=grantors_ext_id,
                                grantors_last_name=grantors_last_name,
                                grantors_first_name=grantors_first_name,
                                grantors_salutation=grantors_salutation,
                                grantors_date_of_birth=grantors_date_of_birth,
                                grantors_citizenship=grantors_citizenship,
                                grantors_ssn=grantors_ssn,
                                grantors_leg_res_country=grantors_leg_res_country,
                                grantors_leg_res_state=grantors_leg_res_state,
                                grantors_issuing_country=grantors_issuing_country,
                                tax_address=tax_address,
                                tax_resid_0_tin=tax_resid_0_tin,
                                tax_resid_0_tin_type=tax_resid_0_tin_type,
                                doc_exec_login_ts=doc_exec_login_ts,
                                doc_exec_ts=doc_exec_ts,
                                signature=signature)

        success = onb.onboard('TRUST', trust_ib_onboard)


            # self.client = client
            # self.account_number = client.id
            # self.asset_exp_0_trds_per_yr = '1'
            # self.asset_exp_0_yrs = '2'
            # self.asset_exp_0_knowledge = 'Limited'
            # self.asset_exp_1_trds_per_yr = '3'
            # self.asset_exp_1_yrs = '4'
            # self.asset_exp_1_knowledge = 'Low'
            # self.benef_same_address = 'False'
            # self.benef_address = residential_address
            # self.benef_last_name = 'Jones'
            # self.benef_first_name = 'Petra'
            # self.benef_salutation = 'Ms.'
            # self.fin_info_net_worth = '1'
            # self.fin_info_address = residential_address
            # self.grantors_last_name = 'Harris'
            # self.grantors_first_name = 'Rolf'
            # self.grantors_salutation = 'Dr.'
            # self.grantors_date_of_birth = pd.Timestamp('1980-04-05').date()
            # self.grantors_citizenship = 'United States'
            # self.grantors_ssn = '11111111111'
            # self.grantors_leg_res_country = 'United States'
            # self.grantors_leg_res_state = 'MA'
            # self.grantors_issuing_country = 'United States'
            # self.other_income = '25000'
            # self.other_income_source = 'Disability'
            # self.trst_date_formed =  pd.Timestamp('1980-04-05').date()
            # self.trst_name = 'Hurtado Onslow Settlement'
            # self.trst_reg_num = '12345678'
            # self.trst_reg_type = 'A'
            # self.trst_same_mail_address = 'False'
            # self.trst_address = residential_address
            # self.trst_reg_country = 'United States'
            # self.trst_form_state = 'NY'
            # self.trst_form_country = 'United States'
            # self.trst_third_party_mgmt = 'True'
            # self.trustee_same_address = 'False'
            # self.trustee_address = residential_address
            # self.trustee_ext_id = '98765'
            # self.trustee_last_name = 'Schmidt'
            # self.trustee_first_name = 'Johan'
            # self.trustee_salutation = 'Herr'
            # self.trustee_date_of_birth = pd.Timestamp('1970-04-05').date()
            # self.trustee_phone = '916331884'
            # self.trustee_email = 'herr.johan@scmidt.com'
            # self.trustee_occupation = 'Lawyer'
            # self.trustee_employee_title = 'Partner'
            # self.trustee_is_nfa_reg = 'False'
            # self.trustee_citizenship = 'United States'
            # self.trustee_ssn = '876435674'
            # self.trustee_leg_res_country = 'United States'
            # self.trustee_leg_res_state = 'MO'
            # self.trustee_issuing_country = 'United States'
            # self.reg_status_memb = 'True'
            # self.reg_status_disp = 'False'
            # self.reg_status_investig = 'True'
            # self.reg_status_stk_cont = 'False'
            # self.reg_status_ib_accounts = 'True'
            # self.reg_status_criminal = 'False'
            # self.reg_status_reg_control = 'True'
            # self.reg_status_broker_deal = 'False'
            # self.reg_status_exch_memb = 'True'
            # self.reg_status_a_trust = 'True'
            '''
