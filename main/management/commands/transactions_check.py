import logging
from django.utils import timezone
from goal.models import Transaction, RecurringTransaction, Goal
from django.core.management.base import BaseCommand
from main.stripe import execute_charge
from main.plaid import get_stripe_account_token
from dateutil.relativedelta import relativedelta


logger = logging.getLogger("main.management.commands.transactions_check")


def execute_recurring_transactions_today():
    # check if recurring transactions that are enabled need to be executed today
    recurring_transactions = RecurringTransaction.objects.filter(enabled=True).exclude(setting__goal_active__isnull=True)

    # create transaction and execute charge if schedule calls for recurring transaction
    for rt in recurring_transactions:
        logger.error(rt.id)
        if rt.setting.goal is not None:
            date_amount_tuple = rt.get_between(timezone.now() - relativedelta(days=1), timezone.now())
            if len(date_amount_tuple) > 0:
                logger.error(rt.account_id)
                # create transaction object for the charge
                transaction = Transaction.objects.create(to_goal=rt.setting.goal,
                                                         amount=rt.amount,
                                                         account_id=rt.account_id,
                                                         reason=Transaction.REASON_DEPOSIT)
                # check if goal is active
                if transaction.to_goal.state == Goal.State.ACTIVE.value:
                    # execute transaction through stripe if active
                    logger.info('Executing valid deposit request for RecurringTransaction %s from %s for %s' % (rt.id, transaction.to_goal.account.primary_owner.user, transaction.amount))
                    stripe_token = get_stripe_account_token(transaction.to_goal.account.primary_owner.user, transaction.account_id)
                    if stripe_token is None:
                        logger.error('Failed to retrieve stripe_token for %s' % transaction.to_goal.account.primary_owner.user)
                    else:
                        charge = execute_charge(transaction.amount, stripe_token)
                        transaction.stripe_id = charge.id
                        transaction.save()
                else:
                    logger.error('Transaction created by goal is not currently ACTIVE, transaction marked AWAITING APPROVAL')
                    transaction.status = Transaction.STATUS_AWAITING_APPROVAL
                    transaction.save()
        else:
            logger.error('RecurringTransaction setting goal is None, skipping.')


class Command(BaseCommand):
    help = 'Checks for RecurringTransaction objects that are enabled and need to have charges executed today.'

    def handle(self, *args, **options):
        execute_recurring_transactions_today()
