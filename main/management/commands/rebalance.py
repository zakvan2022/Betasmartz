'''
Deciding when to rebalance:
 - A user can decide to "Rebalance Now". If the "Rebalance now" button is pressed. Make sure we display to the user
   what the estimated cost of the rebalance is and how it compares to the ATCS.
'''
import logging

import copy
import numpy as np
from django.core.management.base import BaseCommand
from django.db.models import Sum, F, Case, When, Value, FloatField
from django.utils import timezone

from collections import defaultdict
from datetime import timedelta, date, datetime
from execution.models import PositionLot, ExecutionRequest
from goal.models import GoalMetric, GoalSetting
from main import constants
from portfolios.algorithms.markowitz import markowitz_optimizer_3
from portfolios.calculation import get_instruments, \
    MIN_PORTFOLIO_PCT, calc_opt_inputs, create_portfolio_weights, create_portfolio_max_weights, INSTRUMENT_TABLE_EXPECTED_RETURN_LABEL
from portfolios.management.commands.measure_goals import get_risk_score
from portfolios.models import Ticker
from portfolios.providers.data.django import DataProviderDjango
from portfolios.providers.execution.abstract import Reason, ExecutionProviderAbstract
from portfolios.returns import get_return_history
logger = logging.getLogger('rebalance')

TAX_BRACKET_LESS1Y = 0.3
TAX_BRACKET_MORE1Y = 0.2
MAX_WEIGHT_SUM = 1.0001
SAFETY_MARGIN = 0.005 #used for buying - we use limit prices higher by 0.005 from the last recorded price
LOT_LOSS_TLH = 0.005 # loss incurred by tax lot that triggers tax harvesting
CORRELATION_LENGTH = 365 # number of days for calculation of correlation

def optimise_up(opt_inputs, min_weights, max_weights=None):
    """
    Reoptimise the portfolio adding appropriate constraints so there can be no removals from assets.
    :param opt_inputs: The basic optimisation inputs for this goal.
    :param min_weights: A dict from asset_id to new minimum weight.
    :return: weights - The new dict of weights, or None if impossible.
    """
    xs, lam, risk_profile, constraints, constraints_without_model, settings_instruments, settings_symbol_ixs, \
    lcovars, mu = opt_inputs

    pweights = create_portfolio_weights(settings_instruments['id'].values, min_weights=min_weights, abs_min=0)
    new_cons = constraints + [xs >= pweights]

    if max_weights is not None:
        mweights = create_portfolio_max_weights(settings_instruments['id'].values, max_weights=max_weights, abs_max=1)
        new_cons = new_cons + [xs <= mweights]

    weights, cost = markowitz_optimizer_3(xs, lcovars, lam, mu, new_cons)
    return dict(zip(settings_instruments['id'].values, weights)) if weights.any() else None


def get_setting_weights(settings):
    """
    Returns a dict of weights for each asset from the provided settings object.
    :param settings: The settings to use
    :return: dict from symbol to weight in that setting's portfoloio.
    """
    return {item.asset.id: item.weight for item in settings.get_portfolio_items_all()}


def get_position_weights(goal):
    """
    Returns a dict of weights for each asset held by a goal against the goal's total holdings.
    :param goal:
    :return: dict from symbol to current weight in that goal.
    """
    res = []
    total = 0.0
    for position in goal.get_positions_all():
        res.append((position['ticker_id'], position['quantity'] * position['price']))
        total += position.value
    return {tid: val/total for tid, val in res}


def get_held_weights(goal):
    """
    Returns a dict of weights for each asset held by a goal against the goal's available balance.
    We use the available balance, not the total held so we can automatically apply any unused cash if possible.
    :param goal:
    :return: dict from symbol to current weight in that goal.
    """
    avail = goal.available_balance
    return {pos['ticker_id']: (pos['quantity'] * pos['price'])/avail for pos in goal.get_positions_all()}


def metrics_changed(goal):
    """
    Return true if the metrics contributing to the goal have changed between the active_settings and the
    approved_settings in any aspect that contributes to new optimal distribution.
    :param goal:
    :return: Boolean (True if changed)
    """
    return goal.active_settings.metric_group.constraint_inputs() != goal.approved_settings.metric_group.constraint_inputs()


