POLO TRADER
===========
`polo_trader` is alpha at present and should not be used without supervising its actions, especially at 
the time of trading.

`polo_trader` is a tool for automating trades on the Poloniex Exchange. The script trades between two 
different crypto pairs via a crypto fiat when the difference in purchase prices, hits a user controlled 
trading ratio/threshold. The script continuously trades back and forth between the two crypto pairs, 
every time the trading threshold is hit.

`polo_trader` includes a monitoring script called `order_book` which enables the ability to view the current 
gain/loss of the crypto pairs you want to trade between. Always run `order_book` before using `polo_trader`, 
to ensure the outcome is desirable.


Polo Trader Features
--------------------
* Automates trades between crypto pairs on the Poloniex exchange 
* Requires private API to make trades
* Trades between 
  * USDT pairs - USDT_XRP, USDT_STR, USDT_NXT, USDT_ETH, USDT_BTC
  * BTC pairs - BTC_XRP, BTC_STR, BTC_NXT, BTC_ETH
* Tracks most recent trade in a local JSON file 
* Includes a monitoring only script called Order Book


How It Works
------------
* User initiates script defining Sell, Buy and Fiat cryptos
* Script grabs from local JSON file the following items from last trade
  * Amount of units purchased which become sell units in next trade
  * The From and To crypto pairs (symbols)
  * The crypto fiat the trade will go via, USDT or BTC
  * Last trade buy/sell prices
  * Last trade ratio
* If last trade does not exist, script grabs current prices from exchange order books and populates the 
local JSON file with the details
* Script calculates the breakeven ratio between the two crypto pairs. The breakeven ratio is calculated
using the last trade's sell and buy prices, with the addition of the exchange's worst case fees added
* From the breakeven ratio, the trading ratio/threshold is calculated. The user controls the trading
threshold by defining a trading factor which is added to the breakeven ratio. 
* The script then uses the exchange's order books for both sell and buy crypto pairs to calculate the 
price required to fill the sale units and the estimated purchase units. These prices are then used to 
calculate the current trading ratio which the script uses for monitoring
* When the current trading ratio matches the desired trading threshold, the script initiates a sell and 
then a buy of the trading crypto pairs


Install Instructions
--------------------
* Install 3rd party dependency 
```
pip install https://github.com/s4w3d0ff/python-poloniex/archive/v0.4.7.zip
```
* Download package from the following link and unzip
```
https://github.com/madmickstar/polo_trader/archive/develop.zip
```
* Install requirements
```
pip install -r requirements.txt
```
* Rename config.txt to config.py and edit keys
```
api_key = 'you_api_key_here'
private_key = 'your_private_key_here'
```


Usage Polo Trader
-----------------
```
polo_trader [ -s {xrp, str, nxt, eth, btc} | -b {str, xrp, nxt, eth, btc} | -f {usdt, btc} | -r {0.0000} | -u {0.0000} | -tt {0.0,..,20.0} | -mf {0.0025, 0.0015} | -ss {1..10} | -ph {10..50} | -e | -l | -t | -d | -h | --version ] 
```

Argument  | Type   | Format               | Default           | Description
----------|--------|----------------------|-------------------|--------------------
-s [crypto] | string | -s {xrp,str,nxt,eth,btc} | xrp | Selling crypto
-b [crypto] | string | -b {str,xrp,nxt,eth,btc} | str | Buying crypto
-f [crypto] | string | -f {usdt,btc} | usdt | Fiat crypto
-r [ratio] | float | -r {0.0000} | 0.0 | Trading ratio over ride, handy if you want to trade below break even point or between threshold percentages
-u [units] | float | -u {0.0000} | 0.0 | Sell units over ride, set units you want to sell, over rides units retrieved from previous trde stored in JSON
-tt [percent] | float | -tt {0.0,0.5,1.0,..,19.0,19.5,20.0} | 10.0 | Trading threshold percentage, added to breakeven ratio to produce trading threshold
-mf [fee] | float | -mf {0.0025,0.0015} | 0.0025 | Maximum fee for trading
-ss [poles] | int | -ss {1..10} | 3 | Amount of consecutive times ratio needs to be evaluated above threshold before triggering trading
-ph [lines] | int | -ph {10..50} | 20 | Print headers to screen every x amount of lines
-e | switch | -e | disabled | Email when trading
-l | switch | -l | disabled | Log to a file
-t | switch | -t | disabled | Timestamp output
-d | switch | -d | disabled | Enables debug output to console
-h | switch | -h | disabled | Prints help to console   
--version | switch | --version | disabled | Displays version


Usage Order Book
-----------------
```
order_book [ -s {xrp, str, nxt, eth, btc} | -b {str, xrp, nxt, eth, btc} | -f {usdt, btc} | -mf {0.0025, 0.0015} | -l | -t | -d | -h | --version ]
```

Argument  | Type   | Format               | Default           | Description
----------|--------|----------------------|-------------------|--------------------
-s [crypto] | string | -s {xrp,str,nxt,eth,btc} | xrp | Selling crypto
-b [crypto] | string | -b {str,xrp,nxt,eth,btc} | str | Buying crypto
-f [crypto] | string | -f {usdt,btc} | usdt | Fiat crypto
-mf [fee] | float | -mf {0.0025,0.0015} | 0.0025 | Maximum fee for trading
-l | switch | -l | disabled | Log to a file
-t | switch | -t | disabled | Timestamp output
-d | switch | -d | disabled | Enables debug output to console
-h | switch | -h | disabled | Prints help to console   
--version | switch | --version | disabled | Displays version


Disclaimer
------------
I am not your financial adviser, nor is this tool. This software is for educational purposes only. Use the software at your own risk. The authors and all affiliates assume no responsibility for your trading results.

The `polo_trader` script uses a simple trade strategy which may underperform other trading strategies. Read the code, understand the way the script works and never leave the script unmonitored. 

Always start by running the `order_book` monitoring script and do not engage in trading using the `polo_trader` script, before you understand the potential outcomes and what gain/loss you should expect.
