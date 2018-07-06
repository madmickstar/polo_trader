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
from polo_emails import email_starting_trading, send_message, email_finished_trading


def process_cli(max_trading_threshold):

    # validate max_trading_threshold if not b/w 10 - 100, default to 105
    if max_trading_threshold in range(10, 100, 10):
       mtt = (max_trading_threshold * 10 ) + 5
    else:
       mtt = (20 * 10) + 5

    # processes cli arguments and usage guide
    parser = ArgumentParser(prog='polo_trader',
    description='''         Buy and sell on Poloniex exchange \n \
        trade between coins based on ratio
        ''',
    epilog='''Command line examples \n\n \
        Note:- default fiat is usdt \n\n \
        ## Windows and POSIX Users ## \n \
        python polo_trade.py -s xrp -b str -tt 5 \n \
        python polo_trade.py -s xrp -b nxt -tt 5 \n \
        ''',
    formatter_class=RawTextHelpFormatter)
    #g1 = parser.add_mutually_exclusive_group()
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
    parser.add_argument('-tt', '--trade_threshold',
        default='10.0',
        type=float,
        choices=map(lambda x: x/10.0, range(0, mtt, 5)),
        metavar=('{0.5, 1.0, .. 19.5, 20.0}'),
        help='Trade threshold percentage, default = 10.0')
    parser.add_argument('-r', '--ratio_override',
        default='0.0000',
        type=float,
        metavar=('xx.xxxx'),
        help='Ratio to override trade threshold, default = 0.0000 therefore disabled')
    parser.add_argument('-u', '--units_override',
        default='0.0000',
        type=float,
        metavar=('{xx.xxx}'),
        help='Units to override last traded units, default = 0 therefore disabled')
    parser.add_argument('-mf', '--max_fee',
        default='0.0025',
        type=float,
        metavar=('{0.0025, 0.0015}'),
        help='Maximum fee for trading, default is 0.25 percent = 0.0025')
    parser.add_argument('-ft', '--factor_threshold',
        default='2',
        type=int,
        choices=range(1, 11),
        metavar=('{1..10}'),
        help='Threshold to detect if sell and buy coins are around the wrong way, default = 2')
    parser.add_argument('-ss', '--spike_suppress',
        default='3',
        type=int,
        choices=range(1, 11),
        metavar=('{1..10}'),
        help='Amount of consecutive times ratio needs to be evaluated above threshold before triggering trading, disable = 1, default = 3')
    parser.add_argument('-ph', '--print_headers',
        default='20',
        type=int,
        choices=range(10, 51),
        metavar=('{1..50}'),
        help='Print headers to screen frequency, default = 20')
    parser.add_argument('-e', '--email_updates',
        action="store_true",
        help='Email when trading is triggered and rsults at the end of trade')
    parser.add_argument('-l', '--log',
        action="store_true",
        help='Enable logging to a file')
    parser.add_argument('-t', '--timestamp',
        action="store_true",
        help='Enable timestamping all output to console')
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
        if args.timestamp:    
            logging.basicConfig(stream=sys.stdout,
                                level=logging.DEBUG,
                                datefmt='%Y-%m-%d %H:%M:%S',
                                format='[%(asctime)s] %(message)s')
        else:
            logging.basicConfig(stream=sys.stdout,
                                level=logging.DEBUG,
                                format='%(message)s')
                                #format='[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s')
        print_args(args)

    else:
        if args.timestamp:
            logging.basicConfig(stream=sys.stdout,
                                level=logging.INFO,
                                datefmt='%Y-%m-%d %H:%M:%S',
                                format='[%(asctime)s] %(message)s')
        else:
            logging.basicConfig(stream=sys.stdout,
                                level=logging.INFO,
                                format='%(message)s')
                                
    # whitelist moduels that are aloud to log to screen                            
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



