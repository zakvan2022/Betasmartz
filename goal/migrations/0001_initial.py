# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import portfolios.models
import django.core.validators
import django.db.models.deletion
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0002_pricingplanclient'),
        ('eventlog', '0003_auto_20160111_0208'),
        ('portfolios', '0002_auto_20170514_1729'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventMemo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.TextField()),
                ('staff', models.BooleanField(help_text='Staff memos can only be seen by staff members of the firm. Non-Staff memos inherit the permissions of the logged event. I.e. Whoever can see the event, can see the memo.')),
                ('event', models.ForeignKey(to='eventlog.Log', related_name='memos', on_delete=django.db.models.deletion.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name='Goal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('cash_balance', models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0.0)])),
                ('drift_score', models.FloatField(default=0.0, help_text='The maximum ratio of current drift to maximum allowable drift from any metric on this goal.')),
                ('state', models.IntegerField(default=4, choices=[(0, 'Active'), (1, 'Archive Requested'), (2, 'Closing'), (3, 'Archived'), (4, 'Inactive')])),
                ('order', models.IntegerField(default=0, help_text='The desired position in the list of Goals')),
                ('account', models.ForeignKey(related_name='all_goals', to='client.ClientAccount')),
            ],
            options={
                'ordering': ('state', 'order'),
            },
        ),
        migrations.CreateModel(
            name='GoalMetric',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.IntegerField(choices=[(0, 'Portfolio Mix'), (1, 'RiskScore')])),
                ('comparison', models.IntegerField(default=1, choices=[(0, 'Minimum'), (1, 'Exactly'), (2, 'Maximum')])),
                ('rebalance_type', models.IntegerField(help_text='Is the rebalance threshold an absolute threshold or relative (percentage difference) threshold?', choices=[(0, 'Absolute'), (1, 'Relative')])),
                ('rebalance_thr', models.FloatField(help_text='The difference between configured and measured value at which a rebalance will be recommended.')),
                ('configured_val', models.FloatField(help_text='The value of the metric that was configured.')),
                ('feature', models.ForeignKey(to='portfolios.AssetFeatureValue', on_delete=django.db.models.deletion.PROTECT, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='GoalMetricGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.IntegerField(default=0, choices=[(0, 'Custom'), (1, 'Preset')])),
                ('name', models.CharField(null=True, max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='GoalSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('target', models.FloatField(default=0)),
                ('completion', models.DateField(help_text='The scheduled completion date for the goal.')),
                ('hedge_fx', models.BooleanField(help_text='Do we want to hedge foreign exposure?')),
                ('rebalance', models.BooleanField(default=True, help_text='Do we want to perform automated rebalancing?')),
                ('metric_group', models.ForeignKey(to='goal.GoalMetricGroup', related_name='settings', on_delete=django.db.models.deletion.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name='GoalType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('description', models.TextField(null=True, blank=True)),
                ('default_term', models.IntegerField()),
                ('group', models.CharField(null=True, max_length=255)),
                ('risk_sensitivity', models.FloatField(help_text='Default risk sensitivity for this goal type. 0 = not sensitive, 10 = Very sensitive (No risk tolerated)', validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(10.0)])),
                ('order', models.IntegerField(default=0, help_text='The order of the type in the list.')),
                ('risk_factor_weights', jsonfield.fields.JSONField(null=True, blank=True)),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='HistoricalBalance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('balance', models.FloatField()),
                ('goal', models.ForeignKey(related_name='balance_history', to='goal.Goal')),
            ],
        ),
        migrations.CreateModel(
            name='Portfolio',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stdev', models.FloatField()),
                ('er', models.FloatField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('rebalance', models.BooleanField(default=True)),
                ('setting', models.OneToOneField(related_name='portfolio', to='goal.GoalSetting')),
            ],
        ),
        migrations.CreateModel(
            name='PortfolioItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weight', models.FloatField()),
                ('volatility', models.FloatField(help_text='variance of this asset at the time of creating this portfolio.')),
                ('asset', models.ForeignKey(to='portfolios.Ticker', on_delete=django.db.models.deletion.PROTECT)),
                ('portfolio', models.ForeignKey(related_name='items', to='goal.Portfolio')),
            ],
        ),
        migrations.CreateModel(
            name='RecurringTransaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('begin_date', models.DateField()),
                ('amount', models.FloatField()),
                ('growth', models.FloatField(help_text='Daily rate to increase or decrease the amount by as of the begin_date. 0.0 for no modelled change')),
                ('schedule', models.TextField(help_text='RRULE to specify when the transfer happens')),
                ('enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('account_id', models.CharField(null=True, blank=True, max_length=255)),
                ('stripe_id', models.CharField(null=True, blank=True, max_length=255)),
                ('setting', models.ForeignKey(related_name='recurring_transactions', to='goal.GoalSetting')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.IntegerField(db_index=True, choices=[(0, 'DIVIDEND'), (1, 'DEPOSIT'), (2, 'WITHDRAWAL'), (3, 'REBALANCE'), (4, 'TRANSFER'), (5, 'FEE'), (6, 'ORDER'), (7, 'EXECUTION')])),
                ('amount', models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0.0)])),
                ('status', models.CharField(default='PENDING', choices=[('PENDING', 'PENDING'), ('EXECUTED', 'EXECUTED'), ('AWAITING APPROVAL', 'AWAITING APPROVAL'), ('FAILED', 'FAILED')], max_length=20)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('executed', models.DateTimeField(db_index=True, null=True)),
                ('account_id', models.CharField(null=True, blank=True, max_length=255)),
                ('stripe_id', models.CharField(null=True, blank=True, max_length=255)),
                ('from_goal', models.ForeignKey(to='goal.Goal', related_name='transactions_from', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True)),
                ('to_goal', models.ForeignKey(to='goal.Goal', related_name='transactions_to', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True)),
            ],
        ),
        migrations.AddField(
            model_name='goalmetric',
            name='group',
            field=models.ForeignKey(related_name='metrics', to='goal.GoalMetricGroup'),
        ),
        migrations.AddField(
            model_name='goal',
            name='active_settings',
            field=models.OneToOneField(related_name='goal_active', help_text='The settings were last used to do a rebalance.These settings are responsible for our current market positions.', null=True, to='goal.GoalSetting', blank=True),
        ),
        migrations.AddField(
            model_name='goal',
            name='approved_settings',
            field=models.OneToOneField(related_name='goal_approved', help_text='The settings that both the client and advisor have confirmed and will become active the next time the goal is rebalanced.', null=True, to='goal.GoalSetting', blank=True),
        ),
        migrations.AddField(
            model_name='goal',
            name='portfolio_set',
            field=models.ForeignKey(default=portfolios.models.get_default_set_id, to='portfolios.PortfolioSet', related_name='goal'),
        ),
        migrations.AddField(
            model_name='goal',
            name='selected_settings',
            field=models.OneToOneField(related_name='goal_selected', help_text='The settings that the client has confirmed, but are not yet approved by the advisor.', null=True, to='goal.GoalSetting', blank=True),
        ),
        migrations.AddField(
            model_name='goal',
            name='type',
            field=models.ForeignKey(to='goal.GoalType'),
        ),
        migrations.AlterUniqueTogether(
            name='historicalbalance',
            unique_together=set([('goal', 'date')]),
        ),
        migrations.AlterUniqueTogether(
            name='goal',
            unique_together=set([('account', 'name')]),
        ),
    ]
