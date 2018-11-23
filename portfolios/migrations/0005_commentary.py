# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolios', '0004_liveportfolio_liveportfolioitem'),
    ]

    operations = [
        migrations.CreateModel(
            name='Commentary',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('category', models.IntegerField(default=1, choices=[(1, 'Portfolio Information'), (2, 'Economic Information'), (3, 'Market Information'), (4, 'Risk Management')])),
                ('key_commentary', models.TextField()),
                ('near_term_outlook', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('publish_at', models.DateTimeField()),
                ('portfolio', models.ForeignKey(related_name='commentaries', to='portfolios.LivePortfolio')),
            ],
            options={
                'verbose_name': 'commentary',
                'verbose_name_plural': 'commentaries',
            },
        ),
    ]
