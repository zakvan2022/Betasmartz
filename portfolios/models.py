from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.db import models
from django.db.models.deletion import CASCADE, PROTECT
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _
from django_pandas.managers import DataFrameManager
from .abstract import FinancialInstrument
from .returns import get_price_returns, get_portfolio_time_weighted_returns
from common.structures import ChoiceEnum
from common.utils import months_between
from datetime import date, datetime, timedelta
from enum import Enum, unique
from jsonfield.fields import JSONField
from main import constants
from main import redis
from main.finance import mod_dietz_rate
from main.fields import ColorField
from main.tasks import send_portfolio_report_email_to_advisors_task, send_portfolio_report_email_to_clients_task
from scheduler.models import SingleScheduleMixin
import logging

logger = logging.getLogger('portfolios.models')


class InvestmentType(models.Model):
    name = models.CharField(max_length=255,
                            validators=[RegexValidator(
                                regex=r'^[0-9A-Z_]+$',
                                message="Invalid character only accept (0-9a-zA-Z_) ")],
                            unique=True)
    description = models.CharField(max_length=255, blank=True)

    @unique
    class Standard(Enum):
        BONDS = 1
        STOCKS = 2
        MIXED = 3

        def get(self):
            return InvestmentType.objects.get_or_create(name=self.name)[0]

    def __str__(self):
        return self.name


class AssetClass(models.Model):
    name = models.CharField(
        max_length=255,
        validators=[RegexValidator(
            regex=r'^[0-9A-Z_]+$',
            message="Invalid character only accept (0-9a-zA-Z_) ")],
        unique=True)
    display_order = models.PositiveIntegerField(db_index=True)
    primary_color = ColorField()
    foreground_color = ColorField()
    drift_color = ColorField()
    asset_class_explanation = models.TextField(blank=True, null=False,
                                               default='')
    tickers_explanation = models.TextField(blank=True, default='', null=False)
    display_name = models.CharField(max_length=255, blank=False, null=False,
                                    db_index=True)
    investment_type = models.ForeignKey(InvestmentType, related_name='asset_classes')

    # Also has reverse field 'portfolio_sets' from the PortfolioSet model.

    def save(self,
             force_insert=False,
             force_update=False,
             using=None,
             update_fields=None):
        self.name = self.name.upper()

        super(AssetClass, self).save(force_insert, force_update, using,
                                     update_fields)

    @property
    def donut_order(self):
        return 8000 - self.display_order

    def __str__(self):
        return self.name


class MarketIndex(FinancialInstrument):
    """
    For the moment, an index is a concrete FinancialInstrument that may have one or more tickers(funds) that track it.
    """
    trackers = GenericRelation('Ticker',
                               content_type_field='benchmark_content_type',
                               object_id_field='benchmark_object_id')
    daily_prices = GenericRelation('DailyPrice',
                                   content_type_field='instrument_content_type',
                                   object_id_field='instrument_object_id')
    market_caps = GenericRelation('MarketCap',
                                  content_type_field='instrument_content_type',
                                  object_id_field='instrument_object_id')

    def get_returns(self, dates):
        """
        Get the daily returns series for the given index.
        The data should be clean of outliers, but may have gaps.
        :param dates: The pandas index of dates to gather.
        :return: A pandas time-series of the returns
        """
        return get_price_returns(self, dates)


class ExternalInstrument(models.Model):
    class Institution(ChoiceEnum):
        APEX = 0
        INTERACTIVE_BROKERS = 1

    institution = models.IntegerField(choices=Institution.choices(), default=Institution.APEX.value)
    instrument_id = models.CharField(max_length=10, blank=False,null=False)
    ticker = models.ForeignKey('Ticker', related_name='external_instruments', on_delete=PROTECT)

    class Meta:
        unique_together = (('institution', 'instrument_id'), ('institution', 'ticker'))


