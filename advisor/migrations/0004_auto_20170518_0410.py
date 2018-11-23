# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('advisor', '0003_pricingplanadvisor'),
    ]

    operations = [
        migrations.AlterField(
            model_name='advisor',
            name='work_phone_num',
            field=phonenumber_field.modelfields.PhoneNumberField(null=True, max_length=30),
        ),
    ]