def build_positions(goal, weights, instruments):
    """
    Returns a set of positions corresponding to the given weights.
    :param goal:
    :param weights:
        An iterable of proportions of each instrument in the portfolio. Position matches instruments.
        The weights should be aligned to orderable quantities.
    :param instruments: Pandas DataFrame of instruments
    :return: A dict from asset id to qty.
    """
    # Establish the positions required for the new weights.
    res = {}
    idloc = instruments.columns.get_loc('id')
    ploc = instruments.columns.get_loc('price')
    avail = goal.available_balance
    for ix, weight in weights.items():
        if weight > MIN_PORTFOLIO_PCT:
            res[ix] = int(avail * weight / instruments[instruments.id == ix].price.values[0])

    # orderable quantitites will probably always be in single units of shares (ETFs).
    # TODO: Make sure we have landed very near to orderable quantities.
    # TODO: Make sure we are not out of drift now we have made the weights orderable.
    return res


def reduce_cash(volume, ticker, cash_available):
    amount_to_buy = (ticker.latest_tick * (1+SAFETY_MARGIN)) * volume
    if cash_available > amount_to_buy:
        cash_available -= amount_to_buy
    else:
        for v in range(volume + 1):
            amount_to_buy = (ticker.latest_tick * (1+SAFETY_MARGIN)) * v
            if cash_available > amount_to_buy:
                continue
            else:
                volume = max(v - 1, 0)
                amount_to_buy = (ticker.latest_tick * (1 + SAFETY_MARGIN)) * volume
                cash_available -= amount_to_buy
                break
    return cash_available, volume


def create_request(goal, new_positions, reason, execution_provider, data_provider, allowed_side):
    # be smarter - do it proportionatelly

    """
    Create a MarketOrderRequest for the position changes that will take the goal's existing positions to the new
    positions specified.
    :param goal:
    :param positions: A dict from asset id to position
    :param reason: The reason for a change to these positions.
    :return: A MarketOrderRequest and the list of associated ExecutionRequests
    """

    order = execution_provider.create_market_order(account=goal.account)
    requests = []
    new_positions = copy.copy(new_positions)

    cash_available = goal.cash_balance

    # Change any existing positions
    positions = goal.get_positions_all()
    for position in positions:

        new_pos = new_positions.pop(position['ticker_id'], 0)

        volume = new_pos - position['quantity']

        ticker = data_provider.get_ticker(tid=position['ticker_id'])

        if allowed_side == 1:
            cash_available, volume = reduce_cash(volume, ticker, cash_available)

        if volume == 0 or np.sign(volume) != allowed_side:
            continue

        request = execution_provider.create_execution_request(reason=reason,
                                                              goal=goal,
                                                              asset=ticker,
                                                              volume=volume,
                                                              order=order,
                                                              limit_price=None)
        requests.append(request)

    # Any remaining new positions.
    for tid, pos in new_positions.items():
        ticker = data_provider.get_ticker(tid=tid)

        if allowed_side == 1:
            cash_available, volume = reduce_cash(pos, ticker, cash_available)

        if pos == 0 or np.sign(pos) != allowed_side:
            continue

        request = execution_provider.create_execution_request(reason=reason,
                                                              goal=goal,
                                                              asset=ticker,
                                                              volume=pos,
                                                              order=order,
                                                              limit_price=None)
        requests.append(request)

    return order, requests


def get_mix_drift(weights, constraints):
    '''
    :param weights:
    :param constraints:
    :return:
    '''
    # Get the risk score given the portfolio mix constraints.


def process_risk(weights, goal, idata, data_provider, execution_provider):
    """
    Checks if the weights are within our acceptable risk drift, and if not, perturbates to make it so.
    check difference in risk between held weights and weights - weights should be target? and if risk in held_weights
    different than in weights - perturbate_risk

    if difference big, start perturbating - decreasing/increasing risk of weights as needed

    we can increase risk by buying more of a risky asset, selling less risky asset
    but even if we start removing risky asset, total risk can increase due to correlation
    so this is iterative problem, not analytical


    :param weights:
    :param min_weights:
    :return: (changed,
    """
    risk_score = get_risk_score(goal, weights, idata, data_provider, execution_provider)
    metric = GoalMetric.objects\
        .filter(group__settings__goal_approved=goal)\
        .filter(type=GoalMetric.METRIC_TYPE_RISK_SCORE)\
        .first()

    level = metric.get_risk_level()
    #weights = perturbate_risk(goal=goal)
    return weights


