# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('portfolios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dividend',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('record_date', models.DateTimeField()),
                ('amount', models.FloatField(help_text='Amount of the dividend in system currency', validators=[django.core.validators.MinValueValidator(0.0)])),
                ('franking', models.FloatField(help_text='Franking percent. 0.01 = 1% of the dividend was franked.', validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)])),
                ('instrument', models.ForeignKey(to='portfolios.Ticker')),
            ],
        ),
        migrations.CreateModel(
            name='ExchangeRate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('first', models.CharField(max_length=3)),
                ('second', models.CharField(max_length=3)),
                ('date', models.DateField()),
                ('rate', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='Performer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('symbol', models.CharField(blank=True, null=True, max_length=20)),
                ('name', models.CharField(max_length=100)),
                ('group', models.CharField(choices=[('PERFORMER_GROUP_STRATEGY', 'PERFORMER_GROUP_STRATEGY'), ('PERFORMER_GROUP_BENCHMARK', 'PERFORMER_GROUP_BENCHMARK'), ('PERFORMER_GROUP_BOND', 'PERFORMER_GROUP_BOND'), ('PERFORMER_GROUP_STOCK', 'PERFORMER_GROUP_STOCK')], max_length=20, default='PERFORMER_GROUP_BENCHMARK')),
                ('allocation', models.FloatField(default=0)),
                ('portfolio_set', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Platform',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('fee', models.PositiveIntegerField(default=0)),
                ('api', models.CharField(choices=[('YAHOO', 'YAHOO'), ('GOOGLE', 'GOOGLE')], max_length=20, default='YAHOO')),
                ('portfolio_set', models.ForeignKey(to='portfolios.PortfolioSet')),
            ],
        ),
        migrations.CreateModel(
            name='SymbolReturnHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('return_number', models.FloatField(default=0)),
                ('symbol', models.CharField(max_length=20)),
                ('date', models.DateField()),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='dividend',
            unique_together=set([('instrument', 'record_date')]),
        ),
        migrations.AlterUniqueTogether(
            name='exchangerate',
            unique_together=set([('first', 'second', 'date')]),
        ),
    ]
