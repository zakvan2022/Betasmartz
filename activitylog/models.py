from django.db import models
from django.conf import settings


class ActivityLog(models.Model):
    name = models.CharField(max_length=100, unique=True)
    format_str = models.TextField()
    format_args = models.TextField(null=True,
                                   blank=True,
                                   help_text="Dotted '.' dictionary path into the event 'extra' field for each arg "
                                             "in the format_str. Each arg path separated by newline."
                                             "Eg. 'request.amount'")
    # Also has field 'events' from ActivityLogEvent


class ActivityLogEvent(models.Model):
    # Import event here so we have it within our activitylogevent.
    from .event import Event

    id = models.IntegerField(choices=Event.choices(), primary_key=True)
    # foreign key as one Activity Log formatter can cover multiple events.
    activity_log = models.ForeignKey(ActivityLog, related_name='events')

    @classmethod
    def get(cls, event: Event):
        # Import event here so we have it within our activitylogevent.
        from .event import Event

        ale = cls.objects.filter(id=event.value).first()
        if ale is not None:
            return ale

        if event == Event.GOAL_DIVIDEND_DISTRIBUTION:
            alog = ActivityLog.objects.create(name='Dividends',
                                              format_str='Dividend payment of {}{{}} into goal'.format(settings.SYSTEM_CURRENCY_SYMBOL),
                                              format_args='transaction.amount')
        elif event == Event.GOAL_DEPOSIT_EXECUTED:
            alog = ActivityLog.objects.create(name='Deposits',
                                              format_str='Deposit of {}{{}} from Account to Goal'.format(settings.SYSTEM_CURRENCY_SYMBOL),
                                              format_args='transaction.amount')
        elif event == Event.GOAL_WITHDRAWAL_EXECUTED:
            alog = ActivityLog.objects.create(name='Withdrawals',
                                              format_str='Withdrawal of {}{{}} from Goal to Account'.format(settings.SYSTEM_CURRENCY_SYMBOL),
                                              format_args='transaction.amount')
        elif event == Event.GOAL_REBALANCE_EXECUTED:
            alog = ActivityLog.objects.create(name='Rebalances', format_str='Rebalance Applied')
        elif event == Event.GOAL_TRANSFER_EXECUTED:
            alog = ActivityLog.objects.create(name='Transfer', format_str='Transfer Applied')
        elif event == Event.GOAL_FEE_LEVIED:
            alog = ActivityLog.objects.create(name='Fees',
                                              format_str='Fee of {}{{}} applied'.format(settings.SYSTEM_CURRENCY_SYMBOL),
                                              format_args='transaction.amount')
        elif event == Event.GOAL_ORDER_DISTRIBUTION:
            alog = ActivityLog.objects.create(name='Order Distribution Transaction', format_str='Order Distributed')
        elif event == Event.GOAL_BALANCE_CALCULATED:
            alog = ActivityLog.objects.create(name='Balance', format_str='Daily Balance')
        else:
            alog = ActivityLog.objects.create(name=event.name, format_str='DEFAULT_TEXT: {}'.format(event.name))

        return ActivityLogEvent.objects.create(id=event.value, activity_log=alog)
