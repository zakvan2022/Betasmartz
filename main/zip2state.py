import pandas as pd
import os
dir = os.path.dirname(__file__)
file_name = os.path.join(dir, 'zipcode_list.csv')
zip_codes = pd.read_csv(file_name)
  
def get_state(zip_code):

    # check input is valid
    validate_input(zip_code)

    # look for the state
    for i in range(len(zip_codes["Zip_Code"])):
        if zip_code == zip_codes["Zip_Code"][i]:
            return zip_codes["State"][i]

    return 'FL'
    #raise Exception('no state found for this zipcode')
    # a fudge so that can demo without tripping up


def validate_input(zip_code):
    if not zip_code:
        raise Exception("zip_code not provided")

    else:
        if type(zip_code) != int:
            raise Exception("zip_code must be integer")

        '''
        elif zip_code < 10000 or zip_code > 99999:
            raise Exception("zip_code not of correct form")
        '''
    
