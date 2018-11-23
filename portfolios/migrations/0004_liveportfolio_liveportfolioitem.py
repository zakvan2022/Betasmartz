# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('firm', '0005_auto_20181011_1559'),
        ('client', '0006_auto_20170525_0618'),
        ('portfolios', '0003_auto_20170519_0144'),
    ]

    operations = [
        migrations.CreateModel(
            name='LivePortfolio',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('clients', models.ManyToManyField(related_name='live_portfolios', to='client.Client')),
                ('firm', models.ForeignKey(to='firm.Firm', related_name='live_portfolios')),
            ],
        ),
        migrations.CreateModel(
            name='LivePortfolioItem',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('weight', models.FloatField()),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='portfolios.Ticker')),
                ('portfolio', models.ForeignKey(to='portfolios.LivePortfolio', related_name='items')),
            ],
        ),
    ]
