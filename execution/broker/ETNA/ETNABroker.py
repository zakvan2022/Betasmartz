'''
https://wiki.etnasoft.com/display/DOCS/REST+API+Examples
https://wiki.etnasoft.com/display/DOCS/REST+API+Reference

http://docs.python-requests.org/en/master/user/quickstart/
https://ultimatedjango.com/blog/how-to-consume-rest-apis-with-django-python-reques/
https://realpython.com/blog/python/asynchronous-tasks-with-django-and-celery/
http://stackoverflow.com/questions/30259452/proper-way-to-consume-data-from-restful-api-in-django
'''
import logging
from datetime import timedelta

import requests
from django.utils import timezone
from rest_framework.renderers import JSONRenderer

from common.structures import ChoiceEnum
from execution.broker.BaseBroker import BaseBroker
from execution.broker.ETNA.ETNAOrder import ETNAOrder
from execution.exceptions import ETNAApiException
from execution.models import Order, ETNALogin, AccountId, Security
from execution.serializers import LoginSerializer, AccountIdSerializer, SecurityETNASerializer, OrderETNASerializer
from main.settings import ETNA_ENDPOINT_URL, ETNA_LOGIN, ETNA_PASSWORD, ETNA_X_API_KEY, ETNA_X_API_ROUTING, \
    CONTENT_TYPE

logger = logging.getLogger('execution.ETNA_api')

LOGIN_TIME = 10  # in minutes - after this we will assume we logged out and need to relog
DEVICE = 'ios'
VERSION = '3.00'

class ResponseCode(ChoiceEnum):
        Valid = 0,
        Invalid = -1  # no idea, just guess

class ETNABroker(BaseBroker):
    def __init__(self):
       pass
    def _get_header(self):
        header = dict()
        header['x-api-key'] = ETNA_X_API_KEY
        header['x-api-routing'] = ETNA_X_API_ROUTING
        header['Content-type'] = CONTENT_TYPE
        return header

    def _login(self):
        exception_text = 'error deserializing ETNA login response'
        body = '''{
        "device":"%s",
        "version": "%s",
        "login": "%s",
        "password": "%s"
        }''' % (DEVICE, VERSION, ETNA_LOGIN, ETNA_PASSWORD)
        url = ETNA_ENDPOINT_URL + '/login'
        r = requests.post(url=url, data=body, headers=self._get_header())
        response = r.json()
        serializer = LoginSerializer(data=response)
        if not serializer.is_valid():
            raise ETNAApiException(exception_text)
            logger.log(exception_text)
            return
        serializer.save()
        return serializer.validated_data['Ticket']

    def _get_current_login(self):
        qs = ETNALogin.objects.all()
        logins = qs.count()

        if logins == 0:
            self._login()
            self._get_current_login()

        latest_login = qs.latest('created')

        # we should test if we are logged in currently - we will use simple check,
        # if we logged in less than 10 minutes ago, we're all good
        if latest_login.created + timedelta(minutes=LOGIN_TIME) < timezone.now() \
                or latest_login.ResponseCode == ResponseCode.Invalid.value:
            self._logout(latest_login.Ticket)
            self._login()
            self._get_current_login()

        # logout any other valid logins but last
        logged_in = qs.filter(ResponseCode=ResponseCode.Valid.value).exclude(Ticket=latest_login.Ticket)
        for l in logged_in:
            self._logout(l.Ticket)

        return latest_login

    def _get_accounts_ETNA(self, ticket):
        exception_text = 'wrong ETNA account info'

        # we should only even call this model once, to find out ETNA Account ID,
        # and store it in local_settings as ETNA_ACCOUNT_ID
        url = ETNA_ENDPOINT_URL + '/get-accounts'
        body = '''{
            "ticket": "%s",
        }''' % ticket
        r = requests.post(url=url, data=body, headers=self._get_header())

        response = r.json()
        valid = self._validate_json_response(response, ETNAApiException(exception_text))
        if not valid:
            raise ETNAApiException(exception_text)
            logger.log(exception_text)
            return

        serializer = AccountIdSerializer(data=response)
        if not serializer.is_valid():
            raise ETNAApiException(exception_text)
            logger.log(exception_text)
            return
        serializer.save()
        return self._get_current_account_id()

    def _get_current_account_id(self):

        accountlist = AccountId.objects.filter(ResponseCode=ResponseCode.Valid.value)
        if accountlist.count()>0:
            account = accountlist.latest('created').Result[0]
        else:
            login_response = self._get_current_login()
            account = self._get_accounts_ETNA(login_response.Ticket)
        # it returns list for a given user, we will only ever have one account with ETNA
        return account

    def _validate_json_response(self, response, exception):
        correct = True

        if 'Result' not in response.keys():
            raise exception
            correct = False

        if response['ResponseCode'] != ResponseCode.Valid.value:
            raise exception
            correct = False

        return correct

    def _get_security_ETNA(self, symbol, ticket):
        exception_text = 'wrong ETNA security returned'
        url = ETNA_ENDPOINT_URL + '/securities/' + symbol

        header = self._get_header()
        header['ticket'] = ticket
        header['Accept'] = '/'

        r = requests.get(url=url, headers=header)

        response = r.json()

        valid = self._validate_json_response(response, ETNAApiException(exception_text))
        if not valid:
            raise ETNAApiException(exception_text)
            logger.log(exception_text)
            return

        response = response['Result']
        response['symbol_id'] = response['Id']  # ugly hack

        serializer = SecurityETNASerializer(data=response)
        if not serializer.is_valid():
            raise ETNAApiException(exception_text)
            logger.log(exception_text)
            return
        serializer.save()

    def get_security(self, symbol):
        qs = Security.objects.filter(Symbol=symbol)
        security = qs

        if security.count() == 0:
            login = self._get_current_login()
            self._get_security_ETNA(symbol, login.Ticket)

        return qs.latest('created')