class Ticker(FinancialInstrument):
    class State(ChoiceEnum):
        INACTIVE = 1, 'Inactive'  # The fund has been removed from our Approved Product List. Only Sells are allowed.
        ACTIVE = 2, 'Active'  # We can buy and sell the fund.
        # The Fund has closed and will never become active again. It is kept for history. Buys and Sells are not allowed
        CLOSED = 3, 'Closed'

    symbol = models.CharField(
        max_length=10,
        blank=False,
        null=False,
        unique=True,
        validators=[RegexValidator(regex=r'^[^ ]+$',
                                   message="Invalid symbol format")])
    ordering = models.IntegerField(db_index=True)
    unit_price = models.FloatField(default=10)
    latest_tick = models.FloatField(default=0)
    asset_class = models.ForeignKey(AssetClass, related_name="tickers")
    ethical = models.BooleanField(default=False,
                                  help_text='Is this an ethical instrument?')
    etf = models.BooleanField(default=True,
                              help_text='Is this an Exchange Traded Fund (True) or Mutual Fund (False)?')
    # A benchmark should be a subclass of financial instrument
    limit = models.Q(app_label='portfolios', model='marketindex')  # Only using index benchmarks at the moment, but may do more later
    benchmark_content_type = models.ForeignKey(ContentType,
                                               on_delete=models.CASCADE,
                                               limit_choices_to=limit,
                                               verbose_name='Benchmark Type')
    benchmark_object_id = models.PositiveIntegerField(null=True,
                                                      verbose_name='Benchmark Instrument')
    benchmark = GenericForeignKey('benchmark_content_type', 'benchmark_object_id')
    manager_benchmark = models.ManyToManyField('MarketIndex',
                                               related_name='manager_tickers',
                                               through='ManagerBenchmarks')
    daily_prices = GenericRelation('DailyPrice',
                                   content_type_field='instrument_content_type',
                                   object_id_field='instrument_object_id')
    state = models.IntegerField(choices=State.choices(),
                                default=State.ACTIVE.value,
                                help_text='The current state of this ticker.')

    # Also may have 'features' property from the AssetFeatureValue model.
    # also has external_instruments foreign key - to get instrument_id per institution

    def update_latest_tick(self, price):
        self.latest_tick = price
        self.save()

    def __str__(self):
        return self.symbol

    @property
    def primary(self):
        return "true" if self.ordering == 0 else "false"

    def shares(self, goal):
        return self.value(goal) / self.unit_price

    @property
    def is_stock(self):
        return self.asset_class.investment_type == InvestmentType.Standard.STOCKS.get()

    @property
    def is_core(self):
        return self.etf

    @property
    def is_satellite(self):
        return not self.is_core

    def value(self, goal):
        total_qty = PositionLot.objects.filter(execution_distribution__transaction__from_goal=goal).\
            aggregate(Sum('quantity'))

        v = total_qty * self.unit_price

        return v

    def get_returns(self, dates):
        """
        Get the daily returns series for the given index.
        The data may have gaps.
        :param dates: The pandas index of dates to gather.
        :return: A pandas time-series of the returns
        """
        return get_price_returns(self, dates)

    def _get_region_feature(self, name):
        region_feature = AssetFeature.Standard.REGION.get_object()
        if name == 'AU':
            return AssetFeatureValue.Standard.REGION_AUSTRALIAN.get_object()
        elif name == 'EU':
            return AssetFeatureValue.objects.get_or_create(name='European', feature=region_feature)[0]
        elif name == 'US':
            return AssetFeatureValue.objects.get_or_create(name='American (US)', feature=region_feature)[0]
        elif name == 'CN':
            return AssetFeatureValue.objects.get_or_create(name='Chinese', feature=region_feature)[0]
        elif name == 'INT':
            return AssetFeatureValue.objects.get_or_create(name='International', feature=region_feature)[0]
        elif name == 'AS':
            return AssetFeatureValue.objects.get_or_create(name='Asian', feature=region_feature)[0]
        elif name == 'JAPAN':
            return AssetFeatureValue.objects.get_or_create(name='Japanese', feature=region_feature)[0]
        elif name == 'UK':
            return AssetFeatureValue.objects.get_or_create(name='UK', feature=region_feature)[0]
        elif name == 'EM':
            return AssetFeatureValue.objects.get_or_create(name='Emerging Markets', feature=region_feature)[0]
        else:
            # tests run random region names, and people may not put one of the standard regions in.
            return AssetFeatureValue.objects.get_or_create(name=name, feature=region_feature)[0]

    def get_region_feature_value(self):
        """
        Returns the AssetFeatureValue for Ticker's Region
        """
        return self._get_region_feature(self.region.name)

    def get_currency_feature_value(self):
        """
        Returns the AssetFeatureValue for Ticker's Currency
        """
        curr_feature = AssetFeature.Standard.CURRENCY.get_object()
        return AssetFeatureValue.objects.get_or_create(name=self.currency, feature=curr_feature)[0]

    def get_asset_class_feature_value(self):
        """
        Returns the AssetFeatureValue for Ticker's Asset Class
        """
        ac_feature = AssetFeature.Standard.ASSET_CLASS.get_object()
        return AssetFeatureValue.objects.get_or_create(name=self.asset_class.display_name, feature=ac_feature)[0]

    def get_asset_type_feature_value(self):
        """
        Returns the AssetFeatureValue for Ticker's Asset Class Investment Type
        """
        if self.asset_class.investment_type == InvestmentType.Standard.STOCKS.value:
            return AssetFeatureValue.Standard.ASSET_TYPE_STOCK.get_object()
        elif self.asset_class.investment_type == InvestmentType.Standard.BONDS.value:
            return AssetFeatureValue.Standard.ASSET_TYPE_BOND.get_object()
        else:
            return AssetFeatureValue.objects.get_or_create(name=self.asset_class.investment_type.name,
                                                           feature=AssetFeature.Standard.ASSET_TYPE.get_object())[0]

    def populate_features(self):
        """
        Has a Ticker populates its own features
        """
        # AssetFeatureValue types
        satellite_feature_value = AssetFeatureValue.Standard.FUND_TYPE_SATELLITE.get_object()
        core_feature_value = AssetFeatureValue.Standard.FUND_TYPE_CORE.get_object()

        logger.info('Populating features for ticker %s' % self)
        r_feat = self.get_region_feature_value()
        ac_feat = self.get_asset_class_feature_value()
        curr_feat = self.get_currency_feature_value()
        at_feat = self.get_asset_type_feature_value()
        self.features.clear()
        self.features.add(r_feat, ac_feat, curr_feat, at_feat)
        if self.ethical:
            self.features.add(AssetFeatureValue.Standard.SRI_OTHER.get_object())
        self.features.add(core_feature_value if self.etf else satellite_feature_value)

    def save(self,
             force_insert=False,
             force_update=False,
             using=None,
             update_fields=None):
        self.symbol = self.symbol.upper()
        super(Ticker, self).save(force_insert, force_update, using, update_fields)


