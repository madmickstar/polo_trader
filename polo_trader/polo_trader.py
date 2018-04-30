#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division

import sys, os
import json
import time
import logging
from argparse import ArgumentParser, RawTextHelpFormatter
import traceback

# from 3rd party
# pip install https://github.com/s4w3d0ff/python-poloniex/archive/v0.4.7.zip
from poloniex import Poloniex

# from local
from _version import __version__
import polo_tools
from polo_trader_profiling import ProfilePairs, JsonProfiles
from polo_gets import get_current_tickers, get_orderbook, get_coin_balance, get_balances
from polo_gets import get_open_orders, get_trade_ordernumber, get_trade_history
from polo_sell_buy import sell_coins, buy_coins, move_order, cancel_order


def process_cli():
    # processes cli arguments and usage guide
    parser = ArgumentParser(prog='polo_trader',
    description='''         Buy and sell on Poloniex exchange \n \
        trade between coins based on ratio
        ''',
    epilog='''Command line examples \n\n \
        ## Windows and POSIX Users ## \n \
        python polo_trade.py -s xrp -b str -tf 5 \n \
        python polo_trade.py -s xrp -b nxt -tf 5 \n \
        ''',
    formatter_class=RawTextHelpFormatter)
    parser.add_argument('-mf', '--max-fee',
        default='0.0025',
        type=float,
        metavar=('{0.0025, 0.0015}'),
        help='Maximum fee for trading, default is 0.25 = 0.0025')
    parser.add_argument('-s', '--sell',
        default='xrp',
        choices=['xrp', 'str', 'nxt', 'eth', 'btc'],
        metavar=('{str, xrp, nxt, eth, btc}'),
        help='Sell coin, default = xrp')
    parser.add_argument('-b', '--buy',
        default='str',
        choices=['xrp', 'str', 'nxt', 'eth', 'btc'],
        metavar=('{str, xrp, nxt, eth, btc}'),
        help='Buy coin, default = str')
    parser.add_argument('-f', '--fiat',
        default='usdt',
        choices=['usdt', 'eth', 'btc'],
        metavar=('{usdt, eth, btc}'),
        help='Fiat coin, default = usdt')
    parser.add_argument('-tf', '--target-factor',
        default='10.0',
        type=float,
        choices=[0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0],
        metavar=('{0.5 1.0 .. 9.5 10.0}'),
        help='Target factor, default = 10.0')
    parser.add_argument('-ft', '--factor-threshold',
        default='2',
        type=int,
        choices=range(1, 10),
        metavar=('{1..10}'),
        help='Threshold to detect if sell and buy coins are around the wrong way, default = 2')
    parser.add_argument('-l', '--log',
        action="store_true",
        help='Enable logging to a file')
    parser.add_argument('-t', '--timestamp',
        action="store_true",
        help='Enable timestamping log output to console')
    parser.add_argument('-d', '--debug',
        action="store_true",
        help='Enable debug output to console')
    parser.add_argument('--version',
        action='version',
        version='%(prog)s v'+__version__)

    args = parser.parse_args()
    return args


class Whitelist(logging.Filter):

    def __init__(self, *whitelist):
        self.whitelist = [logging.Filter(name) for name in whitelist]

    def filter(self, record):
        return any(f.filter(record) for f in self.whitelist)
        


def configure_logging(args):
    """
    Creates logging configuration and sets logging level based on cli argument

    Args:
        args.debug: all arguments parsed from cli

    Returns:
        logging: logging configuration
    """
    if args.debug:
        logging.basicConfig(stream=sys.stdout,
                            #level=logging.INFO,
                            level=logging.DEBUG,
                            datefmt='%Y-%m-%d %H:%M:%S',
                            format='%(message)s')
                            #format='[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s')
        print_args(args)
    elif args.timestamp:
        logging.basicConfig(stream=sys.stdout,
                            level=logging.INFO,
                            datefmt='%Y-%m-%d %H:%M:%S',
                            format='[%(asctime)s] %(message)s')
    else:
        logging.basicConfig(stream=sys.stdout,
                            level=logging.INFO,
                            format='%(message)s')
    for handler in logging.root.handlers:
        handler.addFilter(Whitelist('__main__', 'polo_tools', 'polo_gets', 'polo_sell_buy'))
    return logging


    
def print_args(args):
    """
    Prints out cli arguments in nice format when debugging is enabled
    """
    logger = logging.getLogger(__name__)
    logger.debug('')
    logger.debug('CLI Arguments, %s', args)



def print_header(current_stats_dict, target_dict, factor_increasing):
    logger = logging.getLogger(__name__)
    date_stamp = current_stats_dict['date']
    date_formatted = (date_stamp[0:4] + "-" + date_stamp[4:6] + "-" + date_stamp[6:8]).center(10)
    sell_coin = current_stats_dict['sell_coin_short'].center(7)
    buy_coin = current_stats_dict['buy_coin_short'].center(28)
    #buy_coin = ("%s     Target = %s" % (current_stats_dict['buy_coin_short'], target_dict['name'])).center(28)
    #factor = ("%s     Target = %s" % ("Factor", target_dict['name'])).center(25)
    if factor_increasing:
        factor = "Factor    Upward".center(25)
    else:
        factor = "Factor    Downward".center(25)
    units = ("%s     Profit = %s%s" % ("Units", target_dict['name'],"%")).center(31)

    logger.info('---------------------------------------------------------------------------------------------------------------------')
    logger.info('| %s | %s | %s | %s | %s |' % (date_formatted, sell_coin, buy_coin, factor, units))
    logger.info('---------------------------------------------------------------------------------------------------------------------')



