import os
import time
import xlwings as xw
import traceback
from constants import O_CNFG, S_DATA, O_SETG, logging
from toolkit.kokoo import timer
from datetime import datetime as dtime, timezone
from login import get_bypass, get_zerodha
from wsocket import Wsocket
from symbol import Symbol, dct_sym
import pendulum as pdlm
import pandas as pd
from traceback import print_exc
from threading import Thread


EXCEL_FILE_NAME = "Viraj_s_Excel_Trading.xlsm"

def init():
    CRED = {}
    if O_SETG["broker"] == "bypass":
        CRED.update(O_CNFG["bypass"])
        return get_bypass(O_CNFG["bypass"], S_DATA)
    else:
        CRED.update(O_CNFG["zerodha"])
        return get_zerodha(O_CNFG["zerodha"], S_DATA)


def candle_data(API, token):
    FM = (
        pdlm.now()
        .subtract(days=2)
        .set(hour=9, minute=15, second=0)
        .strftime("%Y-%m-%d %H:%M:%S")
    )
    to = pdlm.now().strftime("%Y-%m-%d %H:%M:%S")
    kwargs = dict(instrument_token=token, from_date=FM, to_date=to, interval="minute")
    lst = API.kite.historical_data(**kwargs)
    lst = [
        dict(
            date=x["date"],
            open=x["open"],
            high=x["high"],
            low=x["low"],
            close=x["close"],
        )
        for x in lst
    ]
    timer(1)
    return lst


# def run(API, WS):
#     # initiate ws and get quote
#     while True:
#         try:
#             if WS.kws.is_connected():
#                 # WS.kws.set_mode(WS.kws.MODE_LTP, subscribe)
#                 for tick in WS.ticks:
#                     print(tick)
#                     """
#                     history = candle_data(API, tick["instrument_token"])
#                     print(history)
#                     """
#         except KeyboardInterrupt:
#             # if keyboard interrupt stop the websocket
#             WS.kws.on_close
#             __import__("sys").exit(1)
#         except Exception as e:
#             print(f"run: {e}")
#             print_exc()
#             SystemExit(1)
#         finally:
#             __import__("time").sleep(1)


def ltp(API):
    from omspy_brokers.bypass import Bypass

    try:
        # hardcoding lastprice in bypass for time being
        if isinstance(API, Bypass):
            return 47295
        # works in paid api only
        base = O_SETG["base"]
        symbol_key = dct_sym[base]
        exch_sym = symbol_key["exch"] + ":" + symbol_key["index"].upper()
        logging.debug(exch_sym)
        resp = API.kite.ltp(exch_sym)
        return resp[exch_sym]["last_price"]
    except Exception as e:
        print(f"ltp: {e}")
        print_exc()

def fetch_user():
    try:
        global api
        api = init()
        data = api.kite.profile()
        api.username = data.get('user_name')
        return True
    except Exception as e:
        print(f"Error while fetching user profile: {e}")
        return False


def load_bank_nifty_symbol_details():
    # need to first check for file if not found then download.
    fpath = S_DATA + "NFO_symbols.csv"
    # first check for symbol file.
    df = None
    if os.path.exists(fpath): 
        ttm = dtime.now(timezone.utc)
        ftm = dtime.fromtimestamp(os.path.getctime(fpath), timezone.utc)
        # Delete old file, symbol file. 
        if(ftm.date() != ttm.date() and ttm.hour > 2):
            os.remove(fpath)
    
    if not os.path.exists(fpath):
        # Download file & save it.
        url = "https://api.kite.trade/instruments/NFO"
        print("Downloading & Saving Symbol file.")
        df = pd.read_csv(url, on_bad_lines="skip")
        df.fillna(pd.NA, inplace=True)
        df.to_csv(fpath, index=False)
        
    if df is None:
        nfo_symbols_df = pd.read_csv(fpath, on_bad_lines="skip")
        nfo_symbols_df.fillna(pd.NA, inplace=True)
    else:
        nfo_symbols_df = df

    global bank_nifty_df
    bank_nifty_df = nfo_symbols_df[nfo_symbols_df['tradingsymbol'].str.startswith('BANKNIFTY')]
    excel_name = xw.Book(EXCEL_FILE_NAME)
    bank_nifty_sheet = excel_name.sheets("BANKNIFTY_SYMBOL_DETAILS")
    bank_nifty_sheet.range("a1:j5000").value = None
    bank_nifty_sheet.range("a1").options(index=False, header=True).value = bank_nifty_df
    excel_name.save()