@receiver(post_save, sender=Ticker)
def populate_ticker_features(sender, instance, created, **kwargs):
    instance.populate_features()


class DailyPrice(models.Model):
    """
    If a Financial Instrument is tradable, it will have a price.
    """
    objects = DataFrameManager()

    class Meta:
        unique_together = ("instrument_content_type", "instrument_object_id", "date")

    # An instrument should be a subclass of financial instrument
    instrument_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, db_index=True)
    instrument_object_id = models.PositiveIntegerField(db_index=True)
    instrument = GenericForeignKey('instrument_content_type', 'instrument_object_id')
    date = models.DateField(db_index=True)
    price = models.FloatField(null=True)

    def __str__(self):
        return "{} {} {}".format(self.instrument, self.date, self.price)


class MarketCap(models.Model):
    """
    If a Financial Instrument is tradable, it will have a
    market capitalisation. This may not change often.
    """
    objects = DataFrameManager()

    class Meta:
        unique_together = ("instrument_content_type", "instrument_object_id", "date")

    # An instrument should be a subclass of financial instrument
    instrument_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    instrument_object_id = models.PositiveIntegerField()
    instrument = GenericForeignKey('instrument_content_type', 'instrument_object_id')
    date = models.DateField()
    value = models.FloatField()


class Region(models.Model):
    name = models.CharField(max_length=127, blank=False, null=False, help_text='Name of the region')
    description = models.TextField(blank=True, default="", null=False)

    def __str__(self):
        return self.name


class ManagerBenchmarks(models.Model):
    ticker = models.ForeignKey('Ticker')
    market_index = models.ForeignKey('MarketIndex')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = 'ticker', 'market_index'


class ProxyAssetClass(AssetClass):
    class Meta:
        proxy = True
        verbose_name_plural = "Asset classes"
        verbose_name = "Asset class"


class ProxyTicker(Ticker):
    class Meta:
        proxy = True
        verbose_name_plural = "Tickers"
        verbose_name = "Ticker"


