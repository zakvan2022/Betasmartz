# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolios', '0005_commentary'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='commentary',
            options={'ordering': ['-publish_at'], 'verbose_name': 'commentary', 'verbose_name_plural': 'commentaries'},
        ),
        migrations.AlterField(
            model_name='commentary',
            name='portfolio',
            field=models.ForeignKey(to='portfolios.LivePortfolio', blank=True, related_name='commentaries', null=True),
        ),
    ]
