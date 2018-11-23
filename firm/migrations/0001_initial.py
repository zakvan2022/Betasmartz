# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import phonenumber_field.modelfields
import jsonfield.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('multi_sites', '0003_auto_20170513_0344'),
        ('address', '0004_auto_20170125_0046'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('portfolios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthorisedRepresentative',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('date_of_birth', models.DateField(verbose_name='Date of birth', null=True)),
                ('gender', models.CharField(default='Male', max_length=20, choices=[('Male', 'Male'), ('Female', 'Female')])),
                ('phone_num', phonenumber_field.modelfields.PhoneNumberField(max_length=30, null=True)),
                ('civil_status', models.IntegerField(null=True, choices=[(0, 'Single'), (1, 'Married Filing Jointly'), (2, 'Married Filing Separately (lived with spouse)'), (3, "Married Filing Separately (didn't live with spouse)"), (4, 'Head of Household'), (5, 'Qualifying Widow(er)')])),
                ('regional_data', jsonfield.fields.JSONField(default=dict, blank=True)),
                ('geolocation_lock', models.CharField(max_length=30, blank=True)),
                ('is_accepted', models.BooleanField(default=False)),
                ('confirmation_key', models.CharField(max_length=36, null=True, blank=True, editable=False)),
                ('is_confirmed', models.BooleanField(default=False)),
                ('letter_of_authority', models.FileField(upload_to='')),
                ('betasmartz_agreement', models.BooleanField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Firm',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('dealer_group_number', models.CharField(max_length=50, null=True, blank=True)),
                ('slug', models.CharField(max_length=100, unique=True, editable=False)),
                ('logo', models.ImageField(verbose_name='White logo', null=True, blank=True, upload_to='')),
                ('knocked_out_logo', models.ImageField(verbose_name='Colored logo', null=True, blank=True, upload_to='')),
                ('client_agreement_url', models.FileField(verbose_name='Client Agreement (PDF)', null=True, blank=True, upload_to='')),
                ('form_adv_part2', models.FileField(verbose_name='Form Adv', null=True, blank=True, upload_to='')),
                ('token', models.CharField(max_length=36, editable=False)),
                ('fee', models.PositiveIntegerField(default=0)),
                ('can_use_ethical_portfolio', models.BooleanField(default=True)),
                ('account_types', models.ManyToManyField(to='multi_sites.AccountType', help_text='The set of supported account types offered to clients of this firm.')),
                ('default_portfolio_set', models.ForeignKey(to='portfolios.PortfolioSet')),
                ('fiscal_years', models.ManyToManyField(to='multi_sites.FiscalYear')),
            ],
        ),
        migrations.CreateModel(
            name='FirmConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('retiresmartz_enabled', models.BooleanField(default=True, help_text='Enables RetireSmartz feature')),
                ('soc_rsp_invest_enabled', models.BooleanField(default=True, verbose_name='Socially Responsible Investment field enabled', help_text='Enables or disables Socially Responsible Investment field in Goal')),
                ('risk_score_unlimited', models.BooleanField(default=False, verbose_name='Unlimited Risk score', help_text='Allows to set risk score value higher than recommended risk value')),
                ('constraints_enabled', models.BooleanField(default=True, verbose_name='Constraints Enabled', help_text='Enables or disables constraints on Client Allocation page')),
                ('rebalance_enabled', models.BooleanField(default=True, verbose_name='Rebalancing Enabled', help_text='Enables or disables Rebalancing settings on Client Allocation page')),
                ('firm', models.OneToOneField(to='firm.Firm', related_name='firm_config')),
            ],
            options={
                'verbose_name': 'Firm Configuration',
            },
        ),
        migrations.CreateModel(
            name='FirmData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('afsl_asic', models.CharField(max_length=50, verbose_name='AFSL/ASIC number', null=True, blank=True)),
                ('afsl_asic_document', models.FileField(verbose_name='AFSL/ASIC doc.', null=True, blank=True, upload_to='')),
                ('daytime_phone_num', phonenumber_field.modelfields.PhoneNumberField(max_length=16)),
                ('mobile_phone_num', phonenumber_field.modelfields.PhoneNumberField(max_length=16, null=True, blank=True)),
                ('fax_num', phonenumber_field.modelfields.PhoneNumberField(max_length=16, null=True, blank=True)),
                ('alternate_email_address', models.EmailField(max_length=254, verbose_name='Email address', null=True, blank=True)),
                ('last_change', models.DateField(auto_now=True)),
                ('fee_bank_account_name', models.CharField(max_length=100, verbose_name='Name', null=True, blank=True)),
                ('fee_bank_account_branch_name', models.CharField(max_length=100, verbose_name='Branch name', null=True, blank=True)),
                ('fee_bank_account_bsb_number', models.CharField(max_length=20, verbose_name='BSB number', null=True, blank=True)),
                ('fee_bank_account_number', models.CharField(max_length=20, verbose_name='Account number', null=True, blank=True)),
                ('fee_bank_account_holder_name', models.CharField(max_length=100, verbose_name='Account holder', null=True, blank=True)),
                ('australian_business_number', models.CharField(max_length=20, verbose_name='ABN', null=True, blank=True)),
                ('site_url', models.CharField(default='https://www.betasmartz.com', max_length=255, null=True, help_text='Official Site URL', blank=True)),
                ('advisor_support_phone', models.CharField(max_length=255, verbose_name='Advisor Support Phone', null=True, blank=True)),
                ('advisor_support_email', models.EmailField(max_length=254, verbose_name='Advisor Support Email', null=True, blank=True)),
                ('advisor_support_workhours', models.TextField(verbose_name='Advisor Support Workhours', null=True, blank=True)),
                ('client_support_phone', models.CharField(max_length=255, verbose_name='Client Support Phone', null=True, blank=True)),
                ('client_support_email', models.EmailField(max_length=254, verbose_name='Client Support Email', null=True, blank=True)),
                ('client_support_workhours', models.TextField(verbose_name='Client Support Workhours', null=True, blank=True)),
                ('firm', models.OneToOneField(to='firm.Firm', related_name='firm_details')),
                ('office_address', models.ForeignKey(to='address.Address', null=True, blank=True, related_name='+')),
                ('postal_address', models.ForeignKey(to='address.Address', related_name='+')),
            ],
            options={
                'verbose_name': 'Firm detail',
            },
        ),
        migrations.CreateModel(
            name='Supervisor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('can_write', models.BooleanField(default=False, verbose_name='Has Full Access?', help_text="A supervisor with 'full access' can perform actions for their advisors and clients.")),
                ('firm', models.ForeignKey(to='firm.Firm', related_name='supervisors')),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL, related_name='supervisor')),
            ],
        ),
        migrations.AddField(
            model_name='authorisedrepresentative',
            name='firm',
            field=models.ForeignKey(to='firm.Firm', related_name='authorised_representatives'),
        ),
        migrations.AddField(
            model_name='authorisedrepresentative',
            name='residential_address',
            field=models.ForeignKey(to='address.Address', related_name='+'),
        ),
        migrations.AddField(
            model_name='authorisedrepresentative',
            name='user',
            field=models.OneToOneField(to=settings.AUTH_USER_MODEL, related_name='authorised_representative'),
        ),
    ]
