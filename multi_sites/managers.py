import logging
from django.db.models import QuerySet


class AccountTypeQuerySet(QuerySet):
    def filter_by_user(self, user):
        if user.is_advisor:
            return self.filter_by_advisor(user.advisor)
        elif user.is_client:
            return self.filter_by_client(user.client)
        else:
            return self.none()

    def filter_by_advisor(self, advisor):
        return self.filter(id__in=advisor.firm.account_types.all())

    def filter_by_client(self, client):
        return self.filter_by_advisor(client.advisor)
