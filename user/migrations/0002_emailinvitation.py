# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailInvitation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('email', models.EmailField(max_length=254)),
                ('inviter_id', models.PositiveIntegerField()),
                ('send_date', models.DateTimeField(auto_now=True)),
                ('send_count', models.PositiveIntegerField(default=0)),
                ('status', models.PositiveIntegerField(choices=[(0, 'Pending'), (1, 'Submitted'), (3, 'Active'), (4, 'Closed')], default=0)),
                ('invitation_type', models.PositiveIntegerField(choices=[(0, 'Advisor'), (1, 'Authorised representative'), (2, 'Supervisor'), (3, 'Client')], default=3)),
                ('inviter_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
        ),
    ]