class AssetFeature(models.Model):
    @unique
    class Standard(Enum):
        SRI = 0
        ASSET_TYPE = 1
        FUND_TYPE = 2
        REGION = 3
        ASSET_CLASS = 4
        CURRENCY = 5
        # TODO: Add the rest

        def get_object(self):
            names = {
                # feature_tag: feature_name
                self.SRI: 'Social Responsibility',
                self.ASSET_TYPE: 'Asset Type',
                self.FUND_TYPE: 'Fund Type',
                self.REGION: 'Region',
                self.ASSET_CLASS: 'Asset Class',
                self.CURRENCY: 'Currency',
                # TODO: Add the rest
            }
            return AssetFeature.objects.get_or_create(name=names[self])[0]

    name = models.CharField(max_length=127, unique=True, help_text="This should be a noun such as 'Region'.")
    description = models.TextField(blank=True, null=True)
    upper_limit = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])

    @cached_property
    def active(self):
        return AssetFeatureValue.objects.filter(feature=self, assets__state=Ticker.State.ACTIVE.value).exists()

    def __str__(self):
        return "[{}] {}".format(self.id, self.name)


class AssetFeatureValue(models.Model):
    @unique
    class Standard(Enum):
        SRI_OTHER = 0
        ASSET_TYPE_STOCK = 1
        ASSET_TYPE_BOND = 2
        FUND_TYPE_CORE = 3
        FUND_TYPE_SATELLITE = 4
        REGION_AUSTRALIAN = 5
        # TODO: Add the rest

        def get_object(self):
            data = {
                # feature_value_tag: (feature_tag, feature_value_name)
                self.SRI_OTHER: (AssetFeature.Standard.SRI, 'Socially Responsible Investments'),
                self.ASSET_TYPE_STOCK: (AssetFeature.Standard.ASSET_TYPE, 'Stocks only'),
                self.ASSET_TYPE_BOND: (AssetFeature.Standard.ASSET_TYPE, 'Bonds only'),
                self.FUND_TYPE_CORE: (AssetFeature.Standard.FUND_TYPE, 'Core (ETFs)'),
                self.FUND_TYPE_SATELLITE: (AssetFeature.Standard.FUND_TYPE, 'Satellite (Actively Managed)'),
                self.REGION_AUSTRALIAN: (AssetFeature.Standard.REGION, 'Australian'),
            }
            return AssetFeatureValue.objects.get_or_create(name=data[self][1],
                                                           defaults={'feature': data[self][0].get_object()})[0]

    class Meta:
        unique_together = ('name', 'feature')

    name = models.CharField(max_length=127, help_text="This should be an adjective.")
    description = models.TextField(blank=True, null=True, help_text="A clarification of what this value means.")
    feature = models.ForeignKey(AssetFeature,
                                related_name='values',
                                on_delete=PROTECT,
                                help_text="The asset feature this is one value for.")
    assets = models.ManyToManyField(Ticker, related_name='features')

    @cached_property
    def active(self):
        return self.assets.filter(state=Ticker.State.ACTIVE.value).exists()

    def __str__(self):
        return "[{}] {}".format(self.id, self.name)


class MarkowitzScale(models.Model):
    """
    We convert the max and min Markowitz to an exponential function in the form a * b^x + c passing through the points:
    [(-50, min), (0, 1.2), (50, max)]
    So the risk slider is exponential.
    """
    date = models.DateField(unique=True)
    min = models.FloatField()
    max = models.FloatField()
    a = models.FloatField(null=True)
    b = models.FloatField(null=True)
    c = models.FloatField(null=True)


class InvestmentCycleObservation(models.Model):
    class Cycle(ChoiceEnum):
        EQ = (0, 'eq')
        EQ_PK = (1, 'eq_pk')
        PK_EQ = (2, 'pk_eq')
        EQ_PIT = (3, 'eq_pit')
        PIT_EQ = (4, 'pit_eq')
    as_of = models.DateField()
    recorded = models.DateField()
    cycle = models.IntegerField(choices=Cycle.choices())
    source = JSONField()

    def __str__(self):
        return "%s as of %s recorded %s" % (self.cycle, self.as_of, self.recorded)


class InvestmentCyclePrediction(models.Model):
    as_of = models.DateField()
    pred_dt = models.DateField()
    eq = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    eq_pk = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    pk_eq = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    eq_pit = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    pit_eq = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    source = JSONField()

    def __str__(self):
        return "Prediction for %s as of %s" % (self.pred_dt, self.as_of)


