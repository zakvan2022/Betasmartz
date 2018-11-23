from django.test import TestCase

from api.v1.tests.factories import ExecutionRequestFactory, MarketOrderRequestFactory, \
    ClientAccountFactory, GoalFactory, TickerFactory
from execution.end_of_day import *
from portfolios.models import DailyPrice, Ticker
from main.management.commands.populate_test_data import populate_prices
from django.contrib.contenttypes.models import ContentType


class BaseTest(TestCase):
    def setUp(self):
        pass

    def test_ticker_price(self):
        ticker = TickerFactory.create()
        populate_prices(days=500)
        price = ticker.unit_price
        self.assertTrue(price == 10)
        price_object = DailyPrice.objects\
            .filter(instrument_object_id=ticker.id,
                    instrument_content_type=ContentType.objects.get_for_model(ticker))\
            .order_by('-date')\
            .first()

        ticker.update_latest_tick(price_object.price)
        ticker = Ticker.objects.get(id=ticker.id)
        self.assertTrue(ticker.latest_tick == price_object.price)