def get_orders(orders=None):
    try:
        excel_name = xw.Book(EXCEL_FILE_NAME)
        orders_sheet = excel_name.sheets("ORDERS")
        orders_sheet.range("a1:aj900").font.size = 11
        orders_sheet.range("a1:aj900").value = None
        if not orders: orders = fetch_orders(update=True)
        orders_df = pd.DataFrame(orders)
    except Exception as e:
        print(f"[{time.ctime()}] Something is Wrong while updating Orders Sheet: {e}.")
        return
    if orders_df.empty:
        cell = orders_sheet.range("f3")
        cell.font.size = 30
        cell.value = "No order details found"
    else:
        orders_df.drop(columns=['meta'], inplace=True)
        cell = orders_sheet.range("a1").options(index=False, header=True)
        cell.value = orders_df
        

def get_positions():
    try:
        excel_name = xw.Book(EXCEL_FILE_NAME)
        positions_sheet = excel_name.sheets("POSITIONS")
        positions_sheet.range("a1:aj900").font.size = 11
        positions_sheet.range("a1:aj900").value = None
        positions_df = pd.DataFrame(api.positions)
    except Exception as e:
        print(f"[{time.ctime()}] Something is Wrong while updating Positions Sheet: {e}.")
        return
    if positions_df.empty:
        cell = positions_sheet.range("f3")
        cell.font.size = 30
        cell.value = "No position details found"
    else:
        cell = positions_sheet.range("a1").options(index=False, header=True)
        cell.value = positions_df

def get_holdings():
    try:
        excel_name = xw.Book(EXCEL_FILE_NAME)
        holdings_sheet = excel_name.sheets("HOLDINGS")
        holdings_sheet.range("a1:aj900").font.size = None
        holdings_sheet.range("a1:aj900").value = None
        holdings_df = pd.DataFrame(api.kite.holdings())
    except Exception as e:
        print(f"[{time.ctime()}] Something is Wrong while updating Holdings Sheet: {e}.")
        return
    if holdings_df.empty:
        holdings_sheet.range("f3").font.size = 30
        holdings_sheet.range("f3").value = "No holding details found"
    else:
        holdings_sheet.range("a1").options(index=False, header=True).value = holdings_df

def fix_fund_df(fund_json):
    output = []
    for k, v in fund_json.items():
        o = {}
        o["type"] = k
        for k, _v in v.items():
            if isinstance(_v, dict):
                for _k, __v in _v.items():
                    o[k+"-"+_k] = __v
            else:
                o[k] = _v
        output.append(o)
    return pd.DataFrame(output)

def get_funds():
    try:
        excel_name = xw.Book(EXCEL_FILE_NAME)
        funds_sheet = excel_name.sheets("FUNDS")
        funds_sheet.range("a1:z50").font.size = 11
        funds_sheet.range("a1:z50").value = None
        funds_df = pd.DataFrame(fix_fund_df(api.kite.margins()))
    except Exception as e:
        print(f"[{time.ctime()}] Something is Wrong while updating Funds Sheet: {e}.")
        return
    if funds_df.empty:
        funds_sheet.range("f3").font.size = 30
        funds_sheet.range("f3").value = "No funding details found"
    else:
        funds_sheet.range("a1").options(index=False, header=True).value = funds_df


def get_historical_low_candle():
    data = candle_data(api, instrument_token)[::-1]
    data_to_return = ['-','-','-','-','-', '-']
    if data:
        for i, candle in enumerate(data):
            if i >= 6:
                break
            data_to_return[i] = candle.get('low','-')
    return data_to_return
    
def get_manual_low_candle(computed_candle_data):
    df =computed_candle_data.copy()
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    if df.empty: print(df)
    ohlc_df = df.resample('1min').agg({'ltp': 'ohlc'})
    return ohlc_df[('ltp', 'low')].tolist()


def get_order_id(order_details):
    symbol = order_details[0]
    exchange = order_details[1]
    qty = order_details[2]
    order_type = order_details[3]
    limit_price = order_details[4]
    trigger_price = order_details[5]
    
    for order in orders:
        if all((
            order["symbol"] == symbol, 
            order["exchange"] == exchange, 
            order["filled_quantity"] == qty,
            order["side"] == order_type,
            order["price"] == limit_price,
            order["trigger_price"] == trigger_price
        )): 
            return order["order_id"]
    return None


