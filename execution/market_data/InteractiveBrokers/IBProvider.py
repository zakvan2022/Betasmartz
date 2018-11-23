import logging
from ib.lib.logger import logger as basicConfig
from execution.market_data.BaseProvider import BaseProvider
from ib.ext.EWrapper import EWrapper
from ib.ext.EClientSocket import EClientSocket
from main.settings import IB_PROVIDER_CLIENT_ID, IB_HOST, IB_PORT
from ib.ext.Contract import Contract
from execution.data_structures.market_depth import SingleLevelMarketDepth
from functools import partial
from time import sleep

very_short_sleep = partial(sleep, 0.01)
short_sleep = partial(sleep, 1)
long_sleep = partial(sleep, 10)

logger = logging.getLogger('execution.IB_api')

class ReferenceWrapper(EWrapper):
    def __init__(self):
        basicConfig()
        self._market_depth_L1 = {}
        self._requests_finished = {}
        self._errors = {}


    def isError(self, id):
        return id in self._errors

    def getError(self, id):
        if id in self._errors:
            return self._errors[id]
        else:
            return None

    def isExecutionRequestFinished(self, requestId):
        return requestId in self._requests_finished

    def getMarketDepthL1(self, request_id):
        if not request_id in self._market_depth_L1:
            self._market_depth_L1[request_id] = SingleLevelMarketDepth()
        return self._market_depth_L1[request_id]

    def tickPrice(self, tickerId, field, price, canAutoExecute):
        logger.debug('tickPrice', vars())
        md_obj = self.getMarketDepthL1(tickerId)
        if field == 1:
            md_obj.bid = price
        elif field == 2:
            md_obj.ask = price

    def tickSize(self, tickerId, field, size):
        logger.debug('tickSize', vars())
        md_obj = self.getMarketDepthL1(tickerId)
        if field == 0:
            md_obj.bid_volume = size
        elif field == 3:
            md_obj.ask_volume = size

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

    def contractDetails(self, reqId, contractDetails):
        logger.debug('contractDetails', vars())

    def contractDetailsEnd(self, reqId):
        logger.debug('contractDetailsEnd', vars())

    def bondContractDetails(self, reqId, contractDetails):
        logger.debug('bondContractDetails', vars())

    def execDetails(self, reqId, contract, execution):
        logger.debug('execDetails', vars())

    def execDetailsEnd(self, reqId):
        logger.debug('execDetailsEnd', vars())

    def connectionClosed(self):
        logger.debug('connectionClosed', {})

    def error(self, id=None, errorCode=None, errorMsg=None):
        self._errors[id] = errorMsg
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

    def deltaNeutralValidation(self, reqId, underComp):
        logger.debug('deltaNeutralValidation', vars())

    def execDetailsEnd(self, reqId):
        logger.debug('execDetailsEnd', vars())

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
        self._requests_finished[reqId] = 'tickSnapshotEnd'

    def error_0(self, strval):
        logger.debug('error_0', vars())

    def error_1(self, id, errorCode, errorMsg):
        logger.debug('error_1', vars())

    def position(self, account, contract, pos, avgCost):
        logger.debug('position', vars())

    def positionEnd(self):
        logger.debug('positionEnd', vars())

    def accountSummary(self, reqId, account, tag, value, currency):
        logger.debug('accountSummary', vars())

    def accountSummaryEnd(self, reqId):
        logger.debug('accountSummaryEnd', vars())


class IBProvider(BaseProvider):
    def __init__(self):
        basicConfig()
        # These two variables are initialized in Connect method
        self._connection = None
        self._wrapper = None
        self._request_id = 0

    def connect(self):
        self._wrapper = ReferenceWrapper()
        self._connection = EClientSocket(self._wrapper)
        self._connection.eConnect(IB_HOST, IB_PORT, IB_PROVIDER_CLIENT_ID)

    def disconnect(self):
        if self._connection.isConnected():
            self._connection.eDisconnect()

    def _make_contract(self, symbol):
        contract = Contract()
        contract.m_symbol = symbol
        contract.m_secType = 'STK'
        contract.m_exchange = 'SMART'
        contract.m_primaryExch = 'SMART'
        contract.m_currency = 'USD'
        contract.m_localSymbol = symbol
        return contract

    def _get_next_request_id(self):
        self._request_id += 1
        return self._request_id
    def get_market_depth_L1(self, symbol):
        contract = self._make_contract(symbol)
        request_id = self._get_next_request_id()
        self._connection.reqMktData(request_id, contract, '', True)
        while not self._wrapper.isExecutionRequestFinished(request_id):
            err = self._wrapper.getError(request_id)
            if err is not None:
                raise Exception(err)
            very_short_sleep()
        return self._wrapper.getMarketDepthL1(request_id)
