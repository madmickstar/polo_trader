'''
Poloniex gets
 - get_current_tickers
 - get_orderbook
 - get_coin_balance
 - get_balances
 - get_open_orders
 - get_trade_ordernumber
 - get_trade_history

'''
import logging
from polo_tools import date_conversions


def get_current_tickers(polo, sell_coin, buy_coin):
    '''
    get current and calculate stats
    '''
    sell_coin_ticker = polo('returnTicker')[sell_coin]
    buy_coin_ticker = polo('returnTicker')[buy_coin]
    tickers_dict = {
        'formated_date': time.strftime("%Y%m%d-%H%M%S"),
        'cur_sell_coin_price': float(sell_coin_ticker['last']),
        'cur_buy_coin_price': float(buy_coin_ticker['last']),
    }
    return tickers_dict


def get_orderbook(polo, pair, order_type='bid'):
    '''
    retrieve orderbook and return list of dictionaries
    '''

    try:
        results = polo.returnOrderBook(currencyPair=pair)
        # same return {u'seq': 113346801, u'bids': [[u'0.82163798', u'2.43416207'], [u'0.82099275', u'73577.042']], u'isFrozen': u'0', u'asks': [[u'0.82496594', u'8520.057'], [u'0.82496595', u'3921.68897093']]
    except Exception as err:
        result_dict = {
            'result': False,
            'error': err,
        }
        return result_dict

    current_orders = []
    # first check the list returned is not empty
    if len(results) > 0:
        if order_type=='bid':
            for a in results['bids']:
                current_orders.append([a[0], a[1]])
        elif order_type=='ask':
            if int(results['isFrozen']) > 0:
                print('\n%s Asks order book is frozen  - value is %s' % (pair, results['isFrozen']))

            for a in results['asks']:
                current_orders.append([a[0], a[1]])

    if len(current_orders) < 0:
        result_dict = {
            'result': False,
            'error': 'No orders returned',
        }
    else:
        result_dict = {
            'result': current_orders,
            'error': False,
        }
    return result_dict


def get_balances(polo):
    '''
    retrieve available balances for all coin / wallets and return list of dictionaries
    '''

    try:
        results = polo.returnAvailableAccountBalances()
        # returns this {u'exchange': {u'XRP': u'67.47821979', u'STR': u'312.29382782'}}
        # or
        # [] when all funds are tied up in orders
    except Exception as err:
        result_dict = {
            'result': False,
            'error': err,
        }
        return result_dict

    avail_balances_lod = []
    # first check the list returned is not empty
    if len(results) > 0:
        # then check if there is any balances
        if len(results['exchange']) > 0:
            for a in results['exchange']:
                # this is what you need to grab - a, float(results['exchange'][a])))
                balance = {
                    'name': a,
                    'units': float(results['exchange'][a]),
                }
                avail_balances_lod.append(balance)
    result_dict = {
        'result': avail_balances_lod,
        'error': False,
    }
    return result_dict


def get_coin_balance(polo, coin):
    '''
    retrieve available balance for specific coin / wallet and return list of dictionaries
    '''
    #logger = logging.getLogger(__name__)
    try:
        results = polo.returnAvailableAccountBalances()
        # returns this {u'exchange': {u'XRP': u'67.47821979', u'STR': u'312.29382782'}}
        # or
        # [] when all funds are tied up in orders
    except Exception as err:
        #logger.error('get_coin_balance - Error getting balance for %s - %s' % (coin, err))
        result_dict = {
            'result': False,
            'error': err,
        }
        return result_dict
    coin_balance = False
    # first check the list returned is not empty
    if len(results) > 0:
        # then check if there is any balances
        if len(results['exchange']) > 0:
            for a in results['exchange']:
                #logger.debug a, results['exchange'][a]
                if coin == a:
                    #logger.debug('Found balance for %s %s' % (coin, results['exchange'][a]))
                    coin_balance = results['exchange'][a]
    result_dict = {
        'result': coin_balance,
        'error': False,
    }
    return result_dict


