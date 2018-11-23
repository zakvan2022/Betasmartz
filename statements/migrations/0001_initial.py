# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goal', '0001_initial'),
        ('client', '0003_auto_20170515_1146'),
        ('retiresmartz', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecordOfAdvice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('pdf', models.FileField(null=True, upload_to='', blank=True)),
                ('circumstances', models.TextField(verbose_name='Client circumstances', null=True, blank=True)),
                ('basis', models.TextField(verbose_name='Basis of advice', null=True, blank=True)),
                ('details', models.TextField(verbose_name='Details of the advice')),
                ('goal', models.ForeignKey(to='goal.Goal', related_name='records_of_advice')),
            ],
            options={
                'abstract': False,
                'ordering': ('-create_date',),
            },
        ),
        migrations.CreateModel(
            name='RetirementStatementOfAdvice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('pdf', models.FileField(null=True, upload_to='', blank=True)),
                ('retirement_plan', models.OneToOneField(to='retiresmartz.RetirementPlan', related_name='statement_of_advice')),
            ],
            options={
                'abstract': False,
                'ordering': ('-create_date',),
            },
        ),
        migrations.CreateModel(
            name='StatementOfAdvice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('pdf', models.FileField(null=True, upload_to='', blank=True)),
                ('account', models.OneToOneField(to='client.ClientAccount', related_name='statement_of_advice')),
            ],
            options={
                'abstract': False,
                'ordering': ('-create_date',),
            },
        ),
    ]
