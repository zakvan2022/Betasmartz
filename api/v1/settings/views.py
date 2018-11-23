from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site

from rest_framework import serializers as drf_serializers
from rest_framework.decorators import list_route
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin

from activitylog.models import ActivityLog
from api.v1.views import ReadOnlyApiViewMixin
from client.models import RiskProfileGroup
from goal.models import GoalType, GoalMetric
from main import constants
from main.abstract import PersonalData
from main.constants import US_RETIREMENT_ACCOUNT_TYPES
from multi_sites.models import AccountType
from portfolios.models import AssetClass, AssetFeature, Ticker, PortfolioProvider, PortfolioSet
from user.autologout import SessionExpire
from . import serializers
from ..permissions import IsAccessAuthorised
from client import models as client_models, healthdevice
from retiresmartz import models as retirement_models


class SettingsViewSet(ReadOnlyApiViewMixin, NestedViewSetMixin, GenericViewSet):
    """
    Experimental
    """
    serializer_class = drf_serializers.Serializer
    permission_classes = (
        IsAccessAuthorised,
    )

    def list(self, request):
        data = {
            'site': self.site(request).data,
            'goal_types': self.goal_types(request).data,
            'account_types': self.account_types(request).data,
            'activity_types': self.activity_types(request).data,
            'asset_classes': self.asset_classes(request).data,
            'tickers': self.tickers(request).data,
            'asset_features': self.asset_features(request).data,
            'constraint_comparisons': self.constraint_comparisons(request).data,
            'risk_profile_groups': self.risk_profile_groups(request).data,
            'civil_statuses': self.civil_statuses(request).data,
            'employment_statuses': self.employment_statuses(request).data,
            'external_asset_types': self.external_asset_types(request).data,
            'investor_risk_categories': self.investor_risk_categories(request).data,
            'retirement_account_categories': self.retirement_account_categories(request).data,
            'retirement_saving_categories': self.retirement_saving_categories(request).data,
            'retirement_expense_categories': self.retirement_expense_categories(request).data,
            'retirement_housing_categories': self.retirement_housing_categories(request).data,
            'retirement_lifestyle_categories': self.retirement_lifestyle_categories(request).data,
            'retirement_lifestyles': self.retirement_lifestyles(request).data,
            'constants': self.constants(request).data,
            'industry_types': self.industry_types(request).data,
            'occupation_types': self.occupation_types(request).data,
            'employer_types': self.employer_types(request).data,
            'portfolio_providers': self.portfolio_providers(request).data,
            'portfolio_sets': self.portfolio_sets(request).data,
            'health_devices': self.health_devices(request).data
        }
        return Response(data)

    @list_route(methods=['get'], url_path='site', permission_classes=[AllowAny])
    def site(self, request):
        site = get_current_site(request)
        serializer = serializers.SiteSerializer(site)
        return Response(serializer.data)

    @list_route(methods=['get'], url_path='goal-types')
    def goal_types(self, request):
        goal_types = GoalType.objects.order_by('name')
        serializer = serializers.GoalTypeListSerializer(goal_types, many=True)
        return Response(serializer.data)

    @list_route(methods=['get'], url_path='account-types')
    def account_types(self, request):
        res = []
        act = dict(constants.ACCOUNT_TYPES)
        for a_t in AccountType.objects.filter_by_user(request.user):
            res.append({
                "id": a_t.id,
                "name": act.get(a_t.id, constants.ACCOUNT_UNKNOWN),
                "creatable": a_t.id not in US_RETIREMENT_ACCOUNT_TYPES
            })

        return Response(res)

    @list_route(methods=['get'], url_path='activity-types')
    def activity_types(self, request):
        activity_types = ActivityLog.objects.order_by('name')
        serializer = serializers.ActivityLogSerializer(activity_types,
                                                       many=True)
        return Response(serializer.data)

    @list_route(methods=['get'], url_path='asset-classes')
    def asset_classes(self, request):
        asset_classes = AssetClass.objects.order_by('display_order',
                                                           'display_name')
        serializer = serializers.AssetClassListSerializer(asset_classes,
                                                          many=True)
        return Response(serializer.data)

    @list_route(methods=['get'])
    def tickers(self, request):
        tickers = Ticker.objects.filter(state=Ticker.State.ACTIVE.value).order_by('ordering', 'display_name')
        serializer = serializers.TickerListSerializer(tickers, many=True)
        return Response(serializer.data)

    @list_route(methods=['get'], url_path='asset-features')
    def asset_features(self, request):
        res = [{
                   "id": af.id,
                   "name": af.name,
                   "description": af.description,
                   "upper_limit": af.upper_limit,
                   "values": [{
                                  "id": v.id,
                                  "name": v.name,
                                  "description": v.description
                              } for v in af.values.all() if v.active]
               } for af in AssetFeature.objects.all() if af.active]
        return Response(res)

    @list_route(methods=['get'])
    def constraint_comparisons(self, request):
        comparisons = GoalMetric.comparisons
        return Response([{
                             "id": key,
                             "name": value
                         } for key, value in comparisons.items()])

    @list_route(methods=['get'], url_path='risk-profile-groups', permission_classes=[IsAuthenticated])
    def risk_profile_groups(self, request):
        groups = RiskProfileGroup.objects.all()
        serializer = serializers.RiskProfileGroupSerializer(groups, many=True)
        return Response(serializer.data)

    @list_route(methods=['get'])
    def civil_statuses(self, request):
        return Response([{"id": status.value, "name": status.human_name}
                         for status in PersonalData.CivilStatus])

    @list_route(methods=['get'])
    def employment_statuses(self, request):
        return Response([{"id": sid, "name": name}
                         for sid, name in constants.EMPLOYMENT_STATUSES])

    @list_route(methods=['get'])
    def external_asset_types(self, request):
        return Response([{"id": choice[0], "name": choice[1]}
                         for choice in client_models.ExternalAsset.Type.choices()])

    @list_route(methods=['get'])
    def constants(self, request):
        return Response({
            'session_length': SessionExpire(request).get_session_length(),
        })

    @list_route(methods=['get'], url_path='investor-risk-categories')
    def investor_risk_categories(self, request):
        categories = client_models.RiskCategory.objects.all()
        serializer = serializers.InvestorRiskCategorySerializer(categories, many=True)
        return Response(serializer.data)

    @list_route(methods=['get'], url_path='retirement-account-categories')
    def retirement_account_categories(self, request):
        serializer = serializers.EnumSerializer(retirement_models.RetirementPlan.AccountCategory)
        return Response(serializer.data['choices'])

    @list_route(methods=['get'], url_path='retirement-saving-categories')
    def retirement_saving_categories(self, request):
        serializer = serializers.EnumSerializer(retirement_models.RetirementPlan.SavingCategory)
        return Response(serializer.data['choices'])

    @list_route(methods=['get'], url_path='retirement-expense-categories')
    def retirement_expense_categories(self, request):
        serializer = serializers.EnumSerializer(retirement_models.RetirementPlan.ExpenseCategory)
        return Response(serializer.data['choices'])

    @list_route(methods=['get'], url_path='retirement-housing-categories')
    def retirement_housing_categories(self, request):
        serializer = serializers.EnumSerializer(retirement_models.RetirementPlan.HomeStyle)
        return Response(serializer.data['choices'])

    @list_route(methods=['get'], url_path='retirement-lifestyle-categories')
    def retirement_lifestyle_categories(self, request):
        serializer = serializers.EnumSerializer(retirement_models.RetirementPlan.LifestyleCategory)
        return Response(serializer.data['choices'])

    @list_route(methods=['get'], url_path='retirement-lifestyles')
    def retirement_lifestyles(self, request):
        lifestyles = retirement_models.RetirementLifestyle.objects.all().order_by('cost')
        serializer = serializers.RetirementLifestyleSerializer(lifestyles, many=True)
        return Response(serializer.data)

    @list_route(methods=['get'], url_path='industry-types', permission_classes=[IsAuthenticated])
    def industry_types(self, request):
        res = []
        itd = dict(constants.INDUSTRY_TYPES)
        for key in sorted(itd):
            res.append({
                "id": key,
                "name": itd[key]
            })
        return Response(res)

    @list_route(methods=['get'], url_path='occupation-types', permission_classes=[IsAuthenticated])
    def occupation_types(self, request):
        res = []
        itd = dict(constants.OCCUPATION_TYPES)
        for key in sorted(itd):
            res.append({
                "id": key,
                "name": itd[key]
            })
        return Response(res)

    @list_route(methods=['get'], url_path='employer-types', permission_classes=[IsAuthenticated])
    def employer_types(self, request):
        res = []
        itd = dict(constants.EMPLOYER_TYPES)
        for key in sorted(itd):
            res.append({
                "id": key,
                "name": itd[key]
            })
        return Response(res)

    @list_route(methods=['get'], url_path='portfolio-providers')
    def portfolio_providers(self, request):
        pps = PortfolioProvider.objects.all()
        serializer = serializers.PortfolioProviderSerializer(pps, many=True)
        return Response(serializer.data)

    @list_route(methods=['get'], url_path='portfolio-sets')
    def portfolio_sets(self, request):
        pss = PortfolioSet.objects.all()
        serializer = serializers.PortfolioSetSerializer(pss, many=True)
        return Response(serializer.data)

    @list_route(methods=['get'], url_path='health-devices', permission_classes=[IsAuthenticated])
    def health_devices(self, request):
        HEALTH_DEVICES_CONFIG = {
            'FITBIT_REDIRECT_URI': healthdevice.fitbit_get_redirect_uri(),
            'GOOGLEFIT_REDIRECT_URI': healthdevice.googlefit_get_redirect_uri(),
            'MICROSOFTHEALTH_REDIRECT_URI': healthdevice.microsofthealth_get_redirect_uri(),
            'UNDERARMOUR_REDIRECT_URI': healthdevice.underarmour_get_redirect_uri(),
            'WITHINGS_CONNECT_URI': healthdevice.withings_get_redirect_uri(),
            'JAWBONE_REDIRECT_URI': healthdevice.jawbone_get_redirect_uri(),
            'TOMTOM_REDIRECT_URI': healthdevice.tomtom_get_redirect_uri()
        }
        return Response(HEALTH_DEVICES_CONFIG)