def perturbate_risk(min_weights, removals, goal):
    position_lots = get_tax_lots(goal)

    # for each lot get information whether removing this lot would increase/decrease total portfolio risk
    # start removing lots that get our portfolio risk in right direction, starting from lowest tax lost
    # iterate until our risk == desired risk

    #get statistics for each lot - unit_risk (positive or negative number) calculated by removing position lot from portfolio
    # and seeing how much risk of the portfolio changes (increases or decreases)

    #multiply unit_risk with unit_tax_cost to arrive at number how quickly we get closer to desired risk - marginal tax_risk
    #prefer highest marginal tax_risk - start selling those first
    #if we need to increase risk - start selling negative tax_risks? - so always be selling as an adjustment?


def perturbate_withdrawal(goal):
    # start getting rid of lots in - by 1 share and always check if we are already in 100% weight
    position_lots = get_tax_lots(goal)
    desired_lots = position_lots[:]
    weights = get_weights(desired_lots, goal.available_balance)

    for lot in desired_lots:
        while lot['quantity'] > 0 and sum(weights.values()) > MAX_WEIGHT_SUM:
            lot['quantity'] -= 1
            lot['quantity'] = max(lot['quantity'], 0)
            weights = get_weights(desired_lots, goal.available_balance)
        if sum(weights.values()) <= MAX_WEIGHT_SUM:
            return weights


def get_tax_lots(goal):
    # probably we need to change this to order by ST loss, LT loss, LT gain, ST gain, but maybe this is more optimal even.
    '''
    returns position lots sorted by increasing unit tax cost for a given goal
    :param goal
    :return:
    '''
    order_by = ['LT_ST_gain_loss', 'unit_tax_cost']
    year_ago = timezone.now() - timedelta(days=366)
    position_lots = PositionLot.objects\
                    .filter(execution_distribution__transaction__from_goal=goal)\
                    .filter(quantity__gt=0)\
                    .annotate(price_entry=F('execution_distribution__execution__price'),
                              executed=F('execution_distribution__execution__executed'),
                              ticker_id=F('execution_distribution__execution__asset_id'),
                              price=F('execution_distribution__execution__asset__unit_price'))\
                    .annotate(tax_bracket=Case(
                      When(executed__gt=year_ago, then=Value(TAX_BRACKET_LESS1Y)),
                      When(executed__lte=year_ago, then=Value(TAX_BRACKET_MORE1Y)),
                      output_field=FloatField())) \
                    .annotate(unit_tax_cost=(F('price') - F('price_entry')) * F('tax_bracket')) \
                    .annotate(LT_ST_gain_loss=Case(
                      When(executed__gt=year_ago, unit_tax_cost__lte=0, then=Value(-2)),  #ST loss
                      When(executed__lte=year_ago, unit_tax_cost__lte=0, then=Value(-1)), #LT loss
                      When(executed__lte=year_ago, unit_tax_cost__gt=0, then=Value(1)),   #LT gain
                      When(executed__gt=year_ago, unit_tax_cost__gt=0, then=Value(2)),    #ST gain
                      output_field=FloatField()))\
                   .values('id', 'price_entry', 'quantity', 'executed', 'unit_tax_cost', 'ticker_id', 'price','LT_ST_gain_loss') \
                   .order_by(*order_by)
    return position_lots

def get_position_lots_by_tax_lot(ticker_id, current_price, goal_id):
    year_ago = timezone.now() - timedelta(days=366)
    position_lots = PositionLot.objects \
                    .filter(execution_distribution__execution__asset_id=ticker_id,
                            execution_distribution__execution_request__goal_id=goal_id)\
                    .filter(quantity__gt=0)\
                    .annotate(price_entry=F('execution_distribution__execution__price'),
                              executed=F('execution_distribution__execution__executed'),
                              ticker_id=F('execution_distribution__execution__asset_id'))\
                    .annotate(tax_bracket=Case(
                      When(executed__gt=year_ago, then=Value(TAX_BRACKET_LESS1Y)),
                      When(executed__lte=year_ago, then=Value(TAX_BRACKET_MORE1Y)),
                      output_field=FloatField())) \
                    .annotate(unit_tax_cost=(current_price - F('price_entry')) * F('tax_bracket')) \
                    .order_by('unit_tax_cost')
    return position_lots


