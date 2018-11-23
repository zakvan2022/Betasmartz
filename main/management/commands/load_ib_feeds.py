from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
import ftplib
import fnmatch
from datetime import date, datetime, timedelta
import pytz
from io import BytesIO, StringIO
import csv
from address.utils import get_country_code_from_name
from address.models import Address
from client.models import Client, IBOnboard
from django.conf import settings
from brokers.interactive_brokers.generic_reporting.utils import IB_ADDRESS_FIELD_MAPPING, map_keys_object
from brokers.models import IBAccountFeed

# ftp
FTP_DIR = 'outgoing'

# Update keys of an ojbect to new keys

def process_ib_account_file(ftp, filename):
    bio = BytesIO()
    resp = ftp.retrbinary('RETR {}'.format(filename), bio.write)
    sio = StringIO(bio.getvalue().decode('utf-8'))
    header = sio.readline()
    IBAccountFeed.objects.feed_from_csv(sio.read().splitlines())


def sync_ib_account_feeds(begin_date, end_date):
    ib_account_feeds = IBAccountFeed.objects.filter(updated_at__range=[pytz.utc.localize(datetime.combine(begin_date, datetime.min.time())),
                                                                       pytz.utc.localize(datetime.combine(end_date, datetime.max.time()))])

    for item in ib_account_feeds:
        try:
            ib_onboard = IBOnboard.objects.get(account_number=item.account_id)
            client = ib_onboard.client
        except ObjectDoesNotExist:
            continue

        print('Feeding client {} ...'.format(client.name), end='')
        ib_onboard.feed_ib_client(item)
        print(' Done.')


def load_ib_feeds(begin_date, end_date):
    ftp = ftplib.FTP(settings.IB_FTP_DOMAIN)
    ftp.login(settings.IB_FTP_USERNAME, settings.IB_FTP_PASSWORD)
    ftp.set_pasv(True)
    cur_date = begin_date

    while cur_date <= end_date:
        files = []
        try:
            files = ftp.nlst(FTP_DIR)
        except ftplib.error_perm as resp:
            if str(resp) == "550 No files found":
                print('No files in this directory')
            else:
                raise

        dt = cur_date.strftime('%Y%m%d')
        for f in files:
            if fnmatch.fnmatch(f, '*_Account_{}.csv'.format(dt)):
                print('Loading feeds from {} ...'.format(f), end='')
                process_ib_account_file(ftp, f)
                print(' Done.')

        cur_date += timedelta(days=1)
    sync_ib_account_feeds(begin_date, end_date)


def parse_date(val):
    return datetime.strptime(val, '%Y%m%d').date()


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--begin_date',
            action='store',
            dest='begin_date',
            type=parse_date,
            default=date.today(),
            help='Inclusive start date to load the data for. (YYYYMMDD)',
        )
        parser.add_argument(
            '--end_date',
            action='store',
            dest='end_date',
            default=date.today(),
            help='Inclusive end date to load the data for. (YYYYMMDD)',
        )

    def handle(self, *args, **options):
        load_ib_feeds(options['begin_date'], options['end_date'])
