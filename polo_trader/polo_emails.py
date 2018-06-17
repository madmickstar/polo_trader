'''
Poloniex emails
 - send_message
 - email_starting_trading
 - email_finished_trading

'''
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib


def send_message(config, subject, html):
    """
    Create html email abd send 
    """
    ## Connect to host
    server_port = int(config.server_port)
    server_host = config.server
    username = config.server_username
    password = config.server_password
    from_addr = config.from_email
    to_addr = config.to_email
    
    email_status = {
        'error': True,
        'msg': "Success"
    }
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr
    
    # Record the MIME types of both parts - text/plain and text/html.
    #part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    
    # Attach parts into message container.
    #msg.attach(part1)
    msg.attach(part2)

    try:
        server = smtplib.SMTP(server_host, server_port)
        server.starttls()
    except smtplib.socket.gaierror:
        email_status['msg'] = 'Email failed to send - server connection error'
        return email_status

    ## Login
    try:
        server.login(username, password)
    except smtplib.SMTPAuthenticationError:
        server.quit()
        email_status['msg'] = 'Email failed to send - authentication error'
        return email_status

    ## Send message
    try:
        server.sendmail(from_addr, [to_addr], msg.as_string())
        email_status['error'] = False
        return email_status
    except Exception,err: # try to avoid catching Exception unless you have too
        email_status['msg'] = 'Email failed to send ' + str(err)
        return email_status
    finally:
        server.quit()
        

def email_starting_trading(ts_dict, t_dict, ri, c_dict, target_ratio):
    """
    email update with trade results
    """
    trade_status = """<p> Trade Status = {}ing<br>
                   Sell order placed = {}<br>
                   Buy order placed = {}<br>
                   </p>""".format(ts_dict['type'], ts_dict['sell_order_placed'], ts_dict['buy_order_placed'])
    current_trade = """<p>  Selling {} - {} @ {} <br>
                    Buying {} - {} @ {} <br>
                    </p>""".format(c_dict['sell_coin_long'], c_dict['sell_coin_units'], c_dict['sell_coin_price'], c_dict['buy_coin_long'], c_dict['buy_coin_units'], c_dict['buy_coin_price'])
    ratios = """<p>  Ratio Increasing = {}<br>
             Carrent ratio = {}<br>
             Trading ratio = {}<br>
             </p>""".format(ri, c_dict['ratio'], target_ratio)
    targets = """<p> Target ratio = {} <br> 
              Target trading threshold = {}%<br>
              Target buy units = {}<br> 
              </p>""".format(t_dict['ratio'], t_dict['name'], t_dict['buy_coin_units'])
    all_dicts = "<p> {}<br><br> {}<br><br> {}<br><br> </p>".format(ts_dict, t_dict, c_dict)
    
    # Create the body of the message (a plain-text and an HTML version).
    html = """<html>
            <head></head>
            <body>
              <h3> Status </h3>
              {}
              <h3> Trade </h3>
              {}
              <h3> Ratios </h3>
              {}
              <h3> Targets </h3>
              {}
              <h3> Dictionaries </h3>
              {}
            </body>
          </html>
          """.format(trade_status, current_trade, ratios, targets, all_dicts)
    return html


def email_finished_trading(ts_dict, t_dict, c_dict, sell_results, buy_results, ratio):
    """
    email update with sell / buy results
    """

    counters = """<p> Sell Counter = {}<br>
                   Buy Counter = {}<br>
                   Eval Counter = {}<br>
                   </p>""".format(ts_dict['sell_counter'], ts_dict['buy_counter'], ts_dict['eval_counter'])
                   
    current_trade = """<p>  Selling {} - {} @ {} <br>
                    Buying {} - {} @ {} <br>
                    </p>""".format(c_dict['sell_coin_long'], c_dict['sell_coin_units'], c_dict['sell_coin_price'], c_dict['buy_coin_long'], c_dict['buy_coin_units'], c_dict['buy_coin_price'])
                    
    results_sell = """<p> {} Order Number {} {} Units {} PPU {} Total {} <br>
                 """.format(sell_results['type'].title(), sell_results['order_number'], sell_results['pair'], sell_results['unit_total'], sell_results['ppu'], sell_results['fiat_total'])
            
    results_buy = """{} Order Number {} {} Units {} PPU {} Total {} <br>
                 </p>""".format(buy_results['type'].title(), buy_results['order_number'], buy_results['pair'], buy_results['unit_total'], buy_results['ppu'], buy_results['fiat_total'])
    
    trade_ratio = """Trade Ratio {} <br>
                  </p>""".format(ratio['ratio'])    
              
    all_dicts = "<p> {}<br><br> {}<br><br> {}<br><br> {}<br><br> {}<br></p>".format(ts_dict, t_dict, c_dict, sell_results, buy_results)
    
    # Create the body of the message (a plain-text and an HTML version).
    html = """<html>
            <head></head>
            <body>
              <h3> Counters </h3>
              {}
              <h3> Trade </h3>
              {}
              <h3> Results </h3>
              {}
              {}
              {}
              <h3> Dictionaries </h3>
              {}
            </body>
          </html>
          """.format(counters, current_trade, results_sell, results_buy, trade_ratio, all_dicts)
    return html   