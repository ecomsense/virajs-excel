import xlwings as xw
from constants import O_CNFG, S_DATA, logging
from toolkit.kokoo import timer
from datetime import datetime as dtime, timezone
from login import get_bypass, get_zerodha
from wsocket import Wsocket
import pendulum as pdlm
import pandas as pd
from traceback import print_exc
from threading import Thread
import os
import time


EXCEL_FILE_NAME = "VirajExcel.xlsm"
EXCEL_FILE = S_DATA + EXCEL_FILE_NAME

def show_msg(err_txt, msg_type=None):   
    excel_name = xw.Book(EXCEL_FILE)
    live_sheet = excel_name.sheets("LIVE")
    sheet_range = live_sheet.range("a1")
    sheet_range.color =  (146, 208, 80) if msg_type else (234, 99, 70) 
    sheet_range.value = str(err_txt)

def init():
    broker = O_CNFG.get("broker", None)
    if broker is not None:
        cnfg = O_CNFG.get(broker, None)
        if cnfg is not None:
            print(cnfg)
            if broker == "bypass":
                return get_bypass(cnfg, S_DATA)
            elif broker == "zerodha": 
                return get_zerodha(cnfg, S_DATA)     
            else:
                print("cannot find the broker you mentioned in the config yml file") 
    else:
        cnfg = O_CNFG.get("zerodha", None)
        default = O_CNFG.get("bypass", None)
        if cnfg:
            print(cnfg)
            return get_zerodha(cnfg, S_DATA)
        elif default:
            print(default)
            return get_bypass(default, S_DATA)
        else:
            print("cannot find any valid broker in the config yml file")
            __import__("sys").exit()


def candle_data(API, token):
    try:
        lst = []
        FM = (
            pdlm.now()
            .subtract(days=2)
            .set(hour=9, minute=15, second=0)
            .strftime("%Y-%m-%d %H:%M:%S")
        )
        to = pdlm.now().strftime("%Y-%m-%d %H:%M:%S")
        kwargs = dict(instrument_token=token, from_date=FM, to_date=to, interval="minute")
        hist = API.kite.historical_data(**kwargs)
        if hist is not None and any(hist):
            lst = [
                dict(
                    date=x["date"],
                    open=x["open"],
                    high=x["high"],
                    low=x["low"],
                    close=x["close"],
                )
                for x in hist
            ]                          
    except Exception as e:
        # show_msg(e)
        print_exc()        
    finally:
        return lst    

def load_bank_nifty_symbol_details():
    # 1. Download file if not file not or file created is older than next day 8:30AM.
    fpath = S_DATA + "NFO_symbols.csv"
    df = None
    if os.path.exists(fpath): 
        ttm = dtime.now(timezone.utc)
        ftm = dtime.fromtimestamp(os.path.getctime(fpath), timezone.utc)
        # Deleting old symbol file. 
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
    excel_name = xw.Book(EXCEL_FILE)
    bank_nifty_sheet = excel_name.sheets("BANKNIFTY_SYMBOL_DETAILS")
    bank_nifty_sheet.range("a1:j5000").value = None
    bank_nifty_sheet.range("a1").options(index=False, header=True).value = bank_nifty_df
    excel_name.save()


def get_orders(orders=None):
    try:
        excel_name = xw.Book(EXCEL_FILE)
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
        excel_name = xw.Book(EXCEL_FILE)
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
        excel_name = xw.Book(EXCEL_FILE)
        holdings_sheet = excel_name.sheets("HOLDINGS")
        holdings_sheet.range("a1:aj900").font.size = 11
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
        excel_name = xw.Book(EXCEL_FILE)
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
    try:
        data = candle_data(api, instrument_token)[::-1]
        data_to_return = ['-','-','-','-','-', '-']
        if data:
            for i, candle in enumerate(data):
                if i >= 6:
                    break
                data_to_return[i] = candle.get('low','-')
        return data_to_return
    except Exception as e:
        show_msg(e)
        print_exc()
    
def get_manual_low_candle(computed_candle_data):
    df =computed_candle_data.copy()
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
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


