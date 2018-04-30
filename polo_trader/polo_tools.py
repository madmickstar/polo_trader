#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import time
import json
import logging
import datetime
from codecs import open

# time conversion modules
import time
from calendar import timegm
#from dateutil import tz
from datetime import datetime
import pytz    # $ pip install pytz
import tzlocal # $ pip install tzlocal


def process_user_home_app_dir(app_dir):
    '''
    Checks for working dir in home directory and if writable
    If it is not there it checks for write access to home dir and creates working dir

    Returns Users home application dir
    '''
    # prep working dir in users home DIR
    user_home_dir = os.path.expanduser('~')
    user_home_app_dir = os.path.join(user_home_dir, app_dir)

    if os.path.isdir(user_home_app_dir):
        if not check_write_dir(user_home_app_dir):
            sys.stderr.write('ERROR: Failed write access to user home app DIR %s, exiting....' % user_home_app_dir)
            sys.exit(1)
    else:
        if not os.path.isdir(user_home_dir):
            sys.stderr.write('ERROR: Failed to find user home DIR %s, exiting....' % user_home_dir)
            sys.exit(1)
        else:
            if not check_write_dir(user_home_dir):
                sys.stderr.write('ERROR: Failed write access to user home DIR %s, exiting....' % user_home_dir)
                sys.exit(1)
            else:
                # create working dir in home dir
                try:
                    os.makedirs(user_home_app_dir)
                except:
                    sys.stderr.write('ERROR: Failed to create user home app DIR %s, exiting....' % user_home_app_dir)
                    sys.exit(1)
    return user_home_app_dir
    

def write_json_data(json_file, dict_to_json):
    ## Writing JSON data
    with open(json_file, 'w') as f:
         json.dump(dict_to_json,
                   f,
                   sort_keys = False,
                   indent = 4,
                   ensure_ascii = False)
                   

def permissions(user_home_app_dir, log_file, trade_status_json, trade_profile_json, pair_list_curr=False):
    # check write permissions
    logger = logging.getLogger(__name__)

    current_dir = os.getcwd()
    app_dir = os.path.dirname(sys.argv[0])
    app_dir_complete = os.path.join(current_dir, app_dir)
    log_file = os.path.join(user_home_app_dir, log_file)
    trade_status_json = os.path.join(current_dir, app_dir, trade_status_json)
    trade_profile_json = os.path.join(current_dir, app_dir, trade_profile_json)

    logger.debug('Current DIR  %s', current_dir)
    logger.debug('Application DIR %s', app_dir)
    logger.debug('Application DIR complete %s', app_dir_complete)
    logger.debug('Log DIR complete %s', log_file)
    logger.debug('Resulting Trade Status JSON file %s', trade_status_json)
    logger.debug('Resulting Trade Profile JSON file %s', trade_profile_json)

    
    # test current dir
    if not check_write_dir(current_dir):
        raise RuntimeError('Permissions check - Failed write access in current working folder %s exiting....' % current_dir)
    else:
        logger.debug('Current working DIR is writable %s', current_dir)

    # test app dir
    if not check_write_dir(app_dir_complete):
        raise RuntimeError('Permissions check - Failed write access in Application folder %s exiting....' % app_dir_complete)
    else:
        logger.debug('Application DIR is writable %s', app_dir_complete)

    # test creds file
    if os.path.isfile(log_file):
        if not check_read_file(log_file):
            raise RuntimeError('Permissions check - Creds file failed read test %s exiting....' % log_file)
        else:
            logger.debug('Creds file exists and is readable %s', log_file)
            
    # test trade status json file
    if os.path.isfile(trade_status_json):
        if not check_write_file(trade_status_json):
            raise RuntimeError('Permissions check - trade JSON file failed write test %s exiting....' % trade_status_json)
        else:
            logger.debug('Trade JSON file exists and is readable %s', trade_status_json)
    else:
        # create sample trade and write to json file
        trade_time = time.time()
        trade_time = int(trade_time)
        sample_trade = {
            'type' : "sell",
            'trading' : False,
            'trading_complete' : False,
            'flip_coins' : True,
            'sell_coin_long' : "",
            'sell_counter' : "0",
            'sell_order_placed' : False,
            'sell_coin_units' : "0",
            'sell_order_number' : "11111111",
            'sell_coin_utc' : trade_time,
            'buy_coin_long' : "",
            'buy_counter' : "0",
            'buy_order_placed' : False,
            'buy_order_number' : "11111111",             
            'buy_coin_utc' : trade_time,
        }
        write_json_data(trade_status_json, sample_trade)
        
    # test trade status json file
    if os.path.isfile(trade_profile_json):
        if not check_write_file(trade_profile_json):
            raise RuntimeError('Permissions check - trade JSON file failed write test %s exiting....' % trade_profile_json)
        else:
            logger.debug('Trade JSON file exists and is readable %s', trade_profile_json)
    else:
        # create sample trade and write to json file
        #sample_trade_profile = {
        #    'buy_coin_long': "USDT_XRP",
        #    'buy_coin_short': "XRP",
        #    'sell_coin_long': "USDT_STR",
        #    'sell_coin_short': "STR",
        #    'pur_buy_coin_units': 333.9,
        #    'pur_buy_coin_price': 0.948,
        #    'pur_sell_coin_units': 720.3327634,
        #    'pur_sell_coin_price': 0.43989879,
        #}
        #write_json_data(trade_profile_json, sample_trade_profile)
        
        # just n case it hits this for unknown reason
        if not pair_list_curr:
            pair_list_curr = {
                'fsym': 'xrp',
                'tsym': 'str',
            }
        # create very basic trade json structure
        json_starter = { pair_list_curr['fsym']: { }, pair_list_curr['tsym']: { }, }
        write_json_data(trade_profile_json, json_starter)


    logger.debug('Successfully passed all read write access tests')
    return trade_profile_json, trade_status_json, log_file, current_dir

    
def format_time(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    formatted_time = "%d:%02d:%02d" % (h, m, s)
    return formatted_time    
    
def check_write_dir(test_dir):
    if not os.access(test_dir, os.W_OK):
        return False
    return True


def check_write_file(test_file):
    if not os.access(test_file, os.W_OK):
        return False
    return True


def check_exists_file(test_file):
    if not os.access(test_file, os.F_OK):
        return False
    return True

def check_read_file(test_file):
    if not os.access(test_file, os.R_OK):
        return False
    return True
    
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