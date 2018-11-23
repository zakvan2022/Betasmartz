from rest_framework import serializers

from api.v1.serializers import ReadOnlyModelSerializer
from client.models import RiskProfileGroup, RiskProfileQuestion, RiskProfileAnswer, RiskCategory
from django.contrib.sites.models import Site
from goal.models import GoalType
from activitylog.models import ActivityLog
from multi_sites.models import Config as SiteConfig
from portfolios.models import AssetClass, Ticker, PortfolioProvider, PortfolioSet
from retiresmartz.models import RetirementLifestyle

class SiteConfigSerializer(ReadOnlyModelSerializer):
    white_logo = serializers.CharField()
    colored_logo = serializers.CharField()
    class Meta:
        model = SiteConfig
        exclude = ('id', 'logo', 'knocked_out_logo',)


class SiteSerializer(ReadOnlyModelSerializer):
    config = SiteConfigSerializer()
    class Meta:
        model = Site
        fields = ('domain', 'name', 'config',)


class GoalTypeListSerializer(serializers.ModelSerializer):
    """
    Experimental
    """
    class Meta:
        model = GoalType
        exclude = ('risk_sensitivity', 'order', 'risk_factor_weights')


class AssetClassListSerializer(serializers.ModelSerializer):
    """
    Experimental
    """
    class Meta:
        model = AssetClass


class ActivityLogSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = ActivityLog
        exclude = ('format_args',)


class TickerListSerializer(serializers.ModelSerializer):
    """
    Experimental
    """
    class Meta:
        model = Ticker
        exclude = (
            'data_api', 'data_api_param',
        )


class RiskProfileAnswerSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = RiskProfileAnswer
        exclude = (
            'question', 'order', 'b_score', 'a_score', 's_score'
        )


class RiskProfileQuestionSerializer(ReadOnlyModelSerializer):
    answers = RiskProfileAnswerSerializer(many=True)

    class Meta:
        model = RiskProfileQuestion
        exclude = (
            'group', 'order'
        )


class RiskProfileGroupSerializer(ReadOnlyModelSerializer):
    questions = RiskProfileQuestionSerializer(many=True)

    class Meta:
        model = RiskProfileGroup


class InvestorRiskCategorySerializer(ReadOnlyModelSerializer):
    class Meta:
        model = RiskCategory


class RetirementLifestyleSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = RetirementLifestyle


class EnumSerializer(serializers.Serializer):
    choices = serializers.SerializerMethodField()

    def get_choices(self, obj):
        return [ {'id': k, 'title': v} for k, v in obj.choices() ]


class PortfolioProviderSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = PortfolioProvider
        fields = ('id', 'name', 'type',)


class PortfolioSetSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = PortfolioSet
        fields = ('id', 'name', 'portfolio_provider',)
