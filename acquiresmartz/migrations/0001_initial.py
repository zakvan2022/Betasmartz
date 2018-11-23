# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('firm', '0002_pricingplan'),
    ]

    operations = [
        migrations.CreateModel(
            name='Campaign',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('title', models.CharField(help_text='Campaign Title', max_length=255)),
                ('description', models.TextField(blank=True, null=True, help_text='Campaign description')),
                ('search_term', models.CharField(help_text='Campaign search term', max_length=255)),
                ('location', models.CharField(help_text='Campaign location', max_length=255)),
                ('statuses_count', models.CharField(blank=True, choices=[('', 'All'), ('0,50', '< 50'), ('51,100', '51-100'), ('101,250', '101-250'), ('251,500', '251-500'), ('501,1000', '501-1000'), ('1000', '> 1000')], null=True, help_text='Campaign location', max_length=255)),
                ('following', models.CharField(blank=True, choices=[('', 'All'), ('0,10', '< 10'), ('11,25', '11-25'), ('26,50', '26-50'), ('51,100', '51-100'), ('101,250', '101-250'), ('250', '> 250')], null=True, help_text='Campaign Following', max_length=20)),
                ('followers', models.CharField(blank=True, choices=[('', 'All'), ('0,10', '< 10'), ('11,25', '11-25'), ('26,50', '26-50'), ('51,100', '51-100'), ('101,250', '101-250'), ('250', '> 250')], null=True, help_text='Campaign Followers', max_length=20)),
                ('sentiment', models.CharField(null=True, max_length=20, choices=[('', 'All'), ('positive', 'Positive'), ('negative', 'Negative'), ('neutral', 'Neutral'), ('ambivalent', 'Ambivalent')], verbose_name='Tone', blank=True, help_text='Campaign Sentiment/Tone')),
                ('firm', models.ForeignKey(to='firm.Firm', related_name='campaign')),
            ],
        ),
        migrations.CreateModel(
            name='PersonalityInsight',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('json_data', jsonfield.fields.JSONField()),
                ('last_updated', models.DateTimeField(auto_now=True, help_text='Last updated date/time')),
            ],
        ),
        migrations.CreateModel(
            name='TargetUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('twitter_id', models.BigIntegerField(db_index=True, help_text='Twitter User ID')),
                ('twitter_username', models.CharField(help_text='Twitter Username', max_length=255)),
                ('twitter_display_name', models.CharField(help_text='Twitter User Display Name', max_length=255)),
                ('twitter_image', models.CharField(blank=True, null=True, help_text='Twitter Profile Image', max_length=1000)),
                ('message', models.TextField(blank=True, null=True, help_text='Tweet Message')),
                ('posted_time', models.DateTimeField(blank=True, null=True, help_text='Tweet Posted Time')),
                ('location', models.CharField(help_text='Location', max_length=255)),
                ('campaign', models.ForeignKey(to='acquiresmartz.Campaign', related_name='target_user')),
            ],
        ),
        migrations.AddField(
            model_name='personalityinsight',
            name='target_user',
            field=models.OneToOneField(related_name='personality_insight', to='acquiresmartz.TargetUser'),
        ),
        migrations.AlterUniqueTogether(
            name='targetuser',
            unique_together=set([('twitter_id', 'campaign')]),
        ),
    ]
