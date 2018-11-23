# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('firm', '0001_initial'),
        ('client', '0001_initial'),
        ('advisor', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BulkInvestorTransfer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('approved', models.BooleanField(default=False)),
                ('approved_at', models.DateTimeField(null=True)),
                ('create_at', models.DateTimeField(auto_now_add=True)),
                ('signatures', models.FileField(upload_to='')),
                ('firm', models.ForeignKey(to='firm.Firm', editable=False)),
                ('from_advisor', models.ForeignKey(to='advisor.Advisor')),
                ('investors', models.ManyToManyField(to='client.Client')),
                ('to_advisor', models.ForeignKey(related_name='bulk_transfer_to_advisors', to='advisor.Advisor', verbose_name='To Advisor')),
            ],
        ),
        migrations.CreateModel(
            name='SingleInvestorTransfer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('approved', models.BooleanField(default=False)),
                ('approved_at', models.DateTimeField(null=True)),
                ('create_at', models.DateTimeField(auto_now_add=True)),
                ('signatures', models.FileField(upload_to='')),
                ('firm', models.ForeignKey(to='firm.Firm', editable=False)),
                ('from_advisor', models.ForeignKey(to='advisor.Advisor')),
                ('investor', models.ForeignKey(to='client.Client')),
                ('to_advisor', models.ForeignKey(related_name='single_transfer_to_advisors', to='advisor.Advisor', verbose_name='To Advisor')),
            ],
        ),
    ]
