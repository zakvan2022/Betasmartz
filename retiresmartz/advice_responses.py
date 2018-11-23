# -*- coding: utf-8 -*-
from main import constants
from main import tax_helpers as helpers
from datetime import datetime
from rest_framework.exceptions import ValidationError
import logging
logger = logging.getLogger('api.v1.retiresmartz.advice_responses')

# Retiresmartz Advice feed Logic Calls

# On Track / Off Track
def get_on_track(advice):
    return 'Well done. You are on track. If you would like to change any of \
your retirement details you can do so by clicking on bubbles on the chart to \
adjust when you want to retire and your life expectancy.'


def get_off_track(advice):
    return 'Ok, well we are going to have to make a few changes \
to get you back on track. I recommend making some changes to your \
retirement goal details by clicking on this or the previous screen. \
This will help you to plan to get on track to achieve your dream retirement.'


# Change Retirement Age
def get_decrease_retirement_age_to_62(advice):
    # TODO: Need to insert social security benefit in data
    # By increasing your retirement age to 70 your social \
    # security benefit would be estimated to be <estimated SS benefit \
    # multiplied by inflator>
    try:
        return "I see you have decreased your retirement age \
to 62. This will reduce your monthly benefit by 25% compared \
to if you retired at 66 giving you an estimated social security \
benefit of ${:,.2f} per month instead of ${:,.2f} if you chose to retire \
at 66. Social security benefits increase by up to 32% the longer \
you work.".format(helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 62),
                  helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 66))
    except ValidationError: # to handle ValidationError("age_now > future_age")   
        return ""

def get_decrease_retirement_age_to_63(advice):
    # TODO: Need to insert social security benefit in data
    #     By increasing your retirement age to 70 \
    # your social security benefit would be estimated to be \
    # <estimated SS benefit multiplied by inflator>
    try:
        return "I see you have decreased your retirement age to 63. \
This will reduce your monthly benefit by 20% compared to if \
you retired at 66 giving you an estimated social security \
benefit of ${:,.2f} per month instead of ${:,.2f} if you chose to \
retire at 66. Social security benefits increase by up to 32% \
the longer you work.".format(helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 63),
                             helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 66))
    except ValidationError: # to handle ValidationError("age_now > future_age")   
        return ""

def get_decrease_retirement_age_to_64(advice):
    # TODO: Need to insert social security benefit in data\
    #     By increasing your retirement age to 70 \
    # your social security benefit would be estimated to be \
    # <estimated SS benefit multiplied by inflator>
    try:
        return "I see you have decreased your retirement age to 64. \
This will reduce your monthly benefit by 13% compared to \
if you retired at 66 giving you an estimated social security \
benefit of ${:,.2f} per month instead of ${:,.2f} if you chose to \
retire at 66. Social security benefits increase by up to 32% \
the longer you work.".format(helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 64),
                             helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 66))
    except ValidationError: # to handle ValidationError("age_now > future_age")   
        return ""

def get_decrease_retirement_age_to_65(advice):
    # TODO: Need to insert social security benefit in data
    #     By increasing your retirement age to 70 \
    # your social security benefit would be estimated
    # to be <estimated SS benefit multiplied by inflator>
    try:
        return "I see you have decreased your retirement age to 65. \
This will reduce your monthly benefit by 7% compared to if \
you retired at 66 giving you an estimated social security \
benefit of ${:,.2f} per month instead of ${:,.2f} if you chose to \
retire at 66. Social security benefits increase by up to 32% \
the longer you work.".format(helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 65),
                             helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 66))
    except ValidationError: # to handle ValidationError("age_now > future_age")   
        return ""

def get_increase_retirement_age_to_67(advice):
    # TODO: Need to insert social security benefit in data
    try:
        return "I see you have increased your retirement age to 67. \
This will increase your monthly benefit by 8% to ${:,.2f} per \
month instead of ${:,.2f} if you chose to retire at 66. Increasing \
your retirement age will adjust the amount of social security \
benefits that you are able to obtain. Social security benefits \
increase by up to 32% the longer you work.".format(helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 67),
                                                   helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 66))
    except ValidationError: # to handle ValidationError("age_now > future_age")   
        return ""   