def print_orders(order_list):
    logger = logging.getLogger(__name__)
    # order_list looks like this
    # [{'local_epoch': 1516288337, 'amount': u'400.00000000', 'local_timestamp': '2018-01-18 15:12:17', 'order_number': u'77551204294',
    #   'total': u'368.00000000', 'type': u'buy', 'rate': u'0.92000000', 'coin_name': 'USDT_XRP'}, {'local_epoch': 1516288379, 'amount': u'784.74689059',
    #   'local_timestamp': '2018-01-18 15:12:59', 'order_number': u'49390422263', 'total': u'251.11900498', 'type': u'buy', 'rate': u'0.32000000',
    #   'coin_name': 'USDT_STR'}, {'local_epoch': 1516283877, 'amount': u'299.55000000', 'local_timestamp': '2018-01-18 13:57:57',
    #   'order_number': u'49385701988', 'total': u'164.75250000', 'type': u'sell', 'rate': u'0.55000000', 'coin_name': 'USDT_STR'}]
    ''' Print the header '''
    h1 = '{:^10} {:^12}'.format("Order", "Timestamp")
    h2 = '{:^8} | {:^14}'.format("Trade", "Order No.")
    h3 = '{:^9} | {:^14}'.format("Pair", "Price")
    h4 = '{:^15} | {:^14}'.format("Units", "Total")
    logger.info('|-------------------------+---------------------------+----------------------------+----------------------------------|')
    logger.info('| %s | %s | %s | %s |' % (h1, h2, h3, h4))
    logger.info('|-------------------------+----------+----------------+-----------+----------------+-----------------+----------------|')
    ''' Print the orders '''
    for order in order_list:
        coin_name = order['coin_name'].center(10)
        type = order['type'].center(7)
        order_number = order['order_number'].center(12)
        amount = order['amount'].center(13)
        rate = order['rate'].center(10)
        total = order['total'].center(12)
        #local_timestamp = order['local_timestamp'].center(31)

        c1 = '{:12.10} {:10}'.format(order['local_timestamp'], order['local_timestamp'][-8:])
        c2 = '{:^8} | {:^14}'.format(order['type'].title(), order['order_number'])
        c3 = '{:^9} | {:^14}'.format(order['coin_name'], order['rate'])
        c4 = '{:^15} | {:^14}'.format(order['amount'], order['total'])
        logger.info('| %s | %s | %s | %s |' % (c1, c2, c3, c4))



def print_balances(avail_balances_lod):
    '''
    print available balances
    '''
    logger = logging.getLogger(__name__)
    
    #logger.debug('%s' % avail_balances_lod)
    #avail_balances_lod.append({'units': 0.999999999, 'name': u'USDT'})
    
    w = [23, 24, 25, 31]
    if len(avail_balances_lod) > 0:
        header_divider = '|-------------------------+---------------------------+----------------------------+----------------------------------|'
        logger.info('%s' % header_divider)
        count = 0
        for bal in avail_balances_lod:
            count += 1
            if count == 1:
                column_width = w[0]
            elif count == 2:
                column_width = w[1]
            elif count == 3:
                column_width = w[2]
            elif count == 4:
                column_width = w[3]
            coin_units = '{:.8f}'.format(bal['units'])
            coin_display = '{:{align}{width}}'.format(bal['name']+ " " + coin_units, align='^', width=column_width)
            if count == 1:
                balances_header = '| {} | '.format(coin_display)
            elif count <=3:
                balances_header = balances_header + ' {} | '.format(coin_display)
            else:
                count = 0
                balances_header = balances_header + ' {} |'.format(coin_display)
                logger.info('%s' % balances_header)

        # add filler to header if it wasnt the last balance in a row of four
        if count > 0:
            # get the columns remainding
            counter = (4 - (len(avail_balances_lod) % 4))
            # start combined width with missing header dividers
            combined_width = ((counter - 1) * 3) + (counter - 1)
            # add the missing column widths
            for x in reversed(w):
                combined_width += x
                counter -= 1
                if counter == 0:
                    break
            filler = '{:{align}{width}}'.format("",align='^',width=combined_width)
            balances_header = balances_header + ' {} |'.format(filler)
            logger.info('%s' % balances_header)

            

