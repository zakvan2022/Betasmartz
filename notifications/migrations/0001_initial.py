# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('level', models.CharField(max_length=20, default='info', choices=[('success', 'success'), ('info', 'info'), ('warning', 'warning'), ('error', 'error')])),
                ('unread', models.BooleanField(default=True)),
                ('actor_object_id', models.PositiveIntegerField()),
                ('verb', models.CharField(max_length=255)),
                ('description', models.TextField(null=True, blank=True)),
                ('target_object_id', models.PositiveIntegerField(null=True, blank=True)),
                ('action_object_object_id', models.PositiveIntegerField(null=True, blank=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('public', models.BooleanField(default=True)),
                ('deleted', models.BooleanField(default=False)),
                ('emailed', models.BooleanField(default=False)),
                ('data', jsonfield.fields.JSONField(null=True, blank=True)),
                ('action_object_content_type', models.ForeignKey(null=True, blank=True, to='contenttypes.ContentType', related_name='notify_action_object')),
                ('actor_content_type', models.ForeignKey(related_name='notify_actor', to='contenttypes.ContentType')),
                ('recipient', models.ForeignKey(related_name='notifications', to=settings.AUTH_USER_MODEL)),
                ('target_content_type', models.ForeignKey(null=True, blank=True, to='contenttypes.ContentType', related_name='notify_target')),
            ],
            options={
                'ordering': ('-timestamp',),
            },
        ),
    ]
