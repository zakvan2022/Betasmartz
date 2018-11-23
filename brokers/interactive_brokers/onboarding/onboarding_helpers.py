import hashlib
import time
import os
from . import onboarding as onboard
from main import constants
from address.constants import COUNTRY_CHOICES
from main import abstract

def get_sha1_checksum(file):
    '''
    returns sha1 checksum
    '''
    BUF_SIZE = 65536
    sha1 = hashlib.sha1()

    with open(file, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1


def set_modified_element(rt, params):
    '''
    sets to 'val' the attribute of element in root 'rt' with position 'pos'
    '''
    val, pos = params
    if len(pos) == 1:
        rt[pos[0]].text = str(val)
    elif len(pos) == 2:
        rt[pos[0]][pos[1]].text = str(val)
    elif len(pos) == 3:
        rt[pos[0]][pos[1]][pos[2]].text = str(val)
    elif len(pos) == 4:
        rt[pos[0]][pos[1]][pos[2]][pos[3]].text = str(val)
    elif len(pos) == 5:
        rt[pos[0]][pos[1]][pos[2]][pos[3]][pos[4]].text = str(val)
    elif len(pos) == 6:
        rt[pos[0]][pos[1]][pos[2]][pos[3]][pos[4]][pos[5]].text = str(val)
    elif len(pos) == 7:
        rt[pos[0]][pos[1]][pos[2]][pos[3]][pos[4]][pos[5]][pos[6]].text = str(val)
    elif len(pos) == 8:
        rt[pos[0]][pos[1]][pos[2]][pos[3]][pos[4]][pos[5]][pos[6]][pos[7]].text = str(val)


def set_modified_val(rt, params):
    '''
    sets to 'val' the value of item with key 'ky' for the element in root 'rt' with position 'pos'
    '''
    val, ky, pos = params
    if len(pos) == 1:
        rt[pos[0]].attrib[ky] = val
    elif len(pos) == 2:
        rt[pos[0]][pos[1]].attrib[ky] = val
    elif len(pos) == 3:
        rt[pos[0]][pos[1]][pos[2]].attrib[ky] = val
    elif len(pos) == 4:
        rt[pos[0]][pos[1]][pos[2]][pos[3]].attrib[ky] = val
    elif len(pos) == 5:
        rt[pos[0]][pos[1]][pos[2]][pos[3]][pos[4]].attrib[ky] = val
    elif len(pos) == 6:
        rt[pos[0]][pos[1]][pos[2]][pos[3]][pos[4]][pos[5]].attrib[ky] = val
    elif len(pos) == 7:
        rt[pos[0]][pos[1]][pos[2]][pos[3]][pos[4]][pos[5]][pos[6]].attrib[ky] = val
    elif len(pos) == 8:
        rt[pos[0]][pos[1]][pos[2]][pos[3]][pos[4]][pos[5]][pos[6]][pos[7]].attrib[ky] = val


def get_prefix(last_name, first_name):
    '''
    5 or more lowercase letters which will be used to create the client's username.
    IB will add 3 or 4 numbers to the prefix to create the username.

    Below function attempts to construct 5 letter lower case prefix from last_name and
    first_name. If not enough letters are available, dummy_prefix is used. If the resulting
    prefix contains any non alphabetic these are replaced by 'b'.
    '''
    dummy_prefix = 'abcde'
    prefix = ''
    if len(last_name) >= 5:
        prefix = last_name[:5]
    elif len(last_name) == 4 and len(first_name) >= 1:
        prefix = last_name + first_name[:1]
    elif len(last_name) == 3 and len(first_name) >= 2:
        prefix = last_name + first_name[:2]
    elif len(last_name) == 2 and len(first_name) >= 3:
        prefix = last_name + first_name[:3]
    elif len(last_name) == 1 and len(first_name) >= 4:
        prefix = last_name + first_name[:4]
    elif len(last_name) == 0 and len(first_name) >= 5:
        prefix = last_name + first_name[:5]
    else:
        prefix = dummy_prefix

    prefix = ''.join([c if c.isalpha() else 'x' for c in prefix])

    return prefix.lower()


def show_tree(root):
    '''
    shows up to the top 8 elements in root
    '''
    for i in range(len(root)):
        print(i, root[i].tag, root[i].text, root[i].attrib)
        for j in range(len(root[i])):
            print(i, j, root[i][j].tag, root[i][j].text, root[i][j].attrib)
            for k in range(len(root[i][j])):
                print(i, j, k, root[i][j][k].tag, root[i][j][k].text, root[i][j][k].attrib)
                for m in range(len(root[i][j][k])):
                    print(i, j, k, m, root[i][j][k][m].tag, root[i][j][k][m].text, root[i][j][k][m].attrib)
                    for n in range(len(root[i][j][k][m])):
                        print(i, j, k, m, n, root[i][j][k][m][n].tag, root[i][j][k][m][n].text, root[i][j][k][m][n].attrib)
                        for p in range(len(root[i][j][k][m][n])):
                            print(i, j, k, m, n, p, root[i][j][k][m][n][p].tag, root[i][j][k][m][n][p].text, root[i][j][k][m][n][p].attrib)
                            for q in range(len(root[i][j][k][m][n][p])):
                                print(i, j, k, m, n, p, q, root[i][j][k][m][n][p][q].tag, root[i][j][k][m][n][p][q].text, root[i][j][k][m][n][p][q].attrib)
                                for r in range(len(root[i][j][k][m][n][p][q])):
                                    print(i, j, k, m, n, p, q, r, root[i][j][k][m][n][p][q][r].tag, root[i][j][k][m][n][p][q][r].text, root[i][j][k][m][n][p][q][r].attrib)
                                    print('--- NB there may be more levels with child elements, but these will not be shown ---')


def get_address(full_address):
    '''
    returns address from full_address
    '''
    ads = [x for x in full_address.split(',') if x != '']
    if len(ads) >= 2:
        return ads[0]
    else:
        return full_address


def get_zip_code(plan):
    '''
    returns zip code from plan
    '''
    try:
        if not plan.retirement_postal_code:
            return int(plan.client.residential_address.post_code)
        else:
            return int(plan.retirement_postal_code)
    except:
        raise Exception("no valid zip code provided")


def get_country(country):
    '''
    returns full text name for country
    '''
    cs = [c for (code, c) in COUNTRY_CHOICES if code == country]
    try:
        return cs[0]
    except:
        raise Exception("country not found in COUNTRY_CHOICES")


def get_suffix(suffix):
    '''
    returns '' if suffix is None
    '''
    if not suffix:
        return ''
    else:
        return suffix


def get_employment_type(plan):
    '''
    returns 'EMPLOYED', 'UNEMPLOYED', 'SELF EMPLOYED', 'RETIRED', or 'NOT LABORFORCE'
    depening on value of plan.employment_status
    '''
    employment_status = plan.employment_status
    
    if employment_status == constants.EMPLOYMENT_STATUS_EMMPLOYED:
        return 'EMPLOYED'

    elif employment_status == constants.EMPLOYMENT_STATUS_UNEMPLOYED:
        return 'UNEMPLOYED'

    elif employment_status == constants.EMPLOYMENT_STATUS_SELF_EMPLOYED:
        return 'SELFEMPLOYED'

    elif employment_status == constants.EMPLOYMENT_STATUS_RETIRED:
        return 'RETIRED'

    elif employment_status == constants.EMPLOYMENT_STATUS_NOT_LABORFORCE:
        return 'ATHOMETRADER'

    else:
        raise Exception('employment_status not handled')


def get_form_name(dc):
    '''
    returns document name in required form
    '''
    try:
        elem = dc.split('.')
        return str(elem[0])[4:]
    except:
        raise Exception('Failed forming document name')


def get_industry_sector(industry_sector):
    betasm_to_ib_industry_dict = {
        'Agriculture, Forestry, Fishing and Hunting':'Agriculture',
        'Mining, Quarrying, and Oil and Gas Extraction':'Oil and Gas',
        'Construction':'Construction',
        'Manufacturing':'Manufacturing',
        'Wholesale Trade':'Wholesale',
        'Retail Trade ':'Retail',
        'Transportation and Warehousing':'Transportation',
        'Utilities':'Other',
        'Information':'Information Technology',
        'Finance and Insurance ':'Banking',
        'Real Estate and Rental and Leasing ':'Real Estate',
        'Real Estate ':'Real Estate',
        'Professional, Scientific, and Technical Services ':'Professional Services',
        'Management of Companies and Enterprises ':'Management',
        'Administrative and Support and Waste Management and Remediation Services':'Service',
        'Educational Services':'Education',
        'Health Care and Social Assistance':'Healthcare',
        'Arts, Entertainment, and Recreation':'Sports-Entertainment',
        'Accommodation and Food Services ':'Restaurant-Food Service',
        'Other Services':'Other'
        }

    for ind in constants.INDUSTRY_TYPES:
        if industry_sector == ind[0]:
            return betasm_to_ib_industry_dict[ind[1]]
    raise Exception('Unhandled industry_sector.')

def get_marital_status(civil_status):
    '''
    returns 'S', 'M' or 'U', depening on value of filing_status
    '''
    filing_status = abstract.PersonalData.CivilStatus(civil_status)
    
    if filing_status == abstract.PersonalData.CivilStatus['SINGLE']:
        return 'S'

    elif filing_status == abstract.PersonalData.CivilStatus['MARRIED_FILING_SEPARATELY_LIVED_TOGETHER']:
        return 'M'

    elif filing_status == abstract.PersonalData.CivilStatus['MARRIED_FILING_SEPARATELY_NOT_LIVED_TOGETHER']:
        return 'M'

    elif filing_status == abstract.PersonalData.CivilStatus['HEAD_OF_HOUSEHOLD']:
        return  'M'
          
    elif filing_status == abstract.PersonalData.CivilStatus['QUALIFYING_WIDOWER']:
        return 'W'

    elif filing_status == abstract.PersonalData.CivilStatus['MARRIED_FILING_JOINTLY']:
        return 'M'

    else:
        raise Exception('filing_status not handled')


def get_occupation(occupation):
    for occ in constants.OCCUPATION_TYPES:
        if occupation == occ[0]:
            return occ[1]
    raise Exception('Unhandled occupation.')


def get_knowledge(exp):
    '''
    returns experience from numeric value of exp
    '''
    if exp in [0, 1, 2, 3]:
        return "Limited"
    elif exp in [4, 5, 6, 7]:
        return "Good"
    elif exp in [8, 9, 10]:
        return "Extensive"
    else:
        raise Exception('Unhandled exp value')
    
def get_onboarding_path_to_files():
    '''
    returns path to onboarding files
    '''
    dir = os.path.dirname(__file__)
    return os.path.join(dir, onboard.PATH)

def get_str_no_minus(string_in):
    '''
    returns string by stripping out minuses from string_in
    '''
    try:
        return string_in.replace('-','')
    except:
        raise Exception('Failed removing separator')

def get_timestamp(timestamp):
    '''
    returns timestamp in required form
    '''
    try:
        elem = str(timestamp).split('.')
        dt_tm = str(elem[0]).split(' ')
        dt_tm_str = dt_tm[0] + dt_tm[1]
        return dt_tm_str.replace(':', '').replace('-','')
    except:
        raise Exception('Failed forming timestamp')

def get_joint_type(joint_type):
    '''
    returns joint_type in format expected by IB
    '''
    if joint_type == 1:
        return 'community'
    elif joint_type == 2:
        return 'joint_tenants'
    elif joint_type == 3:
        return 'tbe'
    elif joint_type == 4:
        return 'tenants_common'
    else:
        raise Exception('Unhandled joint_type')

def is_test():
    '''
    returns true if detects being run as a unit test (detection is based on
    directory from which command run).
    '''
    if os.getcwd() != '/': 
        print('WARNING: FTP upload to IB disabled because unit test detected. ** Is this is a unit test? **')
        return True
    else:
        return False
    
    


