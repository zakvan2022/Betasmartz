from datetime import date
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.conf import settings
from client.models import EmailInvite
from django.test import Client as DjangoClient
from common.constants import GROUP_SUPPORT_STAFF
from main.constants import ACCOUNT_TYPE_PERSONAL, EMPLOYMENT_STATUS_EMMPLOYED, GENDER_MALE
from .factories import ClientAccountFactory, ClientFactory, GroupFactory


class DocumentTests(APITestCase):
    def setUp(self):
        self.support_group = GroupFactory(name=GROUP_SUPPORT_STAFF)
        self.betasmartz_client = ClientFactory.create()

    def test_get_documents(self):
        url = '/api/v1/documents'
        self.client.force_authenticate(user=self.betasmartz_client.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
