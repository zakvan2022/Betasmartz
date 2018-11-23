from client.models import ClientAccount, IBAccount, APEXAccount
from execution.models import MarketOrderRequest, ExecutionRequest, Execution, ExecutionDistribution
from goal.models import Transaction
from portfolios.models import Ticker


def create_django_executions(order_fills, execution_allocations):
    '''
    :param order_fills: Order
    :param execution_allocations: AccountAllocations
    :return:
    '''
    for id in execution_allocations.keys():
        allocation_per_id = execution_allocations[id]

        for account_id in allocation_per_id.keys():
            if allocation_per_id[account_id].broker == "IB":
                account = IBAccount.objects.get(ib_account=account_id)
            elif allocation_per_id[account_id].broker == "Apex":
                account = APEXAccount.objects.get(apex_account=account_id)
            client_account = ClientAccount.objects.get(ib_account=account)

            mor = MarketOrderRequest.objects.get(account=client_account, state=MarketOrderRequest.State.APPROVED.value)

            ers = ExecutionRequest.objects.all().filter(order__account__ib_account__ib_account=account_id)
            allocation_per_ib_account = allocation_per_id[account_id]
            no_shares = allocation_per_ib_account.shares
            for e in ers:
                to_subtract = min(no_shares, e.volume)
                no_shares -= to_subtract
                ex1 = Execution.objects.create(asset=Ticker.objects.get(symbol=order_fills[id].Symbol),
                                               volume=to_subtract,
                                               order=mor,
                                               price=allocation_per_ib_account.price,
                                               amount=to_subtract * allocation_per_ib_account.price,
                                               executed=allocation_per_ib_account.time[-1])

                t1 = Transaction.objects.create(reason=Transaction.REASON_EXECUTION,
                                                to_goal=None,
                                                from_goal=e.goal,
                                                status=Transaction.STATUS_EXECUTED,
                                                executed=allocation_per_ib_account.time[-1],
                                                amount=to_subtract * allocation_per_ib_account.price)\

                ExecutionDistribution(execution=ex1, transaction=t1, volume=to_subtract)
                e.delete()

        #TODO get amount from IB - including transaction costs
