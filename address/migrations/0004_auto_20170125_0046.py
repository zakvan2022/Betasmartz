# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('address', '0003_auto_20161021_1343'),
    ]

    operations = [
        migrations.CreateModel(
            name='USFips',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('fips', models.CharField(help_text='FIPS (County Code)', unique=True, max_length=5, db_index=True)),
                ('county_name', models.CharField(help_text='County Name', max_length=255)),
                ('rucc', models.IntegerField(choices=[(1, 'Metro - Counties in metro areas of 1 million population or more'), (2, 'Metro - Counties in metro areas of 250,000 to 1 million population'), (3, 'Metro - Counties in metro areas of fewer than 250,000 population'), (4, 'Nonmetro - Urban population of 20,000 or more, adjacent to a metro area'), (5, 'Nonmetro - Urban population of 20,000 or more, not adjacent to a metro area'), (6, 'Nonmetro - Urban population of 2,500 to 19,999, adjacent to a metro area'), (7, 'Nonmetro - Urban population of 2,500 to 19,999, not adjacent to a metro area'), (8, 'Nonmetro - Completely rural or less than 2,500 urban population, adjacent to a metro area'), (9, 'Nonmetro - Completely rural or less than 2,500 urban population, not adjacent to a metro area')])),
            ],
        ),
        migrations.CreateModel(
            name='USState',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('code', models.CharField(help_text='State code', unique=True, max_length=2)),
                ('name', models.CharField(help_text='State name', max_length=32)),
                ('region', models.IntegerField(choices=[(1, 'Northeast'), (2, 'South'), (3, 'Midwest'), (4, 'West')])),
            ],
        ),
        migrations.CreateModel(
            name='USZipcode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('zip_code', models.CharField(help_text='Zip code', max_length=10, db_index=True)),
                ('zip_name', models.CharField(help_text='Zip name', max_length=255)),
                ('phone_area_code', models.CharField(help_text='Phone area code', max_length=3)),
                ('fips', models.ForeignKey(to='address.USFips')),
            ],
        ),
        migrations.AddField(
            model_name='usfips',
            name='state',
            field=models.ForeignKey(to='address.USState'),
        ),
        migrations.AlterUniqueTogether(
            name='uszipcode',
            unique_together=set([('zip_code', 'zip_name')]),
        ),
    ]
