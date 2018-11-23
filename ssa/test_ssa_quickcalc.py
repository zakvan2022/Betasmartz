#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ssa import *


def test_ssa_quickcalc():
    """
    get_social_security_benefit(earnings, last_earn, last_year_earn,
                                retire_month, retire_year, dob_month,
                                dob_day, dob_year)

    should return the estimated retirement age, date, and amount
    """
    ret_age, ret_date, ret_amount = get_social_security_benefit(100000, 80000, 2014,
                                                                1, 2048, 4, 30, 1986)
    assert(ret_age == 62)
    assert(ret_date == 2048)
    assert(ret_amount == 6031.0)
    print('ssa.get_social_security_benefit is working as expected')


if __name__ == '__main__':
    test_ssa_quickcalc()
