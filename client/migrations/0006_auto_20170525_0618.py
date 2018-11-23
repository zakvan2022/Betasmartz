# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0005_auto_20170518_2317'),
    ]

    operations = [
        migrations.AddField(
            model_name='ibonboard',
            name='ib_entity',
            field=models.CharField(max_length=32, blank=True, unique=True, null=True),
        ),
        migrations.AddField(
            model_name='ibonboard',
            name='ib_password',
            field=models.CharField(max_length=32, blank=True, unique=True, null=True),
        ),
        migrations.AddField(
            model_name='ibonboard',
            name='ib_user',
            field=models.CharField(max_length=32, blank=True, unique=True, null=True),
        ),
        migrations.AddField(
            model_name='ibonboard',
            name='ib_user_id',
            field=models.CharField(max_length=32, blank=True, unique=True, null=True),
        ),
    ]
