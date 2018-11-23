# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0002_pricingplanclient'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalAsset',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('type', models.IntegerField(choices=[(0, 'Family Home'), (1, 'Investment Property'), (2, 'Investment Portfolio'), (3, 'Savings Account'), (4, 'Property Loan'), (5, 'Transaction Account'), (6, 'Retirement Account'), (7, 'Other')])),
                ('name', models.CharField(max_length=128)),
                ('description', models.TextField(blank=True, null=True)),
                ('valuation', models.DecimalField(help_text='In the system currency. Could be negative if a debt', decimal_places=2, max_digits=15)),
                ('valuation_date', models.DateField(help_text='Date when the asset was valued')),
                ('growth', models.DecimalField(help_text='Modeled annualized growth of the asset - pos or neg. 0.0 is no growth', decimal_places=4, max_digits=5)),
                ('acquisition_date', models.DateField(help_text="Could be in the future if it's a future acquisition")),
            ],
        ),
        migrations.CreateModel(
            name='ExternalAssetTransfer',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('begin_date', models.DateField()),
                ('amount', models.FloatField()),
                ('growth', models.FloatField(help_text='Daily rate to increase or decrease the amount by as of the begin_date. 0.0 for no modelled change')),
                ('schedule', models.TextField(help_text='RRULE to specify when the transfer happens')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ExternalAccount',
            fields=[
                ('externalasset_ptr', models.OneToOneField(auto_created=True, primary_key=True, parent_link=True, to='client.ExternalAsset', serialize=False)),
                ('institution', models.CharField(help_text='Institute where the account is held.', max_length=128)),
                ('account_id', models.CharField(max_length=64)),
            ],
            bases=('client.externalasset',),
        ),
        migrations.AddField(
            model_name='externalassettransfer',
            name='asset',
            field=models.OneToOneField(related_name='transfer_plan', to='client.ExternalAsset'),
        ),
        migrations.AddField(
            model_name='externalasset',
            name='debt',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, help_text='Any debt that is directly associated to the asset.', related_name='for_asset', to='client.ExternalAsset'),
        ),
        migrations.AddField(
            model_name='externalasset',
            name='owner',
            field=models.ForeignKey(related_name='external_assets', to='client.Client'),
        ),
        migrations.AlterUniqueTogether(
            name='externalasset',
            unique_together=set([('name', 'owner')]),
        ),
    ]
