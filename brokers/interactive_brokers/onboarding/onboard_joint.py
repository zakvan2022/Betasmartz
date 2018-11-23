from brokers.interactive_brokers.onboarding import onboarding_helpers as onb_help
from brokers.interactive_brokers.onboarding import onboarding as onb
from main import zip2state
from brokers.interactive_brokers.onboarding.constants import IB_EMPLOY_STATUSES, IB_EMPLOY_STAT_EMPLOYED,\
     IB_EMPLOY_STAT_SELF_EMPLOYED, SOURCE_OF_FUNDS_TYPES
import xml.etree.ElementTree as ET
import pdb
import os

def get_tree(onboard,
             docs,
             tax_forms_us,
             tax_forms_non_us):
    '''
    returns a new xml tree conforming to IB spec for joint applications
    '''
    uri = onb.URI
    ET.register_namespace('', uri)
    attrib_applications = {'xmlns':uri[1:-1]}
    applications = ET.Element('Applications', attrib_applications)
    tree = ET.ElementTree(applications)
    
    application = ET.SubElement(applications,'Application')

    # CUSTOMER
    attrib_customer = {'email': str(onboard[0].client.user.email),
                       'external_id' :str(onboard[0].client.id),
                       'type' : 'JOINT',
                       'prefix': str(onb_help.get_prefix(onboard[0].client.user.last_name, onboard[0].client.user.first_name))}
    customer = ET.SubElement(application,'Customer', attrib_customer)

    # JOINT HOLDERS
    attrib_joint_holders = {'type' : str(onb_help.get_joint_type(onboard[0].joint_type))}
    joint_holders = ET.SubElement(customer, 'JointHolders', attrib_joint_holders)

    # FIRST HOLDER
    attrib_first_holder_details = {'external_id' : str(onboard[0].client.id)}
    first_holder_details = ET.SubElement(joint_holders,'FirstHolderDetails', attrib_first_holder_details)

    country_of_birth = ET.SubElement(first_holder_details,'CountryOfBirth')
    country_of_birth.text = str(onb_help.get_country(onboard[0].country_of_birth))

    dob = ET.SubElement(first_holder_details,'DOB')
    dob.text = str(onboard[0].date_of_birth)

    attrib_email = {'email': str(onboard[0].client.user.email)}
    email = ET.SubElement(first_holder_details,'Email', attrib_email)

    if onboard[0].ib_employment_status in (IB_EMPLOY_STAT_EMPLOYED,
                                               IB_EMPLOY_STAT_SELF_EMPLOYED):

        employment_details = ET.SubElement(first_holder_details,'EmploymentDetails')

        employer = ET.SubElement(employment_details,'employer')
        employer.text = str(onboard[0].client.employer)
        
        occupation = ET.SubElement(employment_details,'occupation')
        occupation.text = str(onb_help.get_occupation(onboard[0].client.occupation))
        
        employer_business = ET.SubElement(employment_details,'employer_business')
        employer_business.text = str(onb_help.get_industry_sector(onboard[0].client.industry_sector))

        attrib_employer_address =  {'state': str(onboard[0].employer_address.region.code),
                                    'street_2': str(onboard[0].employer_address.address2),
                                    'postal_code': str(onboard[0].employer_address.post_code),
                                    'country': str(onb_help.get_country(onboard[0].employer_address.region.country)),
                                    'street_1': str(onboard[0].employer_address.address1),
                                    'city': str(onboard[0].employer_address.city)}
        employer_address = ET.SubElement(employment_details,'employer_address', attrib_employer_address)

    employment_type = ET.SubElement(first_holder_details,'EmploymentType')
    employment_type.text = str(IB_EMPLOY_STATUSES[onboard[0].ib_employment_status][1])

    gender = ET.SubElement(first_holder_details,'Gender')
    gender.text = str(onboard[0].client.gender)

    attrib_identification = {'citizenship': str(onboard[0].identif_leg_citizenship),
                             'LegalResidenceState': str(onboard[0].residential_address.region.code),
                             'LegalResidenceCountry': str(onb_help.get_country(onboard[0].residential_address.region.country)),
                             'SSN': onb_help.get_str_no_minus(onboard[0].identif_ssn)}
    identification = ET.SubElement(first_holder_details,'Identification', attrib_identification)

    marital_status = ET.SubElement(first_holder_details,'MaritalStatus')
    marital_status.text = str(onb_help.get_marital_status(onboard[0].client.civil_status))

    attrib_name = {'last': str(onboard[0].client.user.last_name),
                   'first': str(onboard[0].client.user.first_name),
                   'salutation': str(onboard[0].salutation),
                   'suffix': str(onb_help.get_suffix(onboard[0].suffix))}
    name = ET.SubElement(first_holder_details,'Name', attrib_name)

    num_dependents = ET.SubElement(first_holder_details,'NumDependents')
    num_dependents.text = str(onboard[0].num_dependents)

    attrib_ownership = {'percentage': '50'}
    ownership = ET.SubElement(first_holder_details,'Ownership', attrib_ownership)

    phones = ET.SubElement(first_holder_details,'Phones')
    attrib_phone = {'number': str(onboard[0].client.phone_num) ,
                    'type' : str(onboard[0].phone_type)}
    phone = ET.SubElement(phones,'Phone', attrib_phone)

    attrib_residence =  {'state': str(onboard[0].residential_address.region.code),
                         'street_2': str(onboard[0].residential_address.address2),
                         'postal_code': str(onboard[0].residential_address.post_code),
                         'country': str(onb_help.get_country(onboard[0].residential_address.region.country)),
                         'street_1': str(onboard[0].residential_address.address1),
                         'city': str(onboard[0].residential_address.city)}
    residence = ET.SubElement(first_holder_details,'Residence', attrib_residence)

    tax_residencies = ET.SubElement(first_holder_details,'TaxResidencies')
    attrib_tax_resid_0 = {'country': str(onb_help.get_country(onboard[0].tax_address.region.country)),
                          'tin_type': str(onboard[0].tax_resid_0_tin_type),
                          'tin': onb_help.get_str_no_minus(onboard[0].identif_ssn)}
    tax_resid_0 = ET.SubElement(tax_residencies,'TaxResidency', attrib_tax_resid_0)

    attrib_title = {'code': 'FIRST HOLDER'}
    title = ET.SubElement(first_holder_details,'Title', attrib_title)

    if str(onb_help.get_country(onboard[0].tax_address.region.country)) == 'United States':
         attrib_w9 = {'customer_type': 'Individual',
                      'cert1': 'true',
                      'cert2': 'true',
                      'cert3': 'true',
                      'name': (str(onboard[0].client.user.first_name) + ' ' + str(onboard[0].client.user.last_name)),
                      'tin': onb_help.get_str_no_minus(onboard[0].identif_ssn),
                      'tin_type': str(onboard[0].tax_resid_0_tin_type),
                      'blank_form' : 'true',
                      'signature_type' : 'Electronic',
                      'proprietary_form_number' : '5002',
                      'tax_form_file' : 'Form5002.pdf'}
         w9 = ET.SubElement(first_holder_details,'W9', attrib_w9)

    else:
        attrib_w8_ben = {'part_2_9a_country' : str(onb_help.get_country(onboard[0].tax_address.region.country)),
                        'name' : (str(onboard[0].client.user.first_name) + ' ' + str(onboard[0].client.user.last_name)),
                        'signature_type' : 'Electronic',
                        'blank_form' : 'true'}
        tax_form = ET.SubElement(first_holder_details,'W8Ben', attrib_w8_ben)

    # SECOND HOLDER
    attrib_second_holder_details = {'external_id' : str(onboard[1].client.id)}
    second_holder_details = ET.SubElement(joint_holders,'SecondHolderDetails', attrib_second_holder_details)

    country_of_birth_second = ET.SubElement(second_holder_details,'CountryOfBirth')
    country_of_birth_second.text = str(onb_help.get_country(onboard[1].country_of_birth))

    dob_second = ET.SubElement(second_holder_details,'DOB')
    dob_second.text = str(onboard[1].date_of_birth)

    attrib_email_second = {'email': str(onboard[1].client.user.email)}
    email_second = ET.SubElement(second_holder_details,'Email', attrib_email_second)

    if onboard[1].ib_employment_status in (IB_EMPLOY_STAT_EMPLOYED,
                                               IB_EMPLOY_STAT_SELF_EMPLOYED):

        employment_details_second = ET.SubElement(second_holder_details,'EmploymentDetails')

        employer_second = ET.SubElement(employment_details_second,'employer')
        employer_second.text = str(onboard[1].client.employer)

        occupation_second = ET.SubElement(employment_details_second,'occupation')
        occupation_second.text = str(onb_help.get_occupation(onboard[1].client.occupation))

        employer_business_second = ET.SubElement(employment_details_second,'employer_business')
        employer_business_second.text = str(onb_help.get_industry_sector(onboard[1].client.industry_sector))

        attrib_employer_address_second =  {'state': str(onboard[1].employer_address.region.code),
                                           'street_2': str(onboard[1].employer_address.address2),
                                           'postal_code': str(onboard[1].employer_address.post_code),
                                           'country': str(onb_help.get_country(onboard[1].employer_address.region.country)),
                                           'street_1': str(onboard[1].employer_address.address1),
                                           'city': str(onboard[1].employer_address.city)}
        employer_address_second = ET.SubElement(employment_details_second,'employer_address', attrib_employer_address_second)

    employment_type_second = ET.SubElement(second_holder_details,'EmploymentType')
    employment_type_second.text = str(IB_EMPLOY_STATUSES[onboard[1].ib_employment_status][1])

    gender_second = ET.SubElement(second_holder_details,'Gender')
    gender_second.text = str(onboard[1].client.gender)

    attrib_identification_second = {'citizenship': str(onboard[1].identif_leg_citizenship),
                                    'LegalResidenceState': str(onboard[1].residential_address.region.code),
                                    'LegalResidenceCountry': str(onb_help.get_country(onboard[1].residential_address.region.country)),
                                    'SSN': onb_help.get_str_no_minus(onboard[1].identif_ssn)}

    identification_second = ET.SubElement(second_holder_details,'Identification', attrib_identification_second)

    marital_status_second = ET.SubElement(second_holder_details,'MaritalStatus')
    marital_status_second.text = str(onb_help.get_marital_status(onboard[1].client.civil_status))

    attrib_name_second = {'last': str(onboard[1].client.user.last_name),
                          'first': str(onboard[1].client.user.first_name),
                          'salutation': str(onboard[1].salutation),
                          'suffix': str(onb_help.get_suffix(onboard[1].suffix))}
    name_second = ET.SubElement(second_holder_details,'Name', attrib_name_second)

    num_dependents_second = ET.SubElement(second_holder_details,'NumDependents')
    num_dependents_second.text = str(onboard[1].num_dependents)

    attrib_ownership = {'percentage': '50'}
    ownership = ET.SubElement(second_holder_details,'Ownership', attrib_ownership)

    phones_second = ET.SubElement(second_holder_details,'Phones')
    attrib_phone_second = {'number': str(onboard[1].client.phone_num),
                           'type' : str(onboard[1].phone_type)}

    phone_second = ET.SubElement(phones_second,'Phone', attrib_phone_second)

    attrib_residence_second =  {'state': str(onboard[1].residential_address.region.code),
                                'street_2': str(onboard[1].residential_address.address2),
                                'postal_code': str(onboard[1].residential_address.post_code),
                                'country': str(onb_help.get_country(onboard[1].residential_address.region.country)),
                                'street_1': str(onboard[1].residential_address.address1),
                                'city': str(onboard[1].residential_address.city)}

    residence_second = ET.SubElement(second_holder_details,'Residence', attrib_residence_second)

    tax_residencies = ET.SubElement(second_holder_details,'TaxResidencies')
    attrib_tax_resid_0 = {'country': str(onb_help.get_country(onboard[1].tax_address.region.country)),
                          'tin_type': str(onboard[1].tax_resid_0_tin_type),
                          'tin': onb_help.get_str_no_minus(onboard[1].identif_ssn)}
    tax_resid_0 = ET.SubElement(tax_residencies,'TaxResidency', attrib_tax_resid_0)

    attrib_title_second = {'code': 'SECOND HOLDER'}
    second_title_second = ET.SubElement(second_holder_details,'Title', attrib_title_second)

    if str(onb_help.get_country(onboard[1].tax_address.region.country)) == 'United States':
         attrib_w9 = {'customer_type': 'Individual',
                      'cert1': 'true',
                      'cert2': 'true',
                      'cert3': 'true',
                      'name': (str(onboard[1].client.user.first_name) + ' ' + str(onboard[1].client.user.last_name)),
                      'tin': onb_help.get_str_no_minus(onboard[1].identif_ssn),
                      'tin_type': str(onboard[1].tax_resid_0_tin_type),
                      'blank_form' : 'true',
                      'signature_type' : 'Electronic',
                      'proprietary_form_number' : '5002',
                      'tax_form_file' : 'Form5002.pdf'}
         w9 = ET.SubElement(second_holder_details,'W9', attrib_w9)

    else:
        attrib_w8_ben = {'part_2_9a_country' : str(onb_help.get_country(onboard[1].tax_address.region.country)),
                        'name' : (str(onboard[1].client.user.first_name) + ' ' + str(onboard[1].client.user.last_name)),
                        'signature_type' : 'Electronic',
                        'blank_form' : 'true'}
        tax_form = ET.SubElement(second_holder_details,'W8Ben', attrib_w8_ben)

    # FINANCIAL INFORMATION
    attrib_fin_info = {'net_worth': str(onboard[0].fin_info_net_worth),
                        'liquid_net_worth': str(onboard[0].fin_info_liq_net_worth),
                        'annual_net_income': str(onboard[0].fin_info_ann_net_inc),
                        'total_assets': str(onboard[0].fin_info_tot_assets)}
    financial_information = ET.SubElement(joint_holders,'FinancialInformation', attrib_fin_info)

    investment_experience = ET.SubElement(financial_information,'InvestmentExperience')

    attrib_asset_experience_0 = {'trades_per_year': str(onboard[0].asset_exp_0_trds_per_yr),
                                 'years_trading': str(onboard[0].asset_exp_0_yrs ),
                                 'knowledge_level': onb_help.get_knowledge((onboard[0].asset_exp_0_knowledge)),
                                 'asset_class': 'FUND'}
    asset_experience_0 = ET.SubElement(investment_experience,'AssetExperience', attrib_asset_experience_0)

    attrib_asset_experience_1 = {'trades_per_year': str(onboard[0].asset_exp_1_trds_per_yr),
                                 'years_trading': str(onboard[0].asset_exp_1_yrs ),
                                 'knowledge_level': onb_help.get_knowledge((onboard[0].asset_exp_1_knowledge)),
                                 'asset_class': 'STK'}
    asset_experience_1 = ET.SubElement(investment_experience,'AssetExperience', attrib_asset_experience_1)

    if onboard[0].ib_employment_status not in (IB_EMPLOY_STAT_EMPLOYED,
                                                IB_EMPLOY_STAT_SELF_EMPLOYED):

        additional_source_of_income = ET.SubElement(financial_information,'AdditionalSourceOfIncome')

        attrib_other_income = {'source_type': str(SOURCE_OF_FUNDS_TYPES[onboard[0].other_income_source][1]).upper(),
                               'percentage': '100'}

        other_income = ET.SubElement(additional_source_of_income, 'SourceOfIncome', attrib_other_income)

    ''''
    investment_objectives = ET.SubElement(financial_information,'InvestmentObjectives')
    income = ET.SubElement(investment_objectives,'objective')
    income.text = 'Income'
    growth = ET.SubElement(investment_objectives,'objective')
    growth.text = 'Growth'
    preservation = ET.SubElement(investment_objectives,'objective')
    preservation.text = 'Preservation'
    '''

    # REGULATORY INFORMATION
    regulatory_details = ET.SubElement(joint_holders, 'RegulatoryInformation')
    
    attrib_reg_broker_deal = {'status' : str(onboard[0].reg_status_broker_deal).lower(),
                              'code' : 'BROKERDEALER'}
    
    attrib_reg_exch_memb = {'status' : str(onboard[0].reg_status_exch_memb).lower(),
                              'code' : 'EXCHANGEMEMBERSHIP'}

    attrib_reg_disp = {'status' : str(onboard[0].reg_status_disp).lower(),
                              'code' : 'DISPUTE'}

    attrib_reg_investig = {'status' : str(onboard[0].reg_status_investig).lower(),
                              'code' : 'INVESTIGATION'}

    if onboard[0].reg_status_stk_cont in ('1', '2', '3',):
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
    '''
    tax_residencies = ET.SubElement(joint_holders,'TaxResidencies')
    attrib_tax_resid_0 = {'country': str(onb_help.get_country(onboard[0].tax_address.region.country)),
                              'TIN_Type': str(onboard[0].tax_resid_0_tin_type),
                              'TIN': str(onboard[0].tax_resid_0_tin)}
    tax_resid_0 = ET.SubElement(tax_residencies,'TaxResidency', attrib_tax_resid_0)
    '''
    # Accounts                     
    accounts = ET.SubElement(application,'Accounts')

    attrib_account = {'external_id': str(onboard[0].client.id),
                      'margin': 'Cash',
                      'base_currency': 'USD',
                      'multicurrency': 'False'}
    account = ET.SubElement(accounts,'Account', attrib_account)

    trading_permissions = ET.SubElement(account,'TradingPermissions')

    attrib_trad_perm_0 = {'exchange_group': 'US-Sec'}
    trad_perm_0 = ET.SubElement(trading_permissions,'TradingPermission', attrib_trad_perm_0)

    attrib_trad_perm_1 = {'exchange_group': 'US-Funds'}
    trad_perm_1 = ET.SubElement(trading_permissions,'TradingPermission', attrib_trad_perm_1)

    investment_objectives = ET.SubElement(account,'InvestmentObjectives')
    income = ET.SubElement(investment_objectives,'objective')
    income.text = 'Income'
    growth = ET.SubElement(investment_objectives,'objective')
    growth.text = 'Growth'
    preservation = ET.SubElement(investment_objectives,'objective')
    preservation.text = 'Preservation'

    attrib_adv_wrap_fees = {'strategy': 'AUTOMATED'}
    adv_wrap_fees = ET.SubElement(account,'AdvisorWrapFees', attrib_adv_wrap_fees)

    attrib_auto_fees_det_0 = {'type': 'PERCENTOFEQUITY_MONTHLY',
                                  'max_fee':'0.25'}
    auto_fees_det_0 = ET.SubElement(adv_wrap_fees,'automated_fees_details', attrib_auto_fees_det_0)

    attrib_auto_fees_det_1 = {'type': 'INVOICE_LIMIT',
                                  'max_fee':'5000'}
    auto_fees_det_1 = ET.SubElement(adv_wrap_fees,'automated_fees_details', attrib_auto_fees_det_1)
    
    # Users
    users = ET.SubElement(application,'Users')

    attrib_user = {'external_individual_id': str(onboard[0].client.id),
                   'external_user_id': str(onboard[0].client.id),
                      'prefix': str(onb_help.get_prefix(onboard[0].client.user.last_name, onboard[0].client.user.first_name))}
    user_onboard = ET.SubElement(users,'User', attrib_user)

    # Documents
    documents = ET.SubElement(application, 'Documents')

    if str(onb_help.get_country(onboard[0].tax_address.region.country)) == 'United States':
        tax_forms = tax_forms_us
    else:
        tax_forms = tax_forms_non_us

    for dc in docs + tax_forms:
        attrib_doc = {'exec_ts' : onb_help.get_timestamp(onboard[0].doc_exec_ts),
                        'exec_login_ts' : onb_help.get_timestamp(onboard[0].doc_exec_login_ts),
                        'form_no' : onb_help.get_form_name(str(dc))}
        doc = ET.SubElement(documents,'Document', attrib_doc)

        doc_signed_by = ET.SubElement(doc, 'SignedBy')
        doc_signed_by.text = onboard[0].signature

        doc_signed_by = ET.SubElement(doc, 'SignedBy')
        doc_signed_by.text = onboard[1].signature

        file = onb_help.get_onboarding_path_to_files() + onb.DOCUMENTS + dc

        attrib_doc_attached_file = {'file_name' : str(dc),
                                      'sha1_checksum' : str(onb_help.get_sha1_checksum(file).hexdigest()),
                                      'file_length' :  str(os.path.getsize(file))}
        doc_attached_file = ET.SubElement(doc,'AttachedFile', attrib_doc_attached_file)
    
    return tree

