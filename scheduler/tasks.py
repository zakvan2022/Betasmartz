from celery.task.schedules import crontab
from celery.decorators import periodic_task
from portfolios.models import LivePortfolio
from scheduler import utils


@periodic_task(
    run_every=(crontab(minute=0, hour='*/1'))
)
def send_live_portfolio_report():
    for lp in LivePortfolio.objects.all():
        schedule = lp.schedule
        if schedule is None:
            continue
        if utils.should_run_schedule(schedule):
            lp.send_portfolio_report_email_to_advisors()
            lp.send_portfolio_report_email_to_clients()