def print_header(ratio_increasing, current_stats_dict, target_dict, ratio_override):
    logger = logging.getLogger(__name__)
    date_stamp = current_stats_dict['date']
    #date_formatted = (date_stamp[0:4] + "-" + date_stamp[4:6] + "-" + date_stamp[6:8]).center(10)
    #sell_coin = current_stats_dict['sell_coin_short'].center(7)
    #buy_coin = current_stats_dict['buy_coin_short'].center(28)

    date_formatted = '{:^10}'.format(date_stamp[0:4] + "-" + date_stamp[4:6] + "-" + date_stamp[6:8])
    sell_coin = '{:^23}'.format(current_stats_dict['sell_coin_long'])
    buy_coin = '{:^25}'.format(current_stats_dict['buy_coin_long'])
    if ratio_increasing:
        #factor = "Factor    Upward".center(25)
        direction = "Up"
    else:
        #factor = "Factor    Downward".center(25)
        direction = "Down"
    if ratio_override:
        factor = '{:^10}{:^10}{:^6.4f}'.format("Ratio " + direction, "override", ratio_override)
    else:
        factor = '{:^26}'.format("Ratio " + direction)
    #units = ("%s    Threshold = %s%s" % ("Units", target_dict['name'],"%")).center(31)
    units = '{:^14}{:4.1f}{}{:^13}'.format("Est. Units",target_dict['name'],"%","Threshold")

    h1 = '{:^11} {:^11}'.format(date_formatted, "Current")
    h2 = '{:^12} {:^12}'.format("Current", "Target")
    h3 = '{:^8} {:^8} {:^8}'.format("Current", "Even", "Target")
    h4 = '{:^10} {:^10} {:^10}'.format("Current", "Even", "Target")
    logger.info('|-------------------------+---------------------------+----------------------------+----------------------------------|')
    logger.info('| %s | %s | %s | %s |' % (sell_coin, buy_coin, factor, units))
    logger.info('| %s | %s | %s | %s |' % (h1, h2, h3, h4))
    logger.info('|-------------------------+---------------------------+----------------------------+----------------------------------|')

    

def print_some_results(ratio_increasing, current_stats_dict, even_stats_dict, target_dict):
    '''
    print results to screen for review
    '''
    logger = logging.getLogger(__name__)
    time_stamp = current_stats_dict['date'][-6:]
    time_formatted = '{}'.format(time_stamp[0:2] + ":" + time_stamp[2:4] + ":" + time_stamp[4:6])
    sell_coin = '{:^11} {:^11.6f}'.format(time_formatted, current_stats_dict['sell_coin_price'])
    buy_coin = '{:^12.6f} {:^12.6f}'.format(current_stats_dict['buy_coin_price'], target_dict['buy_coin_price'])
    factor = '{:^8.4f} {:^8.4f} {:^8.4f}'.format(current_stats_dict['ratio'], even_stats_dict['ratio'], target_dict['ratio'])
    units = '{:^10.3f} {:^10.3f} {:^10.3f}'.format(current_stats_dict['buy_coin_units'], even_stats_dict['buy_coin_units'], target_dict['buy_coin_units'])

    #logger.info('| %s | %s | %s | %s | %s |' % (time_formatted, sell_coin, buy_coin, factor, units))
    logger.info('| %s | %s | %s | %s |' % (sell_coin, buy_coin, factor, units))



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

    
# optimised function
def calc_target(trade_threshold, lod_targets):
    '''
    Match trading threshold to a row in list of target and return
    trading threshold details
    '''
    # logger = logging.getLogger(__name__)
    target_dict = {
        'error': True,
    }
    # cycle through list of dict targets threshold and extract match
    for x in lod_targets:
        #logger.debug("target to match %s" % x['name'])
        if float(trade_threshold) in (x['name'],):
            target_dict = {
                'name': x['name'],
                'buy_coin_price': x['buy_coin_price'],
                'ratio': x['ratio'],
                'buy_coin_units': x['buy_coin_units'],
                'error': False,
            }
            #logger.debug("calc_target matched %s" % target_dict)
            break
    return target_dict


def eval_trading(ratio_increasing, current_ratio, target_ratio):
   '''
   checks if the ratio is above or below target ratio
   '''
   if ratio_increasing:
       if current_ratio >= target_ratio:
           return True
   else:
       if current_ratio <= target_ratio:
           return True
   return False

   
    