def get_increase_retirement_age_to_68(advice):
    # TODO: Need to insert social security benefit in data
    try:
        return "I see you have increased your retirement age to 68. \
This will increase your monthly benefit by 16% to ${:,.2f} per \
month instead of ${:,.2f} if you chose to retire at 66. Increasing \
your retirement age will adjust the amount of social security \
benefits that you are able to obtain. Social security benefits \
increase by up to 32% the longer you work.".format(helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 68),
                                                   helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 66))
    except ValidationError: # to handle ValidationError("age_now > future_age")   
        return ""

def get_increase_retirement_age_to_69(advice):
    # TODO: Need to insert social security benefit in data
    try:
        return "I see you have increased your retirement age to 69. \
This will increase your monthly benefit by 24% to ${:,.2f} per \
month instead of ${:,.2f} if you chose to retire at 66. Increasing \
your retirement age will adjust the amount of social security \
benefits that you are able to obtain. Social security benefits \
increase by up to 32% the longer you work.".format(helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 69),
                                                   helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 66))
    except ValidationError: # to handle ValidationError("age_now > future_age")   
        return ""
 
def get_increase_retirement_age_to_70(advice):
    # TODO: Need to insert social security benefit in data
    try:
        return "I see you have increased your retirement age to 70. \
This will increase your monthly benefit by 32% to ${:,.2f} per \
month instead of ${:,.2f} if you chose to retire at 66. Increasing \
your retirement age will adjust the amount of social security \
benefits that you are able to obtain. Social security benefits \
increase by up to 32% the longer you work.".format(helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 70),
                                                   helpers.get_ss_benefit_future_dollars(advice.plan.client.ss_fra_todays, advice.plan.client.date_of_birth, 66))
    except ValidationError: # to handle ValidationError("age_now > future_age")   
        return ""

# Life Expectancy
def get_manually_adjusted_age(advice):
    return 'Your retirement age has been updated. \
Let us know if anything else changes in your wellbeing \
profile by clicking on the life expectancy bubble.'


def get_smoking_yes(advice):
    return 'You could improve your life expectancy score \
by quitting smoking.'


def get_quitting_smoking(advice):
    # {formula = (Current Age – 18)/42]*7.7 or 7.3 years}
    formula = ((advice.plan.client.age - 18) / 42) * 7.7
    return "We will add this to your life expectancy. \
Based on your age we will add {} years to your life expectancy.".format(formula)


def get_smoking_no(advice):
    return "By not smoking you're already increasing your \
life expectancy by 7 years."


def get_drinks_more_than_one(advice):
    if advice.plan.client.gender == constants.GENDER_MALE:
        diff = 2.2
    else:
        diff = 1.8
    return 'You could improve your life expectancy by up to %s years \
by drinking only one alcoholic beverage a day' % diff


def get_drinks_one_or_less(advice):
    if advice.plan.client.gender == constants.GENDER_MALE:
        diff = 2.2
    else:
        diff = 1.8
    return 'By consuming less alcoholic beverages you\'re already increasing \
your life expectancy by over %s years' % diff


def get_exercise_only(advice):
    return "Thanks for telling us about the exercise you do. Exercise \
does impact your life expectancy. Regular exercise for at \
least 20 minutes each day 5 times a week increases your \
life expectancy by up to 3.2 years."


def get_weight_and_height_only(advice):
    return "Thanks for telling us your weight and height. \
These combined details help us better understand your life expectancy."


def get_combination_of_more_than_one_entry_but_not_all(advice):
    return "Thanks for providing more wellbeing information. This helps us \
better understand your life expectancy. By completing all of the \
details we can get an even more accurate understanding."


def get_all_wellbeing_entries(advice):
    return "Thanks for providing your wellbeing information. This gives us \
the big picture and an accurate understanding of your life expectancy."


