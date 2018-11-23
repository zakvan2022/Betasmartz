# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('firm', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PricingPlan',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('bps', models.FloatField(validators=[django.core.validators.MinValueValidator(0)], default=0.0)),
                ('fixed', models.FloatField(validators=[django.core.validators.MinValueValidator(0)], default=0.0)),
                ('system_bps', models.FloatField(validators=[django.core.validators.MinValueValidator(0)], default=0.0)),
                ('system_fixed', models.FloatField(validators=[django.core.validators.MinValueValidator(0)], default=0.0)),
                ('firm', models.OneToOneField(to='firm.Firm', related_name='pricing_plan')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
