# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('schedule_type', models.CharField(default='LIVE_PORTFOLIO_REPORT', choices=[('LIVE_PORTFOLIO_REPORT', 'Live Portfolio Report')], max_length=64)),
                ('delivery_cycle', models.CharField(default='DAILY', choices=[('DAILY', 'Daily'), ('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly'), ('QUARTERLY', 'Quarterly')], max_length=32)),
                ('day_of_week', models.PositiveIntegerField(blank=True, null=True, choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')], help_text='Day of week')),
                ('day_of_month', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)], blank=True, null=True, help_text='Day of the month')),
                ('time', models.TimeField(blank=True, null=True, help_text='Time')),
                ('timezone', models.CharField(default='UTC', max_length=32, help_text='ISO timezone name')),
                ('meta', jsonfield.fields.JSONField(blank=True, null=True)),
                ('object_id', models.PositiveIntegerField(db_index=True)),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='schedule',
            unique_together=set([('content_type', 'object_id')]),
        ),
    ]
