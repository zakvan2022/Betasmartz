# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('firm', '0005_auto_20181011_1559'),
    ]

    operations = [
        migrations.AddField(
            model_name='firm',
            name='full_name',
            field=models.CharField(null=True, max_length=255, blank=True),
        ),
    ]