def print_some_results(factor_increasing, current_stats_dict, even_stats_dict, target_dict):
    '''
    print results to screen for review
    '''
    logger = logging.getLogger(__name__)
    time_stamp = current_stats_dict['date'][-6:]
    time_formatted = (time_stamp[0:2] + ":" + time_stamp[2:4] + ":" + time_stamp[4:6]).center(10)
    sell_coin = ("%7.4f" % current_stats_dict['sell_coin_price']).center(7)
    buy_coin = ("c%7.4f  e%7.4f  t%7.4f" % (current_stats_dict['buy_coin_price'], even_stats_dict['buy_coin_price'], target_dict['buy_coin_price'])).center(28)
    factor = ("c%6.3f  e%6.3f  t%6.3f" % (current_stats_dict['factor'], even_stats_dict['factor'], target_dict['factor'])).center(25)
    units = ("c%8.3f  e%8.3f  t%8.3f" % (current_stats_dict['buy_coin_units'], even_stats_dict['buy_coin_units'], target_dict['buy_coin_units'])).center(29)
    logger.info('| %s | %s | %s | %s | %s |' % (time_formatted, sell_coin, buy_coin, factor, units))



def print_orders(order_list):
    logger = logging.getLogger(__name__)
    # order_list looks like this
    # [{'local_epoch': 1516288337, 'amount': u'400.00000000', 'local_timestamp': '2018-01-18 15:12:17', 'order_number': u'77551204294', 'total': u'368.00000000', 'type': u'buy', 'rate': u'0.92000000', 'coin_name': 'USDT_XRP'}, {'local_epoch': 1516288379, 'amount': u'784.74689059', 'local_timestamp': '2018-01-18 15:12:59', 'order_number': u'49390422263', 'total': u'251.11900498', 'type': u'buy', 'rate': u'0.32000000', 'coin_name': 'USDT_STR'}, {'local_epoch': 1516283877, 'amount': u'299.55000000', 'local_timestamp': '2018-01-18 13:57:57', 'order_number': u'49385701988', 'total': u'164.75250000', 'type': u'sell', 'rate': u'0.55000000', 'coin_name': 'USDT_STR'}]
    logger.info('---------------------------------------------------------------------------------------------------------------------')
    logger.info('| %s | %s | %s | %s | %s | %s | %s |' % ("Coin".center(10), "Type".center(7), "Order".center(12), "Units".center(13), "Price".center(10), "Total".center(12), "Date".center(31)))
    logger.info('---------------------------------------------------------------------------------------------------------------------')

    for order in order_list:
        coin_name = order['coin_name'].center(10)
        type = order['type'].center(7)
        order_number = order['order_number'].center(12)
        amount = order['amount'].center(13)
        rate = order['rate'].center(10)
        total = order['total'].center(12)
        local_timestamp = order['local_timestamp'].center(31)
        logger.info('| %s | %s | %s | %s | %s | %s | %s |' % (coin_name, type, order_number, amount, rate, total, local_timestamp))



def print_balances(avail_balances_lod):
    '''
    print available balances
    '''
    logger = logging.getLogger(__name__)
    if len(avail_balances_lod) > 0:
        logger.info('---------------------------------------------------------------------------------------------------------------------')
        count = 0
        for a in avail_balances_lod:
            count += 1
            if count == 1:
                column_width = 19
            elif count == 2:
                column_width = 27
            elif count == 3:
                column_width = 23
            elif count == 3:
                column_width = 20
            coin_display = ('%s %8.8f' % (a['name'], a['units'])).center(column_width)
            if count >3:
                print('| %s |' % coin_display)
                count = 0
            else:
                print('| %s ' % coin_display),
        # resets the continue line trick above when finished looping
        if count > 0:
            print('')



def generate_test_trade_data(fsym):
    '''
    I use this for testing code logic
    '''
    if fsym.upper() == 'XRP':
        trading_status = {
            'trading': True,
            'type': "sell",
            'trading_complete': True,
            'flip_coins' : True,
            'sell_counter': 1,
            'sell_order_placed': True,
            'sell_order_number': "77893961194",
            'sell_coin_utc': 1516427432,
            'sell_coin_long': "USDT_XRP",
            'buy_coin_long': "USDT_STR",
            'buy_counter': 1,
            'buy_order_placed': True,
            'buy_order_number': "49590804680",
            'buy_coin_utc': 1516427501,
            'eval_counter': 0,
        }
    if fsym.upper() == 'STR':
        # sell STR buy XRP
        trading_status = {
            'trading': True,
            'type': "sell",
            'trading_complete': True,
            'flip_coins' : True,
            'sell_counter': 1,
            'sell_order_placed': True,
            'sell_coin_units': 328.04963136,
            'sell_order_number': "49853091131",
            'sell_coin_utc': 1516574788,
            'sell_coin_long': "USDT_STR",
            'buy_coin_long': "USDT_XRP",
            'buy_counter': 1,
            'buy_order_placed': True,
            'buy_order_number': "78299981767",
            'buy_coin_utc': 1516574792,
            'eval_counter': 0,
        }
    return trading_status



def calc_target(factor_increasing, trading_factor, even_stats_dict, current_stats_dict, lod_targets):
    '''
    evaluate if trade threshold has been met and start trading
    '''
    logger = logging.getLogger(__name__)
    # threshold list of factors to match against
    lol_factors_to_match = []
    for x in lod_targets:
         lol_factors_to_match.append([x['name'], x['buy_coin_price'], x['factor'], x['buy_coin_units']])

    current_factor = current_stats_dict['factor']

    target_dict = {
        'error': True,
    }

    for x in lol_factors_to_match:
        if float(trading_factor) in x:
            target_dict = {
                'name': x[0],
                'buy_coin_price': x[1],
                'factor': x[2],
                'buy_coin_units': x[3],
                'error': False,
            }
            #logger.debug("calc_target matched %s" % target_dict)
    return target_dict



def eval_trading(factor_increasing, trading_factor, even_stats_dict, current_stats_dict, lod_targets):
    '''
    evaluate if trade threshold has been met and start trading
    '''
    logger = logging.getLogger(__name__)
    # threshold list of factors to match against
    lol_factors_to_match = []
    ## manually add even
    #lol_factors_to_match.append([0, even_stats_dict['factor']])
    for x in lod_targets:
        #logger.debug('%s %s' % (x['name'], x['factor']))
        lol_factors_to_match.append([x['name'], x['factor']])

    current_factor = current_stats_dict['factor']

    for x in lol_factors_to_match:
        if float(trading_factor) in x:
            if factor_increasing:
                if current_factor > x[1]:
                    #logger.debug("eval_trading matched %s" % x[1])
                    return True
            else:
                if current_factor < x[1]:
                    return True
    return False



