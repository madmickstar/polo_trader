'''
Poloniex sell and buy
 - sell_coins
 - buy_coins
 - move_order
 - cancel_order
'''
import logging


def sell_coins(polo, sell_coin, units=1, price=10):
    #logger = logging.getLogger(__name__)
    try:
        result = polo.sell(sell_coin, price, units)
        #returns the following when successful {u'orderNumber': u'76510476064', u'resultingTrades': []}
    except Exception as err:
        #logger.error('sell_coins - Could not fill sell order - %s' % err)
        result_dict = {
            'result': False,
            'error': err,
        }
        return result_dict
    #if result:
    #    #logger.debug('sell_coins - %s %s' % (len(result), result))
    #    for x in result['resultingTrades']:
    #        logger.debug('%s' %x)
    result_dict = {
        'result': result,
        'error': False,
    }
    return result_dict

    
def buy_coins(polo, buy_coin, units=1, price=0.01):
    #logger = logging.getLogger(__name__)
    try:
        result = polo.buy(buy_coin, price, units)
        # returns the following result
        # {u'orderNumber': u'49118215742', u'resultingTrades': [{u'tradeID': u'3412157', u'rate': u'0.45000002', u'amount': u'496.92718622', u'date': u'2018-01-16 08:34:23', u'total': u'223.61724373', u'type': u'buy'}]}
    except Exception as err:
        #logger.error('buying - buy_coins - Could not fill buy order - %s' % err)
        result_dict = {
            'result': False,
            'error': err,
        }
        return result_dict
    #if result:
    #    #logger.debug('buying - buy_coins - order results - %s' % result)
    #    #logger.debug('buying - buy_coins - number of trades - %s' % len(result['resultingTrades']))
    #    #for x in result['resultingTrades']:
    #    #    logger.debug('%s' % x)
    result_dict = {
        'result': result,
        'error': False,
    }
    return result_dict


'''
Have not used this yet in real trading
'''    
def move_order(polo, order_number, price=11):
    logger = logging.getLogger(__name__)
    try:
        result = polo.moveOrder(order_number, price)
        #returns the following when successful {u'orderNumber': u'76513392145', u'success': 1, u'resultingTrades': {u'USDT_XRP': []}}
    except Exception as err:
        logger.error('move_order - Could not move order - %s' % err)
        result_dict = {
            'result': False,
            'error': err,
        }
        return result_dict
    if result:
        logger.debug('move_order - %s %s' % (len(result), result))
        logger.debug('move_order - New order number %s Success %s ' % (result['orderNumber'], result['success']))
        for x in result['resultingTrades']:
            logger.debug('%s' %x)
    result_dict = {
        'result': result,
        'error': False,
    }
    return result_dict


'''
Have not used this yet in real trading
'''
def cancel_order(polo, order_number):
    logger = logging.getLogger(__name__)
    try:
        result = polo.cancelOrder(order_number)
        #returns the following when successful {u'amount': u'1.00000000', u'message': u'Order #76511345194 canceled.', u'success': 1}
        # returns exception = Could not cancel order for reason Invalid order number, or you are not the person who placed the order.
    except Exception as err:
        logger.error('cancel_order - Could not cancel order - %s' % err)
        result_dict = {
            'result': False,
            'error': err,
        }
        return result_dict
    if result:
        logger.debug('cancel_order - %s %s' % (len(result), result))
    result_dict = {
        'result': result,
        'error': False,
    }
    return result_dict
