# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('multi_sites', '0003_auto_20170513_0344'),
    ]

    operations = [
        migrations.AddField(
            model_name='config',
            name='theme',
            field=models.CharField(default='betasmartz', max_length=255, choices=[('betasmartz', 'BetaSmartz'), ('oreana', 'Oreana')]),
        ),
    ]
