from brokers.interactive_brokers.onboarding import onboarding_helpers as onb_help
from brokers.interactive_brokers.onboarding import onboarding as onb
from main import zip2state
from brokers.interactive_brokers.onboarding.constants import IB_EMPLOY_STATUSES, IB_EMPLOY_STAT_EMPLOYED, \
     IB_EMPLOY_STAT_SELF_EMPLOYED, SOURCE_OF_FUNDS_TYPES
from main.constants import INDUSTRY_TYPES, OCCUPATION_TYPES
import xml.etree.ElementTree as ET
import pdb
import os

def get_tree(onboard,
             docs,
             tax_forms_us,
             tax_forms_non_us):
    '''
    returns a new xml tree conforming to IB spec for individual applications 
    '''
    uri = onb.URI
    ET.register_namespace('', uri)
    attrib_applications = {'xmlns':uri[1:-1]}
    applications = ET.Element('Applications', attrib_applications)
    tree = ET.ElementTree(applications)
    
    application = ET.SubElement(applications,'Application')

    # Customer
    attrib_customer = {'email': str(onboard.client.user.email),
                       'external_id' :str(onboard.client.id),
                       'type' : 'INDIVIDUAL',
                       'prefix': str(onb_help.get_prefix(onboard.client.user.last_name, onboard.client.user.first_name))}
    customer = ET.SubElement(application,'Customer', attrib_customer)

    account_holder = ET.SubElement(customer,'AccountHolder')

    # Account Holder Details
    attrib_account_holder_details = {'external_id' : str(onboard.client.id)}
    account_holder_details = ET.SubElement(account_holder,'AccountHolderDetails', attrib_account_holder_details)

    attrib_name = {'last': str(onboard.client.user.last_name),
                   'first': str(onboard.client.user.first_name),
                   'salutation': str(onboard.salutation),
                   'suffix': str(onb_help.get_suffix(onboard.suffix))}
    name = ET.SubElement(account_holder_details,'Name', attrib_name)

    dob = ET.SubElement(account_holder_details,'DOB')
    dob.text = str(onboard.date_of_birth)

    country_of_birth = ET.SubElement(account_holder_details,'CountryOfBirth')
    country_of_birth.text = str(onb_help.get_country(onboard.country_of_birth))

    marital_status = ET.SubElement(account_holder_details,'MaritalStatus')
    marital_status.text = str(onb_help.get_marital_status(onboard.client.civil_status))

    num_dependents = ET.SubElement(account_holder_details,'NumDependents')
    num_dependents.text = str(onboard.num_dependents)

    attrib_residence =  {'state': str(onboard.residential_address.region.code),
                         'street_2': str(onboard.residential_address.address2),
                         'postal_code': str(onboard.residential_address.post_code),
                         'country': str(onb_help.get_country(onboard.residential_address.region.country)),
                         'street_1': str(onboard.residential_address.address1),
                         'city': str(onboard.residential_address.city)}
    residence = ET.SubElement(account_holder_details,'Residence', attrib_residence)

    phones = ET.SubElement(account_holder_details,'Phones')

    attrib_phone = {'number': str(onboard.client.phone_num),
                    'type' : str(onboard.phone_type)}
    phone = ET.SubElement(phones,'Phone', attrib_phone)

    attrib_email = {'email': str(onboard.client.user.email)}
    email = ET.SubElement(account_holder_details,'Email', attrib_email)

    attrib_identification = {'citizenship': str(onb_help.get_country(onboard.identif_leg_citizenship)),
                             'LegalResidenceState': str(onboard.residential_address.region.code),
                             'LegalResidenceCountry': str(onb_help.get_country(onboard.residential_address.region.country)),
                             'SSN': onb_help.get_str_no_minus(onboard.identif_ssn)}

    identification = ET.SubElement(account_holder_details,'Identification', attrib_identification)

    gender = ET.SubElement(account_holder_details,'Gender')
    gender.text = str(onboard.client.gender)

    employment_type = ET.SubElement(account_holder_details,'EmploymentType')
    employment_type.text = str(IB_EMPLOY_STATUSES[onboard.ib_employment_status][1])

    if onboard.ib_employment_status in (IB_EMPLOY_STAT_EMPLOYED,
                                        IB_EMPLOY_STAT_SELF_EMPLOYED):

        employment_details = ET.SubElement(account_holder_details,'EmploymentDetails')

        employer = ET.SubElement(employment_details,'employer')
        employer.text = str(onboard.client.employer)
        occupation = ET.SubElement(employment_details,'occupation')
        occupation.text = str(onb_help.get_occupation(onboard.client.occupation))
        
        employer_business = ET.SubElement(employment_details,'employer_business')
        employer_business.text = str(onb_help.get_industry_sector(onboard.client.industry_sector))

        attrib_employer_address =  {'state': str(onboard.employer_address.region.code),
                                    'street_2': str(onboard.employer_address.address2),
                                    'postal_code': str(onboard.employer_address.post_code),
                                    'country': str(onb_help.get_country(onboard.employer_address.region.country)),
                                    'street_1': str(onboard.employer_address.address1),
                                    'city': str(onboard.employer_address.city)}
        employer_address = ET.SubElement(employment_details,'employer_address', attrib_employer_address)

    title = ET.SubElement(account_holder_details,'Title')
    title.text = 'Account Holder'

    if str(onb_help.get_country(onboard.tax_address.region.country)) == 'United States':
         attrib_w9 = {'customer_type': 'Individual',
                      'cert1': 'true',
                      'cert2': 'true',
                      'cert3': 'true',
                      'name': (str(onboard.client.user.first_name) + ' ' + str(onboard.client.user.last_name)),
                      'tin': onb_help.get_str_no_minus(onboard.identif_ssn),
                      'tin_type': str(onboard.tax_resid_0_tin_type),
                      'blank_form' : 'true',
                      'signature_type' : 'Electronic',
                      'proprietary_form_number' : '5002',
                      'tax_form_file' : 'Form5002.pdf'}
         w9 = ET.SubElement(account_holder_details,'W9', attrib_w9)

    else:
        attrib_w8_ben = {'part_2_9a_country' : str(onb_help.get_country(onboard.tax_address.region.country)),
                        'name' : (str(onboard.client.user.first_name) + ' ' + str(onboard.client.user.last_name)),
                        'signature_type' : 'Electronic',
                        'blank_form' : 'true'}
        tax_form = ET.SubElement(account_holder_details,'W8Ben', attrib_w8_ben)

    # Financial Information
    attrib_fin_info = {'net_worth': str(onboard.fin_info_net_worth),
                                    'liquid_net_worth': str(onboard.fin_info_liq_net_worth),
                                    'annual_net_income': str(onboard.fin_info_ann_net_inc),
                                    'total_assets': str(onboard.fin_info_tot_assets)}
    financial_information = ET.SubElement(account_holder,'FinancialInformation', attrib_fin_info)

    investment_experience = ET.SubElement(financial_information,'InvestmentExperience')

    attrib_asset_experience_0 = {'trades_per_year': str(onboard.asset_exp_0_trds_per_yr),
                                 'years_trading': str(onboard.asset_exp_0_yrs ),
                                 'knowledge_level': onb_help.get_knowledge((onboard.asset_exp_0_knowledge)),
                                 'asset_class': 'FUND'}
    asset_experience_0 = ET.SubElement(investment_experience,'AssetExperience', attrib_asset_experience_0)

    attrib_asset_experience_1 = {'trades_per_year': str(onboard.asset_exp_1_trds_per_yr),
                                 'years_trading': str(onboard.asset_exp_1_yrs ),
                                 'knowledge_level': onb_help.get_knowledge((onboard.asset_exp_1_knowledge)),
                                 'asset_class': 'STK'}
    asset_experience_1 = ET.SubElement(investment_experience,'AssetExperience', attrib_asset_experience_1)

    if onboard.ib_employment_status not in (IB_EMPLOY_STAT_EMPLOYED,
                                        IB_EMPLOY_STAT_SELF_EMPLOYED):

        additional_source_of_income = ET.SubElement(financial_information,'AdditionalSourceOfIncome')

        attrib_other_income = {'source_type': str(SOURCE_OF_FUNDS_TYPES[onboard.other_income_source][1]).upper(),
                               'percentage': '100'}

        other_income = ET.SubElement(additional_source_of_income, 'SourceOfIncome', attrib_other_income)
    '''
    investment_objectives = ET.SubElement(financial_information,'InvestmentObjectives')
    income = ET.SubElement(investment_objectives,'objective')
    income.text = 'Income'
    growth = ET.SubElement(investment_objectives,'objective')
    growth.text = 'Growth'
    preservation = ET.SubElement(investment_objectives,'objective')
    preservation.text = 'Preservation'
    '''

    # Regulatory Information
    regulatory_details = ET.SubElement(account_holder, 'RegulatoryInformation')
    
    attrib_reg_broker_deal = {'status' : str(onboard.reg_status_broker_deal).lower(),
                              'code' : 'BROKERDEALER'}
    
    attrib_reg_exch_memb = {'status' : str(onboard.reg_status_exch_memb).lower(),
                              'code' : 'EXCHANGEMEMBERSHIP'}

    attrib_reg_disp = {'status' : str(onboard.reg_status_disp).lower(),
                              'code' : 'DISPUTE'}

    attrib_reg_investig = {'status' : str(onboard.reg_status_investig).lower(),
                              'code' : 'INVESTIGATION'}

    if onboard.reg_status_stk_cont in ('1', '2', '3',):
        stk_cont = 'true'
    else:
        stk_cont = 'false'
    attrib_reg_stk_cont = {'status' : stk_cont,
                              'code' : 'STOCKCONTROL'}

    reg_broker_deal = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_broker_deal)
    reg_exch_memb = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_exch_memb)
    reg_disp = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_disp)
    reg_investig = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_investig)
    reg_stk_cont = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_stk_cont)

    tax_residencies = ET.SubElement(account_holder_details,'TaxResidencies')
    attrib_tax_resid_0 = {'country': str(onb_help.get_country(onboard.tax_address.region.country)),
                          'tin_type': str(onboard.tax_resid_0_tin_type),
                          'tin': onb_help.get_str_no_minus(onboard.identif_ssn)}
    tax_resid_0 = ET.SubElement(tax_residencies,'TaxResidency', attrib_tax_resid_0)

    # Accounts                     
    accounts = ET.SubElement(application,'Accounts')

    attrib_account = {'external_id': str(onboard.client.id),
                      'margin': 'Cash',
                      'base_currency': 'USD',
                      'multicurrency': 'false'}
    account = ET.SubElement(accounts,'Account', attrib_account)
    
    trading_permissions = ET.SubElement(account,'TradingPermissions')

    attrib_trad_perm_0 = {'exchange_group': 'US-Sec'}
    trad_perm_0 = ET.SubElement(trading_permissions,'TradingPermission', attrib_trad_perm_0)

    attrib_trad_perm_1 = {'exchange_group': 'US-Funds'}
    trad_perm_1 = ET.SubElement(trading_permissions,'TradingPermission', attrib_trad_perm_1)

    attrib_adv_wrap_fees = {'strategy': 'AUTOMATED'}
    adv_wrap_fees = ET.SubElement(account,'AdvisorWrapFees', attrib_adv_wrap_fees)

    attrib_auto_fees_det_0 = {'type': 'PERCENTOFEQUITY_MONTHLY',
                                  'max_fee':'0.25'}
    auto_fees_det_0 = ET.SubElement(adv_wrap_fees,'automated_fees_details', attrib_auto_fees_det_0)

    attrib_auto_fees_det_1 = {'type': 'INVOICE_LIMIT',
                                  'max_fee':'5000'}
    auto_fees_det_1 = ET.SubElement(adv_wrap_fees,'automated_fees_details', attrib_auto_fees_det_1)

    investment_objectives = ET.SubElement(account,'InvestmentObjectives')
    income = ET.SubElement(investment_objectives,'objective')
    income.text = 'Income'
    growth = ET.SubElement(investment_objectives,'objective')
    growth.text = 'Growth'
    preservation = ET.SubElement(investment_objectives,'objective')
    preservation.text = 'Preservation'
    
    # Users
    users = ET.SubElement(application,'Users')

    attrib_user = {'external_individual_id': str(onboard.client.id),
                   'external_user_id': str(onboard.client.id),
                      'prefix': str(onb_help.get_prefix(onboard.client.user.last_name, onboard.client.user.first_name))}
    user_onboard = ET.SubElement(users,'User', attrib_user)

    # Documents
    documents = ET.SubElement(application, 'Documents')

    if str(onb_help.get_country(onboard.tax_address.region.country)) == 'United States':
        tax_forms = tax_forms_us
    else:
        tax_forms = tax_forms_non_us

    for dc in docs + tax_forms:
        attrib_doc = {'exec_ts' : onb_help.get_timestamp(onboard.doc_exec_ts),
                        'exec_login_ts' : onb_help.get_timestamp(onboard.doc_exec_login_ts),
                        'form_no' : onb_help.get_form_name(str(dc))}
        doc = ET.SubElement(documents,'Document', attrib_doc)

        doc_signed_by = ET.SubElement(doc, 'SignedBy')
        doc_signed_by.text = onboard.signature

        file = onb_help.get_onboarding_path_to_files() + onb.DOCUMENTS + dc

        attrib_doc_attached_file = {'file_name' : str(dc),
                                      'sha1_checksum' : str(onb_help.get_sha1_checksum(file).hexdigest()),
                                      'file_length' :  str(os.path.getsize(file))}
        doc_attached_file = ET.SubElement(doc,'AttachedFile', attrib_doc_attached_file)

    return tree

