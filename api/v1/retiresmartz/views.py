import logging
import numpy as np
import pandas as pd
import json
import scipy.stats as st
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.decorators import detail_route, list_route
from rest_framework.exceptions import ValidationError, ParseError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin
from api.v1.goals.serializers import PortfolioSerializer
from api.v1.views import ApiViewMixin
from activitylog.event import Event
from client.models import Client
from common.utils import d2ed
from notifications.models import Notify
from portfolios.calculation import Unsatisfiable
from portfolios.models import Ticker
from retiresmartz import advice_responses
from retiresmartz.calculator import Calculator, create_settings
from retiresmartz.calculator.assets import TaxDeferredAccount
from retiresmartz.calculator.cashflows import EmploymentIncome, \
    InflatedCashFlow, ReverseMortgage
from retiresmartz.calculator.desired_cashflows import RetiresmartzDesiredCashFlow
from retiresmartz.calculator.social_security import calculate_payments
from retiresmartz.models import RetirementAdvice, RetirementPlan, RetirementProjection
from support.models import SupportRequest
from . import serializers
from main import tax_sheet as tax
from main import tax_helpers as helpers
from pinax.eventlog.models import Log as EventLog
from main.inflation import inflation_level
from main import constants
from functools import reduce
import time

logger = logging.getLogger('api.v1.retiresmartz.views')

