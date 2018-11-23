from abc import abstractmethod
from execution.models import Order
from datetime import datetime, timedelta

class BaseBroker(object):
    def __init__(self):
        pass
    def create_order(self, price, quantity, ticker):
        side = Order.SideChoice.Buy.value if quantity > 0 else Order.SideChoice.Sell.value
        security = self.get_security(ticker.symbol)
        order = Order.objects.create(Price=price,
                                     Quantity=abs(quantity),
                                     SecurityId=security.symbol_id,
                                     Symbol=security.Symbol,
                                     Side=side,
                                     TimeInForce=6,
                                     ExpireDate=int((datetime.now() + timedelta(minutes=5)).timestamp()),
                                     ticker=ticker,
                                     Broker=type(self).__name__.replace("Broker",""))
        return order
    @abstractmethod
    def connect(self):
        pass
    @abstractmethod
    def disconnect(self):
        pass
    @abstractmethod
    def request_account_summary(self):
        pass
    @abstractmethod
    def send_order(self, order):
        pass
    def send_orders(self, orders):
        for order in orders:
            if order.Quantity==0:
                order.setFills(0,0)
            else:
                self.send_order(order)
        return orders
    @abstractmethod
    def update_orders(self, orders):
        pass
    @abstractmethod
    def get_security(self, symbol):
        pass
    @abstractmethod
    def send_pre_trade(self, trade_info):
        pass
    @abstractmethod
    def send_post_trade(self, trade_info):
        pass
    @abstractmethod
    def get_post_trade(self):
        pass
    @abstractmethod
    def cancel_order(self, orderid):
        pass
    @abstractmethod
    def get_account_info(self, broker_account):
        pass

