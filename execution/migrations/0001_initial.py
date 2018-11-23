# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators
import jsonfield.fields
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0003_auto_20170515_1146'),
        ('goal', '0001_initial'),
        ('portfolios', '0002_auto_20170514_1729'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountId',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('ResponseCode', models.IntegerField()),
                ('Result', jsonfield.fields.JSONField()),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='ETNALogin',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('ResponseCode', models.IntegerField(db_index=True)),
                ('Ticket', models.CharField(max_length=521)),
                ('created', models.DateTimeField(db_index=True, auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Execution',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('volume', models.FloatField(help_text='Will be negative for a sell.')),
                ('price', models.FloatField(help_text='The raw price paid/received per share. Not including fees etc.')),
                ('executed', models.DateTimeField(help_text='The time the trade was executed.')),
                ('amount', models.FloatField(help_text='The realised amount that was transferred into the account (specified on the order) taking into account external fees etc.')),
                ('asset', models.ForeignKey(to='portfolios.Ticker', related_name='executions', on_delete=django.db.models.deletion.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name='ExecutionDistribution',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('volume', models.FloatField(help_text='The number of units from the execution that were applied to the transaction.')),
                ('execution', models.ForeignKey(to='execution.Execution', related_name='distributions', on_delete=django.db.models.deletion.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name='ExecutionFill',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('execution', models.OneToOneField(to='execution.Execution', related_name='execution_fill')),
            ],
        ),
        migrations.CreateModel(
            name='ExecutionRequest',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('reason', models.IntegerField(choices=[(0, 'DRIFT'), (1, 'WITHDRAWAL'), (2, 'DEPOSIT'), (3, 'METRIC_CHANGE')])),
                ('volume', models.FloatField(help_text='Will be negative for a sell.')),
                ('asset', models.ForeignKey(to='portfolios.Ticker', related_name='execution_requests', on_delete=django.db.models.deletion.PROTECT)),
                ('goal', models.ForeignKey(to='goal.Goal', related_name='execution_requests', on_delete=django.db.models.deletion.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name='Fill',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('volume', models.FloatField(help_text='Will be negative for a sell.')),
                ('price', models.FloatField(help_text='Price for the fill.')),
                ('executed', models.DateTimeField(help_text='The time the trade was executed.')),
            ],
        ),
        migrations.CreateModel(
            name='LoginResult',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('SessionId', models.CharField(max_length=128)),
                ('UserId', models.PositiveIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='MarketOrderRequest',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('state', models.IntegerField(choices=[(0, 'PENDING'), (1, 'APPROVED'), (2, 'SENT'), (3, 'CANCEL_PENDING'), (4, 'COMPLETE')], default=0)),
                ('account', models.ForeignKey(to='client.ClientAccount', related_name='market_orders', on_delete=django.db.models.deletion.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name='MarketOrderRequestAPEX',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('market_order_request', models.ForeignKey(to='execution.MarketOrderRequest', related_name='morsAPEX')),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('Price', models.FloatField()),
                ('Exchange', models.CharField(max_length=128, default='Auto')),
                ('TrailingLimitAmount', models.FloatField(default=0)),
                ('AllOrNone', models.IntegerField(default=0)),
                ('TrailingStopAmount', models.FloatField(default=0)),
                ('Type', models.IntegerField(choices=[(0, 'Market'), (1, 'Limit')], default=1)),
                ('Quantity', models.IntegerField()),
                ('SecurityId', models.IntegerField()),
                ('Symbol', models.CharField(max_length=128, default='Auto')),
                ('Side', models.IntegerField(choices=[(0, 'Buy'), (1, 'Sell')])),
                ('TimeInForce', models.IntegerField(choices=[(0, 'Day'), (1, 'GoodTillCancel'), (2, 'AtTheOpening'), (3, 'ImmediateOrCancel'), (4, 'FillOrKill'), (5, 'GoodTillCrossing'), (6, 'GoodTillDate')], default=6)),
                ('StopPrice', models.FloatField(default=0)),
                ('ExpireDate', models.IntegerField()),
                ('created', models.DateTimeField(db_index=True, auto_now_add=True)),
                ('Order_Id', models.IntegerField(default=-1)),
                ('Status', models.CharField(choices=[('New', 'New'), ('Sent', 'Sent'), ('PartiallyFilled', 'PartiallyFilled'), ('Filled', 'Filled'), ('DoneForDay', 'DoneForDay'), ('Canceled', 'Canceled'), ('Replaced', 'Replaced'), ('PendingCancel', 'PendingCancel'), ('Stopped', 'Stopped'), ('Rejected', 'Rejected'), ('Suspended', 'Suspended'), ('PendingNew', 'PendingNew'), ('Calculated', 'Calculated'), ('Expired', 'Expired'), ('AcceptedForBidding', 'AcceptedForBidding'), ('PendingReplace', 'PendingReplace'), ('Error', 'Error'), ('Archived', 'Archived')], max_length=128, db_index=True, default='New')),
                ('FillPrice', models.FloatField(default=0)),
                ('FillQuantity', models.IntegerField(default=0)),
                ('Description', models.CharField(max_length=128)),
                ('Broker', models.CharField(max_length=128)),
                ('fill_info', models.IntegerField(choices=[(0, 'FILLED'), (1, 'PARTIALY_FILLED'), (2, 'UNFILLED')], default=2)),
                ('ticker', models.ForeignKey(to='portfolios.Ticker', related_name='Order', on_delete=django.db.models.deletion.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name='PositionLot',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('quantity', models.FloatField(blank=True, default=None, null=True)),
                ('execution_distribution', models.OneToOneField(to='execution.ExecutionDistribution', related_name='position_lot')),
            ],
        ),
        migrations.CreateModel(
            name='Sale',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('quantity', models.FloatField(blank=True, default=None, null=True)),
                ('buy_execution_distribution', models.ForeignKey(to='execution.ExecutionDistribution', related_name='bought_lot')),
                ('sell_execution_distribution', models.ForeignKey(to='execution.ExecutionDistribution', related_name='sold_lot')),
            ],
        ),
        migrations.CreateModel(
            name='Security',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('symbol_id', models.IntegerField()),
                ('Symbol', models.CharField(max_length=128)),
                ('Description', models.CharField(max_length=128)),
                ('Currency', models.CharField(max_length=20)),
                ('Price', models.FloatField()),
                ('created', models.DateTimeField(db_index=True, auto_now_add=True)),
            ],
        ),
        migrations.AddField(
            model_name='marketorderrequestapex',
            name='order',
            field=models.ForeignKey(to='execution.Order', related_name='morsAPEX', default=None),
        ),
        migrations.AddField(
            model_name='marketorderrequestapex',
            name='ticker',
            field=models.ForeignKey(to='portfolios.Ticker', related_name='morsAPEX', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='fill',
            name='order',
            field=models.ForeignKey(to='execution.Order', related_name='fills', default=None),
        ),
        migrations.AddField(
            model_name='executionrequest',
            name='order',
            field=models.ForeignKey(to='execution.MarketOrderRequest', related_name='execution_requests'),
        ),
        migrations.AddField(
            model_name='executionrequest',
            name='transaction',
            field=models.OneToOneField(to='goal.Transaction', related_name='execution_request', null=True),
        ),
        migrations.AddField(
            model_name='executionfill',
            name='fill',
            field=models.ForeignKey(to='execution.Fill', related_name='execution_fill'),
        ),
        migrations.AddField(
            model_name='executiondistribution',
            name='execution_request',
            field=models.ForeignKey(to='execution.ExecutionRequest', related_name='execution_distributions', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='executiondistribution',
            name='transaction',
            field=models.OneToOneField(to='goal.Transaction', related_name='execution_distribution', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='execution',
            name='order',
            field=models.ForeignKey(to='execution.MarketOrderRequest', related_name='executions', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='etnalogin',
            name='Result',
            field=models.OneToOneField(to='execution.LoginResult', related_name='ETNALogin'),
        ),
        migrations.AlterUniqueTogether(
            name='marketorderrequestapex',
            unique_together=set([('ticker', 'market_order_request')]),
        ),
    ]
