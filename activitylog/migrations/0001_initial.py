# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(unique=True, max_length=100)),
                ('format_str', models.TextField()),
                ('format_args', models.TextField(null=True, blank=True, help_text="Dotted '.' dictionary path into the event 'extra' field for each arg in the format_str. Each arg path separated by newline.Eg. 'request.amount'")),
            ],
        ),
        migrations.CreateModel(
            name='ActivityLogEvent',
            fields=[
                ('id', models.IntegerField(choices=[(0, 'PLACE_MARKET_ORDER'), (1, 'CANCEL_MARKET_ORDER'), (2, 'ARCHIVE_GOAL_REQUESTED'), (3, 'ARCHIVE_GOAL'), (4, 'REACTIVATE_GOAL'), (5, 'APPROVE_SELECTED_SETTINGS'), (6, 'REVERT_SELECTED_SETTINGS'), (7, 'SET_SELECTED_SETTINGS'), (8, 'UPDATE_SELECTED_SETTINGS'), (9, 'GOAL_WITHDRAWAL'), (10, 'GOAL_DEPOSIT'), (11, 'GOAL_BALANCE_CALCULATED'), (12, 'GOAL_WITHDRAWAL_EXECUTED'), (13, 'GOAL_DEPOSIT_EXECUTED'), (14, 'GOAL_DIVIDEND_DISTRIBUTION'), (15, 'GOAL_FEE_LEVIED'), (16, 'GOAL_REBALANCE_EXECUTED'), (17, 'GOAL_TRANSFER_EXECUTED'), (18, 'GOAL_ORDER_DISTRIBUTION'), (19, 'RETIRESMARTZ_PROTECTIVE_MOVE'), (20, 'RETIRESMARTZ_DYNAMIC_MOVE'), (21, 'RETIRESMARTZ_SPENDING_UP_CONTRIB_DOWN'), (22, 'RETIRESMARTZ_SPENDING_DOWN_CONTRIB_UP'), (23, 'RETIRESMARTZ_RETIREMENT_AGE_ADJUSTED'), (24, 'RETIRESMARTZ_IS_A_SMOKER'), (25, 'RETIRESMARTZ_IS_NOT_A_SMOKER'), (26, 'RETIRESMARTZ_EXERCISE_ONLY'), (27, 'RETIRESMARTZ_WEIGHT_AND_HEIGHT_ONLY'), (28, 'RETIRESMARTZ_COMBINATION_WELLBEING_ENTRIES'), (29, 'RETIRESMARTZ_ALL_WELLBEING_ENTRIES'), (30, 'RETIRESMARTZ_ON_TRACK_NOW'), (31, 'RETIRESMARTZ_OFF_TRACK_NOW'), (32, 'RETIRESMARTZ_SPENDING_UP_CONTRIB_DOWN_AGAIN'), (33, 'RETIRESMARTZ_DRINKS_MORE_THAN_ONE'), (34, 'RETIRESMARTZ_DRINKS_ONE_OR_LESS'), (50, 'SOA_GENERATED'), (51, 'ROA_GENERATED'), (52, 'RETIREMENT_SOA_GENERATED'), (53, 'ALLOCATION_CHANGED'), (54, 'TAX_LOSS_HARVESTED'), (55, 'STATEMENTS_GENERATED'), (56, 'TAX_FORMS_GENERATED'), (57, 'OTHERS_GENERATED')], primary_key=True, serialize=False)),
                ('activity_log', models.ForeignKey(to='activitylog.ActivityLog', related_name='events')),
            ],
        ),
    ]
