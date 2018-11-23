from datetime import datetime, date, time, timedelta
from common.utils import get_tzinfo_by_name, get_quarter_begin_date
from .constants import SCHEDULE_DELIVERY_DAILY, SCHEDULE_DELIVERY_WEEKLY, \
    SCHEDULE_DELIVERY_MONTHLY, SCHEDULE_DELIVERY_QUARTERLY
import pytz


MIN_DELTA_THRESHOLD = timedelta(0)
MAX_DELTA_THRESHOLD = timedelta(hours=1)


def combine_with_timezone(dt, naive_time, timezone):
    return datetime.combine(dt, naive_time).replace(tzinfo=get_tzinfo_by_name(timezone))


def is_in_threshold(delta):
    return delta < MAX_DELTA_THRESHOLD and delta >= MIN_DELTA_THRESHOLD


def should_run_daily_schedule(schedule):
    desired_run_at = combine_with_timezone(datetime.today(), schedule.time, schedule.timezone)
    return is_in_threshold(datetime.now(pytz.utc) - desired_run_at)


def should_run_weekly_schedule(schedule):
    today = datetime.today()
    first_day_of_week = today - timedelta(days=today.weekday())
    scheduled_day = first_day_of_week + timedelta(days=schedule.day or 0)
    desired_run_at = combine_with_timezone(scheduled_day, schedule.time, schedule.timezone)
    return is_in_threshold(datetime.now(pytz.utc) - desired_run_at)


def should_run_monthly_schedule(schedule):
    today = datetime.today()
    desired_date = today - timedelta(days=today.day) + timedelta(days=schedule.day or 1)
    desired_run_at = combine_with_timezone(desired_date, schedule.time, schedule.timezone)
    return is_in_threshold(datetime.now(pytz.utc) - desired_run_at)


def should_run_quarterly_schedule(schedule):
    first_day_of_quarter = get_quarter_begin_date()
    scheduled_day = first_day_of_quarter + timedelta(days=(schedule.day or 1) - 1)
    desired_run_at = combine_with_timezone(scheduled_day, schedule.time, schedule.timezone)
    return is_in_threshold(datetime.now(pytz.utc) - desired_run_at)


def should_run_schedule(schedule):
    if schedule.delivery_cycle == SCHEDULE_DELIVERY_DAILY:
        return should_run_daily_schedule(schedule)
    elif schedule.delivery_cycle == SCHEDULE_DELIVERY_WEEKLY:
        return should_run_weekly_schedule(schedule)
    elif schedule.delivery_cycle == SCHEDULE_DELIVERY_MONTHLY:
        return should_run_monthly_schedule(schedule)
    elif schedule.delivery_cycle == SCHEDULE_DELIVERY_QUARTERLY:
        return should_run_quarterly_schedule(schedule)
    else:
        return False