def get_qty_from_positions(order_details):
    symbol = order_details[0]
    exchange = order_details[1]
    for position in positions:
        if position["symbol"] == symbol and position["exchange"] == exchange:
            return position["quantity"]
    return 0

def get_order_id_for_position(order_details):
    symbol = order_details[0]
    exchange = order_details[1]
    orders_to_cancel = []
    for order in orders:
        if all((
            order["symbol"] == symbol,
            order["exchange"] == exchange, 
            order["status"] not in ('COMPLETE', 'CANCELED', 'REJECTED'))
        ): 
            orders_to_cancel.append(order["order_id"])
    return orders_to_cancel


def fetch_orders(status=None, update=False):
    try:
        global orders
        if update: orders = api.orders
        if orders is None: return None
        
        if status is None: return orders
        elif status.lower() == "open":
            oders = [order for order in orders if order and order.get("status") not in ("COMPLETE", "CANCELED", "REJECTED")]
            return oders
        elif status.lower() == "close":
            oders = [order for order in orders if order and order.get("status", "") in ("COMPLETE", "CANCELED", "REJECTED")]
            return oders
    except Exception as e:
        print(f"Error while getting Orders: {e}.")
    
def fetch_positions(update=False):
    try:
        global positions
        if update: positions = api.positions
        if positions is None: return None
        else: return positions
    except Exception as e:
        print(f"Error while getting Positions: {e}.")


def update_sheet_data(excel):
    name = excel.sheets.active.name
    sheets = ("FUNDS", "HOLDINGS", "POSITIONS", "ORDERS")
    if name not in sheets: return
    lname = DATA.get('lname')
    if lname == name: return
    DATA['lname'] = name
    
    # update Funds.
    if name == sheets[0]:
        get_funds()
    
    # update Holdings.
    elif name == sheets[1]:
        get_holdings()

    # update Postions.
    elif name == sheets[2]:
        get_positions()

    # update Orders.
    elif name == sheets[3]:
        get_orders()

    time.sleep(0.5)

    

