from unittest import mock

from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from errorlog.models import ErrorLog, JiraTicket


class ErrorLogTestCase(APITestCase):
    def test_user_authenticated(self):
        mock_jira = mock.Mock()
        with mock.patch('errorlog.models.JIRA', mock_jira):
            url = 'http://www.example.com'
            message = '''Something really bad happened.
    And no traces.'''
            r = self.client.post(reverse('api:v1:error-log'), {
                'header': 'Error',
                'url': url,
                'message': message,
            })
        self.assertEqual(r.status_code, 201)
        log_records = ErrorLog.objects.all()
        self.assertEqual(len(log_records), 1)
        jira_ticket = log_records.first().jira_ticket  # type: JiraTicket
        self.assertIsNotNone(jira_ticket)