def factor_increasing(cur_sell_coin_price, cur_buy_coin_price):
    if cur_sell_coin_price > cur_buy_coin_price:
        return True
    else:
        return False
    
    
    
def check_factor_diff(factor_threshold, current_factor, even_factor):
     '''
     checks if the difference between current and break even factors is within the factor threshold
     this check essentually picks up if the buy and sell values are around the wrong way
     which is less likely to happen now valus are controlled by XML file populated by script
     '''
     factor_factor = float(current_factor) / float(even_factor)
     if factor_factor > factor_threshold:
         return factor_factor
     else:
         return False


def bad_factor_detected(polo, current_stats_dict, factor_check):
    logger = logging.getLogger(__name__)
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


def generate_stats(current_stats_dict, even_stats_dict, units, trading_status):
    logger = logging.getLogger(__name__)
    if trading_status['type'] == "sell":
        x = "Selling"
    else:
        x = "Buying"

    ##logger.debug('%s - %s' % (x, purchase_stats_dict))
    logger.debug('%s - ================== CURRENT STATS ==========================' % x)
    ##logger.debug('%s - %s' % (x, current_stats_dict))
    logger.debug('%s - %s Name %s Factor %s' % (x, current_stats_dict['date'], current_stats_dict['name'], current_stats_dict['ratio']))
    logger.debug('%s - %s Price %s Units %s Pair %s' % (x, current_stats_dict['sell_coin_short'], current_stats_dict['sell_coin_price'], current_stats_dict['sell_coin_units'], current_stats_dict['sell_coin_long']))
    logger.debug('%s - %s Price %s Units %s Pair %s' % (x, current_stats_dict['buy_coin_short'], current_stats_dict['buy_coin_price'], current_stats_dict['buy_coin_units'], current_stats_dict['buy_coin_long']))
    logger.debug('%s - ================== EVEN STATS =============================' % x)
    logger.debug('%s - %s Name %s Factor %s' % (x, even_stats_dict['date'], even_stats_dict['name'], even_stats_dict['ratio']))
    logger.debug('%s - %s Price %s' % (x, even_stats_dict['sell_coin_short'], even_stats_dict['sell_coin_price']))
    logger.debug('%s - %s Price %s Units %s Pair %s' % (x, even_stats_dict['buy_coin_short'], even_stats_dict['buy_coin_price'], even_stats_dict['buy_coin_units'], even_stats_dict['buy_coin_long']))
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