def get_metric_tickers(metric_id):
    return GoalMetric.objects \
        .filter(type=GoalMetric.METRIC_TYPE_PORTFOLIO_MIX, id=metric_id) \
        .annotate(ticker_id=F('feature__assets__id')) \
        .values_list('ticker_id', flat=True) \
        .distinct()


def get_anti_metric_tickers(metric_id):
    return GoalMetric.objects \
        .filter(type=GoalMetric.METRIC_TYPE_PORTFOLIO_MIX) \
        .exclude(id=metric_id) \
        .annotate(ticker_id=F('feature__assets__id')) \
        .values_list('ticker_id', flat=True) \
        .distinct()


def perturbate_mix(goal, opt_inputs):
    """
                        order assets into groups of metrics constraints - compare with metrics constraints in settings
                        go into group with biggest difference - start selling assets from the group (from lowest tax loss further)
                        until sum of current assets in group == metric constraint for that group
                        try to find solution
                        repeat until solution found
    """
    position_lots = get_tax_lots(goal)
    metrics = GoalMetric.objects.\
        filter(group__settings__goal_approved=goal).\
        filter(type=GoalMetric.METRIC_TYPE_PORTFOLIO_MIX)

    assets_positive_drift = set()
    metric_tickers = defaultdict(set)
    for metric in metrics:
        if metric.comparison == GoalMetric.METRIC_COMPARISON_EXACTLY or \
                        metric.comparison == GoalMetric.METRIC_COMPARISON_MAXIMUM:
            metric_tickers[metric.id].update(get_metric_tickers(metric.id))
        else:
            metric_tickers[metric.id].update(get_anti_metric_tickers(metric.id))
            # minimum - we will use anti-group here

        measured_val = _get_measured_val(position_lots, metric_tickers[metric.id], goal)
        drift = _get_drift(measured_val, metric)

        if drift > 0:
            assets_positive_drift.update(metric_tickers[metric.id])

    desired_lots = position_lots[:]

    weights = None
    for l in desired_lots:
        if l['ticker_id'] not in assets_positive_drift:
            continue

        metrics = GoalMetric.objects.\
            filter(group__settings__goal_approved=goal).\
            filter(type=GoalMetric.METRIC_TYPE_PORTFOLIO_MIX).\
            filter(feature__assets__id=l['ticker_id'])

        for metric in metrics:
            _sell_due_to_drift(desired_lots, l['ticker_id'], goal, metric_tickers[metric.id], metric)

        try:
            weights = optimise_up(opt_inputs, get_weights(desired_lots, goal.available_balance))
        except:
            pass
        if weights is not None:
            return weights, get_weights(desired_lots, goal.available_balance)

    return weights, get_weights(desired_lots, goal.available_balance)


def get_weights(lots, available_balance):
    """
    Returns a dict of weights for each asset held by a goal against the goal's available balance.
    We use the available balance, not the total held so we can automatically apply any unused cash if possible.
    :param goal:
    :return: dict from symbol to current weight in that goal.
    """
    weights = defaultdict(float)
    for lot in lots:
        weights[lot['ticker_id']] += (lot['quantity'] * lot['price'])/available_balance
    return weights


def _get_measured_val(position_lots, metric_tickers, goal):
    """
    :param position_lots: list of tuples, where each tuple contains info for position lot ('id', 'price', 'quantity', 'executed', 'unit_tax_cost')
    :param metric_tickers: tickers to which given metric refers
    :param goal: Goal
    :return:
    The function duplicates GoalMetric.measured_val - but does all calculation on in-memory data structures
    """
    amount_shares = float(np.sum(
        [pos['price'] * pos['quantity'] if pos['ticker_id'] in metric_tickers else 0 for pos in position_lots]
    ))
    return amount_shares / goal.available_balance


