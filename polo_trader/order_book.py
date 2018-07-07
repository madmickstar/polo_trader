#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division

import sys, os
import json
import time
from calendar import timegm
from dateutil import tz
from datetime import datetime
import pytz    # $ pip install pytz
import tzlocal # $ pip install tzlocal
import logging
from argparse import ArgumentParser, RawTextHelpFormatter

# from 3rd party
# pip install https://github.com/s4w3d0ff/python-poloniex/archive/v0.4.7.zip
from poloniex import Poloniex

#from local
from _version import __version__
import polo_tools
from polo_gets import get_balances, get_orderbook
from order_book_tabledraw import tableDraw




def process_cli():
    # processes cli arguments and usage guide
    parser = ArgumentParser(prog='order_book_trading',
    description='''         Grab order books for a pair of coins on Poloniex exchange.  \n \
        Compares buy and sell based on current wallet holdings \n \
        and generates expected outcome of trading pair of coins.''',
    epilog='''Command line examples \n\n \
        Note:- default fiat is usdt \n\n \
        ## Windows and POSIX Users ## \n \
        python order_book.py -s xrp -b nxt -f btc \n \
        python order_book.py -s xrp -b str -f usdt \n \
        ''',
    formatter_class=RawTextHelpFormatter)
    parser.add_argument('-s', '--sell',
        default='xrp',
        choices=['xrp', 'str', 'nxt', 'eth', 'btc'],
        metavar=('{nxt, str, xrp, nxt, eth, btc}'),
        help='Sell coin, default = xrp')
    parser.add_argument('-b', '--buy',
        default='str',
        choices=['xrp', 'str', 'nxt', 'eth', 'btc'],
        metavar=('{nxt, str, xrp, nxt, eth, btc}'),
        help='Buy coin, default = str')
    parser.add_argument('-f', '--fiat',
        default='usdt',
        choices=['usdt', 'btc'],
        metavar=('{usdt, btc}'),
        help='Fiat coin, default = usdt')
    parser.add_argument('-mf', '--max-fee',
        default='0.0025',
        type=float,
        metavar=('{0.0025, 0.0015}'),
        help='Maximum fee for trading, default is 0.25 percent = 0.0025')
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
        handler.addFilter(Whitelist('order_book_tabledraw', 'polo_tools', 'polo_gets', '__main__'))
    return logging



def print_args(args):
    """
    Prints out cli arguments in nice format when debugging is enabled
    """
    logger = logging.getLogger(__name__)
    logger.debug('')
    logger.debug('CLI Arguments, %s', args)




def date_conversions(date_stamp):
    '''
    accepts UTC date stamp in the following format
    2018-01-11 03:57:54
    '''
    # convert to utc epoch
    epoch_utc_stamp = timegm(time.strptime(date_stamp, "%Y-%m-%d %H:%M:%S"))

    # get zones
    from_zone = pytz.utc
    to_zone = tzlocal.get_localzone()

    # convert UTC to local
    utc_time = datetime.strptime(date_stamp, "%Y-%m-%d %H:%M:%S")
    local_time_stamp = utc_time.replace(tzinfo=from_zone).astimezone(to_zone)
    local_time_stamp = str(local_time_stamp)[0:19]

    # convert local to local epoch
    epoch_local_stamp = timegm(time.strptime(local_time_stamp, "%Y-%m-%d %H:%M:%S"))

    date_dict = {
        'utc_time_stamp': date_stamp,
        'utc_epoch': epoch_utc_stamp,
        'local_time_stamp': local_time_stamp,
        'local_epoch': epoch_local_stamp,
    }
    return date_dict

 

