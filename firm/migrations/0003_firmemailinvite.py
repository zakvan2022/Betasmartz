# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import firm.models
from django.conf import settings
import phonenumber_field.modelfields
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('firm', '0002_pricingplan'),
    ]

    operations = [
        migrations.CreateModel(
            name='FirmEmailInvite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first_name', models.CharField(max_length=100)),
                ('middle_name', models.CharField(max_length=100, blank=True)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(max_length=30, blank=True, null=True)),
                ('firm_agreement_url', models.FileField(null=True, blank=True, upload_to='')),
                ('invite_key', models.CharField(max_length=64, default=firm.models.generate_token, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('last_sent_at', models.DateTimeField(null=True, blank=True)),
                ('send_count', models.PositiveIntegerField(default=0)),
                ('status', models.PositiveIntegerField(default=0, choices=[(0, 'Created'), (1, 'Sent'), (2, 'Accepted'), (3, 'Expired'), (4, 'Complete')])),
                ('onboarding_data', jsonfield.fields.JSONField(null=True, blank=True)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL, blank=True, null=True, related_name='firm_invitation')),
            ],
        ),
    ]
