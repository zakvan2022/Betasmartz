from execution.models import Order
from datetime import datetime
from ib.ext.Order import Order as IB_Order, Double, Integer
# IBOrder class inherits IBOrder type from ib.ext namespace, therefore functions
# for two purposes at ones
"""
This code explains what we do here.... shadowing IBOrder and linking it to model Order


from django.db import models
from django.conf import settings
from ib.lib import Double, Integer

#settings.configure()
# Django Model Order
class Order(object):
    def __init__(self):
        self.Price = models.FloatField()
# Order from package IBPy
class IBOrder(object):
    def __init__(self):
        self.m_lmtPrice = Double.MAX_VALUE
        self.m_auxPrice = Double.MAX_VALUE
        self.m_activeStartTime = self.EMPTY_STR
        self.m_activeStopTime = self.EMPTY_STR
# specific IB order for our use
class IBSOrder(Order, IBOrder):
    # Shadowing price as LMT price for use with IB
    @property
    def m_lmtPrice(self):
        return Double(self.Price)
    @m_lmtPrice.setter
    def m_lmtPrice(self, value):
        self.Price = float(value)

# We create Django model object assign price 100
x = Order()
x.Price = 100
# This is how we cast it when used in IBBroker class methods
x.__class__ = IBSOrder # we cast class as IBSOrder
# IB package can use our order as if being IBOrder as multiple inheritance and property based override allows it
# There is direct linkage to Price (++)
print(x.m_lmtPrice)
"""
class IBOrder(Order, IB_Order):

    def prepare_IB_order(self):
        self.m_lmtPrice = Double.MAX_VALUE
        self.m_auxPrice = Double.MAX_VALUE
        self.m_activeStartTime = self.EMPTY_STR
        self.m_activeStopTime = self.EMPTY_STR
        self.m_outsideRth = False
        self.m_openClose = "O"
        self.m_origin = self.CUSTOMER
        self.m_transmit = True
        self.m_designatedLocation = self.EMPTY_STR
        self.m_exemptCode = -1
        self.m_minQty = Integer.MAX_VALUE
        self.m_percentOffset = Double.MAX_VALUE
        self.m_nbboPriceCap = Double.MAX_VALUE
        self.m_optOutSmartRouting = False
        self.m_startingPrice = Double.MAX_VALUE
        self.m_stockRefPrice = Double.MAX_VALUE
        self.m_delta = Double.MAX_VALUE
        self.m_stockRangeLower = Double.MAX_VALUE
        self.m_stockRangeUpper = Double.MAX_VALUE
        self.m_volatility = Double.MAX_VALUE
        self.m_volatilityType = Integer.MAX_VALUE
        self.m_deltaNeutralOrderType = self.EMPTY_STR
        self.m_deltaNeutralAuxPrice = Double.MAX_VALUE
        self.m_deltaNeutralConId = 0
        self.m_deltaNeutralSettlingFirm = self.EMPTY_STR
        self.m_deltaNeutralClearingAccount = self.EMPTY_STR
        self.m_deltaNeutralClearingIntent = self.EMPTY_STR
        self.m_deltaNeutralOpenClose = self.EMPTY_STR
        self.m_deltaNeutralShortSale = False
        self.m_deltaNeutralShortSaleSlot = 0
        self.m_deltaNeutralDesignatedLocation = self.EMPTY_STR
        self.m_referencePriceType = Integer.MAX_VALUE
        self.m_trailStopPrice = Double.MAX_VALUE
        self.m_trailingPercent = Double.MAX_VALUE
        self.m_basisPoints = Double.MAX_VALUE
        self.m_basisPointsType = Integer.MAX_VALUE
        self.m_scaleInitLevelSize = Integer.MAX_VALUE
        self.m_scaleSubsLevelSize = Integer.MAX_VALUE
        self.m_scalePriceIncrement = Double.MAX_VALUE
        self.m_scalePriceAdjustValue = Double.MAX_VALUE
        self.m_scalePriceAdjustInterval = Integer.MAX_VALUE
        self.m_scaleProfitOffset = Double.MAX_VALUE
        self.m_scaleAutoReset = False
        self.m_scaleInitPosition = Integer.MAX_VALUE
        self.m_scaleInitFillQty = Integer.MAX_VALUE
        self.m_scaleRandomPercent = False
        self.m_scaleTable = self.EMPTY_STR
        self.m_whatIf = False
        self.m_notHeld = False

    _tif_map = {Order.TimeInForceChoice.Day: "DAY",
                Order.TimeInForceChoice.GoodTillCancel: "GTC",
                Order.TimeInForceChoice.AtTheOpening: None,
                Order.TimeInForceChoice.ImmediateOrCancel: "IOC",
                Order.TimeInForceChoice.FillOrKill: "FOK",
                Order.TimeInForceChoice.GoodTillCrossing: None,
                Order.TimeInForceChoice.GoodTillDate: "GTD"
                }

    @property
    def m_lmtPrice(self):
        return Double(self.Price)
    @m_lmtPrice.setter
    def m_lmtPrice(self, value):
        self.Price = float(self.Price)

    @property
    def m_totalQuantity(self):
        return self.Quantity
    @m_totalQuantity.setter
    def m_totalQuantity(self, value):
        self.Quantity = value

    @property
    def m_action(self):
        return "Buy" if self.Side==Order.SideChoice.Buy else "Sell"
    @m_action.setter
    def m_action(self, value):
        self.Side =   Order.SideChoice.Buy if value=="Buy" else Order.SideChoice.Sell

    @property
    def m_orderType(self):
        return "LMT"


    @property
    def m_tif(self):
        if Order.TimeInForceChoice(self.TimeInForce) not in self._tif_map:
            raise NotImplementedError('Time in force of this type ' + Order.TimeInForceChoice.to_str(self.TimeInForce))
        return  self._tif_map[Order.TimeInForceChoice(self.TimeInForce)]
    @m_tif.setter
    def m_tif(self, value):
        val = value  # context safe
        keys = [key for key, value in self._tif_map.items() if value == val]
        if keys.count() == 0:
            raise NotImplementedError('Time in force of this type ' + Order.TimeInForceChoice.to_str(self.TimeInForce))
        self.TimeInForce = keys[0]

    @property
    def m_goodTillDate(self):
        if self.ExpireDate == 0:
            return ""
        return datetime.fromtimestamp(self.ExpireDate).strftime('%Y%m%d %H:%M:%S %Z')  #  FORMAT: 20060505 08:00:00 {time zone}
    @m_goodTillDate.setter
    def m_goodTillDate(self, value):
        self.ExpireDate = int(datetime.strptime(value, '%Y%m%d %H:%M:%S %Z').timestamp())
