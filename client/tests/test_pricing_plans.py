from django.test import TestCase

from api.v1.tests.factories import ClientFactory, FirmFactory, UserFactory
from advisor.models import PricingPlanAdvisor
from client.models import PricingPlanClient


class ModelTests(TestCase):
    def setUp(self):
        self.firm = FirmFactory.create()

    def test_create_empty_pricing_for_new_firm(self):
        pricing_plan = self.firm.pricing_plan
        self.assertEqual(pricing_plan.bps, 0)
        self.assertEqual(pricing_plan.fixed, 0)
        self.assertEqual(pricing_plan.system_bps, 0)
        self.assertEqual(pricing_plan.system_fixed, 0)

    def test_firm_properties(self):
        self.assertEqual(self.firm.pricing_plan.system_fee, (0, 0))


class LogicTests(TestCase):
    def setUp(self):
        self.client = ClientFactory.create(user=UserFactory.create())
        self.pricing_plan = self.client.advisor.firm.pricing_plan
        self.pricing_plan.bps = 100
        self.pricing_plan.fixed = 50
        self.pricing_plan.system_fee = 10, 5
        self.pricing_plan.save()

    def test_no_overrides(self):
        pp = self.client.my_pricing_plan
        self.assertEqual(pp.total_bps, 110)
        self.assertEqual(pp.total_fixed, 55)

    def test_client_override(self):
        PricingPlanClient.objects.create(
            parent=self.pricing_plan,
            person=self.client,
            bps=50,
            fixed=20,
        )
        pp = self.client.my_pricing_plan
        self.assertEqual(pp.total_bps, 60)
        self.assertEqual(pp.total_fixed, 25)

    def test_advisor_override(self):
        PricingPlanAdvisor.objects.create(
            parent=self.pricing_plan,
            person=self.client.advisor,
            bps=150,
            fixed=0,
        )
        pp = self.client.my_pricing_plan
        self.assertEqual(pp.total_bps, 160)
        self.assertEqual(pp.total_fixed, 5)

    def test_client_and_advisor_override(self):
        PricingPlanClient.objects.create(
            parent=self.pricing_plan,
            person=self.client,
            bps=50,
            fixed=20,
        )
        PricingPlanAdvisor.objects.create(
            parent=self.pricing_plan,
            person=self.client.advisor,
            bps=150,
            fixed=0,
        )
        pp = self.client.my_pricing_plan
        self.assertEqual(pp.total_bps, 60)
        self.assertEqual(pp.total_fixed, 25)
