# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, verbose_name='ID', serialize=False)),
                ('logo', models.ImageField(upload_to='', verbose_name='White logo', null=True, blank=True)),
                ('knocked_out_logo', models.ImageField(upload_to='', verbose_name='Colored logo', null=True, blank=True)),
                ('ib_enabled', models.BooleanField(default=False, help_text='Enables or disables Interactive Brokers feature', verbose_name='Interactive Brokers Enabled')),
                ('abridged_onboarding_enabled', models.BooleanField(default=False, help_text='Allow Abridged Onboarding section on client invitation page of advisor console.')),
                ('goal_portfolio_name_enabled', models.BooleanField(default=False, help_text='Shows or hides Goal Portfolio Name in client console.')),
                ('retiresmartz_enabled', models.BooleanField(default=True, help_text='Enables RetireSmartz feature')),
                ('soc_rsp_invest_enabled', models.BooleanField(default=True, help_text='Enables or disables Socially Responsible Investment field in Goal', verbose_name='Socially Responsible Investment field enabled')),
                ('risk_score_unlimited', models.BooleanField(default=False, help_text='Allows to set risk score value higher than recommended risk value', verbose_name='Unlimited Risk score')),
                ('constraints_enabled', models.BooleanField(default=True, help_text='Enables or disables constraints on Client Allocation page', verbose_name='Constraints Enabled')),
                ('rebalance_enabled', models.BooleanField(default=True, help_text='Enables or disables Rebalancing settings on Client Allocation page', verbose_name='Rebalancing Enabled')),
                ('plaid_enabled', models.BooleanField(default=True, help_text='Enables or disables linking of Plaid Account and showing of account dropdown.', verbose_name='Plaid Account Enabled')),
                ('ib_acats_enabled', models.BooleanField(default=True, help_text='Enables or disables Interactive Brokers ACATS transfer', verbose_name='IB ACATS Enabled')),
                ('site', models.OneToOneField(to='sites.Site', related_name='site_config')),
            ],
        ),
    ]
