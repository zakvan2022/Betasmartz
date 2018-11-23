# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0004_auto_20170518_0207'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ibonboard',
            name='joint_type',
            field=models.CharField(help_text='Type of joint account', null=True, max_length=250, choices=[(1, 'Community Property'), (2, 'Joint Tenants'), (3, 'Tenants by Entirety'), (4, 'Tenants in Common')], blank=True),
        ),
    ]
