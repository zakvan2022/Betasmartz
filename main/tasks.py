from __future__ import absolute_import, unicode_literals
from .celery import app

@app.task
def send_plan_agreed_email_task(plan_id):
    """
    Send email to notify the plan is agreed along with the SOA attached.
    (called asynchronosly via Celery)
    """
    from retiresmartz.models import RetirementPlan
    RetirementPlan._send_plan_agreed_email(plan_id)

@app.task
def send_portfolio_report_email_to_advisors_task(liveportfolio_id):
    """
    Send email to advisors to notify the Portfolio is reported
    """
    from portfolios.models import LivePortfolio
    LivePortfolio._send_portfolio_report_email_to_advisors(liveportfolio_id)

@app.task
def send_portfolio_report_email_to_clients_task(liveportfolio_id):
    """
    Send email to advisors to notify the Portfolio is reported
    """
    from portfolios.models import LivePortfolio
    LivePortfolio._send_portfolio_report_email_to_clients(liveportfolio_id)

@app.task
def send_roa_generated_email_task(roa_id):
    """
    Send email to notify the client that advisor has created ROA
    (called asynchronosly via Celery)
    """
    from statements.models import RecordOfAdvice
    RecordOfAdvice._send_roa_generated_email(roa_id)