def _get_drift(measured_val, goal_metric):
    """
    :param measured_val: measured_val from GoalMetric model
    :param goal_metric: GoalMetric
    :return:
    The function duplicates GoalMetric.get_drift - but does all calculation on in-memory measured_val
    """
    configured_val = goal_metric.configured_val
    if goal_metric.comparison == GoalMetric.METRIC_COMPARISON_MINIMUM:
        configured_val = 1 - configured_val

    if goal_metric.rebalance_type == GoalMetric.REBALANCE_TYPE_ABSOLUTE:
        return (measured_val - configured_val) / goal_metric.rebalance_thr
    else:
        return ((measured_val - configured_val) / goal_metric.configured_val) / goal_metric.rebalance_thr


def _sell_due_to_drift(position_lots, asset_id, goal, metric_tickers, metric):
    """
    Changes positions lots to bring drift <= 0 for the given metric
    :param position_lots: list of tuples, where each tuple contains info for position lot ('id', 'price', 'quantity', 'executed', 'unit_tax_cost')
    :param asset_ids: list of asset ids which belong to given metric
    :param goal: Goal
    :param metric_tickers: tickers to which metric refers
    :param goal metric
    :return: returns nothing, operates via position_lots, which is changed in place
    """

    measured_val = _get_measured_val(position_lots, metric_tickers, goal)
    drift = _get_drift(measured_val, metric)

    if drift <= 0:
        return

    for lot in position_lots:
        if not lot['ticker_id'] == asset_id:
            continue

        while drift > 0 and lot['quantity'] > 0:
            lot['quantity'] -= 1
            lot['quantity'] = max(lot['quantity'], 0)

            measured_val = _get_measured_val(position_lots, metric_tickers, goal)
            drift = _get_drift(measured_val, metric)

        if drift <= 0:
            break


def get_largest_min_weight_per_asset(held_weights, tax_weights):
    min_weights = dict()
    for w in held_weights.items():
        if w[0] in tax_weights:
            min_weights[w[0]] = max(float(tax_weights[w[0]]), float(w[1]))
        else:
            min_weights[w[0]] = float(w[1])
    return min_weights


def get_tax_max_weights(held_weights, tax_weights):
    max_weights = dict()
    for w in held_weights.items():
        if w[0] in tax_weights:
            max_weights[w[0]] = float(w[1])
    return max_weights

def perform_TLH(goal, data_provider, wash_sale):
    ticker_ids = get_held_weights(goal).keys()

    max_weights = dict()
    min_weights = dict()
    for ticker_id in ticker_ids:
        current_price = Ticker.objects.get(id=ticker_id).unit_price
        position_lots = get_position_lots_by_tax_lot(ticker_id, current_price, goal.id)

        max_weights[ticker_id] = get_held_weights(goal)[ticker_id] #sum lots weight

        for lot in position_lots:
            current_lot_weight = (current_price * lot.quantity)/goal.available_balance
            if lot.execution_distribution.execution.price > current_price and \
                    ((lot.execution_distribution.execution.price - current_price) * lot.quantity)/goal.available_balance > LOT_LOSS_TLH:
                max_weights[ticker_id] = max_weights[ticker_id] - current_lot_weight

        if max_weights[ticker_id] == get_held_weights(goal)[ticker_id]:
            max_weights.pop(ticker_id, None)

        if ticker_id in max_weights:
            tickers = get_tickers_with_same_specs(ticker_id)
            best_match = find_highest_correlated(ticker_id, tickers, data_provider)

            # fill in minimum weight for highly correlated asset - of same asset class, same specs (SRI, ), different index tracked, but respect 30-day wash-sale rule
            minimum_weight = get_held_weights(goal)[ticker_id]
            if best_match is not None and best_match not in wash_sale:
                min_weights[best_match] = minimum_weight

            # if no asset can be found - remove max_weight constraint
            if best_match is None:
                max_weights.pop(ticker_id, None)

    return min_weights, max_weights

def find_highest_correlated(ticker_id, tickers, data_provider):
    return_history, _ = get_return_history(tickers, data_provider.get_current_date() - timedelta(days=CORRELATION_LENGTH), data_provider.get_current_date())
    correlations = defaultdict(float)
    for t in return_history.columns:
        if t != ticker_id:
            correlations[t] = return_history[ticker_id].corr(return_history[t])

    if len(correlations) > 0:
        max_value = max(correlations, key=lambda key: correlations[key])
    else:
        max_value = None
    return max_value



