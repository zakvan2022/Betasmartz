from rest_framework import status
from rest_framework.test import APITestCase
from django.core.urlresolvers import reverse
from main.stripe import convert_dollars_to_cents


class StripeCoreTests(APITestCase):

    def test_convert_dollars_to_cents(self):
        x = 5.00
        y = convert_dollars_to_cents(x)
        self.assertEqual(y, 500)

        x = 5.55
        y = convert_dollars_to_cents(x)
        self.assertEqual(y, 555)