class Inflation(models.Model):
    year = models.PositiveIntegerField(help_text="The year the inflation value is for. "
                                                 "If after recorded, it is a forecast, otherwise it's an observation.")
    month = models.PositiveIntegerField(help_text="The month the inflation value is for. "
                                                  "If after recorded, it is a forecast, otherwise it's an observation.")
    value = models.FloatField(help_text="This is the monthly inflation figure as of the given as_of date.")
    recorded = models.DateField(auto_now=True, help_text="The date this inflation figure was added.")

    class Meta:
        ordering = ['year', 'month']
        unique_together = ('year', 'month')

    @classmethod
    def cumulative(cls):
        """
        :return: A dictionary from (year, month) => cumulative total inflation (1-based) from beginning of records till that time
        """
        data = getattr(cls, '_cum_data', None)
        if not data:
            data = cache.get(redis.Keys.INFLATION)
        if not data:
            data = {}
            vals = list(cls.objects.all().values_list('year', 'month', 'value'))
            if vals:
                f_d = date(vals[0][0], vals[0][1], 1)
                l_d = date(vals[-1][0], vals[-1][1], 1)
                if (months_between(f_d, l_d) + 1) > len(vals):
                    raise Exception("Holes exist in the inflation forecast figures, cannot proceed.")
                isum = 1
                # Add the entry for the start of the series.
                data[((f_d - timedelta(days=1)).month, (f_d - timedelta(days=1)).year)] = isum
                for val in vals:
                    isum *= 1 + val[2]
                    data[(val[0], val[1])] = isum
                cache.set(redis.Keys.INFLATION, data, timeout=60 * 60 * 24)
        cls._cum_data = data
        return data

    @classmethod
    def between(cls, begin_date: datetime.date, end_date: datetime.date) -> float:
        """
        Calculates inflation between two dates. (predicted if in future, actual for all past dates)
        :param start: The start date from when to calculate the inflation
        :param start: The date until when to calculate the inflation
        :return: float value for the inflation. 0.05 = 5% inflation
        """

        if begin_date > end_date:
            raise ValueError('End date must not be before begin date.')
        if begin_date == end_date:
            return 0
        data = cls.cumulative()
        first = data.get((begin_date.year, begin_date.month), None)
        last = data.get((end_date.year, end_date.month), None)
        if first is None or last is None:
            raise ValidationError("Inflation figures don't cover entire period requested: {} - {}".format(begin_date,
                                                                                                          end_date))
        return (last / first) - 1

    def __str__(self):
        return '{0.month}/{0.year}: {0.value}'.format(self)


class Dividend(models.Model):
    class Meta:
        unique_together = ("instrument", "record_date")

    instrument = models.ForeignKey('portfolios.Ticker')
    record_date = models.DateTimeField()
    amount = models.FloatField(validators=[MinValueValidator(0.0)],
                               help_text="Amount of the dividend in system currency")
    franking = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
                                 help_text="Franking percent. 0.01 = 1% of the dividend was franked.")


class PortfolioProvider(models.Model):
    name = models.CharField(max_length=100)
    type = models.IntegerField(choices=constants.PORTFOLIO_PROVIDER_TYPE_CHOICES,
                               unique=False)
    TLH = models.BooleanField(default=True)
    portfolio_optimization = models.BooleanField(default=True)
    constraints = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class DefaultPortfolioProvider(models.Model):
    default_provider = models.OneToOneField('PortfolioProvider', null=True, blank=True)
    changed = models.DateTimeField(auto_now_add=True)


def get_default_provider():
    default_providers = DefaultPortfolioProvider.objects.all()
    if default_providers.count() > 0:
        default = default_providers.latest('changed')
    else:
        krane = PortfolioProvider.objects.get_or_create(name='Krane',
                                                             type=constants.PORTFOLIO_PROVIDER_TYPE_KRANE)[0]
        default = DefaultPortfolioProvider.objects.get_or_create(default_provider=krane)[0]
    return default.default_provider

def get_default_provider_id():
    return get_default_provider().id


