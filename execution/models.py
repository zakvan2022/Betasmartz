from django.db import models
import logging
import uuid
from datetime import datetime
from django.db.models import PROTECT
from jsonfield.fields import JSONField
from common.structures import ChoiceEnum
from django.db.models.deletion import CASCADE, PROTECT, SET_NULL
from django.core.validators import MaxValueValidator, MinValueValidator, ValidationError
from django.db.models import F, Sum
from common.structures import ChoiceEnum
from .managers import PositionLotQuerySet, OrderManager


logger = logging.getLogger('execution.models')


class Order(models.Model):
    class OrderTypeChoice(ChoiceEnum):
        Market = 0
        Limit = 1

    class SideChoice(ChoiceEnum):
        Buy = 0
        Sell = 1

    class TimeInForceChoice(ChoiceEnum):
        Day = 0
        GoodTillCancel = 1
        AtTheOpening = 2
        ImmediateOrCancel = 3
        FillOrKill = 4
        GoodTillCrossing = 5
        GoodTillDate = 6

    class StatusChoice(ChoiceEnum):
        New = 'New'
        Sent = 'Sent'
        PartiallyFilled = 'PartiallyFilled'
        Filled = 'Filled'
        DoneForDay = 'DoneForDay'
        Canceled = 'Canceled'
        Replaced = 'Replaced'
        PendingCancel = 'PendingCancel'
        Stopped = 'Stopped'
        Rejected = 'Rejected'
        Suspended = 'Suspended'
        PendingNew = 'PendingNew'
        Calculated = 'Calculated'
        Expired = 'Expired'
        AcceptedForBidding = 'AcceptedForBidding'
        PendingReplace = 'PendingReplace'
        Error = 'Error'
        Archived = 'Archived'

        @classmethod
        def complete_statuses(cls):
            accessor = Order.StatusChoice
            return (accessor.Filled.value, accessor.DoneForDay.value, accessor.Canceled.value, accessor.Rejected.value,
                    accessor.Expired.value, accessor.Error.value)

    class FillInfo(ChoiceEnum):
        FILLED = 0 # entire quantity of order was filled
        PARTIALY_FILLED = 1 # less than entire quantity was filled, but > 0
        UNFILLED = 2 # 0 shares were transacted for this order
    Uid = uuid.uuid1()
    Price = models.FloatField()
    Exchange = models.CharField(default="Auto", max_length=128)
    TrailingLimitAmount = models.FloatField(default=0)
    AllOrNone = models.IntegerField(default=0)
    TrailingStopAmount = models.FloatField(default=0)
    Type = models.IntegerField(choices=OrderTypeChoice.choices(),default=OrderTypeChoice.Limit.value)
    Quantity = models.IntegerField()
    SecurityId = models.IntegerField()
    Symbol = models.CharField(default="Auto", max_length=128)
    Side = models.IntegerField(choices=SideChoice.choices())
    TimeInForce = models.IntegerField(choices=TimeInForceChoice.choices(), default=TimeInForceChoice.GoodTillDate.value)
    StopPrice = models.FloatField(default=0)
    ExpireDate = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True, db_index=True)

    # response fields
    # -1 not assigned - we will get order Id as response from REST and update it
    Order_Id = models.IntegerField(default=-1)
    Status = models.CharField(choices=StatusChoice.choices(), default=StatusChoice.New.value, max_length=128, db_index=True)
    FillPrice = models.FloatField(default=0)
    FillQuantity = models.IntegerField(default=0)
    Description = models.CharField(max_length=128)
    objects = OrderManager() # ability to filter based on this, property cannot be used to filter
    Broker = models.CharField(max_length=128) # contains identification of broker
    ticker = models.ForeignKey('portfolios.Ticker', related_name='Order', on_delete=PROTECT)
    fill_info = models.IntegerField(choices=FillInfo.choices(), default=FillInfo.UNFILLED.value)
    # also has field order_fills from ApexFill model

    @property
    def is_complete(self):
        return self.Status in self.StatusChoice.complete_statuses()

    def __str__(self):
        return "[{}] - {}".format(self.id, self.Status)

    def setFills(self, FillPrice, FillQuantity):
        self.FillPrice = FillPrice
        self.FillQuantity = FillQuantity
        self.fill_info = Order.FillInfo.FILLED.value if self.FillQuantity == self.Quantity else (Order.FillInfo.UNFILLED.value if self.FillQuantity == 0 else Order.FillInfo.PARTIALY_FILLED.value)
        self.fills.create(order=self, volume=FillQuantity, price=FillPrice, executed=datetime.now())

