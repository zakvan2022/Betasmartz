from abc import abstractmethod

class AccountInfo(object):
    account = ""
    cash = 0
    currency = ""
    @abstractmethod
    def __init__(self):
        pass