def check_factor_diff(factor_threshold, current_factor, even_factor):
     # checks if factor is difference is
     factor_factor = float(current_factor) / float(even_factor)
     if factor_factor > factor_threshold:
         return factor_factor
     else:
         return False



def generate_stats(current_stats_dict, even_stats_dict, units, trading_status):
    logger = logging.getLogger(__name__)
    if trading_status['type'] == "sell":
        x = "Selling"
    else:
        x = "Buying"
    #logger.debug('%s - ================= PURCHASE STATS ==========================' % x)
    ##logger.debug('%s - %s' % (x, purchase_stats_dict))
    #logger.debug('%s - %s Name %s Factor %s' % (x, purchase_stats_dict['date'], purchase_stats_dict['name'], purchase_stats_dict['factor']))
    #logger.debug('%s - %s Price %s Units %s' % (x, purchase_stats_dict['sell_coin_short'], purchase_stats_dict['buy_coin_price'], purchase_stats_dict['buy_coin_units']))
    #logger.debug('%s - %s Price %s Pair %s' % (x, purchase_stats_dict['buy_coin_short'], purchase_stats_dict['sell_coin_price'], purchase_stats_dict['buy_coin_long']))
    logger.debug('%s - ================== CURRENT STATS ==========================' % x)
    ##logger.debug('%s - %s' % (x, current_stats_dict))
    logger.debug('%s - %s Name %s Factor %s' % (x, current_stats_dict['date'], current_stats_dict['name'], current_stats_dict['factor']))
    logger.debug('%s - %s Price %s Units %s Pair %s' % (x, current_stats_dict['sell_coin_short'], current_stats_dict['sell_coin_price'], current_stats_dict['sell_coin_units'], current_stats_dict['sell_coin_long']))
    logger.debug('%s - %s Price %s Units %s Pair %s' % (x, current_stats_dict['buy_coin_short'], current_stats_dict['buy_coin_price'], current_stats_dict['buy_coin_units'], current_stats_dict['buy_coin_long']))
    logger.debug('%s - ================== EVEN STATS =============================' % x)
    #logger.debug('%s - %s' % (x, even_stats_dict))
    logger.debug('%s - %s Name %s Factor %s' % (x, even_stats_dict['date'], even_stats_dict['name'], even_stats_dict['factor']))
    logger.debug('%s - %s Price %s' % (x, even_stats_dict['sell_coin_short'], even_stats_dict['sell_coin_price']))
    logger.debug('%s - %s Price %s Units %s Pair %s' % (x, even_stats_dict['buy_coin_short'], even_stats_dict['buy_coin_price'], even_stats_dict['buy_coin_units'], even_stats_dict['buy_coin_long']))
    #logger.debug('Buying - ==================TARGETS================================')
    #logger.debug('Buying - %s' % lod_targets)
    logger.debug('%s - =========================================================' % x)
    buy_total_value = current_stats_dict['buy_coin_price'] * current_stats_dict['buy_coin_units']
    if trading_status['type'] == "sell":
        logger.debug('Selling - My balance says I have %s of %s to sell' % (units, current_stats_dict['sell_coin_short']))
        logger.debug('Selling - I am trying to sell %s of %s'  % (current_stats_dict['sell_coin_units'], current_stats_dict['sell_coin_short']))
        logger.debug('Selling - Selling %s units of %s at %s' % (current_stats_dict['sell_coin_units'], current_stats_dict['sell_coin_long'], current_stats_dict['sell_coin_price']))
    elif trading_status['type'] == "buy":
        logger.debug('Buying - My balance of %s is %s' % (trading_status['fiat'], units))
        logger.debug('Buying - My estimation of %s was %s' % (trading_status['fiat'], buy_total_value))
        logger.debug('Buying - Buying %s units of %s at %s' % (current_stats_dict['buy_coin_units'], current_stats_dict['buy_coin_long'], current_stats_dict['buy_coin_price']))
        #logger.debug('Buying - Time to buy, get order number and change status to buy once successfully sold')
        #logger.debug('Buying - reset buy counter')



def validate_trade_units(current_stats_dict, units, trading_status):
    '''
    units for sell are actual units to sell
    units for buy are the total fiat in wallet

    '''
    logger = logging.getLogger(__name__)
    if trading_status['type'] == "sell":
        units_to_sell = units
        # check if selling more than whats in wallet - correct if needed
        if float(current_stats_dict['sell_coin_units']) > float(units_to_sell):
            validated_units = float(units_to_sell)
            logger.error('Selling - Error - Selling more units than you have in wallet - try selling %s' % units_to_sell)
            logger.error('Selling - Error - You have less %s %s than your selling amount %s' % (current_stats_dict['sell_coin_short'], units_to_sell, current_stats_dict['sell_coin_units']))
            logger.debug('Selling - Corrected selling values %s %s %s' % (current_stats_dict['sell_coin_long'], validated_units, current_stats_dict['sell_coin_price']))
        else:
            validated_units = current_stats_dict['sell_coin_units']
    elif trading_status['type'] == "buy":
        wallet_total = units
        # check if purchase total is greater than whats in wallet - make adjustment if needed
        buy_total_value = current_stats_dict['buy_coin_price'] * current_stats_dict['buy_coin_units']
        logger.debug('Buying - buying total is %s %s and you have %s %s' % (buy_total_value, trading_status['fiat'], wallet_total, trading_status['fiat']))
        if float(buy_total_value) > float(wallet_total):
            validated_units = float(wallet_total) / float(current_stats_dict['buy_coin_price'])
            logger.error('Buying - Total %s %s estimated %s - changing buying values based on real %s total' % (trading_status['fiat'], wallet_total, buy_total_value, trading_status['fiat']))
            logger.debug('Buying - Corrected buying %s units of %s at %s due to balance being %s %s and estimated total was %s %s' % (validated_units, current_stats_dict['buy_coin_long'], current_stats_dict['buy_coin_price'], wallet_total, trading_status['fiat'], buy_total_value, trading_status['fiat']))
        else:
            # If purchase total is less than whats in wallet, chances are sell trade yielded more than expected
            # unless the extra funds were there before the trade, so to take caution, will only use extra funds if within
            # one percent of expected sell trade value
            buy_total_value_adjusted = float(buy_total_value) * 1.01
            # if value of wallet is below expected value with an extra one percent added - use it
            if float(wallet_total) < buy_total_value_adjusted:
                validated_units = float(wallet_total) / float(current_stats_dict['buy_coin_price'])
            else:
                validated_units = current_stats_dict['buy_coin_units']
    # return
    return round(validated_units, 8)