class ExecutionFill(models.Model):
    # one apex_fill may contribute to many ExecutionApexFills and many Executions
    fill = models.ForeignKey('Fill', related_name='execution_fill')
    execution = models.OneToOneField('Execution', related_name='execution_fill')


class Fill(models.Model):
    #apex_order = models.ForeignKey('ApexOrder', related_name='apex_fills')
    order = models.ForeignKey('Order', related_name='fills', default=None)
    volume = models.FloatField(help_text="Will be negative for a sell.")
    price = models.FloatField(help_text="Price for the fill.")
    executed = models.DateTimeField(help_text='The time the trade was executed.')
    # also has field 'execution_apex_fill' from model ExecutionApexFill


class MarketOrderRequestAPEX(models.Model):
    ticker = models.ForeignKey('portfolios.Ticker', related_name='morsAPEX', on_delete=PROTECT)
    #apex_order = models.ForeignKey('ApexOrder', related_name='morsAPEX')
    order = models.ForeignKey('Order', related_name='morsAPEX', default=None)
    market_order_request = models.ForeignKey('MarketOrderRequest', related_name='morsAPEX')

    class Meta:
        unique_together = ("ticker", "market_order_request")


class MarketOrderRequest(models.Model):
    """
    A Market Order Request defines a request for an order to buy or sell one or more assets on a market.
    It aggregates ExecutionRequests (each execution request is per goal per client) into a group of ExecutionRequests
    of various goals for single client
    """

    class State(ChoiceEnum):
        PENDING = 0  # Raised somehow, but not yet approved to send to market
        APPROVED = 1  # Approved to send to market, but not yet sent.
        SENT = 2  # Sent to the broker (at least partially outstanding).
        CANCEL_PENDING = 3  # Sent, but have also sent a cancel
        COMPLETE = 4  # May be fully or partially executed, but there is none left outstanding.

    # The list of Order states that are still considered open.
    OPEN_STATES = [State.PENDING.value, State.APPROVED.value, State.SENT.value]

    state = models.IntegerField(choices=State.choices(), default=State.PENDING.value)
    account = models.ForeignKey('client.ClientAccount', related_name='market_orders', on_delete=PROTECT)
    # Also has 'execution_requests' field showing all the requests that went into this one order.
    # Also has 'executions' once the request has had executions.
    # also has 'morsAPEX' from MarketOrderRequestAPEX

    def __str__(self):
        return "[{}] - {}".format(self.id, self.State(self.state).name)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.account.confirmed:
            raise ValidationError('Account is not verified.')
        return super(MarketOrderRequest, self).save(force_insert, force_update,
                                                    using, update_fields)


class ExecutionRequest(models.Model):
    """
    An execution request should be immutable. It should not be modified after creation. It can only be
    """
    class Reason(ChoiceEnum):
        DRIFT = 0  # The Request was made to neutralise drift on the goal
        WITHDRAWAL = 1  # The request was made because a withdrawal was requested from the goal.
        DEPOSIT = 2  # The request was made because a deposit was made to the goal
        METRIC_CHANGE = 3  # The request was made because the inputs to the optimiser were changed.

    reason = models.IntegerField(choices=Reason.choices())
    goal = models.ForeignKey('goal.Goal', related_name='execution_requests', on_delete=PROTECT)
    asset = models.ForeignKey('portfolios.Ticker', related_name='execution_requests', on_delete=PROTECT)
    volume = models.FloatField(help_text="Will be negative for a sell.")
    order = models.ForeignKey(MarketOrderRequest, related_name='execution_requests')
    # transaction can be null because once the request is complete, the transaction is removed.
    transaction = models.OneToOneField('goal.Transaction', related_name='execution_request', null=True)

    # also has field 'execution_distribution' from model ExecutionDistribution

    def __str__(self):
        return "[{}] - {}".format(self.asset.symbol, self.volume)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.order.account.confirmed:
            raise ValidationError('Account is not verified.')
        return super(ExecutionRequest, self).save(force_insert, force_update,
                                                  using, update_fields)


