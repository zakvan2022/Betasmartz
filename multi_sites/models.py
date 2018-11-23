from django.db import models
from django.contrib.sites.models import Site
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.validators import MinLengthValidator
from common.structures import ChoiceEnum
from .managers import AccountTypeQuerySet
from main import constants


class Config(models.Model):
    """
    Configuration model for django.contrib.sites.models.Site
    """
    site = models.OneToOneField(Site, related_name='site_config')

    logo = models.ImageField(verbose_name="White logo", null=True, blank=True)

    knocked_out_logo = models.ImageField(verbose_name="Colored logo", null=True, blank=True)
    
    ib_enabled = models.BooleanField(default=False, verbose_name='Interactive Brokers Enabled',
                                     help_text='Enables or disables Interactive Brokers feature')

    abridged_onboarding_enabled = models.BooleanField(default=False,
                                                      help_text='Allow Abridged Onboarding section on client invitation page of advisor console.')

    goal_portfolio_name_enabled = models.BooleanField(default=False,
                                                      help_text='Shows or hides Goal Portfolio Name in client console.')

    plaid_enabled = models.BooleanField(default=True, verbose_name='Plaid Account Enabled',
                                        help_text='Enables or disables linking of Plaid Account and showing of account dropdown.')

    ib_acats_enabled = models.BooleanField(default=True, verbose_name='IB ACATS Enabled',
                                           help_text='Enables or disables Interactive Brokers ACATS transfer')

    theme = models.CharField(max_length=255, choices=constants.THEME_CHOICES, default=constants.THEME_BETASMARTZ)

    @property
    def white_logo(self):
        if self.logo is None:
            return static('images/white_logo.png')
        elif not self.logo.name:
            return static('images/white_logo.png')

        return self.logo.url

    @property
    def colored_logo(self):
        if self.knocked_out_logo is None:
            return static('images/colored_logo.png')
        elif not self.knocked_out_logo.name:
            return static('images/colored_logo.png')

        return self.knocked_out_logo.url

    @property
    def safe_theme(self):
        return self.theme or 'betasmartz'

    def __str__(self):
        return "Configuration for {}".format(self.site)


def site_config(self):
    config, created = Config.objects.get_or_create(site=self)
    return config


class FiscalYear(models.Model):
    name = models.CharField(max_length=127)
    year = models.IntegerField()
    begin_date = models.DateField(help_text="Inclusive begin date for this fiscal year")
    end_date = models.DateField(help_text="Inclusive end date for this fiscal year")
    month_ends = models.CommaSeparatedIntegerField(max_length=35,
                                                   validators=[MinLengthValidator(23)],
                                                   help_text="Comma separated month end days each month of the year. First element is January.")

    def __str__(self):
        return "[%s] (%s) %s" % (self.id, self.year, self.name)


class Company(models.Model):
    name = models.CharField(max_length=127)
    fiscal_years = models.ManyToManyField(FiscalYear)

    def __str__(self):
        return "[{}] {}".format(self.id, self.name)


class AccountType(models.Model):
    """
    This model is simply a technique to bring the list of Supported Account Types into the database layer.
    """
    id = models.IntegerField(choices=constants.ACCOUNT_TYPES, primary_key=True)
    objects = AccountTypeQuerySet.as_manager()

    def __str__(self):
        countries = [c for c, tl in constants.ACCOUNT_TYPES_COUNTRY.items()
                     if self.id in tl]
        title = dict(constants.ACCOUNT_TYPES).get(self.id, constants.ACCOUNT_UNKNOWN)
        return "[{}] ({}) {}".format(self.id, '/'.join(countries), title)