def evaluate_costs_and_units(polo, trading_status):
    '''
    Calculates sell and buy trade stats, amount of units, price per unit (ppu) and end vlaue after fees
    When selling, fees are subtracted from selling pair therefore the fiat
    When buying, fees are subtracted from the purchased coin
    '''
    logger = logging.getLogger(__name__)
    #logger.debug('')
    sell_order_stats = None
    buy_order_stats = None
    for order_number, pair, utc_start in ([trading_status['sell_order_number'], trading_status['sell_coin_long'], trading_status['sell_coin_utc']], [trading_status['buy_order_number'], trading_status['buy_coin_long'], trading_status['buy_coin_utc']]):
        unit_list = []
        total_list = []
        buy_unit_list = []
        final_list = []

        trade_history = get_trade_history(polo, pair, utc_start)
        if trade_history['error']:
            logger.error('Error grabbing trade history - %s' % trade_history['error'])
        else:
            for coin in trade_history['result']:
                #cycle through trades looking for matching order number
                if order_number in (coin['orderNumber'],):
                    # the calc is only good when selling coin - buy coin is different
                    if coin['type'] == "sell":
                        total_fiat = float(coin['total'])-(float(coin['total'])*float(coin['fee']))
                    else:
                        total_fiat = coin['total']
                    #print order_number, coin['coin'], coin['fee'], coin['amount'], coin['rate'], coin['total'], coin['type'], total_fiat
                    final_list.append([order_number, coin['coin'], coin['fee'], coin['amount'], coin['rate'], coin['total'], coin['type'], total_fiat])
            # if trades found get the stats
            if len(final_list) > 0:
                for trade in final_list:
                    unit_list.append(float(trade[3]))
                    total_list.append(float(trade[7]))
                    type = trade[6]
                    if trade[6] == "buy":
                        buy_unit_list.append(float(trade[3])-(float(trade[2])*float(trade[3])))
                    #print trade[6], float(trade[3]), float(trade[2]), float(trade[5]), float(trade[7])

                #logger.debug('Order number %s is a %s trade' % (order_number, type))
                if "sell" in (type,):
                    unit_total = sum(unit_list)
                else:
                    unit_total = sum(buy_unit_list)

                fiat_total = sum(total_list)
                per_unit = fiat_total / unit_total

                #logger.debug('Order Number %s Trade type %s for pair %s'% (order_number, type, pair))
                #logger.debug('Total value after fees %s' % round(fiat_total, 8))
                #logger.debug('Total units %s' % round(unit_total, 8))
                #logger.debug('Price per unit %s' % round(per_unit, 8))
                #logger.debug('Order Number %s Trade type %s for pair %s Units %s PPU %s Total %s' %(order_number, type, pair, round(per_unit, 8), round(unit_total, 8), round(fiat_total, 8)))
                #logger.debug('')
                if "sell" in (type,):
                    sell_order_stats = {
                        'order_number': order_number,
                        'type': type,
                        'pair': pair,
                        'ppu': round(per_unit, 8),
                        'unit_total': round(unit_total, 8),
                        'fiat_total': round(fiat_total, 8),
                    }
                else:
                    buy_order_stats = {
                        'order_number': order_number,
                        'type': type,
                        'pair': pair,
                        'ppu': round(per_unit, 8),
                        'unit_total': round(unit_total, 8),
                        'fiat_total': round(fiat_total, 8),
                    }
            else:
                logger.debug('No trade matching order number %s using UTC %s' % (order_number, utc_start))

    trading_status['trading_complete'] = False
    return trading_status, sell_order_stats, buy_order_stats



def trade_sell_now(polo, current_stats_dict, even_stats_dict, sell_units, trading_status, testing_status):
    logger = logging.getLogger(__name__)

    #logger.debug('Sell coin balance %s' % sell_units['result'])
    validated_units = validate_trade_units(current_stats_dict, sell_units['result'], trading_status)
    generate_stats(current_stats_dict, even_stats_dict, sell_units['result'], trading_status)
    trading_status['sell_coin_utc'] = (time.time() - 10)
    if testing_status:
        # this is a test trade
        rediculous_price = float(current_stats_dict['sell_coin_price']) * 10
        result_dict = sell_coins(polo, current_stats_dict['sell_coin_long'], 1, rediculous_price)  # testing
        logger.debug('Selling - Testing - sell trade sent, enabling buying')
        trading_status['type'] ="buy"
    else:
        # this is a real trade
        result_dict = sell_coins(polo, current_stats_dict['sell_coin_long'], validated_units, current_stats_dict['sell_coin_price'])  # real and tested

    if result_dict['result']:
        logger.debug('Selling - Order placed and order number %s assigned' % result_dict['result']['orderNumber'])
        trading_status['sell_counter'] = 0
        trading_status['sell_order_placed'] = True
        trading_status['sell_order_number'] = result_dict['result']['orderNumber']
    else:
        if "not enough" in result_dict['error']:
            logger.error('Selling - Error - tried to sell more %s than I own' % current_stats_dict['sell_coin_short'])
        else:
            logger.error('Selling - Sell order returned error %s ' % result_dict['error'])

    return trading_status