def get_live():
    """
    READY - 1
    ORDER - 0
    """
    global WS, symbol_in_focus, instrument_token, orders, positions, DATA
    DATA = {}
    orders = positions = []
    excel_name = xw.Book(EXCEL_FILE_NAME)
    live_sheet = excel_name.sheets("LIVE")
    symbol_in_focus = None
    delay_candle_set_time = pdlm.now()
    candle_gen_time = pdlm.now()
    order_book_refresh_time = pdlm.now()
    position_book_refresh_time = pdlm.now()
    # Fetching Orders for 1st time.
    orders = api.orders
    computed_candle_data = pd.DataFrame(columns=["time", "ltp"])
    while not shutdown:
        # To Update Data in sheets...
        update_sheet_data(excel_name)

        # To update Orders Data & Table 3 - Open Orders.
        if pdlm.now() > order_book_refresh_time.add(seconds=2):
            oders = fetch_orders(status='open', update=True)
            if oders is not None:
                # symbol, exchange, filled qty, side, price, triggerPrice. 
                orders_to_excel = [
                    [order.get('symbol'), order.get('exchange'), order.get('filled_quantity'), order.get('side'), order.get('price', 0), order.get('trigger_price', 0)]
                    for order in oders if order]        
                order_book_refresh_time = pdlm.now()
                # Updating Table 3: Open Orders.
                live_sheet.range("b18:g29").value = orders_to_excel
        
        # To update PositionBook.
        if pdlm.now() > position_book_refresh_time.add(seconds=2):
            position = fetch_positions(True)
            if position is not None:
                # symbol, exchange, qty, average_price, side. 
                pos_to_excel = [
                    [pos.get('symbol'), pos.get('exchange'), pos.get('quantity'), pos.get('average_price', 0), pos.get('side', "BUY")]
                    for pos in position if pos]
                position_book_refresh_time = pdlm.now()
                # Updating Table 4: Open Positions.
                live_sheet.range("q18:u29").value = pos_to_excel



        # Table 2: To Update ltp & candle data.
        symbol_in_excel = live_sheet.range("I4").value
        if (symbol_in_excel is not None and symbol_in_focus != symbol_in_excel):
            symbol_in_focus = symbol_in_excel
            try:
                instd = bank_nifty_df[bank_nifty_df["tradingsymbol"] == symbol_in_excel].to_dict(orient='records')
                if len(instd) == 0: 
                    print(f"Wrong Symbol: {symbol_in_excel}")
                    WS.unsubsribe_all()
                    live_sheet.range("G4:V4").value = None
                    symbol_in_focus = None
                    continue
                print(f"Detected new symbol: {symbol_in_focus}")
                instrument_token = instd[0].get('instrument_token')
                WS.unsubsribe_all()
                WS.subscribe(instrument_token)
                print(f"[{time.ctime()}] Subscribed to Token: {instrument_token} ({symbol_in_focus}).")
                
                live_sheet.range("G4").value = str(instd[0].get('expiry'))
                live_sheet.range("H4").value = str(instrument_token)
                live_sheet.range("K4:P4").value = get_historical_low_candle()
                live_sheet.range("Q4:V4").value = get_historical_low_candle()
                delay_candle_set_time = pdlm.now()
                computed_candle_data = pd.DataFrame(columns=["time", "ltp"])

            except:
                print(traceback.format_exc())
                break
        
        # Tick Processing
        if WS.ticks and symbol_in_focus is not None:
            tick = WS.ticks[0]
            ltick = live_sheet.range("J4").value
            ltp = tick.get('ltp')
            if ltick != ltp: 
                live_sheet.range("J4").value = ltp
            new_row = pd.DataFrame([{'time': tick.get('time', pdlm.now()), 'ltp': ltp}])
            if not computed_candle_data.empty:
                computed_candle_data = pd.concat([computed_candle_data, new_row], ignore_index=True)
            else:
                computed_candle_data = new_row.copy()
        
            # Candle Data Processing...
            if pdlm.now() > candle_gen_time.add(minutes=1):
                existing_value = live_sheet.range("K4:P4").value
                if not computed_candle_data.empty:
                    print("computing new 1m candle")
                    new_values = get_manual_low_candle(computed_candle_data)
                    for val in new_values[::-1]:
                        existing_value.insert(0, val)
                    existing_value = existing_value[:6]
                    live_sheet.range("K4:P4").value = existing_value
                    candle_gen_time = pdlm.now()
                else:
                    print(f"Data is empty can't compute Candle.")
                    candle_gen_time = pdlm.now()
            if pdlm.now() > delay_candle_set_time.add(seconds=15):
                print(f"[{time.ctime()}] refreshing 15s delay candle")
                live_sheet.range("Q4:V4").value = live_sheet.range("K4:P4").value
                delay_candle_set_time = pdlm.now()

        elif not WS.ticks and symbol_in_focus is not None:
            print('No tick found...')


        # Table 1: To place requested orders. 
        shortlisted_detail = len(bank_nifty_df[bank_nifty_df["tradingsymbol"] == symbol_in_focus]['instrument_token'].to_list())
        if shortlisted_detail == 1:
            buy_order_details = live_sheet.range(f"b{4}:e{13}").value
            buy_order_details_changed = False
            
            for index, order_details in enumerate(buy_order_details):
                if order_details[3] == 'ORDER':
                    qty = order_details[0]
                    price = order_details[1]
                    trigger_price = order_details[2]
                    args = {
                        "variety": api.kite.VARIETY_REGULAR,
                        "exchange": api.kite.EXCHANGE_NFO,
                        "tradingsymbol": symbol_in_focus,
                        "transaction_type": api.kite.TRANSACTION_TYPE_BUY,
                        "quantity": int(qty),
                        "product": api.kite.PRODUCT_MIS,
                        "order_type": api.kite.ORDER_TYPE_SL if trigger_price else api.kite.ORDER_TYPE_LIMIT,
                        "price": price,
                        "trigger_price": trigger_price,
                        "tag": "EXCEL_TRADE",
                    }
                    print(args)
                    try:
                        d = api.order_place(**args)
                    except Exception as e:
                        print(f"[{time.ctime()}] Error while placing order: {e}")
                    else:
                        print(f"[{time.ctime()}] Order Placed Successfully, OrderId: {d}")
                    buy_order_details[index][3] = 'READY'
                    buy_order_details_changed = True
            # It will reset the button.
            if buy_order_details_changed:
                live_sheet.range(f"b{4}:e{13}").value = buy_order_details
        

        # Table 3: To place requested orders. 
        open_order_details = live_sheet.range(f"b{18}:n{29}").value
        open_order_details_changed = False
        
        for index, order_details in enumerate(open_order_details):  
            if order_details[8] == 'ORDER':
                sl_trigger = order_details[6]
                limit = order_details[7]
                order_id = get_order_id(order_details)
                if order_id:
                    args = {
                        "order_id": order_id,
                        "variety": api.kite.VARIETY_REGULAR,
                        "price": limit,
                        "order_type": api.kite.ORDER_TYPE_SL if sl_trigger else api.kite.ORDER_TYPE_LIMIT,
                        "trigger_price": sl_trigger,
                    }
                    try:
                        d = api.order_modify(**args)
                    except Exception as e:
                        print(f"[{time.ctime()}] Error while modifying order: {e}")
                    else:
                        print(f"[{time.ctime()}] Order Modified Successfully, OrderId: {d}")
                    open_order_details[index][8] = 'READY'
                    open_order_details_changed = True
            
            elif order_details[11] == 'ORDER':
                sl_trigger = order_details[9]
                limit = order_details[10]
                order_id = get_order_id(order_details)
                if order_id:
                    args = {
                        "order_id": order_id,
                        "variety": api.kite.VARIETY_REGULAR,
                        "price": limit,
                        "order_type": api.kite.ORDER_TYPE_SL if sl_trigger else api.kite.ORDER_TYPE_LIMIT,
                        "trigger_price": sl_trigger,
                    }
                    try:
                        d = api.order_modify(**args)
                    except Exception as e:
                        print(f"[{time.ctime()}] Error while modifying order: {e}")
                    else:
                        print(f"[{time.ctime()}] Order Modified Successfully, OrderId: {d}")
                    open_order_details[index][11] = 'READY'
                    open_order_details_changed = True

            elif order_details[12] == 'ORDER':
                order_id = get_order_id(order_details)
                if order_id:
                    args = {
                        "order_id": order_id,
                        "variety": api.kite.VARIETY_REGULAR,
                        "price": 0,
                        "order_type": api.kite.ORDER_TYPE_MARKET,
                    }
                    try:
                        d = api.order_modify(**args)
                    except Exception as e:
                        print(f"[{time.ctime()}] Error while modifying order: {e}")
                    else:
                        print(f"[{time.ctime()}] Order Modified Successfully, OrderId: {d}")
                    open_order_details[index][12] = 'READY'
                    open_order_details_changed = True
        # It will reset the buttons.
        if open_order_details_changed:
            live_sheet.range(f"b{18}:n{29}").value = open_order_details
        

        # Table 4 # Open positions
        open_position_details = live_sheet.range(f"q{18}:ab{29}").value
        open_position_details_changed = False
        for index, order_details in enumerate(open_position_details):
            if order_details[7] == 'ORDER':
                sl_trigger = order_details[5]
                limit = order_details[6]
                # 1. Cancel open orders of the symbol.
                order_ids = get_order_id_for_position(order_details)
                for order_id in order_ids:
                    args = {"order_id": order_id, "variety": api.kite.VARIETY_REGULAR}
                    try:
                        _ = api.order_cancel(**args)
                    except Exception as e:
                        print(f'[{time.ctime()}] Error while cancelling open order: {e}')

                # 2. Place Sell Order to close position.
                qty_ = get_qty_from_positions(order_details)
                if qty_ > 0:
                    args = {
                            "variety": api.kite.VARIETY_REGULAR,
                            "exchange": order_details[1],
                            "tradingsymbol": order_details[0],
                            "transaction_type": api.kite.TRANSACTION_TYPE_SELL,
                            "quantity": qty_,
                            "product": api.kite.PRODUCT_MIS,
                            "order_type": api.kite.ORDER_TYPE_SL if sl_trigger else api.kite.ORDER_TYPE_LIMIT,
                            "price": limit,
                            "trigger_price": sl_trigger,
                            "tag": "EXCEL_TRADE",
                        }
                    try:
                        d = api.order_place(**args)
                    except Exception as e:
                        print(f"[{time.ctime()}] Error while placing order: {e}")
                    else:
                        print(f"[{time.ctime()}] Order Placed Successfully, OrderId: {d}.")
                    open_position_details[index][7] = 'READY'
                    open_position_details_changed = True

            elif order_details[10] == 'ORDER':
                sl_trigger = order_details[8]
                limit = order_details[9]
                order_ids = get_order_id_for_position(order_details)
                # 1. Cancel Open Orders of the symbol.
                for order_id in order_ids:
                    args = {"order_id": order_id, "variety": api.kite.VARIETY_REGULAR}
                    try:
                        _ = api.order_cancel(args)
                    except Exception as e:
                        print(f"[{time.ctime()}] Error while cancelling open order: {e}")

                # 2. Place Sell Order to close position.
                qty_ = get_qty_from_positions(order_details)
                if qty_ > 0:
                    args = {
                            "variety": api.kite.VARIETY_REGULAR,
                            "exchange": order_details[1],
                            "tradingsymbol": order_details[0],
                            "transaction_type": api.kite.TRANSACTION_TYPE_SELL,
                            "quantity": qty_,
                            "product": api.kite.PRODUCT_MIS,
                            "order_type": api.kite.ORDER_TYPE_SL if sl_trigger else api.kite.ORDER_TYPE_LIMIT,
                            "price": limit,
                            "trigger_price": sl_trigger,
                            "tag": "EXCEL_TRADE",
                        }
                    _ = api.order_place(args)
                    open_position_details[index][10] = 'READY'
                    open_position_details_changed = True
            
            elif order_details[11] == 'ORDER':
                order_ids = get_order_id_for_position(order_details)
                # 1. Cancel open orders of the symbol.
                for order_id in order_ids:
                    args = {"order_id": order_id, "variety": api.kite.VARIETY_REGULAR}
                    try:
                        _ = api.order_cancel(**args)
                    except Exception as e:
                        print(f'[{time.ctime()}] Error while cancelling open order: {e}')

                # 2. Place Sell Order to close position.
                qty_ = get_qty_from_positions(order_details)
                if qty_ > 0:
                    args = {
                            "variety": api.kite.VARIETY_REGULAR,
                            "exchange": order_details[1],
                            "tradingsymbol": order_details[0],
                            "transaction_type": api.kite.TRANSACTION_TYPE_SELL,
                            "quantity": qty_,
                            "product": api.kite.PRODUCT_MIS,
                            "order_type": api.kite.ORDER_TYPE_MARKET,
                            "price": 0,
                            "tag": "EXCEL_TRADE",
                        }
                    try:
                        d = api.order_place(**args)
                    except Exception as e:
                        print(f"[{time.ctime()}] Error while placing order: {e}")
                    else:
                        print(f"[{time.ctime()}] Order Placed Successfully, OrderId: {d}.")
                open_position_details[index][11] = 'READY'
                open_position_details_changed = True
        # It will reset the buttons.
        if open_position_details_changed:
            live_sheet.range(f"q{18}:ab{29}").value = open_position_details

        # sleep
        time.sleep(0.7)

    # Closing Websocket before exit.
    WS.kws.close()
    while WS.kws.is_connected():
        time.sleep(0.5)
    print(f"[{time.ctime()}] Closing the program...")


