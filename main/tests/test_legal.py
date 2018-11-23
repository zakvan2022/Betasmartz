# -*- coding: utf-8 -*-
from django.test import TestCase
from django.core.urlresolvers import reverse
from rest_framework import status


class PrivacyPolicyTests(TestCase):
    def test_get_privacy_policy(self):
        url = reverse('privacy_notice')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_online_privacy(self):
        url = reverse('terms_of_use')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_legal(self):
        url = reverse('legal')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_product_brochure(self):
        url = reverse('product-brochure')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
