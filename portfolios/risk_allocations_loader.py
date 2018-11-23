import pandas as pd
import json

def get_allocation(path):
    '''
    reads csv file, checking the columns add up to exactly 1,
    and then reads file contents into json object in format
    required for risk allocations used in
    '''
    df = pd.DataFrame.from_csv(path=path, header=0, index_col=0)

    for col in df.keys():
        col_sum = 0
        for row in df[col]:
            col_sum = col_sum + float(row)
        if round(col_sum, 10) != 1:
            print('WARNING: {} - column {}: sum is not equal to 1 ({}).'.format(str(path), str(col), str(col_sum)))

    js = df.to_json()
    return str(js)
