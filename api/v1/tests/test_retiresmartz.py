from datetime import date, datetime
from ujson import loads
from unittest import mock, skip
from unittest.mock import MagicMock
from dateutil.relativedelta import relativedelta
from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APITestCase
from api.v1.tests.factories import ExternalAssetFactory, MarkowitzScaleFactory, MarketIndexFactory, \
    PortfolioSetFactory, RetirementStatementOfAdviceFactory, EmailInviteFactory
from common.constants import GROUP_SUPPORT_STAFF
from main.management.commands.populate_test_data import populate_prices, populate_cycle_obs, populate_cycle_prediction, \
    populate_inflation
from goal.models import GoalSetting, GoalMetricGroup, GoalMetric
from portfolios.models import InvestmentType
from activitylog.models import ActivityLogEvent
from activitylog.event import Event
from main.tests.fixture import Fixture1
from retiresmartz.models import RetirementPlan
from .factories import AssetClassFactory, ContentTypeFactory, GroupFactory, \
    RetirementPlanFactory, TickerFactory, RetirementAdviceFactory
from django.utils import timezone
from pinax.eventlog.models import log
from retiresmartz.calculator.social_security import calculate_payments
from main import constants
from main import abstract
from statements.models import PDFStatement
import pandas as pd
import os
from django.conf import settings

mocked_now = datetime(2016, 1, 1)

