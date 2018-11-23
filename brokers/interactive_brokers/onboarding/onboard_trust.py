from brokers.interactive_brokers.onboarding import onboarding_helpers as onb_help
from brokers.interactive_brokers.onboarding import onboarding as onb
from main import constants
from main import abstract
from main import zip2state
import xml.etree.ElementTree as ET
import pdb
import os


def get_tree(onboard,
             docs,
             tax_forms_us,
             tax_forms_non_us):
    '''
    returns a new xml tree conforming to IB spec for trust applications
    '''
    uri = onb.URI
    ET.register_namespace('', uri)
    attrib_applications = {'xmlns':uri[1:-1]}
    applications = ET.Element('Applications', attrib_applications)
    tree = ET.ElementTree(applications)

    application = ET.SubElement(applications,'Application')

    # ACCOUNTS
    accounts = ET.SubElement(application,'Accounts')

    attrib_account = {'external_id': str(onboard.client.id),
                      'margin': 'Cash',
                      'base_currency': 'USD',
                      'multicurrency': 'false',}
    account = ET.SubElement(accounts,'Account', attrib_account)

    attrib_adv_wrap_fees = {'strategy': 'AUTOMATED'}
    adv_wrap_fees = ET.SubElement(account,'AdvisorWrapFees', attrib_adv_wrap_fees)

    attrib_auto_fees_det_0 = {'type': 'PERCENTOFEQUITY_MONTHLY',
                                  'max_fee':'0.25'}
    auto_fees_det_0 = ET.SubElement(adv_wrap_fees,'automated_fees_details', attrib_auto_fees_det_0)

    attrib_auto_fees_det_1 = {'type': 'INVOICE_LIMIT',
                                  'max_fee':'5000'}
    auto_fees_det_1 = ET.SubElement(adv_wrap_fees,'automated_fees_details', attrib_auto_fees_det_1)

    investment_objectives = ET.SubElement(account,'InvestmentObjectives')
    investment_trading = ET.SubElement(investment_objectives, 'objective')
    investment_trading.text = 'Income'
    investment_growth = ET.SubElement(investment_objectives, 'objective')
    investment_growth.text = 'Growth'
    investment_income = ET.SubElement(investment_objectives, 'objective')
    investment_income.text = 'Preservation'

    trading_permissions = ET.SubElement(account,'TradingPermissions')
    attrib_trad_perm_0 = {'exchange_group': 'US-Sec'}
    trad_perm_0 = ET.SubElement(trading_permissions,'TradingPermission', attrib_trad_perm_0)
    attrib_trad_perm_1 = {'exchange_group': 'US-Funds'}
    trad_perm_1 = ET.SubElement(trading_permissions,'TradingPermission', attrib_trad_perm_1)

    # CUSTOMER
    attrib_customer = {'email': str(onboard.client.user.email),
                       'external_id' :str(onboard.client.id),
                       'type' : 'TRUST',
                       'prefix': str(onb_help.get_prefix(onboard.client.user.last_name, onboard.client.user.first_name))}
    customer = ET.SubElement(application,'Customer', attrib_customer)

    # TRUST
    attrib_trust = {'third_party_mgmt': str(onboard.trst_third_party_mgmt)}
    trust = ET.SubElement(customer,'Trust', attrib_trust)

    # BENEFICIARIES
    beneficiaries = ET.SubElement(trust, 'Beneficiaries')

    attrib_benef_individual = {'same_mail_address': str(onboard.benef_same_address),
                                 'external_id' : str(onboard.benef_ext_id)}
    benef_individual = ET.SubElement(beneficiaries, 'Individual', attrib_benef_individual)

    country_of_birth = ET.SubElement(benef_individual,'CountryOfBirth')
    country_of_birth.text = str(onb_help.get_country(onboard.benef_country_of_birth))

    dob = ET.SubElement(benef_individual,'DOB')
    dob.text = str(onboard.benef_dob)

    attrib_email = {'email': str(onboard.benef_email)}
    email = ET.SubElement(benef_individual,'Email', attrib_email)

    if onboard.ib_employment_status in (IB_EMPLOY_STAT_EMPLOYED,
                                        IB_EMPLOY_STAT_SELF_EMPLOYED):

        employment_details = ET.SubElement(benef_individual,'EmploymentDetails')

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

    employment_type = ET.SubElement(benef_individual,'EmploymentType')
    employment_type.text = str(IB_EMPLOY_STATUSES[onboard.ib_employment_status][1])

    gender = ET.SubElement(benef_individual,'Gender')
    gender.text = str(onboard.client.gender)

    attrib_identification = {'citizenship': str(onb_help.get_country(onboard.identif_leg_citizenship)),
                             'LegalResidenceState': str(onboard.residential_address.region.code),
                             'LegalResidenceCountry': str(onb_help.get_country(onboard.residential_address.region.country)),
                             'SSN': onb_help.get_str_no_minus(onboard.identif_ssn)}
    identification = ET.SubElement(benef_individual,'Identification', attrib_identification)

    if not onboard.benef_same_address:
        attrib_benef_resid= {'country': str(onboard.benef_address.region.country),
                               'city': str(onboard.benef_address.city),
                               'postal_code': str(onboard.benef_address.post_code),
                               'street_1': str(onboard.benef_address.address1),
                               'street_2': str(onboard.benef_address.address2),
                               'state': str(onboard.benef_address.region.code)}
        benef_residence = ET.SubElement(benef_individual, 'Residence', attrib_benef_resid)

    marital_status = ET.SubElement(benef_individual,'MaritalStatus')
    marital_status.text = str(onb_help.get_marital_status(onboard.client.civil_status))

    attrib_benef_name = {'last': str(onboard.benef_last_name),
                         'first': str(onboard.benef_first_name),
                         'salutation': str(onboard.benef_salutation),
                         'suffix': str(onb_help.get_suffix(onboard.benef_suffix)),}
    benef_name = ET.SubElement(benef_individual, 'Name', attrib_benef_name)

    num_dependents = ET.SubElement(benef_individual,'NumDependents')
    num_dependents.text = str(onboard.num_dependents)

    phones = ET.SubElement(benef_individual,'Phones')

    attrib_phone = {'number': str(onboard.client.phone_num),
                    'type' : str(onboard.phone_type)}
    phone = ET.SubElement(phones,'Phone', attrib_phone)

    tax_residencies = ET.SubElement(benef_individual,'TaxResidencies')

    attrib_tax_resid_0 = {'country': str(onb_help.get_country(onboard.tax_address.region.country)),
                          'tin_type': str(onboard.tax_resid_0_tin_type),
                          'tin': onb_help.get_str_no_minus(onboard.identif_ssn)}
    tax_resid_0 = ET.SubElement(benef_individual,'TaxResidency', attrib_tax_resid_0)

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

    # FINANCIAL INFORMATION
    attrib_fin_info = {'net_worth': str(onboard.fin_info_net_worth),
                       'liquid_net_worth': str(onboard.fin_info_liq_net_worth),
                       'annual_net_income': str(onboard.fin_info_ann_net_inc),
                       'total_assets': str(onboard.fin_info_tot_assets),
                       'source_of_funds': str(onboard.source_inc_type),}
    financial_information = ET.SubElement(trust,'FinancialInformation', attrib_fin_info)

    if onboard.ib_employment_status not in (IB_EMPLOY_STAT_EMPLOYED,
                                        IB_EMPLOY_STAT_SELF_EMPLOYED):
        additional_source_of_income = ET.SubElement(financial_information,'AdditionalSourceOfIncome')
        attrib_other_income = {'source_type': str(SOURCE_OF_FUNDS_TYPES[onboard.other_income_source][1]).upper(),
                               'percentage': '100'}
        other_income = ET.SubElement(additional_source_of_income, 'SourceOfIncome', attrib_other_income)

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

    # GRANTORS
    grantors = ET.SubElement(trust, 'Grantors')

    attrib_grantors_individual = {'same_mail_address': str(onboard.grantors_same_address),
                                 'external_id' : str(onboard.grantors_ext_id)}
    grantors_individual = ET.SubElement(grantors, 'Individual', attrib_grantors_individual)

    grantors_dob = ET.SubElement(grantors_individual, 'DOB')
    grantors_dob.text = str(onboard.grantors_date_of_birth)

    attrib_grantors_identif = {'citizenship': str(onboard.grantors_citizenship),
                              'SSN': str(onboard.grantors_ssn),
                              'LegalResidenceCountry': str(onboard.grantors_leg_res_country),
                              'LegalResidenceState': str(onboard.grantors_leg_res_state),
                              'IssuingCountry': str(onboard.grantors_issuing_country),}
    grantors_identif = ET.SubElement(grantors_individual,'Identification', attrib_grantors_identif)

    attrib_grantors_name = {'last': str(onboard.grantors_last_name),
                           'first': str(onboard.grantors_first_name),
                           'salutation': str(onboard.grantors_salutation)}
    grantors_name = ET.SubElement(grantors_individual, 'Name', attrib_grantors_name)

    if not onboard.grantors_same_address:
        attrib_grantors_resid= {'country': str(onboard.grantors_address.region.country),
                               'city': str(onboard.grantors_address.city),
                               'postal_code': str(onboard.grantors_address.post_code),
                               'street_1': str(onboard.grantors_address.address1),
                               'street_2': str(onboard.grantors_address.address2),
                               'state': str(onboard.grantors_address.region.code)}
        grantors_residence = ET.SubElement(grantors_individual, 'Residence', attrib_grantors_resid)

    # IDENTIFICATION
    attrib_identification = {'date_formed': str(onboard.trst_date_formed),
                             'name': str(onboard.trst_name),
                             'purpose_of_trust': str(onboard.trst_purpose),
                             'registration_number': str(onboard.trst_reg_num),
                             'registration_type': str(onboard.trst_reg_type),
                             'registration_country': str(onboard.trst_reg_country),
                             'same_mail_address': str(onboard.trst_same_mail_address),
                             'type_of_trust': str(onboard.trst_type_of_trust),
                              'formation_state': str(onboard.trst_form_state),
                             'formation_country': str(onboard.trst_form_country),}
    identification = ET.SubElement(trust,'Identification', attrib_identification)

    attrib_identification_address = {'country': str(onboard.trst_address.region.country),
                                     'city': str(onboard.trst_address.city),
                                     'postal_code': str(onboard.trst_address.post_code),
                                     'street_1': str(onboard.trst_address.address1),
                                     'state': str(onboard.trst_address.region.code)}
    identification_address = ET.SubElement(identification,'Address', attrib_identification_address)

    # REGULATORY INFORMATION
    regulatory_details = ET.SubElement(trust, 'RegulatoryInformation')

    attrib_reg_affil = {'status': str(onboard.reg_status_affil),
                              'code': 'AFFILIATION'}
    reg_affil = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_affil)

    attrib_reg_memb = {'status': str(onboard.reg_status_memb),
                              'code': 'MEMBERSHIP'}
    reg_memb = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_memb)

    attrib_reg_disp = {'status': str(onboard.reg_status_disp),
                              'code': 'DISPUTE'}
    reg_disp = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_disp)

    attrib_reg_investig = {'status': str(onboard.reg_status_investig),
                              'code': 'INVESTIGATION'}
    reg_investig = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_investig)

    attrib_reg_stk_cont = {'status': str(onboard.reg_status_stk_cont),
                              'code': 'STOCKCONTROL'}
    reg_stk_cont = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_stk_cont)

    attrib_reg_ib_accounts = {'status': str(onboard.reg_status_ib_accounts),
                              'code' :'IBACCOUNTS'}
    reg_ib_accounts = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_ib_accounts)

    attrib_reg_criminal = {'status': str(onboard.reg_status_criminal),
                              'code': 'CRIMINAL'}
    reg_criminal = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_criminal)

    attrib_reg_reg_control = {'status': str(onboard.reg_status_reg_control),
                              'code': 'REGULATORYCONTROL'}
    reg_reg_control = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_reg_control)

    attrib_reg_broker_deal = {'status': str(onboard.reg_status_broker_deal),
                              'code': 'BROKERDEALER'}
    reg_broker_deal = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_broker_deal)

    attrib_reg_exch_memb = {'status': str(onboard.reg_status_exch_memb),
                              'code': 'EXCHANGEMEMBERSHIP'}
    reg_exch_memb = ET.SubElement(regulatory_details, 'RegulatoryDetail', attrib_reg_exch_memb)

    # TAX RESIDENCIES
    tax_residencies = ET.SubElement(trust,'TaxResidencies')
    attrib_tax_resid_0 = {'country': str(onb_help.get_country(onboard.tax_address.region.country)),
                          'tin_type': str(onboard.tax_resid_0_tin_type),
                          'tin': onb_help.get_str_no_minus(onboard.identif_ssn)}
    tax_resid_0 = ET.SubElement(tax_residencies,'TaxResidency', attrib_tax_resid_0)

    # TRUSTEES
    trustees = ET.SubElement(trust, 'Trustees')

    attrib_trustee_individual = {'same_mail_address': str(onboard.trustee_same_address),
                                 'external_id' : str(onboard.trustee_ext_id)}
    trustee_individual = ET.SubElement(trustees, 'Individual', attrib_trustee_individual)

    attrib_trustee_name = {'last': str(onboard.trustee_last_name),
                           'first': str(onboard.trustee_first_name),
                           'salutation': str(onboard.trustee_salutation),}
    trustee_name = ET.SubElement(trustee_individual, 'Name', attrib_trustee_name)

    trustee_dob = ET.SubElement(trustee_individual, 'DOB')
    trustee_dob.text = str(onboard.trustee_date_of_birth)

    attrib_trustee_email = {'email': str(onboard.trustee_email),}
    trustee_email = ET.SubElement(trustee_individual, 'Email', attrib_trustee_email)

    trustee_employee_title = ET.SubElement(trustee_individual, 'EmployeeTitle')
    trustee_employee_title.text = str(onboard.trustee_employee_title)

    attrib_trustee_identif = {'citizenship': str(onboard.trustee_citizenship),
                              'SSN': str(onboard.trustee_ssn),
                              'LegalResidenceCountry': str(onboard.trustee_leg_res_country),
                              'LegalResidenceState': str(onboard.trustee_leg_res_state),
                              'IssuingCountry': str(onboard.trustee_issuing_country),}
    trustee_identif = ET.SubElement(trustee_individual,'Identification', attrib_trustee_identif)

    trustee_is_nfa_reg = ET.SubElement(trustee_individual, 'IsNFA_Registsred')
    trustee_is_nfa_reg.text = str(onboard.trustee_is_nfa_reg)

    trustee_occupation = ET.SubElement(trustee_individual, 'Occupation')
    trustee_occupation.text = str(onboard.trustee_occupation)

    attrib_trustee_phones = {'primary': str(onboard.trustee_phone)}
    trustee_phones = ET.SubElement(trustee_individual, 'Phones', attrib_trustee_phones)

    if not onboard.trustee_same_address:
        attrib_trustee_resid= {'country': str(onboard.trustee_address.region.country),
                               'city': str(onboard.trustee_address.city),
                               'postal_code': str(onboard.trustee_address.post_code),
                               'street_1': str(onboard.trustee_address.address1),
                               'street_2': str(onboard.trustee_address.address2),
                               'state': str(onboard.trustee_address.region.code)}
        trustee_residence = ET.SubElement(trustee_individual, 'Residence', attrib_trustee_resid)

    # USERS
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
