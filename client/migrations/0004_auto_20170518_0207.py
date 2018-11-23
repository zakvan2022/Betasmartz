# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0003_auto_20170515_1146'),
    ]

    operations = [
        migrations.AddField(
            model_name='ibonboard',
            name='joint_type',
            field=models.CharField(max_length=250, blank=True, choices=[(0, 'Community Property'), (1, 'Joint Tenants'), (2, 'Tenants in Common'), (3, 'Tenants by Entirety')], null=True, help_text='Type of joint account'),
        ),
        migrations.AddField(
            model_name='ibonboard',
            name='xml_inbound',
            field=jsonfield.fields.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ibonboard',
            name='xml_outbound',
            field=models.TextField(blank=True, null=True),
        ),
    ]
