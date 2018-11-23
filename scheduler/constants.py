from datetime import time
from django.utils.translation import ugettext as _
import pytz

SCHEDULE_TYPE_LIVE_PORTFOLIO_REPORT = 'LIVE_PORTFOLIO_REPORT'

SCHEDULE_TYPE_CHOICES = (
    (SCHEDULE_TYPE_LIVE_PORTFOLIO_REPORT, _('Live Portfolio Report')),
)

SCHEDULE_DELIVERY_DAILY = 'DAILY'
SCHEDULE_DELIVERY_WEEKLY = 'WEEKLY'
SCHEDULE_DELIVERY_MONTHLY = 'MONTHLY'
SCHEDULE_DELIVERY_QUARTERLY = 'QUARTERLY'

SCHEDULE_DELIVERY_CYCLE_CHOICES = (
    (SCHEDULE_DELIVERY_DAILY, _('Daily')),
    (SCHEDULE_DELIVERY_WEEKLY, _('Weekly')),
    (SCHEDULE_DELIVERY_MONTHLY, _('Monthly')),
    (SCHEDULE_DELIVERY_QUARTERLY, _('Quarterly')),
)

SCHEDULE_MONDAY = 0
SCHEDULE_TUESDAY = 1
SCHEDULE_WEDNESDAY = 2
SCHEDULE_THURSDAY = 3
SCHEDULE_FRIDAY = 4
SCHEDULE_SATURDAY = 5
SCHEDULE_SUNDAY = 6

SCHEDULE_WEEKDAY_CHOICES = (
    (SCHEDULE_MONDAY, _('Monday')),
    (SCHEDULE_TUESDAY, _('Tuesday')),
    (SCHEDULE_WEDNESDAY, _('Wednesday')),
    (SCHEDULE_THURSDAY, _('Thursday')),
    (SCHEDULE_FRIDAY, _('Friday')),
    (SCHEDULE_SATURDAY, _('Saturday')),
    (SCHEDULE_SUNDAY, _('Sunday')),
)

SCHEDULE_HOUR_CHOICES = (
    (time(0, 0, 0), '00:00 AM'),
    (time(1, 0, 0), '01:00 AM'),
    (time(2, 0, 0), '02:00 AM'),
    (time(3, 0, 0), '03:00 AM'),
    (time(4, 0, 0), '04:00 AM'),
    (time(5, 0, 0), '05:00 AM'),
    (time(6, 0, 0), '06:00 AM'),
    (time(7, 0, 0), '07:00 AM'),
    (time(8, 0, 0), '08:00 AM'),
    (time(9, 0, 0), '09:00 AM'),
    (time(10, 0, 0), '10:00 AM'),
    (time(11, 0, 0), '11:00 AM'),
    (time(12, 0, 0), '12:00 PM'),
    (time(13, 0, 0), '01:00 PM'),
    (time(14, 0, 0), '02:00 PM'),
    (time(15, 0, 0), '03:00 PM'),
    (time(16, 0, 0), '04:00 PM'),
    (time(17, 0, 0), '05:00 PM'),
    (time(18, 0, 0), '06:00 PM'),
    (time(19, 0, 0), '07:00 PM'),
    (time(20, 0, 0), '08:00 PM'),
    (time(21, 0, 0), '09:00 PM'),
    (time(22, 0, 0), '10:00 PM'),
    (time(23, 0, 0), '11:00 PM'),
)

SCHEDULE_TIMEZONE_CHOICES = map(lambda timezone: (timezone, timezone), pytz.all_timezones)
