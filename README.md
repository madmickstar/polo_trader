POLO TRADER
===========
`polo_trader` is alpha at present and should not be used without supervising it, especially at
the time of trading.

`polo_trader` is a tool for automating trades on the Poloniex Exchange. The script trades 
between two different coins/tokens via a fiat token/coin when the difference in purchase prices
hits a user controlled trading ratio. The script will continuously trade back and forth between 
the user defined coins/tokens, every time it hits the trading threshold.

Polo Trader features
--------------------

* Automates trades between trading pairs on the Poloniex exchange 
* Trades between 'USDT' pairs 'USDT_XRP', 'USDT_STR', 'USDT_NXT', 'USDT_ETH', 'USDT_BTC'
* Trades between 'ETH' pairs 'ETH_XRP', 'ETH_STR', 'ETH_NXT', 'ETH_BTC'
* Trades between 'BTC' pairs 'BTC_XRP', 'BTC_STR', 'BTC_NXT', 'BTC_ETH'

How it works
------------
* User defines or script grabs from local JSON file the following
  * Amount of units to sell in next trade
  * To and From trading coins/tokens (symbols)
  * The crypto fiat the trade will go via, USDT, BTC or ETH 
  * Last trade buy sell prices
  * Last trade ratio
* Script calculates the break even trading ratio between the two symbols. The breakeven ratio is 
calculated using the last sale and buy price with the addition of the exchange's worst case fees added
* From the breakeven ratio, the trading ratio is calculated which becomes the trading threshold. The 
user can control the trading threshold by defining a trading factor which is added to the break even ratio. 
* The script then uses the exchange's order books for both sell and buy symbols and calculates the price
required to fill the sale units and the estimated purchase units. 
* The current trading ratio is then calculated from the buy/sell crypto prices and when the current trading
ratio matches the trading threshold, automatic trading begins