def fetch_positions(status=None, update=False):
    try:
        global positions
        if update: positions = api.positions
        if positions is None: return []

        if status is None: return positions
        elif status.lower() == "open":
            poss = [pos for pos in positions if pos and pos.get("quantity") != 0]
            return poss
        elif status.lower() == "close":
            poss = [pos for pos in positions if pos and pos.get("quantity") == 0]
            return poss
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

    timer(0.5)
    

def get_live():
    """
    READY - 1
    ORDER - 0
    """
    global WS, symbol_in_focus, instrument_token, orders, positions, DATA
    DATA = {}
    orders = positions = []
    excel_name = xw.Book(EXCEL_FILE)
    live_sheet = excel_name.sheets("LIVE")
    symbol_in_focus = None
    delay_candle_set_time = pdlm.now()
    candle_gen_time = pdlm.now()
    order_book_refresh_time = pdlm.now()
    position_book_refresh_time = pdlm.now()
    show_msg("HAPPY TRADING", "success")
    
    while not shutdown:
        try:            
            computed_candle_data = pd.DataFrame()
            # To Update Data in sheets...
            update_sheet_data(excel_name)

            # To update Orders Data & Table 3 - Open Orders.
            if pdlm.now() > order_book_refresh_time.add(seconds=2):
                oders = fetch_orders(status='open', update=True)
                if oders is not None:
                    # symbol, exchange, filled/qty, side, price, triggerPrice. 
                    orders_to_excel = [
                        [order.get('symbol'), order.get('exchange'), "{}/{}".format(order.get('filled_quantity'), order.get('quantity')), order.get('side'), order.get('price', 0), order.get('trigger_price', 0)]
                        for order in oders if order]        
                    order_book_refresh_time = pdlm.now()
                    if len(orders_to_excel) != 12:
                        orders_to_excel += [[None, None, None, None, None, None]]*(12-len(orders_to_excel))
                    # Updating Table 3: Open Orders.
                    live_sheet.range("C22:H33").value = orders_to_excel
            
            # To update PositionBook.
            if pdlm.now() > position_book_refresh_time.add(seconds=2):
                position = fetch_positions('open', True)
                if position:
                    # symbol, exchange, qty, average_price, side. 
                    pos_to_excel = [
                        [pos.get('symbol'), pos.get('exchange'), pos.get('quantity'), pos.get('average_price', 0), pos.get('side', "BUY")]
                        for pos in position if pos]
                    position_book_refresh_time = pdlm.now()
                    if len(pos_to_excel) != 12:
                        pos_to_excel += [[None, None, None, None, None]]*(12-len(pos_to_excel))
                    # Updating Table 4: Open Positions.
                    live_sheet.range("R22:V33").value = pos_to_excel



            # Table 2: To Update ltp & candle data.
            symbol_in_excel = live_sheet.range("I6").value
            if (symbol_in_excel is not None and symbol_in_focus != symbol_in_excel):
                symbol_in_focus = symbol_in_excel
                try:
                    fdf = bank_nifty_df[bank_nifty_df.tradingsymbol == symbol_in_excel].reset_index(drop=True).head(1)
                    # Unsubscribing Unnecessary Old Symbols.
                    WS.unsubsribe_all()
                    if fdf.empty:
                        print(f"Wrong Symbol: {symbol_in_excel}")
                        live_sheet.range("G6:V6").value = None
                        symbol_in_focus = WS.ticks = None
                        continue
                    print(f"Detected new symbol: {symbol_in_focus}")
                    instrument_token = int(fdf.instrument_token[0])
                    # Subscribing New Symbol.
                    WS.subscribe(instrument_token)
                    print(f"[{time.ctime()}] Subscribed to Token: {instrument_token} ({symbol_in_focus}).")
                    # Filling Some Infos.
                    live_sheet.range("B3").value = str(fdf.lot_size[0])
                    live_sheet.range("C3").value = str(fdf.tick_size[0])
                    itmType = str(fdf.instrument_type[0])
                    if itmType == "FUT": strike = itmType
                    else: strike = f"{fdf.strike[0]} {itmType}"
                    live_sheet.range("E3").value = str(strike)
                    live_sheet.range("G6").value = str(fdf.expiry[0])
                    live_sheet.range("H6").value = instrument_token
                    live_sheet.range("K6:P6").value = live_sheet.range("Q6:V6").value = get_historical_low_candle()
                    delay_candle_set_time = pdlm.now()
                    computed_candle_data = pd.DataFrame(columns=["time", "ltp"])
                except Exception as e:
                    msg = f"[{time.ctime()}] Error : {e}"
                    show_msg(msg)
                    print_exc()
                   
                    
            
            # Tick Processing
            if WS.ticks and symbol_in_focus is not None:
                tick = WS.ticks[0]
                ltp_cell = live_sheet.range('J6')
                live_sheet.range('J7').value = time.ctime()
                ltick = ltp_cell.value
                ltp = tick.get('ltp')
                if ltick != ltp: 
                    ltp_cell.value = ltp
                new_row = pd.DataFrame([{'time': tick.get('time', pdlm.now()), 'ltp': ltp}])
                if not computed_candle_data.empty:
                    computed_candle_data = pd.concat([computed_candle_data, new_row], ignore_index=True)
                else:
                    computed_candle_data = new_row.copy()
            
                # Candle Data Processing...
                cad_cell1 = live_sheet.range('K6:P6')
                if pdlm.now() > candle_gen_time.add(minutes=1):
                    existing_value = cad_cell1.value
                    if not computed_candle_data.empty:
                        print("computing new 1min candle")
                        new_values = get_manual_low_candle(computed_candle_data)
                        for val in new_values[::-1]:
                            existing_value.insert(0, val)
                        existing_value = existing_value[:6]
                        cad_cell1.value = existing_value
                    else:
                        print(f"Data is empty can't compute Candle.")
                    candle_gen_time = pdlm.now()

                if pdlm.now() > delay_candle_set_time.add(minutes=1, seconds=15):
                    print(f"[{time.ctime()}] refreshing 1min candle with 15s delay")
                    live_sheet.range('Q6:V6').value = cad_cell1.value
                    delay_candle_set_time = pdlm.now()


            elif not WS.ticks and symbol_in_focus is not None:
                # print('No tick found...')
                pass


            # Table 1: To Place Requested Orders.
            if symbol_in_focus:                                  
                for row in live_sheet.range('B6:E15').rows:
                    order_details = row.value
                    if order_details[3] == 'ORDER':
                        qty = order_details[0]
                        price = order_details[1]
                        trigger_price = order_details[2]
                        if not isinstance(qty, float):
                            show_msg('Error: Not valid qty.')                            
                        else:
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
                            show_msg(args, "success")
                            try:
                                d = api.order_place(**args)
                            except Exception as e:
                                msg = f"[{time.ctime()}] Error while placing order: {e}"
                                show_msg(msg)
                            else:
                                msg = f"[{time.ctime()}] Order Placed Successfully, OrderId: {d}"                                
                                show_msg(msg,"success")

                        # It will reset the button.
                        row[3].value = 'READY'



            # Table 3: To Modify Open Orders.
            for row in live_sheet.range('C22:O33').rows:
                order_details = row.value
                if order_details[8] == 'ORDER':
                    order_details[2] = int(str(order_details[2]).split('/')[0])
                    sl_trigger = order_details[6]
                    limit = order_details[7]
                    order_id = get_order_id(order_details)
                    order_type = api.kite.ORDER_TYPE_SL if sl_trigger else api.kite.ORDER_TYPE_LIMIT
                    if order_id:
                        args = {
                            "order_id": order_id,
                            "variety": api.kite.VARIETY_REGULAR,
                            "price": limit,
                            "order_type": order_type,
                            "trigger_price": sl_trigger,
                        }
                        try:
                            d = api.order_modify(**args)
                        except Exception as e:
                            msg = f"[{time.ctime()}] Error while modifying order: {e}"
                            show_msg(msg)                           
                        else:
                            msg = f"[{time.ctime()}] Modified as {order_type}-Order Successfully, OrderId: {d}"
                            row[:11].value = None
                            show_msg(msg, "success")

                    # It will clear the data & reset the button.
                    row[6:11].value = None
                    row[8].value = 'READY'
                
                elif order_details[11] == 'ORDER':
                    order_details[2] = int(str(order_details[2]).split('/')[0])
                    sl_trigger = order_details[9]
                    limit = order_details[10]
                    order_id = get_order_id(order_details)
                    order_type = api.kite.ORDER_TYPE_SL if sl_trigger else api.kite.ORDER_TYPE_LIMIT
                    if order_id:
                        args = {
                            "order_id": order_id,
                            "variety": api.kite.VARIETY_REGULAR,
                            "price": limit,
                            "order_type": order_type,
                            "trigger_price": sl_trigger,
                        }
                        try:
                            d = api.order_modify(**args)
                        except Exception as e:
                            msg = f"[{time.ctime()}] Error while modifying order: {e}"
                            show_msg(msg)
                        else:
                            msg = f"[{time.ctime()}] Modified as {order_type}-Order Successfully, OrderId: {d}"                          
                            show_msg(msg, "success")
                    
                    # It will clear the data & reset the button.
                    row[8:12].value = ['READY', None, None, 'READY']


                elif order_details[12] == 'ORDER':
                    order_details[2] = int(str(order_details[2]).split('/')[0])
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
                            msg = f"[{time.ctime()}] Error while modifying order: {e}"                            
                            show_msg(msg)
                            print_exc()
                        else:
                            msg = f"[{time.ctime()}] Modified as Market-Order Successfully, OrderId: {d}"                            
                            print(msg, "success")
                           
                    
                    # It will reset the button.
                    row[8:13].value = ['READY', None, None, 'READY', 'READY']
            


            # Table 4 # To Modify Open Positions.            
            for row in live_sheet.range('R22:AC33').rows:
                if "ORDER" not in [row.value[7], row.value[10], row.value[11]]: continue
                order_details = row.value
                
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
                            msg = f'[{time.ctime()}] Error while cancelling open order: {e}'                            
                            show_msg(msg)
                            print_exc()

                    # 2. Place Sell Order to close position.
                    qty_ = get_qty_from_positions(order_details)
                    if qty_ > 0:
                        order_type = api.kite.ORDER_TYPE_SL if sl_trigger else api.kite.ORDER_TYPE_LIMIT
                        args = {
                                "variety": api.kite.VARIETY_REGULAR,
                                "exchange": order_details[1],
                                "tradingsymbol": order_details[0],
                                "transaction_type": api.kite.TRANSACTION_TYPE_SELL,
                                "quantity": qty_,
                                "product": api.kite.PRODUCT_MIS,
                                "order_type": order_type,
                                "price": limit,
                                "trigger_price": sl_trigger,
                                "tag": "EXCEL_TRADE",
                            }
                        try:
                            d = api.order_place(**args)
                        except Exception as e:
                            msg = f"[{time.ctime()}] Error while placing {order_type}-sell order: {e}"                           
                            show_msg(msg)
                        else:
                            msg = f"[{time.ctime()}] {order_type}-Sell Order Placed Successfully, OrderId: {d}."                           
                            show_msg(msg, "success")
                    # It will clear the data & reset the button.
                    row[5:8].value = [None, None, 'READY']


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
                            msg = f"[{time.ctime()}] Error while cancelling open order: {e}"                            
                            show_msg(msg)

                    # 2. Place Sell Order to close position.
                    qty_ = get_qty_from_positions(order_details)
                    if qty_ > 0:
                        order_type = api.kite.ORDER_TYPE_SL if sl_trigger else api.kite.ORDER_TYPE_LIMIT
                        args = {
                                "variety": api.kite.VARIETY_REGULAR,
                                "exchange": order_details[1],
                                "tradingsymbol": order_details[0],
                                "transaction_type": api.kite.TRANSACTION_TYPE_SELL,
                                "quantity": qty_,
                                "product": api.kite.PRODUCT_MIS,
                                "order_type": order_type,
                                "price": limit,
                                "trigger_price": sl_trigger,
                                "tag": "EXCEL_TRADE",
                            }
                        try:
                            d = api.order_place(**args)
                        except Exception as e:
                            msg = f"[{time.ctime()}] Error while placing {order_type}-sell order: {e}"                          
                            show_msg(msg)
                        else:
                            msg = f"[{time.ctime()}] {order_type}-Sell Order Placed Successfully, OrderId: {d}."                           
                            show_msg(msg, "success")
                    # It will clear the data & reset the button.
                    row[8:11].value = [None, None, 'READY']


                elif order_details[11] == 'ORDER':
                    order_ids = get_order_id_for_position(order_details)
                    # 1. Cancel open orders of the symbol.
                    for order_id in order_ids:
                        args = {"order_id": order_id, "variety": api.kite.VARIETY_REGULAR}
                        try:
                            _ = api.order_cancel(**args)
                        except Exception as e:
                            msg = f'[{time.ctime()}] Error while cancelling open order: {e}'                           
                            show_msg(msg)
                            

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
                            msg = f"[{time.ctime()}] Error while placing market-sell order: {e}."
                            show_msg(msg)                           
                        else:
                            msg = f"[{time.ctime()}] MARKET-Sell Order Placed Successfully, OrderId: {d}."                         
                            show_msg(msg, "success")
                    
                    # It will reset the button.
                    row[7:12].value = ['READY', None, None, 'READY', 'READY']
            
            timer(0.8)
        except Exception as e:
            show_msg(e)
            print_exc()           
            

    # Closing Websocket before exit.
    WS.kws.close()
    while WS.kws.is_connected():
        timer(0.5)
    print(f"[{time.ctime()}] Closing the program...")
    excel_name.close()


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
        print_exc()
      


