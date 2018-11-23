# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('firm', '0004_auto_20170518_0341'),
    ]

    operations = [
        migrations.AddField(
            model_name='firm',
            name='mini_logo',
            field=models.ImageField(verbose_name='Mini logo', null=True, blank=True, upload_to=''),
        ),
        migrations.AddField(
            model_name='firm',
            name='report_logo',
            field=models.ImageField(verbose_name='Report logo', null=True, blank=True, upload_to=''),
        ),
    ]
