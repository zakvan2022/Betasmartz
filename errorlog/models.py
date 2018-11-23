import logging

from django.conf import settings
from django.db import models
from jira import JIRA
from jsonfield.fields import JSONField

from common.structures import ChoiceEnum

logger = logging.getLogger(__name__)


class ErrorLog(models.Model):
    class ErrorSource(ChoiceEnum):
        WebApp = 1, 'WebApp'
        Backend = 2, 'Backend'
        FrontEnd = 3, 'FrontEnd'

        def __str__(self):
            return self.human_name

    source = models.IntegerField(choices=ErrorSource.choices())
    user = models.ForeignKey('user.User', blank=True, null=True,
                             related_name='logged_ui_errors')
    header = models.CharField(max_length=100)
    message = models.TextField()
    url = models.URLField()
    details = JSONField(blank=True, null=True)  # dict
    version = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    jira_ticket = models.ForeignKey('JiraTicket', blank=True, null=True)

    def __str__(self):
        msg = "{source}: {title}"
        if self.jira_ticket:
            msg += " ({jira_ticket})"
        return msg.format(source=self.get_source_display(),
                          title=self.header,
                          jira_ticket=self.jira_ticket)


class JiraTicket(models.Model):
    ticket = models.URLField(blank=True, null=True)
    header = models.CharField(max_length=100)
    message = models.TextField()
    task = models.CharField(max_length=100)

    class Meta:
        index_together = 'header', 'message'

    def __str__(self):
        return self.task

    @classmethod
    def create(cls, error: ErrorLog) -> 'JiraTicket':
        try:
            environment = '\n'.join(
                '%s: %s' % (k, v) for k, v in error.details.items())
        except (AttributeError, TypeError):
            environment = ''
        if environment:
            environment += error.url + '\n\n' + environment
        else:
            environment = error.url

        jira = JIRA(settings.JIRA_SERVER,
                    basic_auth=(settings.JIRA_USERNAME,
                                settings.JIRA_PASSWORD))

        try:
            issue = jira.create_issue(project=settings.JIRA_ERROR_PROJECT_ID,
                                      summary=error.header,
                                      description=error.message,
                                      issuetype=settings.JIRA_ISSUE_TYPE,
                                      labels=[error.get_source_display()],
                                      environment=environment)
            return cls.objects.create(ticket=issue.permalink(),
                                      header=error.header,
                                      message=error.message,
                                      task=issue.key)
        except Exception as e:
            logger.error('Cannot create a JIRA ticket (%s)', e)