def get_tickers_with_same_specs(ticker_id):
    ticker = Ticker.objects.get(id=ticker_id)
    # TODO need to add benchmark - different than actual ticker - i.e. benchmark!=ticker.benchmark
    tickers = Ticker.objects\
        .filter(asset_class=ticker.asset_class, ethical=ticker.ethical, state=Ticker.State.ACTIVE.value)
    return tickers


def unify_max_weights(max_weights):
    unified_weights = defaultdict(float)
    for w in max_weights:
        for key, value in w.items():
            if key in unified_weights and value < unified_weights[key]:
                pass
            else:
                unified_weights[key] = value
    return unified_weights

def unify_min_weights(min_weights):
    unified_weights = defaultdict(float)
    for w in min_weights:
        for key, value in w.items():
            if key in unified_weights and value > unified_weights[key]:
                pass
            else:
                unified_weights[key] = value
    return unified_weights

def perturbate(goal, idata, data_provider, execution_provider):
    """
    Jiggle the goal's holdings to fit within the current metrics
    :param goal: The goal who's current holding we want to perturbate to fit the current metrics on the active_settings.
    :returns: (weights, reason)
            - weights: The new weights to use for the goal's holdings that fit within the current constraints (drift_score < 0.25).
            - reason: The reason for the perturbation. (Deposit, Withdrawal or Drift)
    """
    # Optimise the portfolio adding appropriate constraints so there can be no removals from assets.
    # This will use any available cash to rebalance if possible.
    held_weights = get_held_weights(goal)

    # do not sell anything
    tax_min_weights = execution_provider.get_asset_weights_held_less_than1y(goal, data_provider.get_current_date())
    min_weights = held_weights
    tax_max_weights = execution_provider.get_assets_sold_less_30d_ago(goal, data_provider.get_current_date())

    min_TLH_weights = dict()
    max_TLH_weights = dict()
    if goal.account.tax_loss_harvesting_consent:
        min_TLH_weights, max_TLH_weights = perform_TLH(goal, data_provider, tax_max_weights)

    opt_inputs = calc_opt_inputs(goal.active_settings, idata, data_provider, execution_provider)
    xs, lam, risk_profile, constraints, constraints_without_model, settings_instruments, settings_symbol_ixs, lcovars, mu = opt_inputs

    tax_max_weights = unify_max_weights([tax_max_weights, max_TLH_weights])
    min_weights = unify_min_weights([min_weights, min_TLH_weights])
    weights = optimise_up(opt_inputs, min_weights, tax_max_weights)

    from portfolios.calculation import get_portfolio_weights, RISK_ALLOCATIONS_KFA, RISK_ALLOCATIONS_AON, RISK_ALLOCATIONS_LEE
    
    pp_type = goal.portfolio_set.portfolio_provider.type
    if pp_type == constants.PORTFOLIO_PROVIDER_TYPE_KRANE:
        weight_list = get_portfolio_weights(RISK_ALLOCATIONS_KFA, settings_instruments, risk_profile)
        weights = {id: w for id, w in zip(settings_instruments.id.values.tolist(), weight_list)}
    elif pp_type == constants.PORTFOLIO_PROVIDER_TYPE_AON:
        weight_list = get_portfolio_weights(RISK_ALLOCATIONS_AON, settings_instruments, risk_profile)
        weights = {id: w for id, w in zip(settings_instruments.id.values.tolist(), weight_list)}
    elif pp_type == constants.PORTFOLIO_PROVIDER_TYPE_LEE:
        weight_list = get_portfolio_weights(RISK_ALLOCATIONS_LEE, settings_instruments, risk_profile)
        weights = {id: w for id, w in zip(settings_instruments.id.values.tolist(), weight_list)}

    if weights is None:
        min_weights = execution_provider.get_asset_weights_without_tax_winners(goal=goal)
        tax_max_weights = execution_provider.get_assets_sold_less_30d_ago(goal, data_provider.get_current_date())

        min_TLH_weights = dict()
        max_TLH_weights = dict()
        if goal.account.tax_loss_harvesting_consent:
            min_TLH_weights, max_TLH_weights = perform_TLH(goal, data_provider, tax_max_weights)

        opt_inputs = calc_opt_inputs(goal.active_settings, idata, data_provider, execution_provider)
        tax_max_weights = unify_max_weights([tax_max_weights, max_TLH_weights])
        min_weights = unify_min_weights([min_weights, min_TLH_weights])

        weights = optimise_up(opt_inputs, min_weights, tax_max_weights)

    if weights is None:
        if sum(held_weights.values()) > MAX_WEIGHT_SUM:
            reason = Reason.WITHDRAWAL.value
            min_weights = perturbate_withdrawal(goal)
            weights = optimise_up(opt_inputs, min_weights)
        else:
            reason = Reason.DRIFT.value

    if weights is None:
        weights, min_weights = perturbate_mix(goal, opt_inputs)
        weights = optimise_up(opt_inputs, min_weights)
        new_weights = process_risk(weights, goal, idata, data_provider, execution_provider)
    else:
        # We got a satisfiable optimisation (mix metrics satisfied), now check and fix any risk drift.
        new_weights = process_risk(weights, goal, idata, data_provider, execution_provider)

        if new_weights == weights:
            reason = Reason.DEPOSIT.value
        else:
            reason = Reason.DRIFT.value
            weights = new_weights

    return weights, reason


