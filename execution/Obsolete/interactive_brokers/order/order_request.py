from django.db import models
import uuid

# order request serves to Ibroker - order_send function, this is to be defined for every order to be send
class IBOrderRequest(BaseOrderRequest):
    def GetOrder():
        return Order()

