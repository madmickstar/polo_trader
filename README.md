POLO TRADER
===========
`polo_trader` is alpha at present and should not be used without supervising its actions, especially at
the time of trading.

`polo_trader` is a tool for automating trades on the Poloniex Exchange. The script trades 
between two different crypto pairs via a fiat crypto when the difference in purchase prices,
hits a user controlled trading ratio. The script continuously trades back and forth between 
the two crypto pairs, every time the trading threshold is hit.

Polo Trader features
--------------------

* Automates trades between crypto pairs on the Poloniex exchange 
* Requires private API to make trades
* Trades between 
  * USDT pairs 'USDT_XRP', 'USDT_STR', 'USDT_NXT', 'USDT_ETH', 'USDT_BTC'
  * ETH pairs 'ETH_XRP', 'ETH_STR', 'ETH_NXT', 'ETH_BTC'
  * BTC pairs 'BTC_XRP', 'BTC_STR', 'BTC_NXT', 'BTC_ETH'
* Tracks most recent trade in a local JSON file 

How it works
------------
* User initiates script defining Sell, Buy and Fiat cryptos
* Script grabs from local JSON file the following items from last trade
  * Amount of units purchased which become sell in next trade
  * The From and To crypto pairs (symbols)
  * The crypto fiat the trade will go via, USDT, BTC or ETH 
  * Last trade buy/sell prices
  * Last trade ratio
* If last trade does not exist, script grabs current prices from exchange order books and populates the 
local JSON file with the details
* Script calculates the breakeven ratio between the two crypto pairs. The breakeven ratio is calculated
using the last trade's sell and buy prices, with the addition of the exchange's worst case fees added
* From the breakeven ratio, the trading ratio/threshold is calculated. The user controls the trading
threshold by defining a trading factor which is added to the breakeven ratio. 
* The script then uses the exchange's order books for both sell and buy crypto pairs to calculates the 
price required to fill the sale units and the estimated purchase units. These prices are then used to 
calculate the current trading ratio which the script uses to monitoring
* When the current trading ratio matches the desired trading threshold, the script initiates a sell and  
then a buy of the trading crypto pairs


Usage
-----
`
polo_trader [ -s {xrp, str, nxt, eth, btc} | -b {str, xrp, nxt, eth, btc} | -f {usdt, eth, btc} | -mf {0.0025, 0.0015} | -tf {0...10} | -l | -t | -d | -h | --version ]
    
`

Argument  | Type   | Format               | Default           | Description
----------|--------|----------------------|-------------------|--------------------
-s [crypto] | string | -s {xrp,str,nxt,eth,btc} | xrp | Selling crypto
-b [crypto] | string | -b {str,xrp,nxt,eth,btc} | str | Buying crypto
-f [crypto] | string | -f {usdt,eth,btc} | usdt | Fiat crypto
-mf [fee] | float | -mf {0.0025,0.0015} | 0.0025 | Maximum fee for trading
-tf [factor] | float | -tf {0.0,0.5,1.0,..,9.0,9.5,10.0} | 10.0 | Trading factor percentage, added to breakeven ratio to produce trading factor
-l | switch | -l | disabled | Log to a file
-t | switch | -t | disabled | Timestamp output
-d | switch | -d | disabled | Enables debug output to console
-h | switch | -h | disabled | Prints help to console   
--version | switch | --version | disabled | Displays version