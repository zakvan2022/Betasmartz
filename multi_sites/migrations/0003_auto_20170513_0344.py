# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('multi_sites', '0002_auto_20170511_2209'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountType',
            fields=[
                ('id', models.IntegerField(serialize=False, choices=[(0, 'Personal Account'), (1, 'Joint Account'), (2, 'Trust Account'), (24, 'Investment Club Account'), (25, 'Partnership/Limited partnership Account'), (26, 'Sole Proprietor Account'), (27, 'Limited Liability Company Account'), (28, 'Association Account'), (29, 'Non-corporate organization Account'), (30, 'Pension Account'), (5, '401K Account'), (38, '401A Account'), (6, 'Roth 401K Account'), (7, 'Individual Retirement Account (IRA)'), (8, 'Roth IRA'), (9, 'SEP IRA'), (10, '403K Account'), (11, 'SIMPLE IRA Account (Savings Incentive Match Plans for Employees)'), (12, 'SARSEP Account (Salary Reduction Simplified Employee Pension)'), (13, 'Payroll Deduction IRA Account'), (14, 'Profit-Sharing Account'), (16, 'Money Purchase Account'), (17, 'Employee Stock Ownership Account (ESOP)'), (18, 'Governmental Account'), (19, '457 Account'), (20, '409A Nonqualified Deferred Compensation Account'), (21, '403B Account'), (31, 'Health Savings Account'), (32, '529 college savings plans Account'), (33, 'Coverdell Educational Savings Account (ESA) Account'), (34, 'UGMA/UTMA Account'), (35, 'Guardianship of the Estate Account'), (36, 'Custodial Account'), (37, 'Thrift Savings Account'), (39, 'Qualified Annuity Plan'), (40, 'Tax Deferred Annuity Plan'), (41, 'Qualified Nonprofit Plan'), (42, 'Qualified Nonprofit Roth Plan'), (43, 'Private 457 Plan'), (44, 'Individual 401k Account'), (45, 'Individual 401k Roth Account'), (46, 'Variable Annuity'), (47, 'Single Life Annuity'), (48, 'Joint & Survivor Annuity')], primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=127)),
            ],
        ),
        migrations.CreateModel(
            name='FiscalYear',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=127)),
                ('year', models.IntegerField()),
                ('begin_date', models.DateField(help_text='Inclusive begin date for this fiscal year')),
                ('end_date', models.DateField(help_text='Inclusive end date for this fiscal year')),
                ('month_ends', models.CommaSeparatedIntegerField(max_length=35, validators=[django.core.validators.MinLengthValidator(23)], help_text='Comma separated month end days each month of the year. First element is January.')),
            ],
        ),
        migrations.AddField(
            model_name='company',
            name='fiscal_years',
            field=models.ManyToManyField(to='multi_sites.FiscalYear'),
        ),
    ]
