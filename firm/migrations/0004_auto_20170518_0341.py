# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('firm', '0003_firmemailinvite'),
    ]

    operations = [
        migrations.AlterField(
            model_name='firmdata',
            name='daytime_phone_num',
            field=phonenumber_field.modelfields.PhoneNumberField(max_length=30),
        ),
        migrations.AlterField(
            model_name='firmdata',
            name='mobile_phone_num',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, null=True, max_length=30),
        ),
    ]
