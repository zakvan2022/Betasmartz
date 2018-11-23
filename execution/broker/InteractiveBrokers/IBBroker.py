import logging
from execution.broker.BaseBroker import BaseBroker
from datetime import datetime
from functools import partial
from time import sleep

from execution.broker.InteractiveBrokers.IBSecurity import IBSecurity
from ib.lib.logger import logger as basicConfig
from ib.ext.EWrapper import EWrapper
from ib.ext.EClientSocket import EClientSocket
from ib.ext.ExecutionFilter import ExecutionFilter
from main.settings import IB_CLIENT_ID, IB_HOST, IB_PORT
from execution.broker.InteractiveBrokers.IBOrder import IBOrder
from execution.models import Order
from execution.data_structures.account_info import AccountInfo
very_short_sleep = partial(sleep, 0.01)
short_sleep = partial(sleep, 1)
long_sleep = partial(sleep, 10)

logger = logging.getLogger('execution.IB_api')

class ReferenceWrapper(EWrapper):
    def __init__(self):
        basicConfig()
        self._time_received_next_valid_order_id = datetime.min
        self._executions = {}
        self._account_info = {}
        self._requests_finished = {}
        self._errors = {}
        self._open_orders_end = {}
        self._max_request = False

    def getMaxRequestFailureError(self):
        if self._max_request:
            self._max_request = False
            return True
        else:
            return False

    def getAccountInfo(self, ib_account):
        return self._account_info[ib_account]

    def getExecutions(self, requestId):
        if requestId in self._executions:
            return self._executions[requestId]

    def isExecutionRequestFinished(self, requestId):
        return requestId in self._requests_finished

    def isOpeningOfOrdersFinished(self, orderId):
        return orderId in self._open_orders_end

    def isError(self, id):
        return id in self._errors

    def getError(self, id):
        if id in self._errors:
            return self._errors[id]
        else:
            return None

    def tickPrice(self, tickerId, field, price, canAutoExecute):
        logger.debug('tickPrice', vars())

    def tickSize(self, tickerId, field, size):
        logger.debug('tickSize', vars())

    def tickOptionComputation(self, tickerId, field, impliedVol, delta, optPrice, pvDividend, gamma, vega, theta,
                              undPrice):
        logger.debug('tickOptionComputation', vars())

    def tickGeneric(self, tickerId, tickType, value):
        logger.debug('tickGeneric', vars())

    def tickString(self, tickerId, tickType, value):
        logger.debug('tickString', vars())

    def tickEFP(self, tickerId, tickType, basisPoints, formattedBasisPoints, impliedFuture, holdDays, futureExpiry,
                dividendImpact, dividendsToExpiry):
        logger.debug('tickEFP', vars())

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId,
                    whyHeId):
        logger.debug('orderStatus', vars())

    def openOrder(self, orderId, contract, order, state):
        self._open_orders_end[orderId] = state
        logger.debug('openOrder', vars())

    def openOrderEnd(self):
        logger.debug('openOrderEnd', vars())

    def updateAccountValue(self, key, value, currency, accountName):
        logger.debug('updateAccountValue', vars())

    def updatePortfolio(self, contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL,
                        accountName):
        logger.debug('updatePortfolio', vars())

    def updateAccountTime(self, timeStamp):
        logger.debug('updateAccountTime', vars())

    def accountDownloadEnd(self, accountName):
        logger.debug('accountDownloadEnd', vars())

    def nextValidId(self, orderId):
        logger.debug('nextValidId', vars())
        self._next_valid_order_id = orderId
        self._time_received_next_valid_order_id = datetime.now()

    def contractDetails(self, reqId, contractDetails):
        logger.debug('contractDetails', vars())

    def contractDetailsEnd(self, reqId):
        logger.debug('contractDetailsEnd', vars())

    def bondContractDetails(self, reqId, contractDetails):
        logger.debug('bondContractDetails', vars())

    def execDetails(self, reqId, contract, execution):
        logger.debug('execDetails', vars())
        if reqId not in self._executions:
            self._executions[reqId] = []
        (self._executions[reqId]).append(execution)

    def execDetailsEnd(self, reqId):
        logger.debug('execDetailsEnd', vars())
        self._requests_finished[reqId] = 'Execution'

    def connectionClosed(self):
        logger.debug('connectionClosed', {})

    def error(self, id=None, errorCode=None, errorMsg=None):
        self._errors[id] = errorMsg
        if "Maximum number of account summary requests exceeded" in errorMsg:
            self._max_request = True
        print('error', vars())
        logger.error('error', vars())

    def error_0(self, strvalue=None):
        logger.error('error_0', vars())

    def error_1(self, id=None, errorCode=None, errorMsg=None):
        logger.error('error_1', vars())

    def updateMktDepth(self, tickerId, position, operation, side, price, size):
        logger.debug('updateMktDepth', vars())

    def updateMktDepthL2(self, tickerId, position, marketMaker, operation, side, price, size):
        logger.debug('updateMktDepthL2', vars())

    def updateNewsBulletin(self, msgId, msgType, message, origExchange):
        logger.debug('updateNewsBulletin', vars())

    def managedAccounts(self, accountsList):
        logger.debug('managedAccounts', vars())

    def receiveFA(self, faDataType, xml):
        logger.debug('receiveFA', vars())


    def historicalData(self, reqId, date, open, high, low, close, volume, count, WAP, hasGaps):
        logger.debug('historicalData', vars())

    def scannerParameters(self, xml):
        logger.debug('scannerParameters', vars())

    def scannerData(self, reqId, rank, contractDetails, distance, benchmark, projection, legsStr):
        logger.debug('scannerData', vars())

    def accountDownloadEnd(self, accountName):
        logger.debug('acountDownloadEnd', vars())

    def commissionReport(self, commissionReport):
        logger.debug('commissionReport', vars())

    def contractDetailsEnd(self, reqId):
        logger.debug('contractDetailsEnd', vars())

    def currentTime(self, time):
        logger.debug('currentTime', vars())
        self._current_time = datetime.fromtimestamp(time)

    def deltaNeutralValidation(self, reqId, underComp):
        logger.debug('deltaNeutralValidation', vars())


    def fundamentalData(self, reqId, data):
        logger.debug('fundamentalData', vars())

    def marketDataType(self, reqId, marketDataType):
        logger.debug('marketDataType', vars())

    def openOrderEnd(self):
        logger.debug('openOrderEnd', vars())

    def realtimeBar(self, reqId, time, open, high, low, close, volume, wap, count):
        logger.debug('realtimeBar', vars())

    def scannerDataEnd(self, reqId):
        logger.debug('scannerDataEnd', vars())

    def tickEFP(self, tickerId, tickType, basisPoints, formattedBasisPoints, impliedFuture, holdDays, futureExpiry,
                dividendImpact, dividendsToExpiry):
        logger.debug('tickEFP', vars())

    def tickGeneric(self, tickerId, tickType, value):
        logger.debug('tickGeneric', vars())

    def tickSnapshotEnd(self, reqId):
        logger.debug('tickSnapshotEnd', vars())

    def error_0(self, strval):
        logger.debug('error_0', vars())

    def error_1(self, id, errorCode, errorMsg):
        logger.debug('error_1', vars())

    def position(self, account, contract, pos, avgCost):
        logger.debug('position', vars())

    def positionEnd(self):
        logger.debug('positionEnd', vars())

    def accountSummary(self, reqId, account, tag, value, currency):
        if(tag == "TotalCashValue"):
            if account not in self._account_info:
                account_info = AccountInfo()
                self._account_info[account] = account_info
            self._account_info[account].acoount = account
            self._account_info[account].cash = float(value)
            self._account_info[account].currency = currency
        logger.debug('accountSummary', vars())

    def accountSummaryEnd(self, reqId):
        logger.debug('accountSummaryEnd', vars())
        self._requests_finished[reqId] = 'AccountSummary'