class PortfolioSet(models.Model):
    name = models.CharField(max_length=100, unique=True)
    asset_classes = models.ManyToManyField(AssetClass, related_name='portfolio_sets')
    portfolio_provider = models.ForeignKey(PortfolioProvider, related_name='portfolio_sets')
    risk_free_rate = models.FloatField(default=0.0)

    def get_views_all(self):
        return self.views.all()

    @property
    def total_balance(self):
        """
        This means total assets under management (AUM)
        :return:
        """
        from client.models import ClientAccount

        accounts = ClientAccount.objects.filter(default_portfolio_set=self)

        return sum(acc.total_balance for acc in accounts)

    def fees_ytd(self, firm):
        """
        """
        # get client accounts
        # check transactions for client accounts from current fiscal year
        # firm has fiscal years set, find current
        from client.models import ClientAccount

        fiscal_year = firm.get_current_fiscal_year()
        total_fees = 0.0
        if fiscal_year:
            for ca in ClientAccount.objects.filter(default_portfolio_set=self):
                for goal in ca.goals:
                    txs = Transaction.objects.filter(Q(to_goal=goal) | Q(from_goal=goal),
                                                     status=Transaction.STATUS_EXECUTED,
                                                     reason=Transaction.REASON_FEE,
                                                     executed__gte=fiscal_year.begin_date,
                                                     executed__lte=datetime.today())
                    for tx in txs:
                        total_fees += tx.amount
        return total_fees


    @property
    def average_return(self):
        from goal.models import Goal
        goals = Goal.objects.filter(account__default_portfolio_set=self)
        return mod_dietz_rate(goals)

    @property
    def clients(self):
        from client.models import Client, ClientAccount
        return Client.objects.filter(primary_accounts__default_portfolio_set=self)

    def __str__(self):
        return '{} - {}'.format(self.portfolio_provider, self.name)


class DefaultPortfolioSet(models.Model):
    default_set = models.OneToOneField('PortfolioSet', null=True, blank=True)
    changed = models.DateTimeField(auto_now_add=True)


def get_default_set():
    default_sets = DefaultPortfolioSet.objects.all()
    if default_sets.count() > 0:
        default = default_sets.latest('changed')
    else:
        krane = PortfolioSet.objects.get_or_create(name='Krane',
                                                        portfolio_provider=get_default_provider(),
                                                        risk_free_rate=0.0)[0]
        default = DefaultPortfolioSet.objects.get_or_create(default_set=krane)[0]
    return default.default_set

def get_default_set_id():
    return get_default_set().id


class View(models.Model):
    q = models.FloatField()
    assets = models.TextField()
    portfolio_set = models.ForeignKey(PortfolioSet, related_name="views")


class Platform(models.Model):
    fee = models.PositiveIntegerField(default=0)
    portfolio_set = models.ForeignKey(PortfolioSet)
    api = models.CharField(max_length=20,
                           default=constants.YAHOO_API,
                           choices=constants.API_CHOICES)

    def __str__(self):
        return "BetaSmartz"


class Performer(models.Model):
    symbol = models.CharField(max_length=20, null=True, blank=True)
    name = models.CharField(max_length=100)
    group = models.CharField(max_length=20,
                             choices=constants.PERFORMER_GROUP_CHOICE,
                             default=constants.PERFORMER_GROUP_BENCHMARK)
    allocation = models.FloatField(default=0)
    #portfolio_set = models.ForeignKey(PortfolioSet)
    portfolio_set = models.IntegerField()


class SymbolReturnHistory(models.Model):
    return_number = models.FloatField(default=0)
    symbol = models.CharField(max_length=20)
    date = models.DateField()


class ExchangeRate(models.Model):
    """
    Describes the rate from the first to the second currency
    """

    class Meta:
        unique_together = ("first", "second", "date")

    first = models.CharField(max_length=3)
    second = models.CharField(max_length=3)
    date = models.DateField()
    rate = models.FloatField()


