from django.db import models
from .managers import IBAccountFeedManager

class IBAccountFeed(models.Model):
	# Feeds from AXXXXXXX_Account_YYMMDD.csv
	type = models.CharField(max_length=2)
	account_id = models.CharField(max_length=32, unique=True)
	account_title = models.CharField(max_length=255)
	address = models.ForeignKey('address.Address', related_name='+')
	account_type = models.CharField(max_length=255)
	customer_type = models.CharField(max_length=255)
	base_currency = models.CharField(max_length=255)
	master_account_id = models.CharField(max_length=255, blank=True, null=True)
	van = models.CharField(max_length=255, blank=True, null=True)
	capabilities = models.CharField(max_length=255)
	trading_permissions = models.CharField(max_length=255)
	alias = models.CharField(max_length=255, blank=True, null=True)
	primary_email = models.EmailField(max_length=255)
	date_opened = models.DateField(blank=True, null=True)
	date_closed = models.DateField(blank=True, null=True)

	updated_at = models.DateTimeField(auto_now=True)

	objects = IBAccountFeedManager()