# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('address', '0004_auto_20170125_0046'),
    ]

    operations = [
        migrations.CreateModel(
            name='IBAccountFeed',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('type', models.CharField(max_length=2)),
                ('account_id', models.CharField(max_length=32, unique=True)),
                ('account_title', models.CharField(max_length=255)),
                ('account_type', models.CharField(max_length=255)),
                ('customer_type', models.CharField(max_length=255)),
                ('base_currency', models.CharField(max_length=255)),
                ('master_account_id', models.CharField(null=True, max_length=255, blank=True)),
                ('van', models.CharField(null=True, max_length=255, blank=True)),
                ('capabilities', models.CharField(max_length=255)),
                ('trading_permissions', models.CharField(max_length=255)),
                ('alias', models.CharField(null=True, max_length=255, blank=True)),
                ('primary_email', models.EmailField(max_length=255)),
                ('date_opened', models.DateField(null=True, blank=True)),
                ('date_closed', models.DateField(null=True, blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('address', models.ForeignKey(to='address.Address', related_name='+')),
            ],
        ),
    ]