def clear_live_data():
    excel_name = xw.Book(EXCEL_FILE)
    live_sheet = excel_name.sheets("LIVE")
    # Clearing Candle data
    live_sheet.range("B3:C3").value = None
    live_sheet.range("E3").value = None
    live_sheet.range("G6:H6").value = None
    live_sheet.range("J6:V6").value = None
    # Clearing Open Order data # TODO: make this dynamic or 
    live_sheet.range("C22:H500").value = None
    # Clearing Open positions data
    live_sheet.range("R22:V500").value = None


def load_excel():
    # 1. checks for excel file in data folder.
    if not os.path.exists(EXCEL_FILE):
        if not os.path.exists(EXCEL_FILE_NAME):
            print('Excel file not found, i think you have deleted it, Contact The Creator.')
            exit(1)
        # move file to data folder.
        try:
            shutil = __import__('shutil')
            shutil.copy2(EXCEL_FILE_NAME, EXCEL_FILE)
        except Exception as e:
            print(f'[{time.ctime()}] Error while copying excel file to data folder: {e}')


def main():
    global WS, shutdown, api
    shutdown = False
    
    try:
        # Icons -
        # 🟢, 🛈, ℹ , 🔔, 🚀 ...
        print(f"Zerodha Excel Based Terminal program initialized")
        print(f"📌 Process id: {os.getpid()}.")
        api = init()
        if api:
            print(f"🟢 Logged in Successfully")
            load_excel()
            load_bank_nifty_symbol_details()
            print("ℹ  Loaded bank nifty symbols sheet")
            clear_live_data()
            print("ℹ  Cleared data in live sheet")
            
            WS = Wsocket(api.kite)
            # Some time required to initialize ws connection.
            while not WS.kws.is_connected():
                timer(1)
            print("🟢 Connected to WebSocket...")
            print("🚀 Enjoy the automation...")
            StartThread()

            while True:
                if not any(th.is_alive() for th in threads):
                    print("Exiting the program...")
                    WS.kws.close()
                    while WS.kws.is_connected():
                        timer(0.5)
                    break
                timer(5)
        else:
            print("Please check the API connection or Either your access token is expired!")
            print('Try Again, By Restarting your program!')
            
    except KeyboardInterrupt:
        shutdown = True


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f" excepion in main {e}")          
        print_exc()
     
