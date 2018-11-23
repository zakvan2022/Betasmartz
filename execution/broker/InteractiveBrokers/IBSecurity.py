from execution.models import Security
from ib.ext.Contract import Contract

class IBSecurity(Contract, Security):
    def __init__(self):
        self.m_secType = 'STK'
        self.m_exchange = 'SMART'
        self.m_primaryExch = 'SMART'
        self.m_currency = 'USD'

    @property
    def m_symbol(self):
        return self.Symbol

    @m_symbol.setter
    def m_symbol(self, value):
        self.Symbol = value

    @property
    def m_localSymbol(self):
        return self.Symbol

    @m_localSymbol.setter
    def m_localSymbol(self, value):
        self.Symbol = value

    @property
    def m_currency(self):
        return self.Currency

    @m_currency.setter
    def m_currency(self, value):
        self.Currency = value
