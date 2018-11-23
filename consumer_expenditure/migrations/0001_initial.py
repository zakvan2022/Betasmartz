# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AreaQuotient',
            fields=[
                ('id', models.IntegerField(primary_key=True, help_text='Expense Category', choices=[(1, 'Alcoholic Beverage'), (2, 'Apparel & Services'), (3, 'Education'), (4, 'Entertainment'), (5, 'Food'), (6, 'Healthcare'), (7, 'Housing'), (8, 'Insuarance, Pensions & Social Security'), (9, 'Personal Care'), (10, 'Reading'), (11, 'Savings'), (12, 'Taxes'), (13, 'Tobacco'), (14, 'Transportation'), (15, 'Miscellaneous')], serialize=False)),
                ('quot_city', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)], help_text='Quotient for City')),
                ('quot_suburb', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)], help_text='Quotient for Suburb')),
                ('quot_rural', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)], help_text='Quotient for Rural area')),
            ],
        ),
        migrations.CreateModel(
            name='PeerGroupData',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('age_group', models.IntegerField(help_text='Age Group', choices=[(0, 'Under 25'), (1, '25 - 34'), (2, '35 - 44'), (3, '45 - 54'), (4, '55 - 64'), (5, '65 +')])),
                ('pc_1', models.FloatField(validators=[django.core.validators.MinValueValidator(-1.0), django.core.validators.MaxValueValidator(1.0)], help_text='Rate value (0 - 1) for income $0 - $19,999')),
                ('pc_2', models.FloatField(validators=[django.core.validators.MinValueValidator(-1.0), django.core.validators.MaxValueValidator(1.0)], help_text='Rate value (0 - 1) for income $20,000 - $29,999')),
                ('pc_3', models.FloatField(validators=[django.core.validators.MinValueValidator(-1.0), django.core.validators.MaxValueValidator(1.0)], help_text='Rate value (0 - 1) for income $30,000 - $39,999')),
                ('pc_4', models.FloatField(validators=[django.core.validators.MinValueValidator(-1.0), django.core.validators.MaxValueValidator(1.0)], help_text='Rate value (0 - 1) for income $40,000 - $49,999')),
                ('pc_5', models.FloatField(validators=[django.core.validators.MinValueValidator(-1.0), django.core.validators.MaxValueValidator(1.0)], help_text='Rate value (0 - 1) for income $50,000 - $69,999')),
                ('pc_7', models.FloatField(validators=[django.core.validators.MinValueValidator(-1.0), django.core.validators.MaxValueValidator(1.0)], help_text='Rate value (0 - 1) for income $70,000 +')),
                ('northeast', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)], help_text='Northeast')),
                ('midwest', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)], help_text='Midwest')),
                ('south', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)], help_text='South')),
                ('west', models.FloatField(validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)], help_text='West')),
                ('expense_cat', models.ForeignKey(help_text='Expense Category', to='consumer_expenditure.AreaQuotient')),
            ],
        ),
    ]
