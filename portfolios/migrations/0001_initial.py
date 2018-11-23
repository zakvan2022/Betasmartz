# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import jsonfield.fields
import main.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssetClass',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(unique=True, max_length=255, validators=[django.core.validators.RegexValidator(regex='^[0-9A-Z_]+$', message='Invalid character only accept (0-9a-zA-Z_) ')])),
                ('display_order', models.PositiveIntegerField(db_index=True)),
                ('primary_color', main.fields.ColorField(max_length=10)),
                ('foreground_color', main.fields.ColorField(max_length=10)),
                ('drift_color', main.fields.ColorField(max_length=10)),
                ('asset_class_explanation', models.TextField(blank=True, default='')),
                ('tickers_explanation', models.TextField(blank=True, default='')),
                ('display_name', models.CharField(max_length=255, db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name='AssetFeature',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(unique=True, help_text="This should be a noun such as 'Region'.", max_length=127)),
                ('description', models.TextField(blank=True, null=True)),
                ('upper_limit', models.FloatField(blank=True, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)], null=True)),
            ],
        ),
        migrations.CreateModel(
            name='AssetFeatureValue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=127, help_text='This should be an adjective.')),
                ('description', models.TextField(blank=True, help_text='A clarification of what this value means.', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='DailyPrice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('instrument_object_id', models.PositiveIntegerField(db_index=True)),
                ('date', models.DateField(db_index=True)),
                ('price', models.FloatField(null=True)),
                ('instrument_content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
        ),
        migrations.CreateModel(
            name='DefaultPortfolioProvider',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('changed', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='DefaultPortfolioSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('changed', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='ExternalInstrument',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('institution', models.IntegerField(choices=[(0, 'APEX'), (1, 'INTERACTIVE_BROKERS')], default=0)),
                ('instrument_id', models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='Inflation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('year', models.PositiveIntegerField(help_text="The year the inflation value is for. If after recorded, it is a forecast, otherwise it's an observation.")),
                ('month', models.PositiveIntegerField(help_text="The month the inflation value is for. If after recorded, it is a forecast, otherwise it's an observation.")),
                ('value', models.FloatField(help_text='This is the monthly inflation figure as of the given as_of date.')),
                ('recorded', models.DateField(help_text='The date this inflation figure was added.', auto_now=True)),
            ],
            options={
                'ordering': ['year', 'month'],
            },
        ),
        migrations.CreateModel(
            name='InvestmentCycleObservation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('as_of', models.DateField()),
                ('recorded', models.DateField()),
                ('cycle', models.IntegerField(choices=[(0, 'eq'), (1, 'eq_pk'), (2, 'pk_eq'), (3, 'eq_pit'), (4, 'pit_eq')])),
                ('source', jsonfield.fields.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='InvestmentCyclePrediction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('as_of', models.DateField()),
                ('pred_dt', models.DateField()),
                ('eq', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)])),
                ('eq_pk', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)])),
                ('pk_eq', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)])),
                ('eq_pit', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)])),
                ('pit_eq', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)])),
                ('source', jsonfield.fields.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='InvestmentType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(unique=True, max_length=255, validators=[django.core.validators.RegexValidator(regex='^[0-9A-Z_]+$', message='Invalid character only accept (0-9a-zA-Z_) ')])),
                ('description', models.CharField(blank=True, max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='ManagerBenchmarks',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='MarketCap',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('instrument_object_id', models.PositiveIntegerField()),
                ('date', models.DateField()),
                ('value', models.FloatField()),
                ('instrument_content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
        ),
        migrations.CreateModel(
            name='MarketIndex',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('display_name', models.CharField(max_length=255, db_index=True)),
                ('description', models.TextField(blank=True, default='')),
                ('url', models.URLField()),
                ('currency', models.CharField(max_length=10, default='AUD')),
                ('data_api', models.CharField(max_length=30, help_text='The module that will be used to get the data for this ticker', choices=[('portfolios.api.bloomberg', 'Bloomberg')])),
                ('data_api_param', models.CharField(unique=True, help_text='Structured parameter string appropriate for the data api. The first component would probably be id appropriate for the given api', max_length=30)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MarkowitzScale',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('date', models.DateField(unique=True)),
                ('min', models.FloatField()),
                ('max', models.FloatField()),
                ('a', models.FloatField(null=True)),
                ('b', models.FloatField(null=True)),
                ('c', models.FloatField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PortfolioProvider',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=100)),
                ('type', models.IntegerField(choices=[(0, 'BetaSmartz'), (1, 'Aon'), (2, 'Krane'), (3, 'Lee')], default=2)),
                ('TLH', models.BooleanField(default=True)),
                ('portfolio_optimization', models.BooleanField(default=True)),
                ('constraints', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='PortfolioSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('risk_free_rate', models.FloatField(default=0.0)),
                ('asset_classes', models.ManyToManyField(related_name='portfolio_sets', to='portfolios.AssetClass')),
                ('portfolio_provider', models.ForeignKey(to='portfolios.PortfolioProvider', related_name='portfolio_sets')),
            ],
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('name', models.CharField(max_length=127, help_text='Name of the region')),
                ('description', models.TextField(blank=True, default='')),
            ],
        ),
        migrations.CreateModel(
            name='Ticker',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('display_name', models.CharField(max_length=255, db_index=True)),
                ('description', models.TextField(blank=True, default='')),
                ('url', models.URLField()),
                ('currency', models.CharField(max_length=10, default='AUD')),
                ('data_api', models.CharField(max_length=30, help_text='The module that will be used to get the data for this ticker', choices=[('portfolios.api.bloomberg', 'Bloomberg')])),
                ('data_api_param', models.CharField(unique=True, help_text='Structured parameter string appropriate for the data api. The first component would probably be id appropriate for the given api', max_length=30)),
                ('symbol', models.CharField(unique=True, max_length=10, validators=[django.core.validators.RegexValidator(regex='^[^ ]+$', message='Invalid symbol format')])),
                ('ordering', models.IntegerField(db_index=True)),
                ('unit_price', models.FloatField(default=10)),
                ('latest_tick', models.FloatField(default=0)),
                ('ethical', models.BooleanField(help_text='Is this an ethical instrument?', default=False)),
                ('etf', models.BooleanField(help_text='Is this an Exchange Traded Fund (True) or Mutual Fund (False)?', default=True)),
                ('benchmark_object_id', models.PositiveIntegerField(null=True, verbose_name='Benchmark Instrument')),
                ('state', models.IntegerField(help_text='The current state of this ticker.', choices=[(1, 'Inactive'), (2, 'Active'), (3, 'Closed')], default=2)),
                ('asset_class', models.ForeignKey(to='portfolios.AssetClass', related_name='tickers')),
                ('benchmark_content_type', models.ForeignKey(verbose_name='Benchmark Type', to='contenttypes.ContentType')),
                ('manager_benchmark', models.ManyToManyField(through='portfolios.ManagerBenchmarks', related_name='manager_tickers', to='portfolios.MarketIndex')),
                ('region', models.ForeignKey(to='portfolios.Region')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='View',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('q', models.FloatField()),
                ('assets', models.TextField()),
                ('portfolio_set', models.ForeignKey(to='portfolios.PortfolioSet', related_name='views')),
            ],
        ),
        migrations.AddField(
            model_name='marketindex',
            name='region',
            field=models.ForeignKey(to='portfolios.Region'),
        ),
        migrations.AddField(
            model_name='managerbenchmarks',
            name='market_index',
            field=models.ForeignKey(to='portfolios.MarketIndex'),
        ),
        migrations.AddField(
            model_name='managerbenchmarks',
            name='ticker',
            field=models.ForeignKey(to='portfolios.Ticker'),
        ),
        migrations.AlterUniqueTogether(
            name='inflation',
            unique_together=set([('year', 'month')]),
        ),
        migrations.AddField(
            model_name='externalinstrument',
            name='ticker',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='external_instruments', to='portfolios.Ticker'),
        ),
        migrations.AddField(
            model_name='defaultportfolioset',
            name='default_set',
            field=models.OneToOneField(blank=True, null=True, to='portfolios.PortfolioSet'),
        ),
        migrations.AddField(
            model_name='defaultportfolioprovider',
            name='default_provider',
            field=models.OneToOneField(blank=True, null=True, to='portfolios.PortfolioProvider'),
        ),
        migrations.AddField(
            model_name='assetfeaturevalue',
            name='assets',
            field=models.ManyToManyField(related_name='features', to='portfolios.Ticker'),
        ),
        migrations.AddField(
            model_name='assetfeaturevalue',
            name='feature',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='values', to='portfolios.AssetFeature', help_text='The asset feature this is one value for.'),
        ),
        migrations.AddField(
            model_name='assetclass',
            name='investment_type',
            field=models.ForeignKey(to='portfolios.InvestmentType', related_name='asset_classes'),
        ),
        migrations.CreateModel(
            name='ProxyAssetClass',
            fields=[
            ],
            options={
                'verbose_name': 'Asset class',
                'verbose_name_plural': 'Asset classes',
                'proxy': True,
            },
            bases=('portfolios.assetclass',),
        ),
        migrations.CreateModel(
            name='ProxyTicker',
            fields=[
            ],
            options={
                'verbose_name': 'Ticker',
                'verbose_name_plural': 'Tickers',
                'proxy': True,
            },
            bases=('portfolios.ticker',),
        ),
        migrations.AlterUniqueTogether(
            name='marketcap',
            unique_together=set([('instrument_content_type', 'instrument_object_id', 'date')]),
        ),
        migrations.AlterUniqueTogether(
            name='managerbenchmarks',
            unique_together=set([('ticker', 'market_index')]),
        ),
        migrations.AlterUniqueTogether(
            name='externalinstrument',
            unique_together=set([('institution', 'instrument_id'), ('institution', 'ticker')]),
        ),
        migrations.AlterUniqueTogether(
            name='dailyprice',
            unique_together=set([('instrument_content_type', 'instrument_object_id', 'date')]),
        ),
        migrations.AlterUniqueTogether(
            name='assetfeaturevalue',
            unique_together=set([('name', 'feature')]),
        ),
    ]