# TODO To be deleted
#    def insert_order_ETNA(price, quantity, ticker):
#       side = Order.SideChoice.Buy.value if quantity > 0 else Order.SideChoice.Sell.value
#       etna_security = get_security(ticker.symbol)
#       order = Order.objects.create(Price=price,
#                                    Quantity=quantity,
#                                    SecurityId=etna_security.symbol_id,
#                                    Side=side,
#                                    TimeInForce=0,
#                                    ExpireDate=0,
#                                    ticker=ticker)
#       return order

    def send_order(self, order):
        exception_text = 'wrong ETNA trade info received'
        login_info = self._get_current_login()
        order.__class__ = ETNAOrder
        serializer = OrderETNASerializer(order)
        json_order = JSONRenderer().render(serializer.data).decode("utf-8")
        url = ETNA_ENDPOINT_URL + '/place-trade-order'
        body = '''{
        "ticket": "%s",
        "accountId": "%d",
        "order":
            %s
        }''' % (login_info.Ticket, self._get_current_account_id(), json_order)

        r = requests.post(url=url, data=body, headers=self._get_header())
        response = r.json()

        valid = self._validate_json_response(response, ETNAApiException(exception_text))
        if not valid:
            raise ETNAApiException(exception_text)
            logger.log(exception_text)
            return

        order.Order_Id = response['Result']

        order.Status = Order.StatusChoice.Sent.value
        order.save()
        return order


    def update_orders(self, orders):
        exception_text = 'Invalid ETNA order status response'
        login_info = self._get_current_login()
        url = ETNA_ENDPOINT_URL + '/get-order'
        for order in orders:
            body = '''{
                "ticket": "%s",
                "orderId": "%d"
                }''' % (login_info.Ticket, order.Order_Id)
            r = requests.post(url=url, data=body, headers=self._get_header())
            response = r.json()
            valid = self._validate_json_response(response, ETNAApiException(exception_text))
            if not valid:
                raise ETNAApiException(exception_text)
                logger.log(exception_text)
                return
            response = response['Result']
            order.FillPrice = response['AveragePrice']
            order.FillQuantity = response['ExecutedQuantity']
            order.Status = response['ExecutionStatus']
            order.Description = response['Description']
            order.save()
        return order

    def connect(self):
        self._login()

    def disconnect(self):
        self._logout(self._get_current_login().Ticket)

    def _logout(self, ticket):
        url = ETNA_ENDPOINT_URL + '/logout'
        body = '''{
        "ticket": "%s"
        }''' % ticket
        r = requests.post(url=url, data=body, headers=self._get_header())
        response = r.json()
        if response['ResponseCode'] == ResponseCode.Valid.value:
            self._set_logged_out(ticket)

    def _set_logged_out(self, ticket):
        login = ETNALogin.objects.get(Ticket=ticket)
        login.ResponseCode = ResponseCode.Invalid.value
        login.save()
