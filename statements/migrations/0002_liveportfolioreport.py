# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolios', '0004_liveportfolio_liveportfolioitem'),
        ('statements', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LivePortfolioReport',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('pdf', models.FileField(null=True, blank=True, upload_to='')),
                ('live_portfolio', models.ForeignKey(to='portfolios.LivePortfolio', related_name='reports')),
            ],
            options={
                'abstract': False,
                'ordering': ('-create_date',),
            },
        ),
    ]
