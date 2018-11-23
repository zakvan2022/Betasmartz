# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolios', '0002_auto_20170514_1729'),
    ]

    operations = [
        migrations.AlterField(
            model_name='portfolioprovider',
            name='type',
            field=models.IntegerField(choices=[(0, 'BetaSmartz'), (1, 'Aon'), (2, 'Krane'), (3, 'Lee')]),
        ),
    ]