class RetiresmartzTests(APITestCase):
    def setUp(self):
        self.support_group = GroupFactory(name=GROUP_SUPPORT_STAFF)
        self.base_plan_data = {
            "name": "Personal Plan",
            "description": "My solo plan",
            'desired_income': 60000,
            'income': 80000,
            'volunteer_days': 1,
            'paid_days': 2,
            'same_home': True,
            'reverse_mortgage': True,
            'expected_return_confidence': 0.5,
            'max_employer_match_percent': 0.04,
        }

        self.expected_tax_transcript_data = {
            'name_spouse': 'MELISSA',
            'SSN_spouse': '477-xx-xxxx',
            'address': {
                'address1': '200 SAMPLE RD',
                'address2': '',
                'city': 'HOT SPRINGS',
                'post_code': '33XXX',
                'state': 'AR'
            },
            'name': 'DAMON M MELISSA',
            'SSN': '432-xx-xxxx',
            'filing_status': 'Married Filing Joint',
            'total_income': '67,681.00',
            'total_payments': '7,009.00',
            'earned_income_credit': '0.00',
            'combat_credit': '0.00',
            'add_child_tax_credit': '0.00',
            'excess_ss_credit': '0.00',
            'refundable_credit': '2,422.00',
            'premium_tax_credit': '',
            'adjusted_gross_income': '63,505.00',
            'taxable_income': '40,705.00',
            'blind': 'N',
            'blind_spouse': 'N',
            'exemptions': '4',
            'exemption_amount': '12,800.00',
            'tentative_tax': '5,379.00',
            'std_deduction': '10,000.00',
            'total_adjustments': '4,176.00',
            'tax_period': 'Dec. 31, 2005',
            'se_tax': '6,052.00',
            'total_tax': '9,431.00',
            'total_credits': '2,000.00',
        }

        self.expected_social_security_statement_data = {
            'EmployerPaidThisYearMedicare': '1,177',
            'EmployerPaidThisYearSocialSecurity': '5,033',
            'EstimatedTaxableEarnings': '21,807',
            'LastYearMedicare': '21,807',
            'LastYearSS': '21,807',
            'PaidThisYearMedicare': '1,177',
            'PaidThisYearSocialSecurity': '4,416',
            'RetirementAtAge62': '759',
            'RetirementAtAge70': '1,337',
            'RetirementAtFull': '1,078',
            'SurvivorsChild': '808',
            'SurvivorsSpouseAtFull': '1,077',
            'SurvivorsSpouseWithChild': '808',
            'SurvivorsTotalFamilyBenefitsLimit': '1,616',
            'date_of_estimate': 'January 2, 2016',
        }
        # Mocked to speed up tests, no need run them every time
        RetirementPlan.send_plan_agreed_email = MagicMock()
        PDFStatement.save_pdf = MagicMock()

    def tearDown(self):
        self.client.logout()

    def test_update_plan_date_of_estimate(self):
        plan = RetirementPlanFactory.create(calculated_life_expectancy=92)
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        expected_date = timezone.now().date()
        data = {
            'date_of_estimate': expected_date,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Updating retirement plan with date_of_estimate returns OK')
        self.assertNotEqual(response.data['date_of_estimate'], None,
                            msg='date_of_estimate is in the response and not None')
        lookup_plan = RetirementPlan.objects.get(id=plan.id)
        self.assertEqual(lookup_plan.date_of_estimate, expected_date,
                         msg='date_of_estimate matches expected date')

    def test_retirement_plan_upload_endpoint(self):
        invite = EmailInviteFactory.create(user=Fixture1.client1().user)  # user needs an associated invite
        url = '/api/v1/clients/{}/retirement-plans/upload'.format(invite.user.client.id)
        self.client.force_authenticate(user=invite.user)
        with open(os.path.join(settings.BASE_DIR, 'pdf_parsers', 'samples', 'sample_2006.pdf'), mode="rb") as tax_transcript:
            data = {
                'tax_transcript': tax_transcript
            }
            response = self.client.put(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Updating retirement plan with tax_transcript PDF returns OK')
        # self.assertNotEqual(response.data['tax_transcript'], None,
        #                     msg='tax_transcript is in the response and not None')
        self.assertNotEqual(response.data['tax_transcript_data'], None,
                            msg='tax_transcript_data is in the response and not None')
        self.assertEqual(response.data['tax_transcript_data'], self.expected_tax_transcript_data,
                         msg='Parsed tax_transcript_data matches expected')

        with open(os.path.join(settings.BASE_DIR, 'pdf_parsers', 'samples', 'ssa-7005-sm-si_wanda_worker_young.pdf'), mode="rb") as ss_statement:
            data = {
                'social_security_statement': ss_statement
            }
            response = self.client.put(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Updating retirement plan with tax_transcript PDF returns OK')
        self.assertNotEqual(response.data['social_security_statement_data'], None,
                            msg='social_security_statement_data is in the response and not None')
        self.assertEqual(response.data['social_security_statement_data'], self.expected_social_security_statement_data,
                         msg='Parsed social_security_statement_data matches expected')

        with open(os.path.join(settings.BASE_DIR, 'pdf_parsers', 'samples', 'ssa-7005-sm-si_wanda_worker_young.pdf'), mode="rb") as ss_statement:
            data = {
                'partner_social_security_statement': ss_statement
            }
            response = self.client.put(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Updating retirement plan with tax_transcript PDF returns OK')
        self.assertNotEqual(response.data['partner_social_security_statement_data'], None,
                            msg='partner_social_security_statement_data is in the response and not None')
        self.assertEqual(response.data['partner_social_security_statement_data'], self.expected_social_security_statement_data,
                         msg='Parsed partner_social_security_statement_data matches expected')

        self.assertEqual(response._headers['content-type'], ('Content-Type', 'application/json'),
                         msg='Response content type is application/json after upload')

    def test_update_plan_with_pdf_uploads(self):
        plan = RetirementPlanFactory.create(calculated_life_expectancy=92)
        invite = EmailInviteFactory.create(user=plan.client.user)  # user needs an associated invite
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=Fixture1.client1().user)

        with open(os.path.join(settings.BASE_DIR, 'pdf_parsers', 'samples', 'sample_2006.pdf'), mode="rb") as tax_transcript:
            data = {
                'tax_transcript': tax_transcript
            }
            response = self.client.put(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Updating retirement plan with tax_transcript PDF returns OK')
        # self.assertNotEqual(response.data['tax_transcript'], None,
        #                     msg='tax_transcript is in the response and not None')
        self.assertNotEqual(response.data['tax_transcript_data'], None,
                            msg='tax_transcript_data is in the response and not None')
        self.assertEqual(response.data['tax_transcript_data'], self.expected_tax_transcript_data,
                         msg='Parsed tax_transcript_data matches expected')

        with open(os.path.join(settings.BASE_DIR, 'pdf_parsers', 'samples', 'ssa-7005-sm-si_wanda_worker_young.pdf'), mode="rb") as ss_statement:
            data = {
                'social_security_statement': ss_statement
            }
            response = self.client.put(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Updating retirement plan with tax_transcript PDF returns OK')
        self.assertNotEqual(response.data['social_security_statement_data'], None,
                            msg='social_security_statement_data is in the response and not None')
        self.assertEqual(response.data['social_security_statement_data'], self.expected_social_security_statement_data,
                         msg='Parsed social_security_statement_data matches expected')

        with open(os.path.join(settings.BASE_DIR, 'pdf_parsers', 'samples', 'ssa-7005-sm-si_wanda_worker_young.pdf'), mode="rb") as ss_statement:
            data = {
                'partner_social_security_statement': ss_statement
            }
            response = self.client.put(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg='Updating retirement plan with tax_transcript PDF returns OK')
        self.assertNotEqual(response.data['partner_social_security_statement_data'], None,
                            msg='partner_social_security_statement_data is in the response and not None')
        self.assertEqual(response.data['partner_social_security_statement_data'], self.expected_social_security_statement_data,
                         msg='Parsed partner_social_security_statement_data matches expected')

        self.assertEqual(response._headers['content-type'], ('Content-Type', 'application/json'),
                         msg='Response content type is application/json after upload')

    def test_add_plan_with_client_field_updates(self):
        '''
        Tests:
        - clients can create a retirement plan.
        - specifying btc on creation works
        '''
        url = '/api/v1/clients/{}/retirement-plans'.format(Fixture1.client1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        start_time = timezone.now() + relativedelta(years=40)
        data = self.base_plan_data
        data['civil_status'] = 2
        data['smoker'] = True
        data['height'] = 200
        data['weight'] = 220
        data['daily_exercise'] = 30

        data['home_value'] = 1000000
        data['home_growth'] = 0.5
        data['ss_fra_todays'] = 2.5
        data['ss_fra_retirement'] = 0.4
        data['state_tax_after_credits'] = 8.5
        data['state_tax_effrate'] = 7.5
        data['pension_name'] = 'Test Pension'
        data['pension_amount'] = 50000.5
        data['pension_start_date'] = start_time.date()
        data['employee_contributions_last_year'] = 4000.0
        data['employer_contributions_last_year'] = 2000.0
        data['total_contributions_last_year'] = 6000.0

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['btc'], 3200)  # 80000 * 0.04
        self.assertNotEqual(response.data['id'], None)
        saved_plan = RetirementPlan.objects.get(id=response.data['id'])
        self.assertEqual(saved_plan.btc, 3200)
        self.assertEqual(saved_plan.client.civil_status, 2)
        self.assertEqual(saved_plan.client.smoker, True)
        self.assertEqual(saved_plan.client.height, 200)
        self.assertEqual(saved_plan.client.weight, 220)
        self.assertEqual(saved_plan.client.daily_exercise, 30)

        self.assertEqual(saved_plan.client.home_value, 1000000)
        self.assertEqual(saved_plan.client.home_growth, 0.5)
        self.assertEqual(saved_plan.client.ss_fra_todays, 2.5)
        self.assertEqual(saved_plan.client.ss_fra_retirement, 0.4)
        self.assertEqual(saved_plan.client.state_tax_after_credits, 8.5)
        self.assertEqual(saved_plan.client.state_tax_effrate, 7.5)
        self.assertEqual(saved_plan.client.pension_name, 'Test Pension')
        self.assertEqual(saved_plan.client.pension_amount, 50000.5)
        self.assertEqual(saved_plan.client.pension_start_date, start_time.date())
        self.assertEqual(saved_plan.client.employee_contributions_last_year, 4000.0)
        self.assertEqual(saved_plan.client.employer_contributions_last_year, 2000.0)
        self.assertEqual(saved_plan.client.total_contributions_last_year, 6000.0)

    def test_update_client_civil_status(self):
        """
        Users should be able to update their civil_status through the
        retirement plan endpoint.
        """
        plan = RetirementPlanFactory.create(calculated_life_expectancy=92)
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=plan.client.user)
        data = {
            'civil_status': 2,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['civil_status'], 2)

        # try one more update to validate against
        data = {
            'civil_status': 1,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['civil_status'], 1)

    def test_update_client_smoker(self):
        plan = RetirementPlanFactory.create(calculated_life_expectancy=92)
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=plan.client.user)
        data = {
            'smoker': True,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['smoker'], True)

        # try one more update to validate against
        data = {
            'smoker': False,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['smoker'], False)

    def test_update_client_daily_exercise(self):
        plan = RetirementPlanFactory.create(calculated_life_expectancy=92)
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=plan.client.user)
        data = {
            'daily_exercise': 25,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['daily_exercise'], 25)

        # try one more update to validate against
        data = {
            'daily_exercise': 30,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['daily_exercise'], 30)

    def test_update_client_weight(self):
        plan = RetirementPlanFactory.create(calculated_life_expectancy=92)
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=plan.client.user)
        data = {
            'weight': 25.0,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['weight'], 25.0)

        # try one more update to validate against
        data = {
            'weight': 30.0,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['weight'], 30.0)

    def test_update_client_height(self):
        plan = RetirementPlanFactory.create(calculated_life_expectancy=92)
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=plan.client.user)
        data = {
            'height': 25.0,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['height'], 25.0)

        # try one more update to validate against
        data = {
            'height': 30,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['height'], 30)

    def test_update_additional_fields(self):
        plan = RetirementPlanFactory.create(calculated_life_expectancy=92)
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=plan.client.user)
        data = {
            'home_value': 123456.7,
            'home_growth': 0.1,
            'ss_fra_todays': 12345.6,
            'ss_fra_retirement': 1234.5,
            'state_tax_after_credits': 12345.6,
            'state_tax_effrate': 0.1,
            'pension_name': 'pension name',
            'pension_amount': 12345.6,
            'pension_start_date': date(2017, 1, 1),
            'employee_contributions_last_year': 23456.7,
            'employer_contributions_last_year': 34567.8,
            'total_contributions_last_year': 1234567.8
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['home_value'], data['home_value'])
        self.assertEqual(response.data['home_growth'], data['home_growth'])
        self.assertEqual(response.data['ss_fra_todays'], data['ss_fra_todays'])
        self.assertEqual(response.data['ss_fra_retirement'], data['ss_fra_retirement'])
        self.assertEqual(response.data['state_tax_after_credits'], data['state_tax_after_credits'])
        self.assertEqual(response.data['state_tax_effrate'], data['state_tax_effrate'])
        self.assertEqual(response.data['pension_name'], data['pension_name'])
        self.assertEqual(response.data['pension_amount'], data['pension_amount'])
        self.assertEqual(response.data['pension_start_date'], data['pension_start_date'])
        self.assertEqual(response.data['employee_contributions_last_year'], data['employee_contributions_last_year'])
        self.assertEqual(response.data['employer_contributions_last_year'], data['employer_contributions_last_year'])
        self.assertEqual(response.data['total_contributions_last_year'], data['total_contributions_last_year'])

        # try one more update to validate against

    def test_get_plan(self):
        """
        Test clients are able to access their own retirement plan by id.
        """
        plan = RetirementPlanFactory.create(calculated_life_expectancy=92)
        soa = plan.statement_of_advice
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=plan.client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['client'], plan.client.id)
        self.assertEqual(response.data['calculated_life_expectancy'], plan.calculated_life_expectancy)
        self.assertNotIn('goal_setting', response.data)
        self.assertEqual(response.data['statement_of_advice'], soa.id)
        self.assertEqual(response.data['statement_of_advice_url'], '/statements/retirement/{}.pdf'.format(soa.id))
        self.assertNotEqual(response.data['created_at'], None)
        self.assertNotEqual(response.data['updated_at'], None)

    def test_agreed_on_plan_generates_soa(self):
        """
        Test agreed on retirement plan generates a statement of advice
        on save.
        """
        plan = RetirementPlanFactory.create(calculated_life_expectancy=92)
        plan.agreed_on = timezone.now()
        plan.save()

        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=plan.client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['client'], plan.client.id)
        self.assertEqual(response.data['calculated_life_expectancy'], plan.calculated_life_expectancy)
        self.assertNotEqual(response.data['statement_of_advice'], None)

    def test_agreed_on_plan_logs_activity(self):
        """
        Test agreed on retirement plan is logged in activity.
        """

        # We need to activate the activity logging for the desired event types.
        ActivityLogEvent.get(Event.RETIREMENT_SOA_GENERATED)

        plan = RetirementPlanFactory.create()
        self.client.force_authenticate(user=plan.client.user)
        url = '/api/v1/clients/%s/retirement-plans/%s'%(plan.client.id, plan.id)
        dt = now()
        new_data = dict(self.base_plan_data, agreed_on=dt)
        response = self.client.put(url, new_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        url = '/api/v1/clients/{}/activity'.format(plan.client.id)
        response = self.client.get(url)
        download = {
            'url': plan.statement_of_advice.pdf_url,
            'name': 'Statement Of Advice'
        }
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['type'], ActivityLogEvent.get(Event.RETIREMENT_SOA_GENERATED).activity_log.id)
        self.assertEqual(response.data[0]['download'], download)

    def test_add_plan(self):
        '''
        Tests:
        - clients can create a retirement plan.
        - specifying btc on creation works
        '''
        url = '/api/v1/clients/{}/retirement-plans'.format(Fixture1.client1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.post(url, self.base_plan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['btc'], 3200)  # 80000 * 0.04
        self.assertNotEqual(response.data['id'], None)
        saved_plan = RetirementPlan.objects.get(id=response.data['id'])
        self.assertEqual(saved_plan.btc, 3200)

    def test_add_plan_with_btc_0(self):
        '''
        Tests:
        - clients can create a retirement plan.
        - specifying btc on creation as 0 returns btc 0
        '''
        url = '/api/v1/clients/{}/retirement-plans'.format(Fixture1.client1().id)
        self.base_plan_data['btc'] = 0
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.post(url, self.base_plan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['btc'], 0)
        self.assertNotEqual(response.data['id'], None)
        saved_plan = RetirementPlan.objects.get(id=response.data['id'])
        self.assertEqual(saved_plan.btc, 0)

    def test_add_plan_with_json_fields(self):
        '''
        Tests:
        - clients can create a retirement plan.
        - specifying btc on creation works
        '''
        external_asset = ExternalAssetFactory.create(owner=Fixture1.client1(), valuation=100000)
        url = '/api/v1/clients/{}/retirement-plans'.format(Fixture1.client1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        plan_data = self.base_plan_data.copy()
        plan_data['partner_data'] = {'name': 'Freddy', 'dob': date(2000, 1, 1), 'income': 50000, 'btc': 1000}
        plan_data['expenses'] = [
            {
                "id": 1,
                "desc": "Car",
                "cat": RetirementPlan.ExpenseCategory.TRANSPORTATION.value,
                "who": "self",
                "amt": 200,
            },
        ]
        plan_data['savings'] = [
            {
                "id": 1,
                "desc": "Health Account",
                "cat": RetirementPlan.SavingCategory.HEALTH_GAP.value,
                "who": "self",
                "amt": 100,
            },
        ]
        plan_data['initial_deposits'] = [
            {
                "id": 1,
                "asset": external_asset.id,
                "amt": 10000,
            },
        ]
        response = self.client.post(url, plan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['partner_data']['btc'], 1000)
        saved_plan = RetirementPlan.objects.get(id=response.data['id'])
        self.assertEqual(saved_plan.savings[0]['amt'], 100)
        self.assertEqual(saved_plan.expenses[0]['amt'], 200)
        self.assertEqual(saved_plan.initial_deposits[0]['amt'], 10000)

    def test_add_plan_no_name(self):
        base_plan_data = {
            "description": "My solo plan",
            'desired_income': 60000,
            'income': 80000,
            'volunteer_days': 1,
            'paid_days': 2,
            'btc': 1000,
            'same_home': True,
            'reverse_mortgage': True,
            'expected_return_confidence': 0.5,
        }
        url = '/api/v1/clients/{}/retirement-plans'.format(Fixture1.client1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.post(url, base_plan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['btc'], 1000)
        self.assertNotEqual(response.data['id'], None)
        saved_plan = RetirementPlan.objects.get(id=response.data['id'])
        self.assertEqual(saved_plan.btc, 1000)
        # make sure name is None
        self.assertEqual(response.data['name'], None)

    def test_sends_soa_email_after_agreed(self):
        '''
        Tests:
        - clients can create a retirement plan.
        - specifying btc on creation works
        '''
        client = Fixture1.client1()
        url = '/api/v1/clients/%s/retirement-plans' % client.id
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.post(url, self.base_plan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        plan = RetirementPlan.objects.get(id=response.data['id'])
        # Now update it with agreed_on=Now
        url = '/api/v1/clients/%s/retirement-plans/%s'%(client.id, response.data['id'])
        dt = now()
        new_data = dict(self.base_plan_data, agreed_on=dt)
        response = self.client.put(url, new_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        plan.send_plan_agreed_email.assert_called_with()

    def test_cant_change_after_agreed(self):
        '''
        Tests:
        - clients can create a retirement plan.
        - specifying btc on creation works
        '''
        client = Fixture1.client1()
        url = '/api/v1/clients/%s/retirement-plans' % client.id
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.post(url, self.base_plan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Now update it with agreed_on=Now
        url = '/api/v1/clients/%s/retirement-plans/%s'%(client.id, response.data['id'])
        dt = now()
        new_data = dict(self.base_plan_data, agreed_on=dt)
        response = self.client.put(url, new_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Now we can't update it
        url = '/api/v1/clients/%s/retirement-plans/%s'%(client.id, response.data['id'])
        response = self.client.put(url, self.base_plan_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_plans(self):
        """
        Tests clients can get a list of their own plans and the list does not include plans where it is a partner.
        """
        plan1 = RetirementPlanFactory.create()
        plan2 = RetirementPlanFactory.create(partner_plan=plan1)
        url = '/api/v1/clients/{}/retirement-plans'.format(plan1.client.id)
        self.client.force_authenticate(user=plan1.client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['client'], plan1.client.id)

    def test_retirement_incomes(self):
        """
        Test listing and creating retirement incomes
        """

        plan = RetirementPlanFactory.create()
        client = plan.client

        # Create an income
        url = '/api/v1/clients/%s/retirement-incomes' % client.id
        self.client.force_authenticate(user=client.user)
        income_data = {'name': 'RetirementIncome1',
                       'plan': plan.id,
                       'account_type': constants.ACCOUNT_TYPE_VARIABLEANNUITY,
                       'begin_date': now().date(),
                       'amount': 200,
                       'growth': 1.0,
                       'schedule': 'DAILY'
                       }
        response = self.client.post(url, income_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        income = response.data
        self.assertEqual(income['schedule'], 'DAILY')
        self.assertEqual(income['account_type'], constants.ACCOUNT_TYPE_VARIABLEANNUITY)
        self.assertEqual(income['amount'], 200)
        self.assertEqual(income['growth'], 1.0)
        self.assertEqual(income['plan'], plan.id)

        # Update it
        url = '/api/v1/clients/%s/retirement-incomes/%s' % (client.id,
                                                            income['id'])
        income_data = { 'schedule': 'WEEKLY' }
        response = self.client.put(url, income_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Make sure it's in the list
        url = '/api/v1/clients/%s/retirement-incomes'%client.id
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], income['id'])

        # And unprivileged users can't see it
        self.client.force_authenticate(user=Fixture1.client2().user)
        url = '/api/v1/clients/%s/retirement-incomes'%client.id
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_put_partner(self):
        """
        Test update partner_plan after tax contribution
        """
        plan1 = RetirementPlanFactory.create()
        plan2 = RetirementPlanFactory.create(partner_plan=plan1)
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan2.client.id, plan2.id)
        self.client.force_authenticate(user=plan1.client.user)
        response = self.client.put(url, data={'atc': 45000})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        check_plan = RetirementPlan.objects.get(id=plan2.id)
        self.assertEqual(check_plan.atc, 45000)

    def test_get_bad_permissions(self):
        """
        Test clients not owning and not on a partner plan cannot access.
        """
        plan = RetirementPlanFactory.create()
        plan2 = RetirementPlanFactory.create()
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan.client.id,
                                                              plan.id)
        self.client.force_authenticate(user=plan2.client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {})

    def test_matching_partnerplans(self):
        """
        Test update plan (link partner plan)
        Check if partner_plan doesn't equal
        partner_plan_reverse and they both are set, then we fail.
        """
        plan1 = RetirementPlanFactory.create()
        plan2 = RetirementPlanFactory.create(partner_plan=plan1)
        plan4 = RetirementPlanFactory.create()
        plan2.reverse_partner_plan = plan4
        plan2.save()

        plan1.reverse_partner_plan = plan2
        plan1.save()

        plan3 = RetirementPlanFactory.create()

        self.assertEqual(plan1.reverse_partner_plan, plan2)
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan1.client.id, plan1.id)
        self.client.force_authenticate(user=plan1.client.user)
        response = self.client.put(url, data={'partner_plan': plan3.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(loads(response.content)['error']['reason'], 'ValidationError')
        self.assertEqual(response.data, {})
        # Make sure the db content didn't change
        self.assertEqual(plan2.partner_plan, plan1)


    def test_partner_delete(self):
        """
        Test on delete sets partner to null
        """
        plan1 = RetirementPlanFactory.create()
        plan2 = RetirementPlanFactory.create(partner_plan=plan1)
        url = '/api/v1/clients/{}/retirement-plans/{}'.format(plan1.client.id, plan1.id)
        self.client.force_authenticate(user=plan1.client.user)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Make sure the db object was removed, and the partner plan set to null.
        self.assertEqual(RetirementPlan.objects.filter(id=plan1.id).first(), None)
        # Make sure cascade not in force, but null.
        check_plan = RetirementPlan.objects.get(id=plan2.id)
        self.assertEqual(check_plan.id, plan2.id)

        self.assertEqual(check_plan.partner_plan, None)

    def test_todos(self):
        # TODO: Advisor tests.
        # Test a clients' primary and secondary advisors are able to access the appropriate plans.
        # Test partner plan clients' primary and secondary advisors are able to access the appropriate plans.
        # Test non-advising advisors cannot access
        # Test only advisors and clients can view and edit the plans. (No-one with firm privileges)
        pass

    def test_retirement_plan_calculate_unauthenticated(self):
        plan = RetirementPlanFactory.create()
        url = '/api/v1/clients/{}/retirement-plans/{}/calculate'.format(plan.client.id, plan.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retirement_plan_calculate_not_found(self):
        plan = RetirementPlanFactory.create()
        url = '/api/v1/clients/{}/retirement-plans/{}/calculate'.format(plan.client.id, plan.id+999)
        self.client.force_authenticate(user=plan.client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_retirement_plan_calculate(self):

        ret_accts = [{'employer_match_type': 'contributions',
                      'id': 1,
                      'owner': 'self',
                      'balance_efdt': '2017-02-02',
                      'name': '401K',
                      'employer_match': 0.49,
                      'contrib_amt': 250,
                      'balance': 25000,
                      'acc_type': 5,
                      'cat': 2,
                      'contrib_period': 'monthly'}]

        plan = RetirementPlanFactory.create(income=100000.,
                                            retirement_home_price=250000.,
                                            paid_days=1,
                                            retirement_age=69.,
                                            lifestyle=1,
                                            reverse_mortgage=True,
                                            income_growth=0.01,
                                            desired_risk=0.5,
                                            selected_life_expectancy=95.,
                                            retirement_postal_code=90210,
                                            retirement_accounts=ret_accts,
                                            btc=10000)

        plan.client.residential_address.post_code=int(94123)
        plan.client.home_value = 250000
        plan.client.employment_status = constants.EMPLOYMENT_STATUS_SELF_EMPLOYED
        plan.client.civil_status = abstract.PersonalData.CivilStatus['SINGLE'].value
        plan.client.ss_fra_retirement = 3490
        plan.client.ss_fra_todays = 1390
        plan.client.date_of_birth = date(1960, 1, 1)
        plan.client.regional_data = { "tax_transcript_data":{   "taxable_income":0,
                                                                "total_payments":0,
                                                                "adjusted_gross_income":1370}}
        plan.client.save()

        # some tickers for portfolio
        bonds_asset_class = AssetClassFactory.create(name='US_TOTAL_BOND_MARKET')
        stocks_asset_class = AssetClassFactory.create(name='HEDGE_FUNDS')

        TickerFactory.create(symbol='IAGG', asset_class=bonds_asset_class)
        TickerFactory.create(symbol='AGG', asset_class=bonds_asset_class)
        TickerFactory.create(symbol='ITOT', asset_class=stocks_asset_class)
        TickerFactory.create(symbol='GRFXX', asset_class=stocks_asset_class)
        TickerFactory.create(symbol='MAMMGCP', asset_class=stocks_asset_class)
        TickerFactory.create(symbol='IPO')
        fund = TickerFactory.create(symbol='rest')

        # Add the asset classes to the advisor's default portfolio set
        plan.client.advisor.default_portfolio_set.asset_classes.add(bonds_asset_class, stocks_asset_class, fund.asset_class)


        # Set the markowitz bounds for today
        self.m_scale = MarkowitzScaleFactory.create()

        # populate the data needed for the optimisation
        # We need at least 500 days as the cycles go up to 70 days and we need at least 7 cycles.
        populate_prices(500, asof=mocked_now.date())
        populate_cycle_obs(500, asof=mocked_now.date())
        populate_cycle_prediction(asof=mocked_now.date())
        populate_inflation(asof=mocked_now.date())

        self.assertIsNone(plan.goal_setting)
        old_settings = GoalSetting.objects.all().count()
        old_mgroups = GoalMetricGroup.objects.all().count()
        old_metrics = GoalMetric.objects.all().count()
        url = '/api/v1/clients/{}/retirement-plans/{}/calculate'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=plan.client.user)

        # First try and calculate without a client date of birth. Make sure we get the correct 400
        old_dob = plan.client.date_of_birth
        plan.client.date_of_birth = None
        plan.client.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Now set the date of birth
        plan.client.date_of_birth = old_dob
        plan.client.save()

        # We should be ready to calculate properly
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('on_track' in response.data)
        self.assertTrue('portfolio' in response.data)
        self.assertTrue('projection' in response.data)
        self.assertTrue('reload_feed' in response.data)
        self.assertEqual(len(response.data['projection']), 50)

        # Make sure the goal_setting is now populated.
        plan.refresh_from_db()
        self.assertIsNotNone(plan.goal_setting.portfolio)
        self.assertEqual(old_settings+1, GoalSetting.objects.all().count())
        self.assertEqual(old_mgroups+1, GoalMetricGroup.objects.all().count())
        self.assertEqual(old_metrics+1, GoalMetric.objects.all().count())
        old_id = plan.goal_setting.id

        # Recalculate and make sure the number of settings, metric groups and metrics in the system is the same
        # Also make sure the setting object is different
        response = self.client.get(url)
        plan.refresh_from_db()
        self.assertEqual(old_settings+1, GoalSetting.objects.all().count())
        self.assertEqual(old_mgroups+1, GoalMetricGroup.objects.all().count())
        self.assertEqual(old_metrics+1, GoalMetric.objects.all().count())
        self.assertNotEqual(old_id, plan.goal_setting.id)

        # Tests calculated-data api endpoint respones with correct data
        url = '/api/v1/clients/{}/retirement-plans/{}/calculated-data'.format(plan.client.id, plan.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('on_track' in response.data)
        self.assertTrue('portfolio' in response.data)
        self.assertTrue('projection' in response.data)
        self.assertTrue('reload_feed' in response.data)

    def test_retirement_plan_advice_feed_list_unread(self):
        self.content_type = ContentTypeFactory.create()
        self.bonds_asset_class = AssetClassFactory.create(investment_type=InvestmentType.Standard.BONDS.get())
        self.stocks_asset_class = AssetClassFactory.create(investment_type=InvestmentType.Standard.STOCKS.get())
        self.bonds_ticker = TickerFactory.create(asset_class=self.bonds_asset_class, benchmark_content_type=self.content_type)
        self.stocks_ticker = TickerFactory.create(asset_class=self.stocks_asset_class, benchmark_content_type=self.content_type)
        plan = RetirementPlanFactory.create()
        elog = log(user=plan.client.user, action='Triggers retirement advice')
        advice = RetirementAdviceFactory(plan=plan, trigger=elog, read=timezone.now())
        elog2 = log(user=plan.client.user, action='Triggers another, unread retirement advice')
        advice2 = RetirementAdviceFactory(plan=plan, trigger=elog)
        url = '/api/v1/clients/{}/retirement-plans/{}/advice-feed'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=plan.client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data.get('results')[0]['id'], advice.id)
        self.assertEqual(response.data.get('results')[0]['id'], advice2.id)
        self.assertEqual(response.data.get('count'), 1)

    def test_retirement_plan_advice_feed_detail(self):
        self.content_type = ContentTypeFactory.create()
        self.bonds_asset_class = AssetClassFactory.create(investment_type=InvestmentType.Standard.BONDS.get())
        self.stocks_asset_class = AssetClassFactory.create(investment_type=InvestmentType.Standard.STOCKS.get())
        self.bonds_ticker = TickerFactory.create(asset_class=self.bonds_asset_class, benchmark_content_type=self.content_type)
        self.stocks_ticker = TickerFactory.create(asset_class=self.stocks_asset_class, benchmark_content_type=self.content_type)
        plan = RetirementPlanFactory.create()
        elog = log(user=plan.client.user, action='Triggers retirement advice')
        advice = RetirementAdviceFactory(plan=plan, trigger=elog)
        url = '/api/v1/clients/{}/retirement-plans/{}/advice-feed/{}'.format(plan.client.id, plan.id, advice.id)
        self.client.force_authenticate(user=plan.client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], advice.id)

    def test_retirement_plan_advice_fed_update(self):
        self.content_type = ContentTypeFactory.create()
        self.bonds_asset_class = AssetClassFactory.create(investment_type=InvestmentType.Standard.BONDS.get())
        self.stocks_asset_class = AssetClassFactory.create(investment_type=InvestmentType.Standard.STOCKS.get())
        self.bonds_ticker = TickerFactory.create(asset_class=self.bonds_asset_class, benchmark_content_type=self.content_type)
        self.stocks_ticker = TickerFactory.create(asset_class=self.stocks_asset_class, benchmark_content_type=self.content_type)
        plan = RetirementPlanFactory.create()
        elog = log(user=plan.client.user, action='Triggers retirement advice')
        advice = RetirementAdviceFactory(plan=plan, trigger=elog)
        url = '/api/v1/clients/{}/retirement-plans/{}/advice-feed/{}'.format(plan.client.id, plan.id, advice.id)
        self.client.force_authenticate(user=plan.client.user)
        read_time = timezone.now()
        data = {
            'read': read_time,
        }
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], advice.id)
        self.assertEqual(response.data['read'][:9], str(read_time)[:9])

    def test_add_retirement_plan_same_location_no_postal(self):
        url = '/api/v1/clients/{}/retirement-plans'.format(Fixture1.client1().id)
        data = {
            "name": "Personal Plan",
            "description": "My solo plan",
            'desired_income': 60000,
            'income': 80000,
            'volunteer_days': 1,
            'paid_days': 2,
            'same_home': False,
            'same_location': True,
            'reverse_mortgage': True,
            'expected_return_confidence': 0.5,
            'retirement_age': 65,
            'btc': 1000,
            'atc': 300,
            'desired_risk': 0.6,
            'selected_life_expectancy': 80,
        }
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['btc'], 1000)
        self.assertNotEqual(response.data['id'], None)
        saved_plan = RetirementPlan.objects.get(id=response.data['id'])
        self.assertEqual(saved_plan.btc, 1000)
        self.assertEqual(saved_plan.retirement_age, 65)

    def test_add_retirement_plan_with_savings(self):
        savings = [{
            "cat": 3,
            "amt": 10000,
            "desc": "123",
            "who": "self",
            "id": 1
        }]
        self.base_plan_data['savings'] = savings
        url = '/api/v1/clients/{}/retirement-plans'.format(Fixture1.client1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.post(url, self.base_plan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['btc'], 3200)  # 80000 * 0.04
        self.assertNotEqual(response.data['id'], None)
        saved_plan = RetirementPlan.objects.get(id=response.data['id'])
        self.assertEqual(saved_plan.btc, 3200)
        self.assertNotEqual(response.data['savings'], None)
        self.assertEqual(response.data['savings'][0]['id'], 1)
        self.assertEqual(response.data['savings'][0]['amt'], 10000)

    def test_add_retirement_plan_with_expenses(self):
        expenses = [{
            "cat": 3,
            "amt": 10000,
            "desc": "123",
            "who": "self",
            "id": 1
        }]
        self.base_plan_data['expenses'] = expenses
        url = '/api/v1/clients/{}/retirement-plans'.format(Fixture1.client1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.post(url, self.base_plan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['btc'], 3200)  # 80000 * 0.04
        self.assertNotEqual(response.data['id'], None)
        saved_plan = RetirementPlan.objects.get(id=response.data['id'])
        self.assertEqual(saved_plan.btc, 3200)
        self.assertNotEqual(response.data['expenses'], None)
        self.assertEqual(response.data['expenses'][0]['id'], 1)
        self.assertEqual(response.data['expenses'][0]['amt'], 10000)

    def test_add_retirement_plan_with_retirement_accounts(self):
        retirement_accounts = [{
            "id": 1,
            "name": 'test account',
            "cat": 3,
            "acc_type": constants.US_RETIREMENT_ACCOUNT_TYPES[0],
            "owner": "self",
            "balance": 12345,
            "balance_efdt": date(2020, 1, 1),
            "contrib_amt": 1234,
            "contrib_period": "yearly",
            "employer_match": 0.5,
            "employer_match_type": "income"
        }]
        self.base_plan_data['retirement_accounts'] = retirement_accounts
        url = '/api/v1/clients/{}/retirement-plans'.format(Fixture1.client1().id)
        self.client.force_authenticate(user=Fixture1.client1().user)
        response = self.client.post(url, self.base_plan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        saved_plan = RetirementPlan.objects.get(id=response.data['id'])
        self.assertNotEqual(response.data['retirement_accounts'], None)
        self.assertEqual(response.data['retirement_accounts'][0]['id'], 1)
        self.assertEqual(response.data['retirement_accounts'][0]['name'], 'test account')
        self.assertEqual(response.data['retirement_accounts'][0]['acc_type'], constants.US_RETIREMENT_ACCOUNT_TYPES[0])
        self.assertEqual(response.data['retirement_accounts'][0]['balance_efdt'], '2020-01-01')

    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_retirement_plan_calculate_notgenerated(self):


        ret_accts = [{'employer_match_type': 'contributions',
                      'id': 1,
                      'owner': 'self',
                      'balance_efdt': '2017-02-02',
                      'name': '401K',
                      'employer_match': 0.49,
                      'contrib_amt': 250,
                      'balance': 25000,
                      'acc_type': 5,
                      'cat': 2,
                      'contrib_period': 'monthly'}]

        plan = RetirementPlanFactory.create(income=100000.,
                                            retirement_home_price=250000.,
                                            paid_days=1,
                                            retirement_age=69.,
                                            lifestyle=1,
                                            reverse_mortgage=True,
                                            income_growth=0.01,
                                            desired_risk=0.5,
                                            selected_life_expectancy=95.,
                                            retirement_postal_code=90210,
                                            retirement_accounts=ret_accts,
                                            btc=10000)

        plan.client.residential_address.post_code=int(94123)
        plan.client.home_value = 250000
        plan.client.employment_status = constants.EMPLOYMENT_STATUS_SELF_EMPLOYED
        plan.client.civil_status = abstract.PersonalData.CivilStatus['SINGLE'].value
        plan.client.ss_fra_retirement = 3490
        plan.client.ss_fra_todays = 1390
        plan.client.date_of_birth = date(1960, 1, 1)
        plan.client.regional_data = { "tax_transcript_data":{   "taxable_income":0,
                                                                "total_payments":0,
                                                                "adjusted_gross_income":1370}}
        plan.client.save()

        # some tickers for portfolio
        bonds_asset_class = AssetClassFactory.create(name='US_TOTAL_BOND_MARKET')
        stocks_asset_class = AssetClassFactory.create(name='HEDGE_FUNDS')

        TickerFactory.create(symbol='IAGG', asset_class=bonds_asset_class)
        TickerFactory.create(symbol='ITOT', asset_class=stocks_asset_class)
        TickerFactory.create(symbol='AGG', asset_class=bonds_asset_class)
        TickerFactory.create(symbol='GRFXX', asset_class=stocks_asset_class)
        TickerFactory.create(symbol='MAMMGCP', asset_class=stocks_asset_class)
        TickerFactory.create(symbol='IPO')
        fund = TickerFactory.create(symbol='rest')

        # Add the asset classes to the advisor's default portfolio set
        plan.client.advisor.default_portfolio_set.asset_classes.add(bonds_asset_class, stocks_asset_class, fund.asset_class)


        # Set the markowitz bounds for today
        self.m_scale = MarkowitzScaleFactory.create()

        # populate the data needed for the optimisation
        # We need at least 500 days as the cycles go up to 70 days and we need at least 7 cycles.
        populate_prices(500, asof=mocked_now.date())
        populate_cycle_obs(500, asof=mocked_now.date())
        populate_cycle_prediction(asof=mocked_now.date())
        populate_inflation(asof=mocked_now.date())

        url = '/api/v1/clients/{}/retirement-plans/{}/calculate'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=plan.client.user)

        # We should be ready to calculate properly
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('on_track' in response.data)
        self.assertTrue('portfolio' in response.data)
        self.assertTrue('projection' in response.data)
        self.assertTrue('reload_feed' in response.data)
        self.assertEqual(len(response.data['projection']), 50)


    @mock.patch.object(timezone, 'now', MagicMock(return_value=mocked_now))
    def test_retirement_plan_calculate_retirement_model(self):
        ret_accts = [{'employer_match_type': 'contributions',
                      'id': 1,
                      'owner': 'self',
                      'balance_efdt': '2017-02-02',
                      'name': '401K',
                      'employer_match': 0.49,
                      'contrib_amt': 250,
                      'balance': 25000,
                      'acc_type': 5,
                      'cat': 2,
                      'contrib_period': 'monthly'}]

        plan = RetirementPlanFactory.create(income=100000.,
                                            retirement_home_price=250000.,
                                            paid_days=1,
                                            retirement_age=69.,
                                            lifestyle=1,
                                            reverse_mortgage=True,
                                            income_growth=0.01,
                                            desired_risk=0.5,
                                            selected_life_expectancy=95.,
                                            retirement_postal_code=90210,
                                            retirement_accounts=ret_accts,
                                            btc=10000)

        plan.client.residential_address.post_code=int(94123)
        plan.client.home_value = 250000
        plan.client.employment_status = constants.EMPLOYMENT_STATUS_SELF_EMPLOYED
        plan.client.civil_status = abstract.PersonalData.CivilStatus['SINGLE'].value
        plan.client.ss_fra_retirement = 3490
        plan.client.ss_fra_todays = 1390
        plan.client.date_of_birth = date(1960, 1, 1)
        plan.client.regional_data = { "tax_transcript_data":{   "taxable_income":0,
                                                                "total_payments":0,
                                                                "adjusted_gross_income":1370}}
        plan.client.save()

        # some tickers for portfolio
        bonds_asset_class = AssetClassFactory.create(name='US_TOTAL_BOND_MARKET')
        stocks_asset_class = AssetClassFactory.create(name='HEDGE_FUNDS')

        TickerFactory.create(symbol='IAGG', asset_class=bonds_asset_class)
        TickerFactory.create(symbol='AGG', asset_class=bonds_asset_class)
        TickerFactory.create(symbol='ITOT', asset_class=stocks_asset_class)
        TickerFactory.create(symbol='MAMMGCP', asset_class=stocks_asset_class)
        TickerFactory.create(symbol='GRFXX', asset_class=stocks_asset_class)
        TickerFactory.create(symbol='IPO')
        fund = TickerFactory.create(symbol='rest')

        # Add the asset classes to the advisor's default portfolio set
        plan.client.advisor.default_portfolio_set.asset_classes.add(bonds_asset_class, stocks_asset_class, fund.asset_class)

        # Set the markowitz bounds for today
        self.m_scale = MarkowitzScaleFactory.create()

        # populate the data needed for the optimisation
        # We need at least 500 days as the cycles go up to 70 days and we need at least 7 cycles.
        populate_prices(500, asof=mocked_now.date())
        populate_cycle_obs(500, asof=mocked_now.date())
        populate_cycle_prediction(asof=mocked_now.date())
        populate_inflation(asof=mocked_now.date())

        self.assertIsNone(plan.goal_setting)
        old_settings = GoalSetting.objects.all().count()
        old_mgroups = GoalMetricGroup.objects.all().count()
        old_metrics = GoalMetric.objects.all().count()
        url = '/api/v1/clients/{}/retirement-plans/{}/calculate'.format(plan.client.id, plan.id)
        self.client.force_authenticate(user=plan.client.user)

        # We should be ready to calculate properly
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('on_track' in response.data)
        self.assertTrue('portfolio' in response.data)
        self.assertTrue('projection' in response.data)
        self.assertTrue('reload_feed' in response.data)
        self.assertEqual(len(response.data['projection']), 50)

        # Try life_expectancy below valid range
        old_life_expectancy = plan.selected_life_expectancy
        plan.selected_life_expectancy = 60
        plan.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Try life_expectancy above valid range
        plan.selected_life_expectancy = 101
        plan.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Now set valid life expectancy
        plan.selected_life_expectancy = old_life_expectancy
        plan.save()

        # Try with an older partner ...
        plan.client.civil_status = abstract.PersonalData.CivilStatus['MARRIED_FILING_JOINTLY'].value
        plan.client.save()

        partner_year = pd.Timestamp(plan.client.date_of_birth).year - 3
        partner_day = min(pd.Timestamp(plan.client.date_of_birth).day, 28)
        partner_month = pd.Timestamp(plan.client.date_of_birth).month
        partner_dob = pd.Timestamp(str(partner_year)+'-'+str(partner_month)+'-'+str(partner_day))

        plan.partner_data = {'income': 75000.,'dob': partner_dob}
        plan.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Try with a younger partner ...
        partner_year = pd.Timestamp(plan.client.date_of_birth).year + 5
        partner_day = min(pd.Timestamp(plan.client.date_of_birth).day, 28)
        partner_month = pd.Timestamp(plan.client.date_of_birth).month
        partner_dob = pd.Timestamp(str(partner_year)+'-'+str(partner_month)+'-'+str(partner_day))

        plan.partner_data = {'income': 75000.,'dob': partner_dob}
        plan.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Go back to being all alone ...
        plan.client.civil_status = abstract.PersonalData.CivilStatus['SINGLE'].value
        plan.client.save()

    @skip('Fails intermittently on deployment, something wrong with calculate_payments')
    def test_get_social_security(self):
        ss_all = calculate_payments(date(1960, 1, 1), 100000)
        ss_income = ss_all.get(67, None)
        if ss_income is None:
            ss_income = ss_all[sorted(ss_all)[0]]
        self.assertTrue(ss_income == 2487)
