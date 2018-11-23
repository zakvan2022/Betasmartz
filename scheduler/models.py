from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _
from jsonfield.fields import JSONField
from .constants import SCHEDULE_DELIVERY_CYCLE_CHOICES, SCHEDULE_DELIVERY_DAILY, \
                       SCHEDULE_TYPE_CHOICES, SCHEDULE_TYPE_LIVE_PORTFOLIO_REPORT, \
                       SCHEDULE_WEEKDAY_CHOICES
from .utils import should_run_schedule


class Schedule(models.Model):
    schedule_type = models.CharField(max_length=64,
                                    choices=SCHEDULE_TYPE_CHOICES,
                                    default=SCHEDULE_TYPE_LIVE_PORTFOLIO_REPORT)
    delivery_cycle = models.CharField(max_length=32,
                                      choices=SCHEDULE_DELIVERY_CYCLE_CHOICES,
                                      default=SCHEDULE_DELIVERY_DAILY)
    day = models.PositiveIntegerField(null=True, blank=True,
                                      help_text=_('Day of week (0 Mon - 6 Sun), or month (1 - 31), or quarter (1 - 90) based on delivery cycle'))
    time = models.TimeField(null=True, blank=True, help_text=_('Time'))
    timezone = models.CharField(max_length=32, default='UTC', help_text=_('ISO timezone name'))
    meta = JSONField(null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, db_index=True)
    object_id = models.PositiveIntegerField(db_index=True)
    owner = GenericForeignKey('content_type', 'object_id')

    class Meta:
        unique_together = ('content_type', 'object_id')

    def __str__(self):
        return 'Schedule for {}'.format(self.owner)

    def should_run_schedule(self):
        return should_run_schedule(self)


class SingleScheduleMixin(object):
    @cached_property
    def schedule(self):
        ctype = ContentType.objects.get_for_model(self.__class__)
        try:
            return Schedule.objects.get(content_type__pk = ctype.id, object_id=self.id)
        except:
            return None
