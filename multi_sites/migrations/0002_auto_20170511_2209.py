# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('multi_sites', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='config',
            name='constraints_enabled',
        ),
        migrations.RemoveField(
            model_name='config',
            name='rebalance_enabled',
        ),
        migrations.RemoveField(
            model_name='config',
            name='retiresmartz_enabled',
        ),
        migrations.RemoveField(
            model_name='config',
            name='soc_rsp_invest_enabled',
        ),
        migrations.RemoveField(
            model_name='config',
            name='risk_score_unlimited',
        ),
    ]
