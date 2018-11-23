import logging

from django.db.models import Manager, QuerySet
from django.db.models.query_utils import Q


logger = logging.getLogger('execution.managers')


class PositionLotQuerySet(QuerySet):
    def filter_by_firm(self, firm):
        return self.filter(Q(execution_distribution__transaction__from_goal__account__primary_owner__advisor__firm=firm) |
                           Q(execution_distribution__transaction__to_goal__account__primary_owner__advisor__firm=firm))

    def filter_by_advisors(self, advisors):
        q = Q()
        for advisor in advisors:
            q |= Q(execution_distribution__transaction__from_goal__account__primary_owner__advisor=advisor)
            q |= Q(execution_distribution__transaction__to_goal__account__primary_owner__advisor=advisor)
        return self.filter(q)

    def filter_by_clients(self, clients):
        q = Q()
        for client in clients:
            q |= Q(execution_distribution__transaction__from_goal__account__primary_owner=client)
            q |= Q(execution_distribution__transaction__to_goal__account__primary_owner=client)
        return self.filter(q)

    def filter_by_risk_level(self, risk_levels=None):
        if risk_levels is None:
            return self

        from goal.models import GoalMetric

        if isinstance(risk_levels, int):
            risk_levels = [risk_levels, ]
        else:
            risk_levels = [int(r) for r in risk_levels]

        q = Q()
        for level in risk_levels:
            risk_min, risk_max = GoalMetric.risk_level_range(level)
            risk_min /= 100
            risk_max /= 100
            q |= Q(execution_distribution__transaction__from_goal__selected_settings__metric_group__metrics__configured_val__gte=risk_min,
                   execution_distribution__transaction__from_goal__selected_settings__metric_group__metrics__configured_val__lt=risk_max)
            q |= Q(execution_distribution__transaction__to_goal__selected_settings__metric_group__metrics__configured_val__gte=risk_min,
                   execution_distribution__transaction__to_goal__selected_settings__metric_group__metrics__configured_val__lt=risk_max)
        qs = self.filter(q, execution_distribution__transaction__to_goal__selected_settings__metric_group__metrics__type=GoalMetric.METRIC_TYPE_RISK_SCORE)

        return qs

    def filter_by_worth(self, worth=None):
        from client.models import Client
        qs = self
        if worth is None:
            return self

        clients = [p.execution_distribution.transaction.to_goal.account.primary_owner for p in qs]
        cmap = {}
        if worth == Client.WORTH_AFFLUENT:
            cmap['affluent'] = [c.id for c in clients if c.get_worth() == Client.WORTH_AFFLUENT]
            qs = self.filter(execution_distribution__transaction__to_goal__account__primary_owner__in=cmap['affluent'])
        elif worth == Client.WORTH_HIGH:
            cmap['high'] = [c.id for c in clients if c.get_worth() == Client.WORTH_HIGH]
            qs = self.filter(execution_distribution__transaction__to_goal__account__primary_owner__in=cmap['high'])
        elif worth == Client.WORTH_VERY_HIGH:
            cmap['very-high'] = [c.id for c in clients if c.get_worth() == Client.WORTH_VERY_HIGH]
            qs = self.filter(execution_distribution__transaction__to_goal__account__primary_owner__in=cmap['very-high'])
        elif worth == Client.WORTH_ULTRA_HIGH:
            cmap['ultra-high'] = [c.id for c in clients if c.get_worth() == Client.WORTH_ULTRA_HIGH]
            qs = self.filter(execution_distribution__transaction__to_goal__account__primary_owner__in=cmap['ultra-high'])
        return qs


class OrderManager(Manager):
    def is_complete(self):
        return self.filter(Status__in=Order.StatusChoice.complete_statuses())

    def is_not_complete(self):
        return self.exclude(Status__in=Order.StatusChoice.complete_statuses())