def main():
    app_dir = '.polo_trade'
    working_dir = polo_tools.process_user_home_app_dir(app_dir)
    args = process_cli()

    logging = configure_logging(args)
    logger = logging.getLogger(__name__)
    
    # confirm user has updated the config file
    try:
        import config
    except:
        logger.error('config.py not found in module dir, rename config.txt to config.py and edit api and private key')
        sys.exit(1)

    trade_status_json = 'trade_status.json'
    trade_profile_json = 'trade_profile_test.json'
    log_file = 'polo_trade.log'
    try:
        trade_profile_json, trade_status_json, log_file, current_working_dir = polo_tools.permissions(working_dir, log_file, trade_status_json, trade_profile_json )
    except Exception, err:
        logger.error(str(err))
        sys.exit(1)

    if args.buy == args.sell:
        logger.error('Buy and sell cryptos are the same, try again')
        sys.exit(1)
        
    # double fee because buy and sell attracts fees
    worst_trade_fee = args.max_fee * 2
     
    ''' define the pairs and convert to upper case ''' 
    fiat = args.fiat
    if fiat.lower() in ('eth', 'btc'):
       pairing = fiat.upper()
    else:
       pairing = 'USDT'
        
    buy = args.buy
    if buy.lower() in ('eth', 'btc', 'nxt', 'xrp'):
       buy_coin_short = buy.upper()
    else:
       buy_coin_short = 'STR'
               
    sell = args.sell
    if sell.lower() in ('eth', 'btc', 'nxt', 'str'):
       sell_coin_short = sell.upper()
    else:
       sell_coin_short = 'XRP'
        
    sell_coin_pair = pairing + '_' + sell_coin_short
    buy_coin_pair = pairing  + '_' + buy_coin_short

    logger.debug('Sell coin %s Buy coin %s' % (sell_coin_pair, buy_coin_pair))


    # initialise the poloniex querier     
    polo = Poloniex()
    polo.key = config.api_key
    polo.secret = config.private_key

    
    order_book_trade = {
        'sell_coin_long': sell_coin_pair,
        'sell_coin_short': sell_coin_short,
        'buy_coin_long': buy_coin_pair,
        'buy_coin_short': buy_coin_short,
        }
    
    ''' get date '''
    date_stamp = time.strftime("%Y%m%d-%H%M%S")
    date_formatted = (date_stamp[0:4] + "-" + date_stamp[4:6] + "-" + date_stamp[6:8]).center(10)
        
    # create header
    headers_row = [(date_formatted, 'Sell Pair', 'Units', 'Price', '$ '+pairing+' $', 'Buy Pair', 'Est. Units', 'Price', 'Ratio')]
    header_counter = 20
    
    
    while True:
        table_rows = [headers_row]
        bid_order = get_orderbook(polo, sell_coin_pair, 'bid')
        if not bid_order['result']:
            logger.error('Error grabbing bid order book for %s - %s' % (sell_coin_pair, bid_order['error']))
            continue
            #sys.exit(1)
            
        ask_order = get_orderbook(polo, buy_coin_pair, 'ask')
        if not ask_order['result']:
           logger.error('Error grabbing ask order book for %s - %s' % (buy_coin_pair, ask_order['error']))
           continue
           #sys.exit(1)
                 
        if header_counter >= 20:
            ''' Get balances and if errors redo loop '''  
            avail_balances_lod = get_balances(polo)
            order_book_trade['sell_coin_units'] = None
            if avail_balances_lod['error']:
               ''' if errors redo loop '''  
               logger.error('Error getting balances - %s' % avail_balances_lod['error'])
               continue
            else:
                ''' if it finds balances check if their is a balance for the selling coin'''  
                for x in avail_balances_lod['result']:
                    if x['name'] == order_book_trade['sell_coin_short']:
                        logger.debug('Balance is %s' % x['units'])
                        #balance = x['units']
                        order_book_trade['sell_coin_units'] = x['units']
                        
            if order_book_trade['sell_coin_units'] is None:
                ''' If found balances but not for selling coin print available balances and exit'''  
                logger.error('No balance matching sell coin - %s' % order_book_trade['sell_coin_short'])
                balances_headers = [('Name', 'Units')]
                print('Available balances')
                # header_counter = 20
                balances_rows = []
                for x in avail_balances_lod['result']:
                    balances_rows.append((x['name'], format(x['units'], '.8f')))
                #if header_counter >= 20:
                #    a = tableDraw(headers=balances_headers, rows=balances_rows, print_header=True)
                #    header_counter = 0
                #else:
                #    a = tableDraw(headers=balances_headers, rows=balances_rows, print_header=False)
                try:
                    a = tableDraw(headers=balances_headers, rows=balances_rows, print_header=True)
                except Exception as err:
                    logger.error('Problem printing available balances in a table - %s' % err)
                    break
                a.tableSize()
                a.tableData()
                break
        
        ''' get time '''
        date_stamp = time.strftime("%Y%m%d-%H%M%S")
        #date_formatted = (date_stamp[0:4] + "-" + date_stamp[4:6] + "-" + date_stamp[6:8]).center(10)
        time_stamp = date_stamp[-6:]
        time_formatted = (time_stamp[0:2] + ":" + time_stamp[2:4] + ":" + time_stamp[4:6]).center(10)

        
        ''' get bid price'''
        order_units_bid = 0
        order_units_ask = 0
        for x in bid_order['result']:
            order_units_bid += float(x[1])
            logger.debug('%s %s' % (x[1], order_units_bid))
            if order_units_bid > order_book_trade['sell_coin_units']:
                order_book_trade['sell_coin_price'] = float(x[0])
                order_book_trade['sell_fiat'] = float(order_book_trade['sell_coin_units']) * float(x[0])
                logger.debug('%s' % order_book_trade)
                break
            
             
        ''' get ask price'''
        for x in ask_order['result']:
            order_units_ask += float(x[1])
            logger.debug('%s %s' % (x[1], order_units_ask))
            buy_units = order_book_trade['sell_fiat'] / float(x[0])
            if order_units_ask > buy_units:
                order_book_trade['buy_coin_price'] = float(x[0])
                order_book_trade['buy_coin_units'] = buy_units
                break
                
        ''' calc ratio '''
        if order_book_trade['buy_coin_price'] > order_book_trade['sell_coin_price']:
           order_book_trade['ratio'] = order_book_trade['buy_coin_price'] / order_book_trade['sell_coin_price']
        else:
           order_book_trade['ratio'] = order_book_trade['sell_coin_price'] / order_book_trade['buy_coin_price']
        
        content_row = [(time_formatted, order_book_trade['sell_coin_long'], format(order_book_trade['sell_coin_units'], '.4f'), format(order_book_trade['sell_coin_price'], '.4f'), format(order_book_trade['sell_fiat'], '.2f'), order_book_trade['buy_coin_long'], format(order_book_trade['buy_coin_units'], '.4f'), format(order_book_trade['buy_coin_price'], '.4f'), format(order_book_trade['ratio'], '.4f'))]
        table_rows.append(content_row)

        # if user pauses screen or scrolls up this try handles the IO exception
        try:
            # send results to table maker 
            if header_counter >= 20:
                a = tableDraw(headers=headers_row, rows=content_row, print_header=True)
                header_counter = 0
            else:
                a = tableDraw(headers=headers_row, rows=content_row, print_header=False)
            a.tableSize()
            a.tableData()
            header_counter += 1
        except IOError:
            pass
        except Exception:
            raise
        


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