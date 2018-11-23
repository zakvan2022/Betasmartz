# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import phonenumber_field.modelfields
import jsonfield.fields
from django.conf import settings
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('firm', '0001_initial'),
        ('address', '0004_auto_20170125_0046'),
        ('portfolios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountGroup',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Advisor',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('date_of_birth', models.DateField(null=True, verbose_name='Date of birth')),
                ('gender', models.CharField(default='Male', max_length=20, choices=[('Male', 'Male'), ('Female', 'Female')])),
                ('phone_num', phonenumber_field.modelfields.PhoneNumberField(null=True, max_length=30)),
                ('civil_status', models.IntegerField(null=True, choices=[(0, 'Single'), (1, 'Married Filing Jointly'), (2, 'Married Filing Separately (lived with spouse)'), (3, "Married Filing Separately (didn't live with spouse)"), (4, 'Head of Household'), (5, 'Qualifying Widow(er)')])),
                ('regional_data', jsonfield.fields.JSONField(default=dict, blank=True)),
                ('geolocation_lock', models.CharField(blank=True, max_length=30)),
                ('is_accepted', models.BooleanField(default=False)),
                ('confirmation_key', models.CharField(null=True, blank=True, max_length=36, editable=False)),
                ('is_confirmed', models.BooleanField(default=False)),
                ('token', models.CharField(null=True, max_length=36, editable=False)),
                ('letter_of_authority', models.FileField(upload_to='')),
                ('work_phone_num', phonenumber_field.modelfields.PhoneNumberField(null=True, max_length=16)),
                ('betasmartz_agreement', models.BooleanField()),
                ('last_action', models.DateTimeField(null=True)),
                ('default_portfolio_set', models.ForeignKey(to='portfolios.PortfolioSet')),
                ('firm', models.ForeignKey(to='firm.Firm', related_name='advisors')),
                ('residential_address', models.ForeignKey(to='address.Address', related_name='+')),
                ('user', models.OneToOneField(related_name='advisor', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ChangeDealerGroup',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('approved', models.BooleanField(default=False)),
                ('create_at', models.DateTimeField(auto_now_add=True)),
                ('approved_at', models.DateTimeField(null=True, blank=True)),
                ('work_phone', phonenumber_field.modelfields.PhoneNumberField(max_length=128)),
                ('new_email', models.EmailField(max_length=254)),
                ('letter_previous_group', models.FileField(upload_to='', verbose_name='Prev. Group Letter')),
                ('letter_new_group', models.FileField(upload_to='', verbose_name='New Group Letter')),
                ('signature', models.FileField(upload_to='')),
                ('advisor', models.ForeignKey(to='advisor.Advisor')),
                ('new_firm', models.ForeignKey(to='firm.Firm', related_name='new_advisors')),
                ('old_firm', models.ForeignKey(to='firm.Firm', related_name='old_advisors')),
            ],
        ),
        migrations.AddField(
            model_name='accountgroup',
            name='advisor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='primary_account_groups', to='advisor.Advisor'),
        ),
        migrations.AddField(
            model_name='accountgroup',
            name='secondary_advisors',
            field=models.ManyToManyField(related_name='secondary_account_groups', to='advisor.Advisor'),
        ),
    ]
