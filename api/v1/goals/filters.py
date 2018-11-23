import django_filters

from goal.models import Goal


class GoalFilter(django_filters.FilterSet):
    class Meta:
        model = Goal
        fields = []