def validate_trade_units(current_stats_dict, units, trading_status):
    '''
    units for sell are actual units to sell
    units for buy are the total crypto fiat in wallet
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
            # If wallet has more than expected sell trade value, chances are sell trade yielded more than expected
            # unless the extra funds were there before the trade, so to take caution, will only use extra funds if within
            # one percent of expected sell trade value
  
            buy_total_value_adjusted = float(buy_total_value) * 1.01
            logger.debug('Buying - %s wallet is greater than expected, checking to see if 1 percent adjustment %s is greater than %s %s' % (trading_status['fiat'], buy_total_value_adjusted, wallet_total, trading_status['fiat']))
            # if value of wallet is below expected value with an extra one percent added (buy_total_value_adjusted) - use wallet
            if float(wallet_total) < buy_total_value_adjusted:
                validated_units = float(wallet_total) / float(current_stats_dict['buy_coin_price'])
                logger.debug('Buying - %s wallet is less than 1 percent greater, adjusting purchase units to %s' % (trading_status['fiat'], validated_units))
            else:
                validated_units = current_stats_dict['buy_coin_units']
                logger.debug('Buying - %s wallet is more than 1 percent greater, leaving purchase units as %s' % (trading_status['fiat'], validated_units))
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
    '''
    main function
    '''
    # maximum trading threshold value - must be between 10 - 100
    max_trading_threshold = 20

    # set app dir name
    app_dir = '.polo_trade'
    working_dir = polo_tools.process_user_home_app_dir(app_dir)

    args = process_cli(max_trading_threshold)

    # configure logging
    logging = configure_logging(args)
    logger = logging.getLogger(__name__)

    # confirm user has updated the config file
    try:
        import config
    except:
        logger.error('config.py not found in module dir, rename config.txt to config.py and edit api and private key')
        sys.exit(1)
        
    if args.buy == args.sell:
        logger.error('Buy and sell cryptos are the same, try again')
        sys.exit(1)

    # create current trade pair list
    pair_list_curr = {
        'fsym': args.sell,
        'fiat': args.fiat,
        'tsym': args.buy
    }

    # check if over ride ratio is default
    if args.ratio_override == 0:
        ratio_override = False
        logger.debug('Override ratio is disabled')
    else:
        ratio_override = round(args.ratio_override, 4)
        logger.debug('Overriding trading threshold with %.4f' % ratio_override)    
        
        
    # check if over ride units is default
    if args.units_override == 0:
        units_override = False
        logger.debug('Override units is disabled')
    else:
        units_override = args.units_override
        logger.debug('Overriding units with %s' % units_override)  
        
    
    # double fee because buying and selling attracts fees for both trades
    worst_trade_fee = args.max_fee * 2
    trade_threshold = args.trade_threshold
    
    email_me_updates = args.email_updates
    spike_suppress = args.spike_suppress  
    print_headers = args.print_headers
        

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
        trade_threshold = 0.0

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

    polo.key = config.api_key
    polo.secret = config.private_key

    
    # starting first trade so this needs to be set to true to trigger
    # grabbing the last trade details and profiling
    trading_status['flip_coins'] = True


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
            logger.debug('##### Previous Trade #####')
            logger.debug('Sold %s units of %s at %s' % (t['fsym_units'], t['fsym_name_long'], t['fsym_price']))
            logger.debug('Bought %s units of %s at %s' % (t['tsym_units'], t['tsym_name_long'], t['tsym_price']))
            logger.debug('Trading ratio was %s' % t['ratio'])

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

            # if over ride units are provided - change the units to sell
            if units_override:
                trading_pairs['fsym_units'] = units_override
            
            tp = trading_pairs
            if factor_increasing(tp['fsym_price'], tp['tsym_price']):
                break_even_ratio = tp['ratio'] + (tp['ratio'] * worst_trade_fee)
            else:
                break_even_ratio = tp['ratio'] - (tp['ratio'] * worst_trade_fee)

            logger.debug('')
            logger.debug('##### Current Trade #####')
            logger.debug('Selling %s units of %s' % (tp['fsym_units'], tp['fsym_name_long']))
            logger.debug('Break even ratio of %s' % round(break_even_ratio,4))
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
            # trigger script to update break even and targets
            refresh_targets = True
            # enable evaluate trading status
            trading_status['eval_trading'] = True
            # zero trade threshold spike suppressor
            spike_suppress_counter = 0
            # force headers to print after trade
            print_headers_counter = print_headers
            

        # just a little debugging to screen
        #logger.debug('header counter %s' % print_headers_counter)

        # profile the trading pair
        mycoins = ProfilePairs(polo, worst_trade_fee, trading_pairs)

        try:
            #purchase_stats_dict, current_stats_dict, even_stats_dict = mycoins.get_stats()
            current_stats_dict, even_stats_dict = mycoins.get_stats()
        except RuntimeError, err:
            logger.error(str(err))
            continue
        except Exception, err:
            traceback.print_exc()
            continue


        ratio_increasing = mycoins.get_ratio_direction(current_stats_dict['sell_coin_price'], current_stats_dict['buy_coin_price'])

        # targets are only updated after a trade is completed or first time run
        if refresh_targets:
            refresh_targets = False
            lod_targets = mycoins.get_targets(max_trading_threshold, trading_pairs['fsym_units'], current_stats_dict, even_stats_dict)
            target_dict = calc_target(trade_threshold, lod_targets)
            if not target_dict:
                logger.error('Error matching trading factor to list of targets, exiting....')
                sys.exit(1)
        else:
            # adjust target buy coin price based on latest sell price and target ratio
            if ratio_increasing:
                updated_buy_coin_price = current_stats_dict['sell_coin_price'] / target_dict['ratio']
            else:
                updated_buy_coin_price = current_stats_dict['sell_coin_price'] * target_dict['ratio']
            target_dict['buy_coin_price'] = round(updated_buy_coin_price,8)


        print_headers_counter += 1
        try:
            if print_headers_counter > print_headers:
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
                print_header(ratio_increasing, current_stats_dict, target_dict, ratio_override)
                print_headers_counter = 0
            ''' print results '''
            print_some_results(ratio_increasing, current_stats_dict, even_stats_dict, target_dict)
        except IOError:
            ''' if user pauses screen or scrolls up catch and continue '''
            pass
        except Exception:
            raise

        '''
        Check if difference in ratios is not greater than factor_threshold
        Due to management of crypto trades via XML there is less human error therefore this is not required anymore I suspect
        '''
        factor_check = check_factor_diff(args.factor_threshold, current_stats_dict['ratio'], even_stats_dict['ratio'])
        if factor_check:
            bad_factor_detected(polo, current_stats_dict, factor_check)
            break

        '''
        Check if ready to start trading
        '''       
        # check if evaluate trading is enabled
        if trading_status['eval_trading']:
            # evaluate if ratio has hit threshold
            if ratio_override:
                trading_status['trading'] = eval_trading(ratio_increasing, current_stats_dict['ratio'], ratio_override)
            else:
                trading_status['trading'] = eval_trading(ratio_increasing, current_stats_dict['ratio'], target_dict['ratio'])

            # increment spike suppress counter if trading is enabled
            if trading_status['trading']:     
                spike_suppress_counter += 1
                logger.debug('Trade threshold met %s / %s' % (spike_suppress_counter, spike_suppress))
            else:
                spike_suppress_counter = 0
                
            # start trading if spike suppress counter is >= to spike suppress value
            if spike_suppress_counter >= spike_suppress:
                trading_status['trading'] = True
                # suppress headers from printing when trading is triggered
                print_headers_counter = 0
            else:
                trading_status['trading'] = False
           

        '''
        start or continue trading
        '''
        if trading_status['trading']:
        
            # disable trading evaluation - this will be set to true after finished trading
            trading_status['eval_trading'] = False
                   
            # this variable only needs to be set the first time round, for use when emailing
            if trading_status['sell_counter'] == 0:
                if ratio_override:
                    target_ratio = ratio_override
                else:
                    target_ratio = target_dict['ratio']
                logger.debug('Target ratio %s - current ratio %s - Trading triggered' % (target_ratio, current_stats_dict['ratio']))
                   
            # this is for major debug option, not needed in future
            if args.debug:
                print_trade_status(trading_status)

            # # check open orders
            # # if it errors restart loop
            # open_orders_dict = get_open_orders(polo)
            # if open_orders_dict['error']:
            #     logger.error('Grabbing open orders returned error - %s' % open_orders_dict['error'])
            #     continue

            if trading_status['type'] == "sell":
                # send email update
                if trading_status['sell_counter'] == 0:
                    if email_me_updates:
                        html = email_starting_trading(trading_status, target_dict, ratio_increasing, current_stats_dict, target_ratio)
                        subject = "Started trading - selling"
                        email_status = send_message(config, subject, html)
                        if email_status['error']:
                            logger.error(email_status['msg'])
                        
                # debug to exit before trading        
                #sys.exit(1)
                
                # if sell order is placed check for orders
                order_to_review = None
                if trading_status['sell_order_placed']:
                    # check open orders
                    # if it errors restart loop
                    open_orders_dict = get_open_orders(polo)
                    if open_orders_dict['error']:
                        logger.error('Grabbing open orders returned error - %s' % open_orders_dict['error'])
                        continue
    
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
                    # if sell order is placed and no orders found
                    # it means selling is complete - change to buying
                    if trading_status['sell_order_placed']:
                        trading_status['type'] = "buy"
                        logger.debug('Selling - COMPLETE - Trading Status changed to %s' % (trading_status['type']))
                    else:
                        # sell order is not placed so get balances and proceed
                        sell_units = get_coin_balance(polo, current_stats_dict['sell_coin_short'])
                        # if there were errors
                        if sell_units['error']:
                            logger.error('Error retrieving balances, can not buy or sell')
                            logger.error('%s' % sell_units['error'])
                        else:
                            trading_status = trade_sell_now(polo, current_stats_dict, even_stats_dict, sell_units, trading_status, testing_status)
                            #
                            # these lines below will not work with expensive cryptos, sums being moved around all could be below 1 so I 
                            # suspect the code is not suitable
                            #
                            # # if sell coin has no balance
                            # if float(sell_units['result']) < 1:
                            #     logger.error('Selling - Sell coin returned no units to sell, skipping sell')
                            #     trading_status['trading'] = False
                            # else:
                            #     # start selling
                            #     trading_status = trade_sell_now(polo, current_stats_dict, even_stats_dict, sell_units, trading_status, testing_status)


            if trading_status['type'] == "buy":
                # send email update
                if trading_status['buy_counter'] == 0:
                    if email_me_updates:
                        html = email_starting_trading(trading_status, target_dict, ratio_increasing, current_stats_dict, target_ratio)
                        subject = "Started trading - buying"
                        email_status = send_message(config, subject, html)
                        if email_status['error']:
                            logger.error(email_status['msg'])
            

                # if buy order is placed check for orders
                order_to_review = None
                if trading_status['buy_order_placed']:
                    # check open orders
                    # if it errors restart loop
                    open_orders_dict = get_open_orders(polo)
                    if open_orders_dict['error']:
                        logger.error('Grabbing open orders returned error - %s' % open_orders_dict['error'])
                        continue
                    
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
                    # if buy order is placed and no orders found
                    # it means buy is complete
                    if trading_status['buy_order_placed']:
                        trading_status['trading_complete'] = True
                        # change type to something other than buy or sell to ensure script does nto hit buy or sell if statements, 
                        # at this point in time eval does nothing else.
                        trading_status['type'] = "eval"
                        trading_status['eval_counter'] = 0
                        logger.debug('Buying - COMPLETE - Trading Status changed to %s' % (trading_status['type']))
                    else:
                        # buy order is not placed so get fiat balance and proceed
                        buy_units = get_coin_balance(polo, trading_status['fiat'])
                        # if there were errors
                        if buy_units['error']:
                            logger.error('Buying - Error retrieving balances, can not buy or sell')
                            logger.error('Buying - %s' % buy_units['error'])
                        else:
                            trading_status = trade_buy_now(polo, current_stats_dict, even_stats_dict, buy_units, trading_status, testing_status)
                            #
                            # these lines below will not work with expensive cryptos, sums being moved around all could be below 1 so I 
                            # suspect the code is not suitable
                            #
                            # # if fiat has no balance
                            # if float(buy_units['result']) < 1:
                            #      logger.error('Buying - Not enough %s to buy coins, skipping buy' % trading_status['fiat'])
                            #      trading_status['trading'] = False
                            #      # I need to figure out if order was cancelled
                            #      # get balance and compare selling units
                            #      # if same or similar i would suggest the buy was cancelled
                            # else:
                            #     trading_status = trade_buy_now(polo, current_stats_dict, even_stats_dict, buy_units, trading_status, testing_status)


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
                Email trade stats
                '''
                if email_me_updates:
                    html = email_finished_trading(trading_status, target_dict, current_stats_dict, sell_order_stats, buy_order_stats, ratio)
                    subject = "Finished trading - results"
                    email_status = send_message(config, subject, html)
                    if email_status['error']:
                        logger.error(email_status['msg'])
                
                '''
                Flip trading pair before starting the next loop
                '''
                pair_list_curr = flippa_da_syms(pair_list_curr)
                
                '''
                Disable settings that trigger immediately trading after a trade completes
                '''
                # if set to break even it will trigger a trade immediately
                if trade_threshold <= 0:
                    trade_threshold = 10

                # Disable override ratio. If enabled it will trigger a trade immediately
                ratio_override = False
                # Disable override units. No need for override after a trade is complete
                units_override = False
                
                
                
                
        '''
        ===== To do list =====
        over ride trading ratio - done
        over ride selling units
        sell only
        email when trading - done
        
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

