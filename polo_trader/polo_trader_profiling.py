#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division


import sys, os
import time
import json
import datetime


# from 3rd party
# pip install https://github.com/s4w3d0ff/python-poloniex/archive/v0.4.7.zip
#from poloniex import Poloniex


class ProfilePairs:

    def __init__(self, polo, worst_trade_fee, prof_dict):
        self.polo = polo
        self.worst_trade_fee = worst_trade_fee
        #self.sell_coin_long = prof_dict['sell_coin_long']
        #self.sell_coin_short = prof_dict['sell_coin_short']
        #self.buy_coin_long = prof_dict['buy_coin_long']
        #self.buy_coin_short = prof_dict['buy_coin_short']
        #self.pur_buy_coin_units = float(prof_dict['pur_buy_coin_units'])
        #self.pur_buy_coin_price = float(prof_dict['pur_buy_coin_price'])
        #self.pur_sell_coin_units = float(prof_dict['pur_sell_coin_units'])
        #self.pur_sell_coin_price = float(prof_dict['pur_sell_coin_price'])
        
        self.sell_coin_long = prof_dict['fsym_name_long']
        self.sell_coin_short = prof_dict['fsym_name_short']
        self.buy_coin_long = prof_dict['tsym_name_long']
        self.buy_coin_short = prof_dict['tsym_name_short']
        self.pur_buy_coin_units = float(prof_dict['fsym_units'])
        self.pur_buy_coin_price = float(prof_dict['fsym_price'])
        #self.pur_sell_coin_units = float(prof_dict['pur_sell_coin_units'])
        self.pur_sell_coin_price = float(prof_dict['tsym_price'])
        self.purchase_stats_dict = False
        self.current_stats_dict = False
        self.even_stats_dict = False
 
        #print('self.sell_coin_long %s' % self.sell_coin_long) 
        #print('self.sell_coin_short %s' % self.sell_coin_short)
        #print('self.buy_coin_long %s' % self.buy_coin_long)
        #print('self.buy_coin_short %s' % self.buy_coin_short)
        #print('self.pur_buy_coin_units %s' % self.pur_buy_coin_units)
        #print('self.pur_buy_coin_price %s' % self.pur_buy_coin_price)
        #print('self.pur_sell_coin_price %s' % self.pur_sell_coin_price)
       

    def get_even_only(self):
        try:
            return self._generate_price()
        except:
            raise

    def get_even_and_targets(self, max_target_value):
        self.max_target_value = max_target_value
        try:
            self.purchase_stats_dict, self.current_stats_dict, self.even_stats_dict = self._generate_price()
        except:
            raise
        self.factor_increasing = self._is_factor_increasing(self.current_stats_dict['sell_coin_price'], self.current_stats_dict['buy_coin_price'])
        self.lod_targets = self._generate_targets(self.max_target_value, self.worst_trade_fee, self.factor_increasing, self.purchase_stats_dict, self.current_stats_dict, self.even_stats_dict)
        return self.purchase_stats_dict, self.current_stats_dict, self.even_stats_dict, self.lod_targets

    def get_factor_direction(self, cur_sell_coin_price, cur_buy_coin_price):
        return self._is_factor_increasing(cur_sell_coin_price, cur_buy_coin_price)

    def _is_factor_increasing(self, cur_sell_coin_price, cur_buy_coin_price):
        self.sell_price = cur_sell_coin_price
        self.buy_price = cur_buy_coin_price
        if self.sell_price > self.buy_price:
            self.factor_increasing = True
        else:
            self.factor_increasing = False
        return self.factor_increasing
     


    def _get_orderbook(self, polo, pair, order_type='bid'):
        '''
        retrieves order book and return list of prices in dictionaries
        '''
        self.polo = polo
        self.pair = pair
        self.order_type = order_type

        try:
            self.results = self.polo.returnOrderBook(currencyPair = self.pair)
            # same return {u'seq': 113346801, u'bids': [[u'0.82163798', u'2.43416207'], [u'0.82099275', u'73577.042']], u'isFrozen': u'0', u'asks': [[u'0.82496594', u'8520.057'], [u'0.82496595', u'3921.68897093']]
        except Exception as err:
            self.result_dict = {
                'result': False,
                'error': err,
            }
            return self.result_dict
        self.current_orders = []
        # first check the list returned is not empty
        if len(self.results) > 0:
            if self.order_type=='bid':
                for a in self.results['bids']:
                    self.current_orders.append([a[0], a[1]])
            elif self.order_type=='ask':
                if int(self.results['isFrozen']) > 0:
                    print('\n%s Asks is frozen  - value is %s' % (self.pair, self.results['isFrozen']))

                for a in self.results['asks']:
                    self.current_orders.append([a[0], a[1]])

        if len(self.current_orders) < 0:
            self.result_dict = {
                'result': False,
                'error': 'No orders returned',
            }
        else:
            self.result_dict = {
                'result': self.current_orders,
                'error': False,
            }
        return self.result_dict


    def _generate_price(self):
        self.bid_order = self._get_orderbook(self.polo, self.sell_coin_long, 'bid')
        if self.bid_order['error']:
           raise RuntimeError('Failed to grab buy order book for selling - %s' % self.bid_order['error'])
        self.ask_order = self._get_orderbook(self.polo, self.buy_coin_long, 'ask')
        if self.ask_order['error']:
           raise RuntimeError('Failed to grab sell order book for buying - %s' % self.ask_order['error'])

        self.order_book_trade = {
            'buy_coin_long': self.buy_coin_long,
            'sell_coin_long': self.sell_coin_long,
            'formated_date': time.strftime("%Y%m%d-%H%M%S"),
            }
        self.order_units_bid = 0
        self.order_units_ask = 0
        for x in self.bid_order['result']:
            self.order_units_bid += float(x[1])
            if self.order_units_bid > self.pur_buy_coin_units:
                self.order_book_trade['cur_sell_coin_price'] = float(x[0])
                self.order_book_trade['cur_sell_usdt'] = self.pur_buy_coin_units * float(x[0])
                break

        for x in self.ask_order['result']:
            self.order_units_ask += float(x[1])
            self.buy_units = self.order_book_trade['cur_sell_usdt'] / float(x[0])
            if self.order_units_ask > self.buy_units:
                self.order_book_trade['cur_buy_coin_price'] = float(x[0])
                break

        self.formated_date = self.order_book_trade['formated_date']
        self.cur_sell_coin_price = self.order_book_trade['cur_sell_coin_price']
        self.cur_buy_coin_price = self.order_book_trade['cur_buy_coin_price']
        self.factor_increasing = self._is_factor_increasing(self.cur_sell_coin_price, self.cur_buy_coin_price)

        # calc units to sell less fee and total used from selling theose units at current price
        self.units_less_fees = self.pur_buy_coin_units - (self.pur_buy_coin_units * self.worst_trade_fee)
        self.cur_sale_usdt = self.cur_sell_coin_price * self.units_less_fees

        # calc purchase factor and add or subtract worst case fee to get break even factor
        if self.factor_increasing:
            self.pur_factor = self.pur_buy_coin_price / self.pur_sell_coin_price
            self.cur_factor = self.cur_sell_coin_price / self.cur_buy_coin_price
            self.even_factor = self.pur_factor + (self.pur_factor * self.worst_trade_fee)
            # calculate even buy coin
            self.even_buy_coin_price = self.cur_sell_coin_price / self.even_factor
        else:
            self.pur_factor = self.pur_sell_coin_price / self.pur_buy_coin_price
            self.cur_factor = self.cur_buy_coin_price / self.cur_sell_coin_price
            self.even_factor = self.pur_factor - (self.pur_factor * self.worst_trade_fee)
            # calculate even buy coin price
            self.even_buy_coin_price = self.cur_sell_coin_price * self.even_factor

        # calculate current buy coin units
        self.cur_buy_coin_units = self.cur_sale_usdt / self.cur_buy_coin_price
        # calculate even buy coin units
        self.even_buy_coin_units = self.cur_sale_usdt / self.even_buy_coin_price

        self.purchase_stats_dict = {
            'name': 'purchase',
            'date': self.formated_date,
            #'factor': format(self.pur_factor, '.4f'),
            'factor': round(self.pur_factor, 4),
            'buy_coin_price': round(self.pur_buy_coin_price, 8),
            'buy_coin_units': round(self.pur_buy_coin_units, 8),
            #'buy_coin_price': self.pur_buy_coin_price,
            #'buy_coin_units': self.pur_buy_coin_units,
            'buy_coin_short': self.buy_coin_short,
            'buy_coin_long': self.buy_coin_long,
            #'sell_coin_price': round(self.pur_sell_coin_price, 4),
            'sell_coin_price': self.pur_sell_coin_price,
            'sell_coin_short': self.sell_coin_short,
        }
        self.current_stats_dict = {
            'name': 'current',
            'date': self.formated_date,
            #'factor': format(self.cur_factor, '.4f'),
            'factor': round(self.cur_factor, 4),
            'buy_coin_price': round(self.cur_buy_coin_price, 8),
            'buy_coin_units': round(self.cur_buy_coin_units, 8),
            #'buy_coin_price': self.cur_buy_coin_price,
            #'buy_coin_units': self.cur_buy_coin_units,
            'buy_coin_short': self.buy_coin_short,
            'buy_coin_long': self.buy_coin_long,
            'sell_coin_price': self.cur_sell_coin_price,
            'sell_coin_units': self.pur_buy_coin_units,
            'sell_coin_short': self.sell_coin_short,
            'sell_coin_long': self.sell_coin_long,
        }
        self.even_stats_dict = {
            'name': 'even',
            'date': self.formated_date,
            #'factor': format(self.even_factor, '.4f'),
            'factor': round(self.even_factor, 4),
            'buy_coin_price': round(self.even_buy_coin_price, 8),
            'buy_coin_units': round(self.even_buy_coin_units, 8),
            #'buy_coin_price': self.even_buy_coin_price,
            #'buy_coin_units': self.even_buy_coin_units,
            'buy_coin_short': self.buy_coin_short,
            'buy_coin_long': self.buy_coin_long,
            #'sell_coin_price': round(self.cur_sell_coin_price, 4),
            'sell_coin_price': self.cur_sell_coin_price,
            'sell_coin_short': self.sell_coin_short,
        }
        return self.purchase_stats_dict, self.current_stats_dict, self.even_stats_dict


    def _generate_targets(self, max_target_value, worst_trade_fee, factor_increasing, purchase_stats_dict, current_stats_dict, even_stats_dict):

        self.max_target_value = max_target_value
        self.trade_fee = worst_trade_fee / 2
        self.factor_increasing = factor_increasing
        self.pur = purchase_stats_dict
        self.curr = current_stats_dict
        self.even = even_stats_dict
        self.lod_targets = []

        # first add even target
        self.even_target =  self.even
        self.even_target['name'] = 0.0
        self.lod_targets.append(self.even_target)

        # then loop in the rest of the targets
        self.count = 0.0
        # estimate total from sell - based on units to sell and current sell price
        self.sell_total = self.curr['sell_coin_price'] * (self.pur['buy_coin_units']-(self.pur['buy_coin_units'] * self.trade_fee))
        while (self.count < self.max_target_value):
            self.count = self.count + 0.5
            self.factor_adjustment = self.even['factor'] * self.count * 0.01
            if self.factor_increasing:
                self.target_factor = self.even['factor'] + self.factor_adjustment
                self.target_buy_coin_price = self.curr['sell_coin_price'] / self.target_factor
            else:
                self.target_factor = self.even['factor'] - self.factor_adjustment
                self.target_buy_coin_price = self.curr['sell_coin_price'] * self.target_factor

            self.target_buy_coin_units = self.sell_total / self.target_buy_coin_price
            self.current_target_dict = {
                'name': self.count,
                'date': current_stats_dict['date'],
                'factor': self.target_factor,
                'buy_coin_price': round(self.target_buy_coin_price, 8),
                'buy_coin_units': round(self.target_buy_coin_units, 8),
                'buy_coin_short': current_stats_dict['buy_coin_short'],
                'sell_coin_price': current_stats_dict['sell_coin_price'],
                'sell_coin_short': current_stats_dict['sell_coin_short'],
            }
            self.lod_targets.append(self.current_target_dict)

        return self.lod_targets




