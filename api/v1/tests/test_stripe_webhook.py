from rest_framework import status
from rest_framework.test import APITestCase
from django.core.urlresolvers import reverse
from api.v1.tests.factories import TransactionFactory
from goal.models import Transaction


class StripeWebhookTests(APITestCase):
    def setUp(self):
        self.event = {
          "id": "evt_1A2DXMIlMPPulN33wOcxU7Lp",
          "object": "event",
          "api_version": None,
          "created": 1490681436,
          "data": {
            "object": {
              "id": "ch_1A2DXNIlMPPulN33Vakds950",
              "object": "charge",
              "amount": 100,
              "amount_refunded": 0,
              "application": None,
              "application_fee": None,
              "balance_transaction": "txn_1A2DXNIlMPPulN33thIMqBiz",
              "captured": True,
              "created": 1490681437,
              "currency": "usd",
              "customer": None,
              "description": "My First Test Charge (created for API docs)",
              "destination": None,
              "dispute": None,
              "failure_code": None,
              "failure_message": None,
              "fraud_details": {
              },
              "invoice": None,
              "livemode": False,
              "metadata": {
              },
              "on_behalf_of": None,
              "order": None,
              "outcome": None,
              "paid": True,
              "receipt_email": None,
              "receipt_number": None,
              "refunded": False,
              "refunds": {
                "object": "list",
                "data": [

                ],
                "has_more": False,
                "total_count": 0,
                "url": "/v1/charges/ch_1A2DXNIlMPPulN33Vakds950/refunds"
              },
              "review": None,
              "shipping": None,
              "source": {
                "id": "card_19kX6dIlMPPulN33Pi9Pt0jP",
                "object": "card",
                "address_city": None,
                "address_country": None,
                "address_line1": None,
                "address_line1_check": None,
                "address_line2": None,
                "address_state": None,
                "address_zip": None,
                "address_zip_check": None,
                "brand": "Visa",
                "country": "US",
                "customer": None,
                "cvc_check": None,
                "dynamic_last4": None,
                "exp_month": 8,
                "exp_year": 2018,
                "funding": "credit",
                "last4": "4242",
                "metadata": {
                },
                "name": None,
                "tokenization_method": None
              },
              "source_transfer": None,
              "statement_descriptor": None,
              "status": "succeeded",
              "transfer_group": None
            }
          },
          "livemode": False,
          "pending_webhooks": 0,
          "request": None,
          "type": "charge.succeeded"
        }

        self.transfer = {
          "id": "evt_1A2DXMIlMPPulN33wOcxU7Lp",
          "object": "event",
          "api_version": None,
          "created": 1490681436,
          "data": {
            "object": {
              "id": "po_1A2E9tIlMPPulN33CWMDQ8m3",
              "object": "transfer",
              "amount": 1100,
              "amount_reversed": 0,
              "application_fee": None,
              "balance_transaction": "txn_1A2E9tIlMPPulN33ZjZ5LuLa",
              "created": 1490683825,
              "currency": "usd",
              "date": 1490683825,
              "description": "Transfer to test@example.com",
              "destination": "ba_1A2E9tIlMPPulN33SMTL48Iv",
              "failure_code": None,
              "failure_message": None,
              "livemode": False,
              "metadata": {
              },
              "method": "standard",
              "recipient": None,
              "reversals": {
                "object": "list",
                "data": [

                ],
                "has_more": False,
                "total_count": 0,
                "url": "/v1/transfers/po_1A2E9tIlMPPulN33CWMDQ8m3/reversals"
              },
              "reversed": False,
              "source_transaction": None,
              "source_type": "card",
              "statement_descriptor": None,
              "status": "in_transit",
              "transfer_group": None,
              "type": "bank_account"
            }
          },
          "livemode": False,
          "pending_webhooks": 0,
          "request": None,
          "type": "charge.succeeded"
        }

    def test_charge_succeeded(self):
        url = reverse('api:v1:stripe-webhook')
        data = self.event
        request = self.client.post(url, data)
        self.assertEqual(request.status_code, status.HTTP_200_OK)

    def test_charge_failed(self):
        trans = TransactionFactory.create(stripe_id=self.event['data']['object']['id'], status=Transaction.STATUS_PENDING)
        self.assertEqual(trans.status, Transaction.STATUS_PENDING)

        url = reverse('api:v1:stripe-webhook')
        data = self.event
        data['type'] = 'charge.failed'
        data['data']['object']['failure_code'] = 1
        data['data']['object']['failure_message'] = 'Some error occurred trying to process charge'
        request = self.client.post(url, data)
        self.assertEqual(request.status_code, status.HTTP_200_OK)
        lookup_trans = Transaction.objects.get(pk=trans.id)
        self.assertEqual(lookup_trans.status, Transaction.STATUS_FAILED)

    def test_charge_pending(self):
        url = reverse('api:v1:stripe-webhook')
        data = self.transfer
        data['type'] = 'transfer.pending'
        request = self.client.post(url, data)
        self.assertEqual(request.status_code, status.HTTP_200_OK)

    def test_transfer_paid(self):
        url = reverse('api:v1:stripe-webhook')
        data = self.event
        data['type'] = 'transfer.paid'
        request = self.client.post(url, data)
        self.assertEqual(request.status_code, status.HTTP_200_OK)

    def test_transfer_failed(self):
        trans = TransactionFactory.create(stripe_id=self.transfer['data']['object']['id'], status=Transaction.STATUS_PENDING)
        self.assertEqual(trans.status, Transaction.STATUS_PENDING)

        url = reverse('api:v1:stripe-webhook')
        data = self.transfer
        data['type'] = 'transfer.failed'
        data['data']['object']['failure_code'] = 1
        data['data']['object']['failure_message'] = 'Some error occurred trying to process transfer'
        request = self.client.post(url, data)
        self.assertEqual(request.status_code, status.HTTP_200_OK)
        lookup_trans = Transaction.objects.get(pk=trans.id)
        self.assertEqual(lookup_trans.status, Transaction.STATUS_FAILED)

    def test_transfer_reversed(self):
        url = reverse('api:v1:stripe-webhook')
        data = self.transfer
        data['type'] = 'transfer.reversed'
        request = self.client.post(url, data)
        self.assertEqual(request.status_code, status.HTTP_200_OK)

    def test_pending_transaction_status_executed_after_charge(self):
        trans = TransactionFactory.create(stripe_id=self.transfer['data']['object']['id'], status=Transaction.STATUS_PENDING)
        self.assertEqual(trans.status, Transaction.STATUS_PENDING)

        url = reverse('api:v1:stripe-webhook')
        data = self.transfer
        request = self.client.post(url, data)
        self.assertEqual(request.status_code, status.HTTP_200_OK)
        lookup_trans = Transaction.objects.get(pk=trans.id)
        self.assertEqual(lookup_trans.status, Transaction.STATUS_EXECUTED)