class IBBroker(BaseBroker):
    def __init__(self):
        basicConfig()
        # These two variables are initialized in Connect method
        self._connection = None
        self._wrapper = None
        self._request_id = 0

    def _get_next_request_id(self):
        self._request_id += 1
        return self._request_id

    def get_security(self, symbol):
        contract = IBSecurity()
        contract.Symbol = symbol
        contract.symbol_id = 0
        contract.Currency = 'USD'
        return contract

    def _get_next_valid_order_id(self):
        """
        You must assign a unique order ID to each order you place. IB's servers
        keep track of the next available order ID you can use; this function
        requests that value from IB's servers, waits until IB sends a response,
        then returns the ID.
        """
        last_time = self._wrapper._time_received_next_valid_order_id
        self._connection.reqIds(1)
        # Wait until IB sends the next valid ID
        while last_time == self._wrapper._time_received_next_valid_order_id:
            very_short_sleep()
        return self._wrapper._next_valid_order_id

    def _request_current_time(self):
        self._connection.reqCurrentTime()

    def connect(self):
        self._wrapper = ReferenceWrapper()
        self._connection = EClientSocket(self._wrapper)
        self._connection.eConnect(IB_HOST, IB_PORT, IB_CLIENT_ID)

    def disconnect(self):
        if self._connection.isConnected():
            self._connection.eDisconnect()

    def send_pre_trade(self, trade_info): # trade info is fa profile

        self._connection.requestFA(self._connection.PROFILES)
        self._connection.replaceFA(self._connection.PROFILES, trade_info)

    def send_order(self, order):
        order.__class__ = IBOrder # casting to IBOrder
        order.prepare_IB_order()
        order_id = self._get_next_valid_order_id()
        contract = self.get_security(order.Symbol)
        #order.m_transmit = True # forces IB to transmit order straight away
        self._connection.placeOrder(order_id, contract, order) # places order
        order.Status = Order.StatusChoice.Sent.value # order status is set to SENT
        order.Order_Id = order_id # sets broker specific ID
        while not self._wrapper.isOpeningOfOrdersFinished(order_id):
            err = self._wrapper.getError(order_id)
            if err is not None:
                raise Exception(err)
            very_short_sleep()
            #if(self._wrapper.isError(id)):
            #   raise Exception(self.wrapper.isError(id))

    def update_orders(self, orders):
        requestId = self._get_next_request_id()
        exf = ExecutionFilter()
        distribution = {}
        self._connection.reqExecutions(requestId, exf)  #
        while not self._wrapper.isExecutionRequestFinished(requestId):
            err = self._wrapper.getError(requestId)
            if err is not None:
                raise Exception(err)
            very_short_sleep()
        executions = self._wrapper.getExecutions(requestId)
        for order in orders:
            price = 0
            shares = 0
            if executions is not None:
                for execution in executions:
                    if execution.m_shares > 0 and execution.m_orderId == order.Order_Id and not execution.m_acctNumber.startswith('DF'):
                        price = execution.m_price
                        if order.Symbol not in distribution:
                            distribution[order.Symbol] = {}
                        if execution.m_acctNumber not in distribution[order.Symbol]:
                            distribution[order.Symbol][execution.m_acctNumber] = 0
                        distribution[order.Symbol][execution.m_acctNumber] += execution.m_shares
                        shares += execution.m_shares
                if price != 0:
                    order.setFills(price, shares)
        return distribution

    def get_account_info(self, broker_account):
        requestId = self._get_next_request_id()
        self._connection.reqAccountSummary(requestId, 'All', 'AccountType,TotalCashValue')
        while not self._wrapper.isExecutionRequestFinished(requestId):
            err = self._wrapper.getError(requestId)
            max_resp = self._wrapper.getMaxRequestFailureError()
            if err is not None:
                raise Exception(err)
            if max_resp:
                raise Exception("Maximum number of account summary requests exceeded")
            very_short_sleep()
        return self._wrapper.getAccountInfo(broker_account.ib_account)



       # long_sleep()