class LivePortfolio(models.Model, SingleScheduleMixin):
    name = models.CharField(max_length=255)
    firm = models.ForeignKey('firm.Firm', related_name='live_portfolios', on_delete=CASCADE)
    clients = models.ManyToManyField('client.Client', related_name='live_portfolios')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Also has 'items' field from PortfolioItem
    # Also has 'clients' field from client.Client

    def __str__(self):
        result = u'Live Portfolio #{}: {}'.format(self.id, self.name)
        return result

    def get_items_all(self):
        return self.items.all()

    @property
    def total_balance(self):
        """
        This means total assets under management (AUM)
        :return:
        """
        from client.models import ClientAccount

        accounts = ClientAccount.objects.filter(primary_owner__in=self.clients.all())

        return sum(acc.total_balance for acc in accounts)

    @cached_property
    def asset_classes(self):
        return AssetClass.objects.filter(pk__in=self.items.values_list('asset__asset_class', flat=True))

    def fees_ytd(self, firm):
        """
        """
        # get client accounts
        # check transactions for client accounts from current fiscal year
        # firm has fiscal years set, find current
        from client.models import ClientAccount

        fiscal_year = firm.get_current_fiscal_year()
        total_fees = 0.0
        if fiscal_year:
            for ca in ClientAccount.objects.filter(primary_owner__in=self.clients.all()):
                for goal in ca.goals:
                    txs = Transaction.objects.filter(Q(to_goal=goal) | Q(from_goal=goal),
                                                     status=Transaction.STATUS_EXECUTED,
                                                     reason=Transaction.REASON_FEE,
                                                     executed__gte=fiscal_year.begin_date,
                                                     executed__lte=datetime.today())
                    for tx in txs:
                        total_fees += tx.amount
        return total_fees


    @property
    def average_return(self):
        from goal.models import Goal
        goals = Goal.objects.filter(account__primary_owner__in=self.clients.all())
        return mod_dietz_rate(goals)

    @cached_property
    def advisors(self):
        from advisor.models import Advisor
        return Advisor.objects.filter(pk__in=self.clients.values_list('advisor', flat=True).distinct())

    def send_portfolio_report_email_to_advisors(self):
        try:
            send_portfolio_report_email_to_advisors_task.delay(self.id)
        except:
            self._send_portfolio_report_email_to_advisors(self.id)

    def get_time_weighted_returns(self):
        return get_portfolio_time_weighted_returns(self, self.created_at, date.today())

    @staticmethod
    def _send_portfolio_report_email_to_advisors(liveportfolio_id):
        from portfolios.models import LivePortfolio

        liveportfolio = LivePortfolio.objects.get(id=liveportfolio_id)
        for advisor in liveportfolio.advisors:
            liveportfolio._send_portfolio_report_email_to_advisor(advisor)

    def _send_portfolio_report_email_to_advisor(self, advisor):
        context = {
            'advisor': advisor,
            'liveportfolio' : self,
            'liveportfolio_report': self.get_report(),
            'site': Site.objects.get_current()
        }

        subject = "Portfolio Report"
        html_content = render_to_string('email/firm_portfolio/portfolio_report_advisor.html', context)
        email = EmailMessage(subject, html_content, None, [advisor.user.email])
        email.content_subtype = "html"
        email.send()

    def send_portfolio_report_email_to_clients(self):
        try:
            send_portfolio_report_email_to_clients_task.delay(self.id)
        except:
            self._send_portfolio_report_email_to_clients(self.id)

    @staticmethod
    def _send_portfolio_report_email_to_clients(liveportfolio_id):
        from portfolios.models import LivePortfolio
        from client.models import Client

        liveportfolio = LivePortfolio.objects.get(id=liveportfolio_id)
        # Send to clients
        for client in liveportfolio.clients.all():
            liveportfolio._send_portfolio_report_email_to_client(client)

    def _send_portfolio_report_email_to_client(self, client):
        context = {
            'client': client,
            'liveportfolio' : self,
            'liveportfolio_report': self.get_report(),
            'site': Site.objects.get_current()
        }

        subject = "Portfolio Report"
        html_content = render_to_string('email/firm_portfolio/portfolio_report_client.html', context)
        email = EmailMessage(subject, html_content, None, [client.user.email])
        email.content_subtype = "html"
        email.send()

    def get_report(self):
        from statements.models import LivePortfolioReport
        lpr = self.reports.filter(create_date__gte=datetime.now() - timedelta(minutes=5)).order_by('-create_date').first()
        if lpr is None:
            lpr = LivePortfolioReport(live_portfolio=self)
            lpr.save()
        return lpr


class LivePortfolioItem(models.Model):
    portfolio = models.ForeignKey(LivePortfolio, related_name='items', on_delete=CASCADE)
    asset = models.ForeignKey(Ticker, on_delete=PROTECT)
    weight = models.FloatField()


class Commentary(models.Model):
    portfolio = models.ForeignKey(LivePortfolio, related_name='commentaries', on_delete=CASCADE, null=True, blank=True)
    category = models.IntegerField(choices=constants.COMMENTARY_CATEGORY_CHOICES, default=constants.COMMENTARY_PORTFOLIO_INFO)
    key_commentary = models.TextField(blank=False, null=False)
    near_term_outlook = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    publish_at = models.DateTimeField()

    class Meta:
        ordering = ['-publish_at',]
        verbose_name = _('commentary')
        verbose_name_plural = _('commentaries')