def trade_buy_now(polo, current_stats_dict, even_stats_dict, buy_units, trading_status, testing_status):

    logger = logging.getLogger(__name__)

    validated_units = validate_trade_units(current_stats_dict, buy_units['result'], trading_status)
    generate_stats(current_stats_dict, even_stats_dict, buy_units['result'], trading_status)
    trading_status['buy_coin_utc'] = (time.time() - 10)

    if testing_status:
        # this is a real trade with ridiculous price tag
        rediculous_price = float(current_stats_dict['buy_coin_price']) / 10
        test_units = int(1.5 / rediculous_price)
        if test_units < 1:
            test_units = 1
        result_dict = buy_coins(polo, current_stats_dict['buy_coin_long'], test_units, rediculous_price)   # testing
        logger.debug('Buying - Testing - buy order sent with values, pair %s, units %s, price %s' % (current_stats_dict['buy_coin_long'], test_units, rediculous_price))
    else:
        # this is a real trade with real price
        result_dict = buy_coins(polo, current_stats_dict['buy_coin_long'], validated_units, current_stats_dict['buy_coin_price'])  # real

    # process results
    if result_dict['result']:
        logger.debug('Buying - Order placed and order number %s assigned' % result_dict['result']['orderNumber'])
        trading_status['buy_counter'] = 0
        trading_status['buy_order_placed'] = True
        trading_status['buy_order_number'] = result_dict['result']['orderNumber']
    else:
        # if error detected
        if "not enough" in result_dict['error']:
            logger.error('Buying - Error - Tried to buy %s with not enough %s' % (current_stats_dict['buy_coin_short'], trading_status['fiat']))
        else:
            logger.error('Buying - Buy order returned error %s ' % result_dict['error'])

    return trading_status



def get_json_trades(status_json_file):
    logger = logging.getLogger(__name__)
    json_data = False
    ## Reading data back
    with open(status_json_file, 'r') as f:
         try:
             json_data = json.load(f)
         except ValueError as err:
             raise RuntimeError('JSON value error %s' % err)
         except Exception, err:
             raise RuntimeError('JSON unknown error %s' % err)
    return json_data



#def switch_buy_sell_around(trade_profile):
#    '''
#    switch around the buy and sell names only
#    '''
#    new_sell_long = trade_profile['buy_coin_long']
#    new_sell_short = trade_profile['buy_coin_short']
#    new_buy_long = trade_profile['sell_coin_long']
#    new_buy_short = trade_profile['sell_coin_short']
#    trade_profile['sell_coin_long'] = new_sell_long
#    trade_profile['sell_coin_short'] = new_sell_short
#    trade_profile['buy_coin_long'] = new_buy_long
#    trade_profile['buy_coin_short'] = new_buy_short
#    return trade_profile



def flippa_da_syms(pair_list):
    '''
    switch around the fsym and tsym
    '''
    logger = logging.getLogger(__name__)

    pairs = {
        'fsym': pair_list['tsym'],
        'fiat': pair_list['fiat'],
        'tsym': pair_list['fsym'],
    }
    logger.debug('')
    before = '{}_{}_{}'.format(pair_list['fsym'].upper(), pair_list['fiat'].upper(), pair_list['tsym'].upper())
    after = '{}_{}_{}'.format(pairs['fsym'].upper(), pairs['fiat'].upper(), pairs['tsym'].upper())
    logger.debug('Trade complete flip coin from %s to %s' % (before, after))
    return pairs



def print_trade_status(trading_status):
    logger = logging.getLogger(__name__)
    logger.debug('')
    logger.debug('Trading - =================  TRADE_STATUS  ==========================')
    logger.debug('Trading - Type %s - Complete %s - Flip Coins %s' % (trading_status['type'], trading_status['trading_complete'], trading_status['flip_coins']))
    logger.debug('Trading - Selling %s - Order Placed %s --- Buying %s - Order Placed %s' % (trading_status['sell_coin_long'], trading_status['sell_order_placed'], trading_status['buy_coin_long'], trading_status['buy_order_placed']))
    logger.debug('Trading - Selling UTC %s - O/N %s - Loop %s' % (trading_status['sell_coin_utc'], trading_status['sell_order_number'], trading_status['sell_counter']))
    logger.debug('Trading - Buying  UTC %s - O/N %s - Loop %s' % (trading_status['buy_coin_utc'], trading_status['buy_order_number'], trading_status['buy_counter']))



def print_json_trade_status(json_data):
    logger = logging.getLogger(__name__)
    logger.debug('JSON Trade Status - =================  JSON_TRADE_STATUS  ==========================')
    #logger.debug('JSON trade status %s', json_data)
    logger.debug('JSON Trade Status - Type %s - Complete %s - Flip Coins %s - Trading %s' % (json_data['type'], json_data['trading_complete'], json_data['flip_coins'], json_data['trading']))
    logger.debug('JSON Trade Status - Selling %s - Order Placed %s --- Buying %s - Order Placed %s' % (json_data['sell_coin_long'], json_data['sell_order_placed'], json_data['buy_coin_long'], json_data['buy_order_placed']))
    logger.debug('JSON Trade Status - Selling UTC %s - O/N %s - Loop %s' % (json_data['sell_coin_utc'], json_data['sell_order_number'], json_data['sell_counter']))
    logger.debug('JSON Trade Status - Buying  UTC %s - O/N %s - Loop %s' % (json_data['buy_coin_utc'], json_data['buy_order_number'], json_data['buy_counter']))



def print_json_trade_profile(json_data):
    logger = logging.getLogger(__name__)
    logger.debug('JSON Trade Profile - =================  JSON_TRADE_PROFILE  ==========================')
    #logger.debug('JSON trades profile %s', json_data)
    logger.debug('JSON Trade Profile - %s Price %s - Units %s - Pair %s' % (json_data['sell_coin_short'], json_data['pur_sell_coin_price'], json_data['pur_sell_coin_units'], json_data['sell_coin_long']))
    logger.debug('JSON Trade Profile - %s Price %s - Units %s - Pair %s' % (json_data['buy_coin_short'], json_data['pur_buy_coin_price'], json_data['pur_buy_coin_units'], json_data['buy_coin_long']))
    logger.debug('')



def get_ratio(f_units, to_units, ratio_to_match=1):
    '''
    Generates ratio of f_units and to_units - use ppu for calculating ratio
    If known ratio supplied, it will check if generated ratio matches
    '''
    ratio_to_match = float(ratio_to_match)
    ratio_to_match = round(ratio_to_match, 4)
    if f_units > to_units:
        tmp_ratio = f_units / to_units
    else:
        tmp_ratio = to_units / f_units
    result = {
        'ratio': round(tmp_ratio, 4),
        'match': False
    }
    if ratio_to_match == result['ratio']:
        result['match'] = True
    return result



