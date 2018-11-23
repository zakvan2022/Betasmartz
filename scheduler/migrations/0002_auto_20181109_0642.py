# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='schedule',
            name='day_of_month',
        ),
        migrations.RemoveField(
            model_name='schedule',
            name='day_of_week',
        ),
        migrations.AddField(
            model_name='schedule',
            name='day',
            field=models.PositiveIntegerField(help_text='Day of week (0 Mon - 6 Sun), or month (1 - 31), or quarter (1 - 90) based on delivery cycle', blank=True, null=True),
        ),
    ]
