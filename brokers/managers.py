import csv
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from datetime import datetime
from address.models import Address
from address.utils import get_country_code_from_name
from .interactive_brokers.generic_reporting.utils import IB_ACCOUNT_FEEDS_MAPPING, \
    IB_ADDRESS_FIELD_MAPPING, map_keys_object

class IBAccountFeedManager(models.Manager):
    def feed_from_csv(self, csv_file):
        csv_reader = csv.DictReader(csv_file, delimiter=',')
        for csv_row in csv_reader:
            feed_fields = map_keys_object(IB_ACCOUNT_FEEDS_MAPPING, csv_row)
            # account_id is unique field, it should always return a single row.
            ib_account_feeds = self.filter(account_id=feed_fields['account_id'])

            if feed_fields['type'] != 'D':
                continue
            try:
                feed_fields['date_opened'] = datetime.strptime(feed_fields['date_opened'], '%Y%m%d')
            except ValueError:
                feed_fields['date_opened'] = None
            try:
                feed_fields['date_closed'] = datetime.strptime(feed_fields['date_closed'], '%Y%m%d')
            except ValueError:
                feed_fields['date_closed'] = None
            
            address_fields = map_keys_object(IB_ADDRESS_FIELD_MAPPING, csv_row)
            address_fields['country'] = get_country_code_from_name(address_fields['country'])
            address = ib_account_feeds[0].address if ib_account_feeds.count() > 0 else Address()
            address.update_address(**address_fields)
            feed_fields['address'] = address

            if ib_account_feeds.count() > 0:
                ib_account_feeds.update(**feed_fields)
            else:
                self.create(**feed_fields)