def StartThread():
    try:
        # Define the threads and put them in an array
        global threads
        threads = []
        target = (get_live, get_orders, get_positions, get_holdings, get_funds)
        for t in target:
            thread = Thread(target=t)
            thread.start()
            threads.append(thread)
    except Exception:
        print(traceback.format_exc())

def clear_live_data():
    excel_name = xw.Book(EXCEL_FILE_NAME)
    live_sheet = excel_name.sheets("LIVE")
    # Clearing Candle data
    live_sheet.range("l4:x4").value = None
    # Clearing Open Order data # TODO: make this dynamic or 
    live_sheet.range("b18:g500").value = None
    # Clearing Open positions data
    live_sheet.range("q18:u500").value = None
    

def main():
    global WS, shutdown
    shutdown = False
    
    try:
        # Icons -
        # 🟢, 🛈, ℹ , 🔔, 🚀 ...
        print(f"Zerodha Excel Based Terminal program initialized")
        print(f"📌 Process id: {os.getpid()}.")
        if fetch_user():
            print(f"🟢 Logged in Successfully for {api.username}")
            load_bank_nifty_symbol_details()
            print("ℹ  Loaded bank nifty symbols sheet")
            clear_live_data()
            print("ℹ  Cleared data in live sheet")
            
            WS = Wsocket(api.kite)
            # Some time required to initialize ws connection.
            while not WS.kws.is_connected():
                time.sleep(1)
            print("🟢 Connected to WebSocket...")
            print("🚀 Enjoy the automation...")
            StartThread()

            while True:
                if not any(th.is_alive() for th in threads):
                    print("Exiting the program...")
                    WS.kws.close()
                    while WS.kws.is_connected():
                        time.sleep(0.5)
                    break
                time.sleep(5)
        else:
            print("Please check the API connection or Either your access token is expired!")
            inp = input('Do want to Refresh your access token [y/n]: ').lower()
            if inp == 'y':
                os.remove(api.tokpath)
                print('Restart your program!')

    except KeyboardInterrupt:
        shutdown = True


if __name__ == "__main__":
    try:
        main()
    except:
        print(traceback.format_exc())