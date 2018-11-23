# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('firm', '0002_pricingplan'),
        ('client', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PricingPlanClient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('bps', models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0)])),
                ('fixed', models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0)])),
                ('parent', models.ForeignKey(to='firm.PricingPlan', related_name='client_overrides')),
                ('person', models.OneToOneField(to='client.Client', related_name='pricing_plan')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