class Execution(models.Model):
    """
    - The time the execution was processed (The time the cash balance on the goal was updated) is the 'executed' time
      on the related transaction.
    """
    asset = models.ForeignKey('portfolios.Ticker', related_name='executions', on_delete=PROTECT)
    volume = models.FloatField(help_text="Will be negative for a sell.")
    order = models.ForeignKey(MarketOrderRequest, related_name='executions', on_delete=PROTECT)
    price = models.FloatField(help_text="The raw price paid/received per share. Not including fees etc.")
    executed = models.DateTimeField(help_text='The time the trade was executed.')
    amount = models.FloatField(help_text="The realised amount that was transferred into the account (specified on the "
                                         "order) taking into account external fees etc.")
    # Also has field 'distributions' from the ExecutionDistribution model describing to what goals this execution was
    # distributed

    # also has field 'execution_apex_fill' from model ExecutionApexFill to map execution to ApexFill via
    # ExecutionApexFill

    def __str__(self):
        return '{}|{}|{}|{}@{}'.format(self.id, self.executed, self.asset, self.volume, self.price)


class ExecutionDistribution(models.Model):
    # One execution can contribute to many distributions.
    execution = models.ForeignKey('Execution', related_name='distributions', on_delete=PROTECT)
    transaction = models.OneToOneField('goal.Transaction', related_name='execution_distribution', on_delete=PROTECT)
    volume = models.FloatField(help_text="The number of units from the execution that were applied to the transaction.")
    execution_request = models.ForeignKey('ExecutionRequest', related_name='execution_distributions',blank=True,null=True)
    # also has field 'position_lot' from PositionLot model
    # also has field 'sold_lot' from Sale model
    # also has field 'bought_lot' from Sale model

    def __str__(self):
        return "{}|{}|{}".format(self.execution, self.transaction, self.volume)


class PositionLot(models.Model):
    # create on every buy
    execution_distribution = models.OneToOneField(ExecutionDistribution, related_name='position_lot')
    quantity = models.FloatField(null=True, blank=True, default=None)
    # quantity gets decreased on every sell, until it it zero, then delete the model

    objects = PositionLotQuerySet.as_manager()

    def __str__(self):
        return "{}|{}".format(self.execution_distribution, self.quantity)


class Sale(models.Model):
    # create on every sale
    sell_execution_distribution = models.ForeignKey(ExecutionDistribution, related_name='sold_lot')
    buy_execution_distribution = models.ForeignKey(ExecutionDistribution, related_name='bought_lot')
    quantity = models.FloatField(null=True, blank=True, default=None)


class ETNALogin(models.Model):
    # big caps due to serializer - response json
    ResponseCode = models.IntegerField(db_index=True)
    Ticket = models.CharField(max_length=521)
    Result = models.OneToOneField('LoginResult', related_name='ETNALogin')
    created = models.DateTimeField(auto_now_add=True, db_index=True)


class LoginResult(models.Model):
    SessionId = models.CharField(max_length=128)
    UserId = models.PositiveIntegerField()


class AccountId(models.Model):
    ResponseCode = models.IntegerField()
    Result = JSONField()
    created = models.DateTimeField(auto_now_add=True)


class Security(models.Model):
    symbol_id = models.IntegerField()
    Symbol = models.CharField(max_length=128)
    Description = models.CharField(max_length=128)
    Currency = models.CharField(max_length=20)
    Price = models.FloatField()
    created = models.DateTimeField(auto_now_add=True, db_index=True)