def rebalance(goal, idata, data_provider, execution_provider):
    """
    Rebalance Strategy:
    :param goal: The goal to rebalance
    :param idata: The current instrument data
    :return:
    """
    # If our important metrics were changed, all attempts to perturbate the old holdings is avoided, and we simply
    # apply the new desired weights.
    optimal_weights = get_setting_weights(goal.approved_settings)
    if metrics_changed(goal):
        weights = optimal_weights
        reason = ExecutionRequest.Reason.METRIC_CHANGE.value
    else:
            
        # The important metrics weren't changed, so try and perturbate.
        weights, reason = perturbate(goal, idata, data_provider=data_provider, execution_provider=execution_provider)

        # TODO: check the difference in execution cost (including tax impact somehow) between optimal and weights,
        # TODO: use whichever better.

        # The algo should rebalance whenever the Expected Return on the rebalance is greater than the expected excecution cost

        #The expected return on the rebalancing should be: The cost of not being optimal (the utility cost function of
        #drift of the portfolio)
        #Normally it should be consistent with the optimizing function
        #Minimize(quad_form(x, sigma) - lam * mu * x)
        #So the proposed function will be :
        # markowitz_cost(diff of weights, other params)
        #SHould I take into account the building of the tax algo?, if so, how are the trades being stored? and where?

        #trades are stored in execution_provider.executions, which is a list, as ExecutionMock() or Execution() classes.

        #A goal is a portfolio? If the rebalance is being made by goal it could be inneficient from a cost perspective

    _, instruments, _ = idata

    # using limit prices - higher by treshold (e.g. 0.5%) than real market prices
    # update latest prices from instruments here - to be 0.5% higher than latest_tick

    return weights, instruments, reason


def archive_goal(goal):
    """
    This method should be called when the rebalance algo finds a goal in the CLOSING state.
    :param goal: The goal to process
    :return: ExecutionRequests??
    """

    # TODO: Build the execution requests to clear the positions if any.
    # TODO: Do the ordering along with all the ordering in the main rebalance loop.
    # TODO: Once we've received response from the market that the goal has no more positions,
    # TODO: complete the goal's archive process.
    # TODO: goal.complete_archive()


class Command(BaseCommand):
    help = 'Rebalances GoalSettings if they are are able to be rebalanced.'

    def handle(self, *args, **options):
        from portfolios.providers.execution.django import ExecutionProviderDjango
        data_provider = DataProviderDjango(timezone.now().date())
        execution_provider = ExecutionProviderDjango()
        idata = get_instruments(data_provider)
        for gs in GoalSetting.objects.all():
            if gs.can_rebalance:
                logger.info('Rebalancing goal %s' % gs.goal)
                rebalance(gs.goal, idata, data_provider, execution_provider)
