from abc import abstractmethod
class BaseProvider(object):
    def __init__(self):
        pass
    @abstractmethod
    def connect(self):
        pass
    @abstractmethod
    def disconnect(self):
        pass
    @abstractmethod
    def get_market_depth_L1(self, symbol):
        pass

