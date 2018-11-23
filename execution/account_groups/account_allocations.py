class Execution(object):
    def __init__(self, price, account, shares, time, order_id, broker):
        self.price = price
        self.account = account # should be account object
        self.shares = shares
        self.order_id = order_id
        self.time = [time]
        self.broker = broker


class AccountAllocations(object):
    '''
    Allocation holder - allocation of filled orders for each account
    '''
    def __init__(self):
        self.allocations = dict()

    def add_execution_allocation(self, execution):
        if execution.order_id not in self.allocations:
            self.allocations[execution.order_id] = dict()

        if execution.account not in self.allocations[execution.order_id]:
            self.allocations[execution.order_id][execution.account] = execution
            return

        existing_execution = self.allocations[execution.order_id][execution.account]

        avg_price = (existing_execution.price * existing_execution.shares +
                     execution.price * execution.shares) / \
                    (existing_execution.shares + execution.shares)

        existing_execution.price = avg_price
        existing_execution.shares += execution.shares
        existing_execution.time.extend(execution.time)
