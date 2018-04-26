POLO TRADER
===========
'polo_trader' is alpha and should not be used without supervision. Use at your own risk.

'polo_trader' is a tool for automating trades on the Poloniex Exchange. The script trades 
between two different coins/tokens via a fiat token/coin when the difference in purchase prices
hits a user controlled trading ratio. The script will continuously trade back and forth between 
the user defined coins/tokens, everytime it hits the trading threshold.

Polo Trader features
--------------------

* Automates trading on Poloneix exchange based on last trade ratio
* Calculates trading threshold based on last trade coin prices
* Trades between 'USDT' pairs 'USDT_XRP', 'USDT_STR', 'USDT_NXT', 'USDT_ETH', 'USDT_BTC'
* Trades between 'ETH' pairs 'ETH_XRP', 'ETH_STR', 'ETH_NXT', 'ETH_BTC'
* Trades between 'BTC' pairs 'BTC_XRP', 'BTC_STR', 'BTC_NXT', 'BTC_ETH',
* Tracks last trade between pairs


How it works
------------
User defines the amount of units to sell, the From and To trading coins/tokens (symbols) and the fiat 
the trade will go via. The tool looks for a previous trade between the two symbols and calculates the 
break even trading ratio between the two symbols. The break even ratio is calculated using the last
sale and buy price with the addition of the exchange's worst case fees added to the ratio. From the
break even ratio, the trading ratio is calculated which becomes the trading threshold. The user can
control the trading threshold by defining a trading factor which is added to the break even ratio. The
tool then uses the exchange's order books for both symbols and calculates the price required to fill
the sale of the defined From units and the estimated To units. Using the From and To prices, the current
trading ratio is calculated and when the current traind threshold is reached the script begins to sell 
and buy based on the From and To prices.