class JsonProfiles:
    '''
    Takes trading pair and checks if exists in JSON file
    if not in JSON, it grabs current order book prices and updates
    JSON with ratio, current price, long and short names and
    generic qauntity values
    '''
    def __init__(self, json_file, pair_list, polo=False, worst_trade_fee=0.005):

        self.json_file = json_file
        self.pair_list = pair_list
        self.polo = polo
        self.worst_trade_fee = worst_trade_fee

        # create current trade pair list
        self.pair_list_curr = {
            'fsym': self.pair_list['fsym'],
            'fiat': self.pair_list['fiat'],
            'tsym': self.pair_list['tsym']
        }
        # create previous trade pair list
        self.pair_list_prev = {
            'fsym': self.pair_list['tsym'],
            'fiat': self.pair_list['fiat'],
            'tsym': self.pair_list['fsym']
        }

        # get complete data from JSON file
        try:
            self.json_data_complete = self._get_json_trades()
        except:
            raise

        # get trade details of previous pair trade
        self.pair_prev_trade_details = self._check_pair_in_json(self.pair_list_prev)
        self.pair_prev_check_error = False
        # if trading pair does not exist get details and update JSON dict
        if self.pair_prev_trade_details['error']:
            self.pair_prev_check_error = self.pair_prev_trade_details['result']
            try:
                self.json_data_complete = self._add_new_to_json()
            except:
                raise
            # get trade details of previous pair traded
            self.pair_prev_trade_details = self._check_pair_in_json(self.pair_list_prev)

    def check_previously_traded(self):
        return self.pair_prev_check_error

    def get_previous_trade_details(self):
        return self.pair_prev_trade_details

    def get_updated_json_data(self):
        return self.json_data_complete

    def write_json_data(self, j_data, p_list, j_update):
        self.j_data_complete = self._update_json_dict(j_data, p_list, j_update)
        self._write_json_data(self.j_data_complete)
        return self.j_data_complete

    def get_short_long_names(self):
        '''
        create short and long names for current and previous trade
        return results in a dictionary
        '''
        self.pair_list_prev_transformed = self._pair_list_transform(self.pair_list_prev)
        self.pair_list_curr_transformed = self._pair_list_transform(self.pair_list_curr)
        self.short_long_names = {
            'prev_trade' : self.pair_list_prev_transformed,
            'curr_trade' : self.pair_list_curr_transformed,
        }
        return self.short_long_names

    def _add_new_to_json(self):
        '''
        Add new pair to JSON dictionary
        populate details from current order book values
        '''
        if not self.polo:
            raise RuntimeError('Failed to add new pair to JSON profile - no poloniex object passed')

        self.short_long_names = self.get_short_long_names()
        self.prev_trade = self.short_long_names['prev_trade']
        # generate generic trade values so coin pair can be profiled
        self.prof_dict = {
            'fsym_name_long':  self.prev_trade['fsym_name_long'],
            'fsym_name_short':  self.prev_trade['fsym_name_short'],
            'tsym_name_long':  self.prev_trade['tsym_name_long'],
            'tsym_name_short':  self.prev_trade['tsym_name_short'],
            'tsym_units': 1,
            'tsym_price': 1,
            'fsym_units': 1,
            'fsym_price': 1,
        }
        
        # profile pair
        self.mycoins = ProfilePairs(self.polo, self.worst_trade_fee, self.prof_dict)
        # get current stats only dont care for other two dics it returns
        dont_care_dic1, self.current_stats_dict, dont_care_dic2 = self.mycoins.get_even_only()
        # build json update
        self.json_update = {
                      'ratio': format(self.current_stats_dict['factor'], '.4f'),
                      'tsym_price': format(self.current_stats_dict['buy_coin_price'], '.8f'),
                      'tsym_units': '1',
                      'tsym_name_short': self.prev_trade['tsym_name_short'],
                      'tsym_name_long': self.prev_trade['tsym_name_long'],
                      'fsym_price': format(self.current_stats_dict['sell_coin_price'], '.8f'),
                      'fsym_units': '1',
                      'fsym_name_short': self.prev_trade['fsym_name_short'],
                      'fsym_name_long': self.prev_trade['fsym_name_long'],
        }

        # update json dictionary
        self.json_data_updated = self._update_json_dict(self.json_data_complete, self.pair_list_prev, self.json_update)
        #logger.info('JSON missing syms - updating new sym based on current order book prices and ratio')
       
        #write JSON dictionary to file
        self._write_json_data(self.json_data_updated)
        
        return self.json_data_updated



    def _update_json_dict(self, j_data, p_list, j_update):
        '''
        j_data - complete JSON data from file
        p_list - pair list
        j_update - partial JSON data that needs to be added or updated

        JSON structure per pair

        fsym: {
            fiat: {
                tsym: {
                   'ratio': '',
                   'fsym_price': '',
                   'tsym_price': '',
                   'fsym_units': '',
                   'tsym_units': '',
                   'fsym_name_short': '',
                   'tsym_name_short': '',
                   'fsym_name_long': '',
                   'tsym_name_long': '',
                },
            },
        }
        '''
        self.j_data = j_data
        self.p_list = p_list
        self.fsym = p_list['fsym']
        self.fiat = p_list['fiat']
        self.tsym = p_list['tsym']
        self.j_update = j_update

        # calc timestamps for reference only, I do not call the values in the script
        self.time_stamp_local = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_stamp_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        self.trans = self._pair_list_transform(self.p_list)
        self.tsym_updates = {
            self.tsym: {
               'ratio': self.j_update['ratio'],
               'time_stamp_local': self.time_stamp_local,
               'time_stamp_utc': self.time_stamp_utc,
               'tsym_price': self.j_update['tsym_price'],
               'tsym_units': self.j_update['tsym_units'],
               'fsym_price': self.j_update['fsym_price'],
               'fsym_units': self.j_update['fsym_units'],
               'fsym_name_short': self.trans['fsym_name_short'],
               'tsym_name_short': self.trans['tsym_name_short'],
               'fsym_name_long': self.trans['fsym_name_long'],
               'tsym_name_long': self.trans['tsym_name_long'],
            },
        }

        self.check_pair = self._check_pair_in_json(self.p_list)
        ## if pair does not exist
        if self.check_pair['error']:
            if 'fsym' in self.check_pair['sym']:
                # build json structure
                self.dict = { self.fsym: { self.fiat: {}, }, }
                # combine json structure to update
                self.dict[self.fsym][self.fiat].update(self.tsym_updates)
                # update main json
                self.j_data.update(self.dict)
            elif 'fiat' in self.check_pair['sym']:
                self.dict = { self.fiat: {}, }
                self.dict[self.fiat].update(self.tsym_updates)
                self.j_data[self.fsym].update(self.dict)
            else:
                self.dict = self.tsym_updates
                self.j_data[self.fsym][self.fiat].update(self.dict)
        ## if pair already exists - this targets only the updates
        else:
            #j_data[fsym][fiat][tsym]['ratio'] = j_update['ratio']
            #j_data[fsym][fiat][tsym]['tsym_price'] = j_update['tsym_price']
            #j_data[fsym][fiat][tsym]['tsym_units'] = j_update['tsym_units']
            #logger.debug('JSON update from tsym %s %s %s' % (fsym, fiat, tsym))
            self.dict = self.tsym_updates
            self.j_data[self.fsym][self.fiat].update(self.dict)
        # return complete JSON after being updated
        return self.j_data



    def _write_json_data(self, dict_to_json):
        '''
        Writing JSON data
        '''
        self.dict_to_json = dict_to_json

        with open(self.json_file, 'w') as f:
             json.dump(self.dict_to_json,
                       f,
                       sort_keys = False,
                       indent = 4,
                       ensure_ascii = False)



    def _check_pair_in_json(self, pair_list):
        '''
        checks for previous trade in JSON that matches pair list
        if successful returns trading pairs details
        if not successful returns details of which symbol was not found
        '''
        self.fsym = pair_list['fsym']
        self.fiat = pair_list['fiat']
        self.tsym = pair_list['tsym']

        self.trading_pairs = '{}_{}_{}'.format(self.fsym.upper(), self.fiat.upper(), self.tsym.upper())
        
        self.result_dict = {
            'error': True,
            'result': None,
            'sym': None,
        }
        
        if not self.fsym in self.json_data_complete:
            self.result_dict['result'] = "No previous trade for {} in JSON - Missing SELL symbol {}".format(self.trading_pairs, self.fsym.upper())
            self.result_dict['sym'] = "fsym"
        elif not self.fiat in self.json_data_complete[self.fsym]:
            self.result_dict['result'] = "No previous trade for {} in JSON - Missing FIAT symbol {}".format(self.trading_pairs, self.fiat.upper())
            self.result_dict['sym'] = "fiat"
        elif not self.tsym in self.json_data_complete[self.fsym][self.fiat]:
            self.result_dict['result'] = "No previous trade for {} in JSON - Missing BUY symbol {}".format(self.trading_pairs, self.tsym.upper())
            self.result_dict['sym'] = "tsym"
        else:
            self.result_dict['error'] = False
            self.result_dict['result'] = self.json_data_complete[self.fsym][self.fiat][self.tsym]
        return self.result_dict



    def _get_json_trades(self):
        '''
        read in details from JSON file
        '''
        self.json_data_complete = False
        ## Reading data back
        with open(self.json_file, 'r') as f:
             try:
                 self.json_data_complete = json.load(f)
             except ValueError as err:
                 raise RuntimeError('JSON value error %s' % err)
             except Exception, err:
                 raise RuntimeError('JSON unknown error %s' % err)
        return self.json_data_complete



    def _pair_list_transform(self, pair_list):
        '''
        create long and short symbol names
        '''
        fsym = pair_list['fsym']
        fiat = pair_list['fiat']
        tsym = pair_list['tsym']

        self.pair_list_transformed = {
            'fsym_name_short': fsym.upper(),
            'fsym_name_long': '{}_{}'.format(fiat.upper(), fsym.upper()),
            'tsym_name_short':  tsym.upper(),
            'tsym_name_long': '{}_{}'.format(fiat.upper(), tsym.upper()),
        }
        return self.pair_list_transformed
