# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('firm', '0002_pricingplan'),
        ('advisor', '0002_bulkinvestortransfer_singleinvestortransfer'),
    ]

    operations = [
        migrations.CreateModel(
            name='PricingPlanAdvisor',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('bps', models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0)])),
                ('fixed', models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0)])),
                ('parent', models.ForeignKey(to='firm.PricingPlan', related_name='advisor_overrides')),
                ('person', models.OneToOneField(to='advisor.Advisor', related_name='pricing_plan')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
