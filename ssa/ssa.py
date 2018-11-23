# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import logging
logger = logging.getLogger('ssa.ssa')


def parse_retirement_paragraph(soup):
    """
    given beautiful soup from quickcalc return the
    retirement int age, int date (year) and float amount
    """
    ret_age = int(soup.find(id='ret_age').string.split(' ')[0])
    ret_date = int(soup.find(id='ret_date').string.strip(' '))
    ret_amount = float(soup.find(id='ret_amount').string.strip(' ').replace(',', ''))
    return ret_age, ret_date, ret_amount


def ssa_quickcalc_soup(earnings, last_earn, last_year_earn,
                       retire_month, retire_year, dob_month,
                       dob_day, dob_year):
    """
    submits post to quickcalc script and returns beautiful
    soup of response
    """
    url = 'https://www.ssa.gov/cgi-bin/benefit6.cgi'
    data = {
        'earnings': earnings,
        'retiremonth': retire_month,
        'retireyear': retire_year,
        'lastEarn': last_earn,
        'lastYearEarn': last_year_earn,
        'dobmon': dob_month,  # dob month
        'dobday': dob_day,  # dob day
        'yob': dob_year,  # dob year
    }
    r = requests.post(url, data)
    soup = BeautifulSoup(r.content, 'html.parser')
    return soup


def get_social_security_benefit(earnings, last_earn, last_year_earn,
                                retire_month, retire_year, dob_month,
                                dob_day, dob_year):
    soup = ssa_quickcalc_soup(earnings, last_earn, last_year_earn,
                              retire_month, retire_year, dob_month,
                              dob_day, dob_year)
    ret_age, ret_date, ret_amount = parse_retirement_paragraph(soup)
    return ret_age, ret_date, ret_amount
