from django.db import models
from common.structures import ChoiceEnum
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.deletion import CASCADE
from jsonfield.fields import JSONField
from datetime import datetime
from .ibm_watson import get_personality_insight_data

class Campaign(models.Model):
    class StatusCounts(ChoiceEnum):
        SC_ALL = ('', 'All')
        SC_0_50 = ('0,50', '< 50')
        SC_51_100 = ('51,100', '51-100')
        SC_101_250 = ('101,250', '101-250')
        SC_251_500 = ('251,500', '251-500')
        SC_501_1000 = ('501,1000', '501-1000')
        SC_1001 = ('1000', '> 1000')

    class FollowRanges(ChoiceEnum):
        FR_ALL = ('', 'All')
        FR_0_10 = ('0,10', '< 10')
        FR_11_25 = ('11,25', '11-25')
        FR_26_50 = ('26,50', '26-50')
        FR_51_100 = ('51,100', '51-100')
        FR_101_250 = ('101,250', '101-250')
        FR_250 = ('250', '> 250')

    class SentimentTypes(ChoiceEnum):
        ALL = ('', 'All')
        POSITIVE = ('positive', 'Positive')
        NEGATIVE = ('negative', 'Negative')
        NEUTRAL = ('neutral', 'Neutral')
        AMBIVALENT = ('ambivalent', 'Ambivalent')

    firm = models.ForeignKey('firm.Firm', related_name='campaign')
    title = models.CharField(max_length=255, help_text='Campaign Title')
    description = models.TextField(null=True, blank=True, help_text='Campaign description')
    search_term = models.CharField(max_length=255, help_text='Campaign search term')
    location = models.CharField(max_length=255, help_text='Campaign location')
    statuses_count = models.CharField(max_length=255, choices=StatusCounts.choices(), blank=True, null=True, help_text='Campaign location')
    following = models.CharField(max_length=20, choices=FollowRanges.choices(), blank=True, null=True, help_text='Campaign Following')
    followers = models.CharField(max_length=20, choices=FollowRanges.choices(), blank=True, null=True, help_text='Campaign Followers')
    sentiment = models.CharField(max_length=20, choices=SentimentTypes.choices(), blank=True, null=True, verbose_name='Tone', help_text='Campaign Sentiment/Tone')

class TargetUser(models.Model):
    campaign = models.ForeignKey(Campaign, related_name='target_user', db_index=True)
    twitter_id = models.BigIntegerField(help_text='Twitter User ID', db_index=True)
    twitter_username = models.CharField(max_length=255, help_text='Twitter Username')
    twitter_display_name = models.CharField(max_length=255, help_text='Twitter User Display Name')
    twitter_image = models.CharField(max_length=1000, help_text='Twitter Profile Image', null=True, blank=True)
    message = models.TextField(help_text='Tweet Message', null=True, blank=True)
    posted_time = models.DateTimeField(blank=True, null=True, help_text='Tweet Posted Time')
    location = models.CharField(max_length=255, help_text='Location')

    class Meta:
        unique_together = ('twitter_id', 'campaign')

    def get_personality_insight_data(self):
        should_refresh = False
        try:
            pi = self.personality_insight
            if (datetime.now() - pi.last_updated.replace(tzinfo=None)).days > 90 or pi.json_data is None:
                should_refresh = True
        except ObjectDoesNotExist:
            pi = PersonalityInsight(target_user=self)
            should_refresh = True

        if should_refresh:
            pi.json_data = get_personality_insight_data(self.twitter_id)
            pi.save()
        return pi.json_data


class PersonalityInsight(models.Model):
    target_user = models.OneToOneField('TargetUser', related_name='personality_insight', on_delete=CASCADE)
    json_data = JSONField()
    last_updated = models.DateTimeField(auto_now=True, help_text='Last updated date/time')