def get_open_orders(polo):
    #logger = logging.getLogger(__name__)
    try:
        open_orders = polo.returnOpenOrders()
        
        # sample return
        # {u'USDT_REP': [],
        # u'USDT_NXT': [{u'orderNumber': u'79088415541', u'margin': 0, u'amount': u'10.00000000', u'rate': u'0.90000000', u'date': u'2018-07-02 11:30:58', u'total': u'9.00000000', u'type': u'sell', u'startingAmount': u'10.00000000'}],
        # u'BTC_NEOS': [], u'BTC_OMG': [], etc.....
        # u'USDT_XRP': [{u'orderNumber': u'110198753065', u'margin': 0, u'amount': u'10.00000000', u'rate': u'5.00000000', u'date': u'2018-07-02 11:30:30', u'total': u'50.00000000', u'type': u'sell', u'startingAmount': u'10.00000000'}],
        # u'BTC_GAME': [], u'BTC_PPC': [], u'BTC_POT': [], u'USDT_STR': []}

    except Exception as err:
        #logger.error('get_open_orders - Could not get open orders - %s' % err)
        result_dict = {
            'result': False,
            'error': err,
        }
        return result_dict

    orders_found = False
    order_list = []
    order_sell_count = 0
    order_buy_count = 0

    for crypto_pair in open_orders:
        if len(open_orders[crypto_pair]) > 0:
            # process only crypto pairs with open orders
            orders_found = True
            for order in open_orders[crypto_pair]:
                # store all orders associated with crypto pair
                date_dict = date_conversions(order['date'])
                coin_dict = {
                   'coin_name': crypto_pair,
                   'type': order['type'],
                   'order_number': order['orderNumber'],
                   'amount': order['amount'],
                   'rate': order['rate'],
                   'total': order['total'],
                   'local_timestamp': date_dict['local_time_stamp'],
                   'local_epoch': date_dict['local_epoch'],
                }
                order_list.append(coin_dict)
                if coin_dict['type'] == "sell":
                    order_sell_count += 1
                if coin_dict['type'] == "buy":
                    order_buy_count += 1

    result_dict = {
        #'result': open_orders,
        'error': False,
        'orders_found': orders_found,
        'order_list': order_list,
        'order_sell_count': order_sell_count,
        'order_buy_count': order_buy_count,

    }
    return result_dict



def get_trade_ordernumber(polo, order_number):
    #logger = logging.getLogger(__name__)
    try:
        result = polo.returnOrderTrades(order_number)
        # returns [{u'fee': u'0.00250000', u'tradeID': 4531595, u'rate': u'1.99425517', u'amount': u'81.57964876', u'currencyPair': u'USDT_XRP', u'date': u'2018-01-13 23:54:17', u'total': u'162.69063630', u'type': u'buy', u'globalTradeID': 326319671}, {u'fee': u'0.00250000', u'tradeID': 4531594, u'rate': u'1.99425514', u'amount': u'88.54624458', u'currencyPair': u'USDT_XRP', u'date': u'2018-01-13 23:54:17', u'total': u'176.58380338', u'type': u'buy', u'globalTradeID': 326319670}]
        #for a in all_trades:
        #    print('%s %s %s %s %s %s %s %s %s %s' % (a['category'], a['fee'], a['tradeID'], a['orderNumber'], a['amount'], a['rate'], a['date'], a['total'], a['type'], a['globalTradeID']))
    except Exception as err:
        #logger.error('get_trade_ordernumber - Failed to get trade by order number - %s' % err)
        result_dict = {
            'result': False,
            'error': err,
        }
        return result_dict
    #if result:
    #    logger.debug('get_trade_ordernumber - %s %s' % (len(result), result))
    result_dict = {
        'result': result,
        'error': False,
    }
    return result_dict



def get_trade_history(polo, pair="USDT_XRP", start=None):
    #logger = logging.getLogger(__name__)
    try:
        result = polo.returnTradeHistory(pair, start)
        # returns
        # [{u'category': u'exchange', u'fee': u'0.00250000', u'tradeID': u'4789137', u'orderNumber': u'78301054693', u'amount': u'4.38083089', u'rate': u'1.39400000', u'date': u'2018-01-22 09:55:38', u'total': u'6.10687826', u'type': u'buy', u'globalTradeID': 333144146}, {u'category': u'exchange', u'fee': u'0.00250000', u'tradeID': u'4789026', u'orderNumber': u'78299981767', u'amount': u'98.32477678', u'rate': u'1.39500000', u'date': u'2018-01-22 09:46:45', u'total': u'137.16306360', u'type': u'buy', u'globalTradeID': 333139901}]

    except Exception as err:
        #logger.error('get_trade_history - Failed to get trade history - %s' % err)
        result_dict = {
            'result': False,
            'error': err,
        }
        return result_dict

    # cant figure why this is here, suspect copied from somewhere else
    # has no point because gets over written by code below
    result_dict = {
        'result': result,
        'error': False,
    }

    result_list = []
    for a in result:
        a['coin'] = pair
        result_list.append(a)

    result_dict = {
        'result': result_list,
        'error': False,
    }
    return result_dict