class RetiresmartzViewSet(ApiViewMixin, NestedViewSetMixin, ModelViewSet):
    model = RetirementPlan
    permission_classes = (IsAuthenticated,)

    # We don't want pagination for this viewset. Remove this line to enable.
    pagination_class = None

    # We define the queryset because our get_queryset calls super so the Nested queryset works.
    queryset = RetirementPlan.objects.all()

    # Set the response serializer because we want to use the 'get' serializer for responses from the 'create' methods.
    # See api/v1/views.py
    serializer_class = serializers.RetirementPlanSerializer
    serializer_response_class = serializers.RetirementPlanSerializer

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.RetirementPlanSerializer
        elif self.request.method == 'POST':
            return serializers.RetirementPlanWritableSerializer
        elif self.request.method == 'PUT':
            return serializers.RetirementPlanWritableSerializer

    def get_queryset(self):
        """
        The nested viewset takes care of only returning results for the client we are looking at.
        We need to add logic to only allow access to users that can view the plan.
        """
        qs = super(RetiresmartzViewSet, self).get_queryset()
        # Check user object permissions
        user = SupportRequest.target_user(self.request)
        return qs.filter_by_user(user)

    def perform_create(self, serializer):
        """
        We don't allow users to create retirement plans for others... So we set the client from the URL and validate
        the user has access to it.
        :param serializer:
        :return:
        """
        user = SupportRequest.target_user(self.request)
        client = Client.objects.filter_by_user(user).get(id=int(self.get_parents_query_dict()['client']))
        if 'client' in serializer.validated_data:
            if 'civil_status' in serializer.validated_data['client']:
                client.civil_status = serializer.validated_data['client']['civil_status']
            if 'smoker' in serializer.validated_data['client']:
                client.smoker = serializer.validated_data['client']['smoker']
            if 'drinks' in serializer.validated_data['client']:
                client.drinks = serializer.validated_data['client']['drinks']
            if 'height' in serializer.validated_data['client']:
                client.height = serializer.validated_data['client']['height']
            if 'weight' in serializer.validated_data['client']:
                client.weight = serializer.validated_data['client']['weight']
            if 'daily_exercise' in serializer.validated_data['client']:
                client.daily_exercise = serializer.validated_data['client']['daily_exercise']

            if 'home_value' in serializer.validated_data['client']:
                client.home_value = serializer.validated_data['client']['home_value']
            if 'home_growth' in serializer.validated_data['client']:
                client.home_growth = serializer.validated_data['client']['home_growth']
            if 'ss_fra_todays' in serializer.validated_data['client']:
                client.ss_fra_todays = serializer.validated_data['client']['ss_fra_todays']
            if 'ss_fra_retirement' in serializer.validated_data['client']:
                client.ss_fra_retirement = serializer.validated_data['client']['ss_fra_retirement']
            if 'state_tax_after_credits' in serializer.validated_data['client']:
                client.state_tax_after_credits = serializer.validated_data['client']['state_tax_after_credits']
            if 'state_tax_effrate' in serializer.validated_data['client']:
                client.state_tax_effrate = serializer.validated_data['client']['state_tax_effrate']
            if 'pension_name' in serializer.validated_data['client']:
                client.pension_name = serializer.validated_data['client']['pension_name']
            if 'pension_amount' in serializer.validated_data['client']:
                client.pension_amount = serializer.validated_data['client']['pension_amount']
            if 'pension_start_date' in serializer.validated_data['client']:
                client.pension_start_date = serializer.validated_data['client']['pension_start_date']
            if 'employee_contributions_last_year' in serializer.validated_data['client']:
                client.employee_contributions_last_year = serializer.validated_data['client']['employee_contributions_last_year']
            if 'employer_contributions_last_year' in serializer.validated_data['client']:
                client.employer_contributions_last_year = serializer.validated_data['client']['employer_contributions_last_year']
            if 'total_contributions_last_year' in serializer.validated_data['client']:
                client.total_contributions_last_year = serializer.validated_data['client']['total_contributions_last_year']
            client.save()
        return serializer.save(client=client)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.agreed_on:
            raise ParseError('Unable to update a RetirementPlan that has been agreed on')

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        orig = RetirementPlan.objects.get(pk=instance.pk)
        orig_client = orig.client
        updated = serializer.update(instance, serializer.validated_data)
        updated_client = updated.client

        if getattr(instance, '_prefetched_objects_cache', None) is not None:
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()
            serializer = self.get_serializer(instance)

        # RetirementAdvice Triggers
        orig_daily_exercise = 0 if orig_client.daily_exercise is None else orig_client.daily_exercise
        orig_drinks = 0 if orig_client.drinks is None else orig_client.drinks
        orig_smoker = orig_client.smoker
        orig_height = orig_client.height
        orig_weight = orig_client.weight

        life_expectancy_field_updated = (updated_client.daily_exercise != orig_client.daily_exercise or
                                         updated_client.weight != orig_weight or
                                         updated_client.height != orig_height or
                                         updated_client.smoker != orig_smoker or
                                         updated_client.drinks != orig_drinks)
        updated_life_expectancy_fields_all_filled = (updated_client.daily_exercise and
                                                     updated_client.weight and
                                                     updated_client.height and
                                                     updated_client.smoker is not None and
                                                     updated_client.drinks)
        org_life_expectancy_fields_not_all_filled = (not orig_client.daily_exercise or
                                                     not orig_client.weight or
                                                     not orig_client.height or
                                                     orig_client.smoker is None or
                                                     not orig_client.drinks)
        # Advice feed for toggling smoker
        if updated_client.smoker != orig_smoker:
            if updated_client.smoker:
                e = Event.RETIRESMARTZ_IS_A_SMOKER.log(None,
                                                       user=updated_client.user,
                                                       obj=updated_client)
                advice = RetirementAdvice(plan=updated, trigger=e)
                advice.text = advice_responses.get_smoking_yes(advice)
                advice.save()
            elif updated_client.smoker is False:
                e = Event.RETIRESMARTZ_IS_NOT_A_SMOKER.log(None,
                                                           user=updated_client.user,
                                                           obj=updated_client)
                advice = RetirementAdvice(plan=updated, trigger=e)
                advice.text = advice_responses.get_smoking_no(advice)
                advice.save()

        # Advice feed for daily_exercise change
        if updated_client.daily_exercise != orig_daily_exercise:
            # exercise only
            e = Event.RETIRESMARTZ_EXERCISE_ONLY.log(None,
                                                     user=updated_client.user,
                                                     obj=updated_client)
            advice = RetirementAdvice(plan=updated, trigger=e)
            advice.text = advice_responses.get_exercise_only(advice)
            advice.save()

        # Advice feed for drinks change
        if updated_client.drinks != orig_drinks:
            if updated_client.drinks > 1:
                e = Event.RETIRESMARTZ_DRINKS_MORE_THAN_ONE.log(None,
                                                     user=updated_client.user,
                                                     obj=updated_client)
                advice = RetirementAdvice(plan=updated, trigger=e)
                advice.text = advice_responses.get_drinks_more_than_one(advice)
                advice.save()
            else:
                e = Event.RETIRESMARTZ_DRINKS_ONE_OR_LESS.log(None,
                                                     user=updated_client.user,
                                                     obj=updated_client)
                advice = RetirementAdvice(plan=updated, trigger=e)
                advice.text = advice_responses.get_drinks_one_or_less(advice)
                advice.save()

        # frontend posts one at a time, weight then height, not together in one post
        if (updated_client.weight != orig_weight or updated_client.height != orig_height):
            # weight and/or height updated
            e = Event.RETIRESMARTZ_WEIGHT_AND_HEIGHT_ONLY.log(None,
                                                              user=updated_client.user,
                                                              obj=updated_client)
            advice = RetirementAdvice(plan=updated, trigger=e)
            advice.text = advice_responses.get_weight_and_height_only(advice)
            advice.save()

        if life_expectancy_field_updated and updated_life_expectancy_fields_all_filled and org_life_expectancy_fields_not_all_filled:
            # every wellbeing field
            e = Event.RETIRESMARTZ_ALL_WELLBEING_ENTRIES.log(None,
                                                             user=updated_client.user,
                                                             obj=updated_client)
            advice = RetirementAdvice(plan=updated, trigger=e)
            advice.text = advice_responses.get_all_wellbeing_entries(advice)
            advice.save()

        # Spending and Contributions
        # TODO: Replace income with function to calculate expected income
        # increase in these two calls to get_decrease_spending_increase_contribution
        # and get_increase_contribution_decrease_spending
        if orig.btc > updated.btc:
            # spending increased, contributions decreased\
            events = EventLog.objects.filter(
                Q(action='RETIRESMARTZ_SPENDING_UP_CONTRIB_DOWN') |
                Q(action='RETIRESMARTZ_SPENDING_DOWN_CONTRIB_UP')
            ).order_by('-timestamp')
            # TODO: calculate nth rate based on retirement age?
            years = updated.retirement_age - updated.client.age
            nth_rate = reduce((lambda acc, rate: acc * (1 + rate)), inflation_level[:years], 1)

            if events.count() > 0 and events[0].action == 'RETIRESMARTZ_SPENDING_UP_CONTRIB_DOWN':
                e = Event.RETIRESMARTZ_SPENDING_UP_CONTRIB_DOWN_AGAIN.log(None,
                                                                            orig.btc,
                                                                            updated.btc,
                                                                            user=updated.client.user,
                                                                            obj=updated)
                advice = RetirementAdvice(plan=updated, trigger=e)
                advice.text = advice_responses.get_increase_spending_decrease_contribution_again(advice, orig.btc, orig.btc * nth_rate)
                advice.save()
            else:
                e = Event.RETIRESMARTZ_SPENDING_UP_CONTRIB_DOWN.log(None,
                                                                            orig.btc,
                                                                            updated.btc,
                                                                            user=updated.client.user,
                                                                            obj=updated)
                advice = RetirementAdvice(plan=updated, trigger=e)
                advice.text = advice_responses.get_increase_spending_decrease_contribution(advice, orig.btc, orig.btc * nth_rate)
                advice.save()

        if orig.btc < updated.btc:
            nth_rate = reduce((lambda acc, rate: acc * (1 + rate)), inflation_level[:25], 1)
            e = Event.RETIRESMARTZ_SPENDING_DOWN_CONTRIB_UP.log(None,
                                                                orig.btc,
                                                                updated.btc,
                                                                user=updated.client.user,
                                                                obj=updated)
            advice = RetirementAdvice(plan=updated, trigger=e)
            advice.text = advice_responses.get_increase_contribution_decrease_spending(advice, updated.btc, updated.btc * nth_rate)
            advice.save()

            # contributions increased, spending decreased
            # this one is suppose to trigger if there is a second
            # contribution increase - check if previous event is in current
            # retirementadvice feed
            # e = Event.RETIRESMARTZ_SPENDABLE_INCOME_DOWN_CONTRIB_UP.log(None,
            #                                                             orig.btc,
            #                                                             updated.btc,
            #                                                             user=updated.client.user,
            #                                                             obj=updated)
            # advice = RetirementAdvice(plan=updated, trigger=e)
            # advice.text = advice_responses.get_decrease_spending_increase_contribution(advice)
            # advice.save()

        # Risk Slider Changed
        if updated.desired_risk < orig.desired_risk:
            # protective move
            e = Event.RETIRESMARTZ_PROTECTIVE_MOVE.log(None,
                                                       orig.desired_risk,
                                                       updated.desired_risk,
                                                       user=updated.client.user,
                                                       obj=updated)
            advice = RetirementAdvice(plan=updated, trigger=e)
            advice.text = advice_responses.get_protective_move(advice)
            advice.save()
        elif updated.desired_risk > orig.desired_risk:
            # dynamic move
            e = Event.RETIRESMARTZ_DYNAMIC_MOVE.log(None,
                                                    orig.desired_risk,
                                                    updated.desired_risk,
                                                    user=updated.client.user,
                                                    obj=updated)
            advice = RetirementAdvice(plan=updated, trigger=e)
            advice.text = advice_responses.get_dynamic_move(advice)
            advice.save()

        # age manually adjusted selected_life_expectancy
        if updated.selected_life_expectancy != orig.selected_life_expectancy:
            e = Event.RETIRESMARTZ_RETIREMENT_AGE_ADJUSTED.log(None,
                                                               orig.retirement_age,
                                                               updated.retirement_age,
                                                               user=updated.client.user,
                                                               obj=updated)
            advice = RetirementAdvice(plan=updated, trigger=e)
            advice.text = advice_responses.get_manually_adjusted_age(advice)
            advice.save()

        # Retirement Age Adjusted
        if updated.retirement_age >= 62 and updated.retirement_age <= 70:
            if orig.retirement_age != updated.retirement_age:
                # retirement age changed
                if orig.retirement_age > 62 and updated.retirement_age == 62:
                    # decreased to age 62
                    e = Event.RETIRESMARTZ_RETIREMENT_AGE_ADJUSTED.log(None,
                                                                       orig.retirement_age,
                                                                       updated.retirement_age,
                                                                       user=updated.client.user,
                                                                       obj=updated)
                    advice = RetirementAdvice(plan=updated, trigger=e)
                    advice.text = advice_responses.get_decrease_retirement_age_to_62(advice)
                    advice.save()
                elif orig.retirement_age > 63 and updated.retirement_age == 63:
                    # decreased to age 63
                    e = Event.RETIRESMARTZ_RETIREMENT_AGE_ADJUSTED.log(None,
                                                                       orig.retirement_age,
                                                                       updated.retirement_age,
                                                                       user=updated.client.user,
                                                                       obj=updated)
                    advice = RetirementAdvice(plan=updated, trigger=e)
                    advice.text = advice_responses.get_decrease_retirement_age_to_63(advice)
                    advice.save()
                elif orig.retirement_age > 64 and updated.retirement_age == 64:
                    # decreased to age 64
                    e = Event.RETIRESMARTZ_RETIREMENT_AGE_ADJUSTED.log(None,
                                                                       orig.retirement_age,
                                                                       updated.retirement_age,
                                                                       user=updated.client.user,
                                                                       obj=updated)
                    advice = RetirementAdvice(plan=updated, trigger=e)
                    advice.text = advice_responses.get_decrease_retirement_age_to_64(advice)
                    advice.save()
                elif orig.retirement_age > 65 and updated.retirement_age == 65:
                    # decreased to age 65
                    e = Event.RETIRESMARTZ_RETIREMENT_AGE_ADJUSTED.log(None,
                                                                       orig.retirement_age,
                                                                       updated.retirement_age,
                                                                       user=updated.client.user,
                                                                       obj=updated)
                    advice = RetirementAdvice(plan=updated, trigger=e)
                    advice.text = advice_responses.get_decrease_retirement_age_to_65(advice)
                    advice.save()
                elif orig.retirement_age < 67 and updated.retirement_age == 67:
                    # increased to age 67
                    e = Event.RETIRESMARTZ_RETIREMENT_AGE_ADJUSTED.log(None,
                                                                       orig.retirement_age,
                                                                       updated.retirement_age,
                                                                       user=updated.client.user,
                                                                       obj=updated)
                    advice = RetirementAdvice(plan=updated, trigger=e)
                    advice.text = advice_responses.get_increase_retirement_age_to_67(advice)
                    advice.save()
                elif orig.retirement_age < 68 and updated.retirement_age == 68:
                    # increased to age 68
                    e = Event.RETIRESMARTZ_RETIREMENT_AGE_ADJUSTED.log(None,
                                                                       orig.retirement_age,
                                                                       updated.retirement_age,
                                                                       user=updated.client.user,
                                                                       obj=updated)
                    advice = RetirementAdvice(plan=updated, trigger=e)
                    advice.text = advice_responses.get_increase_retirement_age_to_68(advice)
                    advice.save()
                elif orig.retirement_age < 69 and updated.retirement_age == 69:
                    # increased to age 69
                    e = Event.RETIRESMARTZ_RETIREMENT_AGE_ADJUSTED.log(None,
                                                                       orig.retirement_age,
                                                                       updated.retirement_age,
                                                                       user=updated.client.user,
                                                                       obj=updated)
                    advice = RetirementAdvice(plan=updated, trigger=e)
                    advice.text = advice_responses.get_increase_retirement_age_to_69(advice)
                    advice.save()
                elif orig.retirement_age < 70 and updated.retirement_age == 70:
                    # increased to age 70
                    e = Event.RETIRESMARTZ_RETIREMENT_AGE_ADJUSTED.log(None,
                                                                       orig.retirement_age,
                                                                       updated.retirement_age,
                                                                       user=updated.client.user,
                                                                       obj=updated)
                    advice = RetirementAdvice(plan=updated, trigger=e)
                    advice.text = advice_responses.get_increase_retirement_age_to_70(advice)
                    advice.save()

        if orig.on_track != updated.on_track:
            # user update to goal caused on_track status changed
            if updated.on_track:
                # RetirementPlan now on track
                e = Event.RETIRESMARTZ_ON_TRACK_NOW.log(None,
                                                        user=updated.client.user,
                                                        obj=updated)
                advice = RetirementAdvice(plan=updated, trigger=e)
                advice.text = advice_responses.get_off_track_item_adjusted_to_on_track(advice)
                advice.save()
            else:
                # RetirementPlan now off track

                e = Event.RETIRESMARTZ_OFF_TRACK_NOW.log(None,
                                                         user=updated.client.user,
                                                         obj=updated)
                advice = RetirementAdvice(plan=updated, trigger=e)
                advice.text = advice_responses.get_on_track_item_adjusted_to_off_track(advice)
                advice.save()

        if updated.agreed_on:
            # Log event
            e = Event.RETIREMENT_SOA_GENERATED.log('New Retirement Plan Agreed.',
                                              user=updated.client.user,
                                              obj=updated.statement_of_advice)

            Notify.CLIENT_AGREE_RETIREMENT_PLAN.send(
                actor=updated.client,
                recipient=updated.client.advisor.user,
                action_object=updated,
                target=updated.client.firm
            )
            updated.send_plan_agreed_email()

        return Response(self.serializer_response_class(updated).data)

    @detail_route(methods=['get'], url_path='suggested-retirement-income')
    def suggested_retirement_income(self, request, parent_lookup_client, pk, format=None):
        """
        Calculates a suggested retirement income based on the client's
        retirement plan and personal profile.
        """
        # TODO: Make this work
        return Response(1234)

    @detail_route(methods=['get'], url_path='calculate-contributions')
    def calculate_contributions(self, request, parent_lookup_client, pk, format=None):
        """
        Calculates suggested contributions (value for the amount in the
        btc and atc) that will generate the desired retirement income.
        """
        # TODO: Make this work
        return Response({'btc_amount': 1111, 'atc_amount': 0})

    @detail_route(methods=['get'], url_path='calculate-income')
    def calculate_income(self, request, parent_lookup_client, pk, format=None):
        """
        Calculates retirement income possible given the current contributions
        and other details on the retirement plan.
        """
        # TODO: Make this work
        return Response(2345)

    @detail_route(methods=['get'], url_path='calculate-balance-income')
    def calculate_balance_income(self, request, parent_lookup_client, pk, format=None):
        """
        Calculates the retirement balance required to provide the
        desired_income as specified in the plan.
        """
        # TODO: Make this work
        return Response(5555555)

    @detail_route(methods=['get'], url_path='calculate-income-balance')
    def calculate_income_balance(self, request, parent_lookup_client, pk, format=None):
        """
        Calculates the retirement income possible with a supplied
        retirement balance and other details on the retirement plan.
        """
        # TODO: Make this work
        return Response(1357)

    @detail_route(methods=['get'], url_path='calculate-balance-contributions')
    def calculate_balance_contributions(self, request, parent_lookup_client, pk, format=None):
        """
        Calculates the retirement balance generated from the contributions.
        """
        # TODO: Make this work
        return Response(6666666)

    @detail_route(methods=['get'], url_path='calculate-contributions-balance')
    def calculate_contributions_balance(self, request, parent_lookup_client, pk, format=None):
        """
        Calculates the contributions required to generate the
        given retirement balance.
        """
        # TODO: Make this work
        return Response({'btc_amount': 2222, 'atc_amount': 88})

    @detail_route(methods=['get'], url_path='calculate-demo')
    def calculate_demo(self, request, parent_lookup_client, pk, format=None):
        """
        Calculate the single projection values for the
        current retirement plan settings.
        {
          "portfolio": [
            # list of [fund id, weight as percent]. There will be max 33 of these. Likely 5-10
            [1, 5],
            [53, 12],
            ...
          ],
          "projection": [
            # this is the asset and cash-flow projection. It is a list of [date, assets, income]. There will be at most 50 of these. (21 bytes each)
            [143356, 120000, 2000],
            [143456, 119000, 2004],
            ...
          ]
        plans = RetirementPlan.objects.all()
        }
        "portfolio": 10% each for the first 10 tickers in the systems
        that aren't Closed.
        "projection": 50 time points evenly spaced along the
        remaining time until expected end of life.  Each time
        point with assets starting at 100000,
        going up by 1000 every point, income starting
        at 200000, increasing by 50 every point.
        """

        retirement_plan = self.get_object()
        tickers = Ticker.objects.filter(~Q(state=Ticker.State.CLOSED.value))
        portfolio = []
        projection = []
        for idx, ticker in enumerate(tickers[:10]):
            percent = 0
            if idx <= 9:
                # 10% each for first 10 tickers
                percent = 10
            portfolio.append([ticker.id, percent])
        # grab 50 evenly spaced time points between dob and current time
        today = timezone.now().date()
        last_day = retirement_plan.client.date_of_birth + relativedelta(years=retirement_plan.selected_life_expectancy)
        day_interval = (last_day - today) / 49
        income_start = 20000
        assets_start = 100000
        for i in range(50):
            income = income_start + (i * 50)
            assets = assets_start + (i * 1000)
            dt = today + i * day_interval
            projection.append([d2ed(dt), assets, income])
        return Response({'portfolio': portfolio, 'projection': projection})

    @list_route(methods=['put'], url_path='upload')
    def upload(self, request, parent_lookup_client, format=None):
        """
        Endpoint for pdf uploads
        accepts fields:
            tax_transcript
            social_security_statement
            partner_social_security_statement
        """
        serializer = serializers.PDFUploadWritableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user.client, serializer.validated_data)
        client = Client.objects.get(pk=parent_lookup_client)
        return Response(serializers.PDFUploadSerializer(client).data)

    @detail_route(methods=['get'], url_path='calculated-data')
    def calculated_data(self, request, parent_lookup_client, pk, format=None):
        plan = self.get_object()
        try:
            projection = plan.projection
            pser = PortfolioSerializer(instance=plan.goal_setting.portfolio)
            return Response({'portfolio': pser.data,
                             'projection': projection.proj_data,
                             'on_track': projection.on_track,
                             'reload_feed': False})
        except ObjectDoesNotExist:
            return self.calculate(request, parent_lookup_client, format)

    @detail_route(methods=['get'], url_path='calculate')
    def calculate(self, request, parent_lookup_client, pk, format=None):
        """
        Calculate the single projection values for the current retirement plan.
        {
          "portfolio": [
            # list of [fund id, weight as percent]. There will be max 20 of these. Likely 5-10
            [1, 5],
            [53, 12],
            ...
          ],
          "projection": [
            # this is the asset and cash-flow projection. It is a list of [date, assets, income]. There will be at most 50 of these. (21 bytes each)
            [43356, 120000, 2000],
            [43456, 119000, 2004],
            ...
          ]
        }
        """

        plan = self.get_object()
        # We need a date of birth for the client
        if not plan.client.date_of_birth:
            raise ValidationError("Client must have a date of birth entered to calculate retirement plans.")

        # Selected_life_expectancy must be between 65 - 100
        if plan.selected_life_expectancy > 100:
            raise ValidationError("Life expectancy value above valid range (>100)")

        if plan.selected_life_expectancy < 65:
            raise ValidationError("Life expectancy value below valid range (<65)")

        # TODO: We can cache the portfolio on the plan and only update it every 24hrs, or if the risk changes.
        try:
            settings = create_settings(plan)
        except Unsatisfiable as e:
            rdata = {'reason': "No portfolio could be found: {}".format(e)}
            if e.req_funds is not None:
                rdata['req_funds'] = e.req_funds
            return Response({'error': rdata}, status=status.HTTP_400_BAD_REQUEST)

        plan.set_settings(settings)
        plan.save()

        # Get the z-multiplier for the given confidence
        z_mult = -st.norm.ppf(plan.expected_return_confidence)
        performance = (settings.portfolio.er + z_mult * settings.portfolio.stdev)/100

        # Get external_income plans
        plans = RetirementPlan.objects.all()

        # Get projection of future income and assets for US tax payer
        projection_end = plan.selected_life_expectancy

        # terminate projection based on partner with longest life expectancy
        # i.e. based on life expectancy of younger of user or partner
        if plan.client.is_married:
            user_age = helpers.get_age(plan.client.date_of_birth)
            partner_age = helpers.get_age(plan.partner_data['dob'])
            user_older_by = user_age - partner_age
            if user_older_by > 0:
                # life expectancy must be no greater than 100
                projection_end = min(projection_end + user_older_by, 100)

        user = tax.TaxUser(plan, projection_end, False, plans)
        user.create_maindf()

        try:
            projection = plan.projection
        except ObjectDoesNotExist:
            projection = RetirementProjection(plan=plan)

        projection.income_actual_monthly = user.income_actual_monthly
        projection.income_desired_monthly = user.income_desired_monthly
        projection.taxable_assets_monthly = user.taxable_assets_monthly
        projection.nontaxable_assets_monthly = user.nontaxable_assets_monthly
        projection.proj_balance_at_retire_in_todays = user.proj_balance_at_retire_in_todays
        projection.proj_inc_actual_at_retire_in_todays = user.proj_inc_actual_at_retire_in_todays
        projection.proj_inc_desired_at_retire_in_todays = user.proj_inc_desired_at_retire_in_todays
        projection.savings_end_date_as_age = user.savings_end_date_as_age
        projection.current_percent_soc_sec = user.current_percent_soc_sec
        projection.current_percent_medicare = user.current_percent_medicare
        projection.current_percent_fed_tax = user.current_percent_fed_tax
        projection.current_percent_state_tax = user.current_percent_state_tax
        projection.non_taxable_inc = user.non_taxable_inc
        projection.tot_taxable_dist = user.tot_taxable_dist
        projection.annuity_payments = user.annuity_payments
        projection.pension_payments = user.pension_payments
        projection.ret_working_inc = user.ret_working_inc
        projection.soc_sec_benefit = user.soc_sec_benefit
        projection.taxable_accounts = user.taxable_accounts
        projection.non_taxable_accounts = user.non_taxable_accounts

        projection.list_of_account_balances = [
            {'account_type' : constants.ACCOUNT_TYPE_401A, 'data' : user.accounts_401a},
            {'account_type' : constants.ACCOUNT_TYPE_401K, 'data' : user.accounts_401k},
            {'account_type' : constants.ACCOUNT_TYPE_403B, 'data' : user.accounts_403b},
            {'account_type' : constants.ACCOUNT_TYPE_403K, 'data' : user.accounts_403k},
            {'account_type' : constants.ACCOUNT_TYPE_409A, 'data' : user.accounts_409a},
            {'account_type' : constants.ACCOUNT_TYPE_457, 'data' : user.accounts_457},
            {'account_type' : constants.ACCOUNT_TYPE_ESOP, 'data' : user.accounts_esop},
            {'account_type' : constants.ACCOUNT_TYPE_GOVERMENTAL, 'data' : user.accounts_gov},
            {'account_type' : constants.ACCOUNT_TYPE_INDIVDUAL401K, 'data' : user.accounts_ind_401k},
            {'account_type' : constants.ACCOUNT_TYPE_INDROTH401K, 'data' : user.accounts_ind_roth_401k},
            {'account_type' : constants.ACCOUNT_TYPE_IRA, 'data' : user.accounts_ira},
            {'account_type' : constants.ACCOUNT_TYPE_MONEYPURCHASE, 'data' : user.accounts_mon_purch},
            {'account_type' : constants.ACCOUNT_TYPE_PAYROLLDEDUCTIRA, 'data' : user.accounts_pay_deduct_ira},
            {'account_type' : constants.ACCOUNT_TYPE_PROFITSHARING, 'data' : user.accounts_prof_sharing},
            {'account_type' : constants.ACCOUNT_TYPE_QUALIFIEDANNUITY, 'data' : user.accounts_qual_annuity},
            {'account_type' : constants.ACCOUNT_TYPE_QUALIFIEDNPPLAN, 'data' : user.accounts_qual_np},
            {'account_type' : constants.ACCOUNT_TYPE_QUALIFIEDNPROTHPLAN, 'data' : user.accounts_qual_np_roth},
            {'account_type' : constants.ACCOUNT_TYPE_QUALIFIEDPRIV457PLAN, 'data' : user.accounts_priv_457},
            {'account_type' : constants.ACCOUNT_TYPE_ROTH401K, 'data' : user.accounts_roth_401k},
            {'account_type' : constants.ACCOUNT_TYPE_ROTHIRA, 'data' : user.accounts_roth_ira},
            {'account_type' : constants.ACCOUNT_TYPE_SARSEPIRA, 'data' : user.accounts_sarsep_ira},
            {'account_type' : constants.ACCOUNT_TYPE_SEPIRA, 'data' : user.accounts_sep_ira},
            {'account_type' : constants.ACCOUNT_TYPE_SIMPLEIRA, 'data' : user.accounts_simple_ira},
            {'account_type' : constants.ACCOUNT_TYPE_TAXDEFERRED_ANNUITY, 'data' : user.accounts_tax_def_annuity}]

        projection.reverse_mort = user.reverse_mort
        projection.house_value = user.house_value
        projection.house_value_at_retire_in_todays = user.house_value_at_retire_in_todays
        projection.reverse_mort_pymnt_at_retire_in_todays = user.reverse_mort_pymnt_at_retire_in_todays

        if plan.client.civil_status == 1 or plan.client.civil_status == 2:
            partner = tax.TaxUser(plan, projection_end, True, plans)
            partner.create_maindf()

            projection.part_income_actual_monthly = partner.income_actual_monthly
            projection.part_income_desired_monthly = partner.income_desired_monthly
            projection.part_taxable_assets_monthly = partner.taxable_assets_monthly
            projection.part_nontaxable_assets_monthly = partner.nontaxable_assets_monthly
            projection.part_proj_balance_at_retire_in_todays = partner.proj_balance_at_retire_in_todays
            projection.part_proj_inc_actual_at_retire_in_todays = partner.proj_inc_actual_at_retire_in_todays
            projection.part_proj_inc_desired_at_retire_in_todays = partner.proj_inc_desired_at_retire_in_todays
            projection.part_savings_end_date_as_age = partner.savings_end_date_as_age
            projection.part_current_percent_soc_sec = partner.current_percent_soc_sec
            projection.part_current_percent_medicare = partner.current_percent_medicare
            projection.part_current_percent_fed_tax = partner.current_percent_fed_tax
            projection.part_current_percent_state_tax = partner.current_percent_state_tax
            projection.part_non_taxable_inc = partner.non_taxable_inc

            projection.part_list_of_account_balances = [
                {'account_type' : constants.ACCOUNT_TYPE_401A, 'data' : partner.accounts_401a},
                {'account_type' : constants.ACCOUNT_TYPE_401K, 'data' : partner.accounts_401k},
                {'account_type' : constants.ACCOUNT_TYPE_403B, 'data' : partner.accounts_403b},
                {'account_type' : constants.ACCOUNT_TYPE_403K, 'data' : partner.accounts_403k},
                {'account_type' : constants.ACCOUNT_TYPE_409A, 'data' : partner.accounts_409a},
                {'account_type' : constants.ACCOUNT_TYPE_457, 'data' : partner.accounts_457},
                {'account_type' : constants.ACCOUNT_TYPE_ESOP, 'data' : partner.accounts_esop},
                {'account_type' : constants.ACCOUNT_TYPE_GOVERMENTAL, 'data' : partner.accounts_gov},
                {'account_type' : constants.ACCOUNT_TYPE_INDIVDUAL401K, 'data' : partner.accounts_ind_401k},
                {'account_type' : constants.ACCOUNT_TYPE_INDROTH401K, 'data' : partner.accounts_ind_roth_401k},
                {'account_type' : constants.ACCOUNT_TYPE_IRA, 'data' : partner.accounts_ira},
                {'account_type' : constants.ACCOUNT_TYPE_MONEYPURCHASE, 'data' : partner.accounts_mon_purch},
                {'account_type' : constants.ACCOUNT_TYPE_PAYROLLDEDUCTIRA, 'data' : partner.accounts_pay_deduct_ira},
                {'account_type' : constants.ACCOUNT_TYPE_PROFITSHARING, 'data' : partner.accounts_prof_sharing},
                {'account_type' : constants.ACCOUNT_TYPE_QUALIFIEDANNUITY, 'data' : partner.accounts_qual_annuity},
                {'account_type' : constants.ACCOUNT_TYPE_QUALIFIEDNPPLAN, 'data' : partner.accounts_qual_np},
                {'account_type' : constants.ACCOUNT_TYPE_QUALIFIEDNPROTHPLAN, 'data' : partner.accounts_qual_np_roth},
                {'account_type' : constants.ACCOUNT_TYPE_QUALIFIEDPRIV457PLAN, 'data' : partner.accounts_priv_457},
                {'account_type' : constants.ACCOUNT_TYPE_ROTH401K, 'data' : partner.accounts_roth_401k},
                {'account_type' : constants.ACCOUNT_TYPE_ROTHIRA, 'data' : partner.accounts_roth_ira},
                {'account_type' : constants.ACCOUNT_TYPE_SARSEPIRA, 'data' : partner.accounts_sarsep_ira},
                {'account_type' : constants.ACCOUNT_TYPE_SEPIRA, 'data' : partner.accounts_sep_ira},
                {'account_type' : constants.ACCOUNT_TYPE_SIMPLEIRA, 'data' : partner.accounts_simple_ira},
                {'account_type' : constants.ACCOUNT_TYPE_TAXDEFERRED_ANNUITY, 'data' : partner.accounts_tax_def_annuity}]

            projection.part_tot_taxable_dist = partner.tot_taxable_dist
            projection.part_annuity_payments = partner.annuity_payments
            projection.part_pension_payments = partner.pension_payments
            projection.part_ret_working_inc = partner.ret_working_inc
            projection.part_soc_sec_benefit = partner.soc_sec_benefit
            projection.part_taxable_accounts = partner.taxable_accounts
            projection.part_non_taxable_accounts = partner.non_taxable_accounts
            projection.part_reverse_mort = partner.reverse_mort
            projection.part_house_value = partner.house_value
            projection.part_house_value_at_retire_in_todays = partner.house_value_at_retire_in_todays
            projection.part_reverse_mort_pymnt_at_retire_in_todays = partner.reverse_mort_pymnt_at_retire_in_todays

        # Convert these returned values to a format for the API
        if plan.client.civil_status == 1 or plan.client.civil_status == 2:
            user.maindf['Joint_Taxable_And_Nontaxable_Accounts'] = user.maindf['Taxable_And_Nontaxable_Accounts'] + partner.maindf['Taxable_And_Nontaxable_Accounts']
            user.maindf['Joint_Actual_Inc'] = user.maindf['Actual_Inc'] + partner.maindf['Actual_Inc']
            user.maindf['Joint_Desired_Inc'] = user.maindf['Desired_Inc'] + partner.maindf['Desired_Inc']
            catd = pd.concat([user.maindf['Joint_Taxable_And_Nontaxable_Accounts'], user.maindf['Joint_Actual_Inc'], user.maindf['Joint_Desired_Inc']], axis=1)

        else:
            catd = pd.concat([user.maindf['Taxable_And_Nontaxable_Accounts'], user.maindf['Actual_Inc'], user.maindf['Desired_Inc']], axis=1)

        locs = np.linspace(0, len(catd)-1, num=50, dtype=int)
        proj_data = [(d2ed(d), a, i, desired) for d, a, i, desired in catd.iloc[locs, :].itertuples()]
        pser = PortfolioSerializer(instance=settings.portfolio)

        on_track = self.check_is_on_track(proj_data, plan)

        projection.proj_data = proj_data
        projection.on_track = on_track

        projection.save()

        # log status of on/off track change.
        reload_feed = False
        events = EventLog.objects.filter(
            Q(action='RETIRESMARTZ_ON_TRACK_NOW') |
            Q(action='RETIRESMARTZ_OFF_TRACK_NOW')
        ).order_by('-timestamp')

        if on_track and (events.count() == 0 or events[0].action == 'RETIRESMARTZ_OFF_TRACK_NOW'):
            e = Event.RETIRESMARTZ_ON_TRACK_NOW.log(None,
                                                    user=plan.client.user,
                                                    obj=plan)
            advice = RetirementAdvice(plan=plan, trigger=e)
            advice.text = advice_responses.get_off_track_item_adjusted_to_on_track(advice)
            advice.save()
            reload_feed = True

        if not on_track and (events.count() == 0 or events[0].action == 'RETIRESMARTZ_ON_TRACK_NOW'):
            e = Event.RETIRESMARTZ_OFF_TRACK_NOW.log(None,
                                                    user=plan.client.user,
                                                    obj=plan)
            advice = RetirementAdvice(plan=plan, trigger=e)
            advice.text = advice_responses.get_on_track_item_adjusted_to_off_track(advice)
            advice.save()
            reload_feed = True

        return Response({'portfolio': pser.data,
                         'projection': proj_data,
                         'on_track': on_track,
                         'reload_feed': reload_feed})

    def check_is_on_track(self, proj_data, plan):
        def values_since_retirement(retirement_date, arr):
            return list(filter(lambda item: item['x'] >= retirement_date, arr))

        def value_map(item_array):
            return {
                'x': item_array[0] * 8.64e4, # epoch days => epoch ms
                'y': item_array[2]
            }

        def target_value_map(item_array):
            return {
                'x': item_array[0] * 8.64e4, # epoch days => epoch ms
                'y': item_array[3]
            }

        values = list(map(value_map, proj_data))
        target_values = list(map(target_value_map, proj_data))

        retirement_date = plan.client.date_of_birth + relativedelta(years=+plan.retirement_age)
        rt_dt_epoch = time.mktime(retirement_date.timetuple())

        rt_values = values_since_retirement(rt_dt_epoch, values)
        target_rt_values = values_since_retirement(rt_dt_epoch, target_values)

        ary_len = min(len(rt_values), len(target_rt_values))
        for i in range(0, ary_len):
            if rt_values[i]['y'] < target_rt_values[i]['y']:
                return False
        return True


class RetiresmartzAdviceViewSet(ApiViewMixin, NestedViewSetMixin, ModelViewSet):
    model = RetirementPlan
    permission_classes = (IsAuthenticated,)
    queryset = RetirementAdvice.objects.filter(read=None).order_by('-dt')  # unread advice
    serializer_class = serializers.RetirementAdviceReadSerializer
    serializer_response_class = serializers.RetirementAdviceReadSerializer

    def get_queryset(self):
        """
        The nested viewset takes care of only returning results for the client we are looking at.
        We need to add logic to only allow access to users that can view the plan.
        """
        qs = super(RetiresmartzAdviceViewSet, self).get_queryset()
        # Check user object permissions
        user = SupportRequest.target_user(self.request)
        return qs.filter_by_user(user)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.RetirementAdviceReadSerializer
        elif self.request.method == 'PUT':
            return serializers.RetirementAdviceWritableSerializer
