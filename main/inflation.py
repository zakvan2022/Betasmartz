'''
monthly inflation (annualized), taken from 'Retirement Modelling
V4.xlsx' (tab 'Inflation Forecast')
'''
import pandas as pd
from dateutil.relativedelta import relativedelta
import os
  
def get_inflation():
    # check input is valid
    validate_input(inflation)

    for i in range(len(inflation)):
        if inflation['Month'][i].date() > pd.Timestamp('today').date():
            break

    inflation_forecast = [inflation['Annual_Inflation'][j] for j in range(i, len(inflation))]

    #add tail so that have enough future inflation to deal with users born in 2016 who live 300 years, etc

    inflation_forecast_tail = [inflation['Annual_Inflation'][len(inflation['Annual_Inflation']) - 1] for j in range(i, 300 * 12)]
    
    return inflation_forecast + inflation_forecast_tail

def validate_input(inflation):
    if len(inflation) == 0:
            raise Exception("inflation data is empty")

    if inflation['Month'][0].date() > pd.Timestamp('today').date() + relativedelta(months=1):
            raise Exception("inflation forecast is missing data for near months")


dir = os.path.dirname(__file__)
file_name = os.path.join(dir, 'inflation.csv')
inflation = pd.read_csv(file_name,parse_dates=['Month'] )
inflation_level = get_inflation()
