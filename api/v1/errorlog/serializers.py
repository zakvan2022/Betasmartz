from __future__ import unicode_literals

from django.conf import settings
from rest_framework import serializers

from errorlog.models import ErrorLog, JiraTicket


class ErrorLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorLog
        fields = ('header', 'message', 'source', 'user',
                  'url', 'details', 'created_at')
        read_only_fields = ('source', 'user', 'url', 'details', 'created_at')

    def save(self, **kwargs):
        instance = super(ErrorLogSerializer, self).save(**kwargs)

        if settings.JIRA_ENABLED:
            try:
                jira_ticket = JiraTicket.objects.get(header=instance.header,
                                                     message=instance.message)
            except JiraTicket.DoesNotExist:
                jira_ticket = JiraTicket.create(instance)

            instance.jira_ticket = jira_ticket
            instance.save()
        return super(ErrorLogSerializer, self).save(**kwargs)