# Risk Slider
def get_protective_move(advice):
    # TODO: Need to add risk and amounts
    """
    This might reduce the returns from your portfolio or increase \
    the amount you need to contribute from your paycheck each month \
    from <previous amount> to <new amount>
    """
    risk = round(advice.plan.recommended_risk, 2)
    if risk == 1.0:
        risk = 100
    elif risk == 0.9:
        risk = 90
    elif risk == 0.8:
        risk = 80
    elif risk == 0.7:
        risk = 70
    elif risk == 0.6:
        risk = 60
    elif risk == 0.5:
        risk == 50
    elif risk == 0.4:
        risk == 40
    elif risk == 0.3:
        risk = 30
    elif risk == 0.2:
        risk = 20
    elif risk == 0.1:
        risk = 10
    else:
        risk = str(risk)[2:]
    return "I can see you have adjusted your risk profile to be more \
protective. We base your risk profile on the risk questionnaire \
you completed and determined your score to be {}. By adjusting the slider you \
change the asset allocation in your retirement goal.".format(str(risk))


def get_dynamic_move(advice):
    # TODO: Need to add risk and amounts
    """
    This might increase the returns from your portfolio and decrease the amount \
    you need to contribute from your paycheck each month from <previous amount> \
    to <new amount>
    """
    risk = round(advice.plan.recommended_risk, 2)
    if risk == 1.0:
        risk = 100
    elif risk == 0.9:
        risk = 90
    elif risk == 0.8:
        risk = 80
    elif risk == 0.7:
        risk = 70
    elif risk == 0.6:
        risk = 60
    elif risk == 0.5:
        risk == 50
    elif risk == 0.4:
        risk == 40
    elif risk == 0.3:
        risk = 30
    elif risk == 0.2:
        risk = 20
    elif risk == 0.1:
        risk = 10
    else:
        risk = str(risk)[2:]
    return "I can see you have adjusted your risk profile to be more dynamic. \
We base your risk profile on the risk questionnaire you completed and \
determined your score to be {}. By adjusting the slider you change the asset allocation \
in your retirement goal.\nYou will be taking more risk.".format(str(risk))


# Contributions / Spending
def get_increase_spending_decrease_contribution(advice, diff_now, diff_later):
    # TODO: Need to add $X and $Y calculations, max_contributions needs to come in
    # if advice.plan.client.account.account_type == constants.ACCOUNT_TYPE_401K or \
    #    advice.plan.client.account.account_type == constants.ACCOUNT_TYPE_ROTH401K:
    #     # [If 401K we need to remember here that for a person under 50 the
    #     # maximum contribution amount is $18,000 per annum and $24,000
    #     # if they are over 50]
    #     if advice.plan.client.age < 50:
    #         max_contribution = 18000
    #     else:
    #         max_contribution = 24000

    rv = "Hey big spender! I can see you want to spend a bit more. \
If you decreased your spending by ${:,.2f} a month, you could increase your \
retirement income by ${:,.2f} a month.".format(diff_now / 12, diff_later / 12)
    if advice.plan.client.employment_status == constants.EMPLOYMENT_STATUS_EMMPLOYED:
        rv += " Your employer will match these contributions making it easier to reach your goal."

    return rv


def get_increase_contribution_decrease_spending(advice, contrib, income):
    return "Well done, by increasing your retirement contributions to ${:,.2f} \
a month, you have increased your retirement income by ${:,.2f} a month.".format(contrib / 12., income / 12.)


def get_increase_spending_decrease_contribution_again(advice, contrib, income):
    # TODO: Need to add $X and $Y calculations
    return "Are you sure you need to increase your spending again and reduce your \
retirement contributions? Just think, if your contributions stayed \
at ${:,.2f} a month, you would be ${:,.2f} a month better off in retirement.".format(contrib / 12., income / 12.)


def get_off_track_item_adjusted_to_on_track(advice):
    years = advice.plan.retirement_age - advice.plan.client.age
    return "Well done, by adjusting your details your retirement goal is now on track.\n\
We want to make sure our advice keeps you on track so that when you retire \
in {} there are no nasty surprises. If you would like to change or see the \
impact of any of your choices, you can make changes to your details on \
this dashboard.".format(datetime.now().date().year + years)


def get_on_track_item_adjusted_to_off_track(advice):
    return "Uh oh, you are now off track to achieve your retirement goal. \
We are here to give you’re the advice to ensure you get on track. \
You may want to reconsider the changes you have made to your details \
to get your retirement goal back on track."
