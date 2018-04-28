POLO TRADER
===========

``polo_trader`` is alpha at present and should not be used without
supervising it, especially at the time of trading.

``polo_trader`` is a tool for automating trades on the Poloniex
Exchange. The script trades between two different coins/tokens via a
fiat token/coin when the difference in purchase prices hits a user
controlled trading ratio. The script will continuously trade back and
forth between the user defined coins/tokens, every time it hits the
trading threshold.

Polo Trader features
--------------------

-  Automates trades between trading pairs on the Poloniex exchange
-  Trades between 'USDT' pairs 'USDT\_XRP', 'USDT\_STR', 'USDT\_NXT',
   'USDT\_ETH', 'USDT\_BTC'
-  Trades between 'ETH' pairs 'ETH\_XRP', 'ETH\_STR', 'ETH\_NXT',
   'ETH\_BTC'
-  Trades between 'BTC' pairs 'BTC\_XRP', 'BTC\_STR', 'BTC\_NXT',
   'BTC\_ETH'

How it works
------------

-  User defines or script grabs from local JSON file the following
-  Amount of units to sell in next trade
-  To and From trading coins/tokens (symbols)
-  The crypto fiat the trade will go via, USDT, BTC or ETH
-  Last trade buy sell prices
-  Last trade ratio
-  Script calculates the break even trading ratio between the two
   symbols. The breakeven ratio is calculated using the last sale and
   buy price with the addition of the exchange's worst case fees added
-  From the breakeven ratio, the trading ratio is calculated which
   becomes the trading threshold. The user can control the trading
   threshold by defining a trading factor which is added to the break
   even ratio.
-  The script then uses the exchange's order books for both sell and buy
   symbols and calculates the price required to fill the sale units and
   the estimated purchase units.
-  The current trading ratio is then calculated from the buy/sell crypto
   prices and when the current trading ratio matches the trading
   threshold, automatic trading begins