def main():
    app_dir = '.polo_trade'
    working_dir = polo_tools.process_user_home_app_dir(app_dir)
    args = process_cli()

    # configure logging
    logging = configure_logging(args)
    logger = logging.getLogger(__name__)
    
    # confirm user has updated the config file
    try:
        import config
    except:
        logger.error('config.py not found in module dir, rename config.txt to config.py and edit api and private key')
        sys.exit(1)
    
    # targets maximum value
    max_target_value = 10

    # double fee because buying and selling attracts fees for both trades
    worst_trade_fee = args.max_fee * 2

    trading_factor = args.target_factor

    # create current trade pair list
    pair_list_curr = {
        'fsym': args.sell,
        'fiat': args.fiat,
        'tsym': args.buy
    }

    status_json_file = 'trade_status.json'
    trades_json_file = 'polo_trader_trades.json'
    log_file = 'polo_trade.log'

    try:
        trades_json_file, status_json_file, log_file, current_working_dir = polo_tools.permissions(working_dir, log_file, status_json_file, trades_json_file, pair_list_curr)
    except Exception, err:
        logger.error(str(err))
        sys.exit(1)

    # enable testing
    #testing_status = True
    testing_status = False
    if testing_status:
        trading_factor = 0.0

    # get json values
    try:
        trading_status = get_json_trades(status_json_file)
        #prof_dict = get_json_trades(trades_json_file)
    except Exception, err:
        logger.error(str(err))
        sys.exit(1)

    # initialise the poloniex querier
    polo = Poloniex()
    polo.key = config.api_key
    polo.secret = config.private_key

    # starting first trade so this needs to be set to true to trigger
    # grabbing the last trade details and profiling
    trading_status['flip_coins'] = True

    # this is the main loop
    header_counter = 20
    while True:
        '''
        if its the first time to loop or first time since completing a sell / buy trade
        it will hit this and flip the coins around and grab previous trade stats 
        '''
        if trading_status['flip_coins']:
        
            #prof_dict = switch_buy_sell_around(prof_dict)
            #trading_status['flip_coins'] = False
            #logger.debug('Starting trade coins flipped %s_%s_%s' % (pair_list_curr['fsym'], pair_list_curr['fiat'], pair_list_curr['tsym']))

            # grab JSON trades
            try:
                trade = JsonProfiles(trades_json_file, pair_list_curr, polo, worst_trade_fee)
            except Exception, err:
                traceback.print_exc()
                sys.exit(1)

            # get specific json data for trading pair
            prev_traded_details = trade.get_previous_trade_details()
            if prev_traded_details['error']:
                logger.error(prev_traded_details['result'])
                sys.exit()

            # check if not previous traded and if JSON had to be updated
            if trade.check_previously_traded():
                logger.warning('')
                logger.warning(trade.check_previously_traded())
                logger.warning('Updated JSON trades file with previous trade details using current order book values')
                logger.warning('Stopping script - you need to edit JSON values to match your target trade ratio and units')
                logger.warning('JSON file to edit %s', trades_json_file)
                sys.exit()

            # this is for debugging only
            #json_data_complete = trade.get_updated_json_data()
            #logger.debug('Full past trade details from JSON %s', json_data_complete)

            t = prev_traded_details['result']
            logger.debug('')
            logger.debug('Past trade sold %s units of %s at %s' % (t['fsym_units'], t['fsym_name_long'], t['fsym_price']))
            logger.debug('Past trade bought %s units of %s at %s' % (t['tsym_units'], t['tsym_name_long'], t['tsym_price']))
            logger.debug('Past trade ratio %s' % t['ratio'])
            
            # take previous traded details and update the current trade's details for profiling
            trading_pairs = {
                 'fsym_name_long': t['tsym_name_long'],
                 'fsym_name_short': t['tsym_name_short'],
                 'fsym_price': float(t['tsym_price']),
                 'fsym_units': float(t['tsym_units']),
                 'ratio': float(t['ratio']),
                 'tsym_name_long': t['fsym_name_long'],
                 'tsym_name_short': t['fsym_name_short'],
                 'tsym_price': float(t['fsym_price']),
                 'tsym_units': float(t['fsym_units']),
            }

            tp = trading_pairs
            logger.debug('Current trade selling %s units of %s at %s' % (tp['fsym_units'], tp['fsym_name_long'], tp['fsym_price']))           
            logger.debug('')
            
            # check if from units and to units are matching b/c if matching it
            # most likley means the JSON file for this pair was auto added to
            # JSON by script and not generated from a trade. User needs to update
            # JSON file for this pair
            if tp['fsym_units'] == tp['tsym_units']:
                logger.warning('')
                logger.warning('From units (fsym_units) and To units (tsym_units) are matching values, trades JSON requires manual update to continue')
                logger.warning('Change the to units (tsym_units) to the value of units you will be selling in next trade')
                #
                # this is not true yet b/c not using the ratio value just yet, plan to in the future
                #logger.warning('Update the ratio (ratio) to the target value you wish to trigger a sell / buy trade')
                logger.warning('Currently the ratio is based on the difference between fsym and tsym price, so to influence trading ratio, change the fsym or tsym price in JSON')
                logger.warning('In the future, the ratio in JSON will be used to control the next trade ratio')
                logger.warning('Increase ratio by decreasing the price of the cheaper coin or increasing the price of more expensive coin')
                logger.warning('Decrease ratio by increasing the price of the cheaper coin or decreasing the price of more expensive coin')
                sys.exit()
            
            # update trading status
            trading_status['sell_coin_long'] = tp['fsym_name_long']
            trading_status['buy_coin_long'] = tp['tsym_name_long']
            trading_status['fiat'] = pair_list_curr['fiat'].upper()
            # set flip coins to false so it does not hit this if statement until trading complete
            trading_status['flip_coins'] = False


        # profile the trading pair
        mycoins = ProfilePairs(polo, worst_trade_fee, trading_pairs)
        header_counter += 1

        try:
            purchase_stats_dict, current_stats_dict, even_stats_dict, lod_targets = mycoins.get_even_and_targets(max_target_value)
        except RuntimeError, err:
            logger.error(str(err))
        except Exception, err:
            traceback.print_exc()
            continue


        factor_increasing = mycoins.get_factor_direction(current_stats_dict['sell_coin_price'], current_stats_dict['buy_coin_price'])
        #logger.debug('checking factor direction %s %s result %s' % (current_stats_dict['sell_coin_price'], current_stats_dict['buy_coin_price'], factor_increasing))
        target_dict = calc_target(factor_increasing, trading_factor, even_stats_dict, current_stats_dict, lod_targets)
        
        
        try:
            if header_counter > 20:
                ''' print balances '''
                avail_balances_lod = get_balances(polo)
                if not avail_balances_lod['error']:
                    print_balances(avail_balances_lod['result'])
                else:
                    logger.error('Error getting balances - %s' % avail_balances_lod['error'])
                ''' print open orders '''
                open_orders_dict = get_open_orders(polo)
                if not open_orders_dict['error'] and open_orders_dict['orders_found']:
                    print_orders(open_orders_dict['order_list'])
                if open_orders_dict['error']:
                    logger.error('Grabbing open orders returned error - %s' % open_orders_dict['error'])
                ''' print column headers '''
                print_header(current_stats_dict, target_dict, factor_increasing)
                header_counter = 0
            ''' print results '''
            print_some_results(factor_increasing, current_stats_dict, even_stats_dict, target_dict)
        except IOError:
            ''' if user pauses screen or scrolls up catch and continue '''
            pass
        except Exception:
            raise

            
        '''
        Check ratio is not greater than factor_threshold
        '''
        factor_check = check_factor_diff(args.factor_threshold, current_stats_dict['factor'], even_stats_dict['factor'])
        if factor_check:
            sell_units = get_coin_balance(polo, current_stats_dict['sell_coin_short'])
            if not sell_units['error']:
                logger.warning('')
                logger.warning('Coin check - Selling coin %s wallet has %s' % (current_stats_dict['sell_coin_short'], sell_units['result']))
            else:
                logger.error('')
                logger.error('Coin check - %s' % sell_units['error'])

            buy_units = get_coin_balance(polo, current_stats_dict['buy_coin_short'])
            if not buy_units['error']:
                logger.warning('Coin check - Buy coin %s - wallet has %s' % (current_stats_dict['buy_coin_short'], buy_units['result']))
            else:
                logger.error('Coin check - %s' % buy_units['error'])

            logger.error('Coin check - Current factor is unexpectly higher than even factor by %s - suspect selling coin is around the wrong way' % factor_check)
            logger.error('Coin check - Probably need to swap around buy and sell coins')
            break


        '''
        Check if ready to start trading
        '''
        # check if orders have been placed
        if not trading_status['buy_order_placed'] and not trading_status['sell_order_placed']:
            # check if hit break even point, if over, evaluate how far over and if it matches target
            if factor_increasing:
                if current_stats_dict['factor'] > even_stats_dict['factor']:  
                    trading_status['trading'] = eval_trading(factor_increasing, trading_factor, even_stats_dict, current_stats_dict, lod_targets)
            else:
                if current_stats_dict['factor'] < even_stats_dict['factor']:  
                    trading_status['trading'] = eval_trading(factor_increasing, trading_factor, even_stats_dict, current_stats_dict, lod_targets)



        # debugging - can be removed later
        #print('trade status is %s' % trading_status['trading'])
        #trading_status['trading'] = False
        if trading_status['trading']:

            # this is for major debug option, not needed in future
            if args.debug:
                print_trade_status(trading_status)

            # check open orders
            # if it errors restart loop
            open_orders_dict = get_open_orders(polo)
            if open_orders_dict['error']:
                logger.error('Grabbing open orders returned error - %s' % open_orders_dict['error'])
                continue

            if trading_status['type'] == "sell":
                order_to_review = None
                # if found sell orders
                if open_orders_dict['order_sell_count'] > 0:
                    # and orders match last order number
                    for order in open_orders_dict['order_list']:
                        if trading_status['sell_order_number'] in (order['order_number'],):
                            order_to_review = order

                # if a current unfilled order is found
                if order_to_review is not None:
                    trading_status['sell_counter'] += 1
                    ## if loop threshold has been hit, take action
                    #if trading_status['sell_counter'] > 2:
                    #    logger.debug('Selling - Waiting for sell order to complete %s order needs to be sold using values or cancelled' % trading_status['sell_counter'])
                    #    # evaluate price versus target factor
                    #    # moveorder or cancel it
                    #    # detect half filled orders
                    #    # zero counter once updated
                    #    # trading_status['sell_counter'] = 0
                # else - there are no unfilled orders
                else:
                    # check if status is in order placed status and because no orders have been found
                    # it means selling is complete - change to buying
                    if trading_status['sell_order_placed']:
                        trading_status['type'] = "buy"
                        logger.debug('Selling - COMPLETE changing trading status to %s' % (trading_status['type']))
                    else:
                        sell_units = get_coin_balance(polo, current_stats_dict['sell_coin_short'])
                        # if there were errors
                        if sell_units['error']:
                            logger.error('Error retrieving balances, can not buy or sell')
                            logger.error('%s' % sell_units['error'])
                        else:
                            # if their no coins to sell
                            if float(sell_units['result']) < 1:
                                logger.error('Selling - Sell coin returned no units to sell, skipping sell')
                                trading_status['trading'] = False
                            else:
                                trading_status = trade_sell_now(polo, current_stats_dict, even_stats_dict, sell_units, trading_status, testing_status)


            if trading_status['type'] == "buy":
                order_to_review = None
                # if found buy orders
                if open_orders_dict['order_buy_count'] >0:
                    # and orders match last order number
                    for order in open_orders_dict['order_list']:
                        if trading_status['buy_order_number'] in (order['order_number'],):
                            order_to_review = order

                # if a current unfilled order is found
                if order_to_review is not None:
                    trading_status['buy_counter'] += 1
                    logger.debug('Buying - %s Found buy order matching order number %s' % (trading_status['buy_counter'], order['order_number']))
                    ## if loop threshold has been hit, take action
                    #if trading_status['buy_counter'] > 2:
                    #    logger.debug('Buying - order needs to be moved or cancelled')
                    #    # evaluate price versus target factor
                    #    # moveorder or cancel it
                    #    # detect half filled orders
                    #    # zero counter
                    #    trading_status['buy_counter'] = 0
                # else - there are no unfilled orders
                else:
                    # check if status is in order placed status and because no orders have been found
                    # it means buy is complete
                    if trading_status['buy_order_placed']:
                        trading_status['trading_complete'] = True
                        # eval does nothing at this point other than help skip the sell buy if statements
                        trading_status['type'] = "eval"
                        trading_status['eval_counter'] = 0
                        logger.debug('Buying - COMPLETE - Trading Status changed to %s' % (trading_status['type']))
                    else:
                        buy_units = get_coin_balance(polo, trading_status['fiat'])
                        if buy_units['error']:
                            logger.error('Buying - Error retrieving balances, can not buy or sell')
                            logger.error('Buying - %s' % buy_units['error'])
                        else:
                            # if buy units balance is less than 1.0
                            if float(buy_units['result']) < 1:
                                 logger.error('Buying - Not enough %s to buy coins, skipping buy' % trading_status['fiat'])
                                 trading_status['trading'] = False
                                 # I need to figure out if order was cancelled
                                 # get balance and compare selling units
                                 # if same or similar i would suggest the buy was cancelled
                            else:
                                trading_status = trade_buy_now(polo, current_stats_dict, even_stats_dict, buy_units, trading_status, testing_status)

            '''
            When testing is enabled generate bogus  trade details
            '''
            if testing_status:
                trading_status = generate_test_trade_data(pair_list_curr['fsym'])
                
            '''
            When trade is complete finalise the trade details
            '''
            if trading_status['trading_complete']:
                trading_status, sell_order_stats, buy_order_stats = evaluate_costs_and_units(polo, trading_status)
                trading_status['eval_counter'] += 1

                # print trade results to window
                logger.info('')
                if sell_order_stats is not None:
                    logger.info('Order Number %s Trade type %s for pair %s Units %s PPU %s Total %s' % (sell_order_stats['order_number'], sell_order_stats['type'], sell_order_stats['pair'], sell_order_stats['unit_total'], sell_order_stats['ppu'], sell_order_stats['fiat_total']))
                else:
                    logger.error('%s Error no sell order stats' % trading_status['eval_counter'])
                    continue

                if buy_order_stats is not None:
                    logger.info('Order Number %s Trade type %s for pair %s Units %s PPU %s Total %s' % (buy_order_stats['order_number'], buy_order_stats['type'], buy_order_stats['pair'], buy_order_stats['unit_total'], buy_order_stats['ppu'], buy_order_stats['fiat_total']))
                else:
                    logger.error('%s Error no buy order stats' % trading_status['eval_counter'])
                    continue
                logger.info('')


                '''
                Finalise the trade status and write to the status JSON
                '''
                # finalise trading status so it can be written to JSON file
                trading_status['trading'] = False
                trading_status['trading_complete'] = False
                trading_status['buy_order_placed'] = False
                trading_status['sell_order_placed'] = False
                trading_status['type'] = "sell"
                trading_status['sell_counter'] = 0
                trading_status['buy_counter'] = 0
                trading_status['eval_counter'] = 0
                trading_status['flip_coins'] = True


                # write trade status to json
                polo_tools.write_json_data(status_json_file, trading_status)
                json_data = get_json_trades(status_json_file)
                print_json_trade_status(json_data)


                '''
                Finalise the trade stats and write to the trades JSON
                '''
                ratio = get_ratio(sell_order_stats['ppu'], buy_order_stats['ppu'])
                names = trade.get_short_long_names()['curr_trade']
                json_update = {
                    'ratio': ratio['ratio'],
                    'tsym_price': buy_order_stats['ppu'],
                    'tsym_units': buy_order_stats['unit_total'],
                    'fsym_price': sell_order_stats['ppu'],
                    'fsym_units': sell_order_stats['unit_total'],
                    'fsym_name_short': names['fsym_name_short'],
                    'tsym_name_short': names['tsym_name_short'],
                    'fsym_name_long': names['fsym_name_long'],
                    'tsym_name_long': names['tsym_name_long'],
                }
                json_data_complete = trade.get_updated_json_data()
                json_data_updated = trade.write_json_data(json_data_complete, pair_list_curr, json_update)


                
                '''
                Flip trading pair before starting the next loop
                '''
                pair_list_curr = flippa_da_syms(pair_list_curr)

                # if set to break even change to 5 before completing trading
                # otherwise it will trade again as soon as this trade is complete
                if trading_factor <= 0:
                    trading_factor = 5


        '''
        ===== To do list =====
        email when hits 1% 2% or 3%
        email when well below break even
        email when trading

        write seperate code to get history and put in DB
        get balances and put in DB the cript just reads it or use json file and check stat for changes
        watch order book to discover big jumps

        log when factor is well below break even to 3% mark - for over an hour high and low is below break even
           possible solution, sell currency when the value goes above buy value, this corrects issue i think
           currently I beelive there is nothing to do but to stop trading unitl they come back into alignment - bit scary
        loop check
        when partially filled is cancelled, buy coin at price below the partially filled order price, to fix :)
        when sustain a loss due to order not being filled, and having to take lower price - next attempt fall back to break even b/c this recovers the loss before bad ordering
        add switch to trade immediately trading_status['trading'] = True
        trade on surges - this would be a completed different way to trade
        auto adjust factor based on last huors high and low, whe no surging it should be low, when surging maybe change it up a notch
        '''


if __name__ == '__main__':
    '''
     This catches it all but will kill any clean up code
    '''
    try:
        main()
    except KeyboardInterrupt:
        print 'Interrupted by keyboard. Exiting....'
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception, err:
        traceback.print_exc()
        try:
            sys.exit(1)
        except SystemExit:
            os._exit(1)
        
