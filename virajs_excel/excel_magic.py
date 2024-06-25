import xlwings as xw
import traceback
from constants import O_CNFG, S_DATA, O_SETG, logging
from toolkit.kokoo import timer
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


def run(API, WS):
    # initiate ws and get quote
    while True:
        try:
            if WS.kws.is_connected():
                # WS.kws.set_mode(WS.kws.MODE_LTP, subscribe)
                for tick in WS.ticks:
                    print(tick)
                    """
                    history = candle_data(API, tick["instrument_token"])
                    print(history)
                    """
        except KeyboardInterrupt:
            # if keyboard interrupt stop the websocket
            WS.kws.on_close
            __import__("sys").exit(1)
        except Exception as e:
            print(f"run: {e}")
            print_exc()
            SystemExit(1)
        finally:
            __import__("time").sleep(1)


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


def check_api_connectivity():
    global api
    api = init()
    return 1 if ltp(api) else 0


def load_bank_nifty_symbol_details():
    global bank_nifty_df
    nfo_symbols_df = pd.read_csv(S_DATA + 'NFO_symbols.csv')
    bank_nifty_df = nfo_symbols_df[nfo_symbols_df['tradingsymbol'].str.startswith('BANKNIFTY')]
    excel_name = xw.Book(EXCEL_FILE_NAME)
    bank_nifty_sheet = excel_name.sheets("BANKNIFTY_SYMBOL_DETAILS")
    bank_nifty_sheet.range("a1:j5000").value = None
    bank_nifty_sheet.range("a1").options(index=False, header=True).value = bank_nifty_df


def get_orders():
    excel_name = xw.Book(EXCEL_FILE_NAME)
    orders_sheet = excel_name.sheets("ORDERS")
    orders_sheet.range("a1:j5000").value = None
    orders_df = pd.DataFrame(api.orders)
    if orders_df.empty:
        orders_sheet.range("a1").value = "No order details found"
    else:
        orders_sheet.range("a1").options(index=False, header=True).value = orders_df

def get_positions():
    excel_name = xw.Book(EXCEL_FILE_NAME)
    positions_sheet = excel_name.sheets("POSITIONS")
    positions_sheet.range("a1:j5000").value = None
    positions_df = pd.DataFrame(api.positions)
    if positions_df.empty:
        positions_sheet.range("a1").value = "No position details found"
    else:
        positions_sheet.range("a1").options(index=False, header=True).value = positions_df

def get_holdings():
    excel_name = xw.Book(EXCEL_FILE_NAME)
    holdings_sheet = excel_name.sheets("HOLDINGS")
    holdings_sheet.range("a1:j5000").value = None
    holdings_df = pd.DataFrame(api.kite.holdings())
    if holdings_df.empty:
        holdings_sheet.range("a1").value = "No holding details found"
    else:
        holdings_sheet.range("a1").options(index=False, header=True).value = holdings_df

def fix_fund_df(fund_json):
    output = []
    for k, v in fund_json.items():
        o = {}
        # if k in ('equity', 'commodity'):
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
    excel_name = xw.Book(EXCEL_FILE_NAME)
    funds_sheet = excel_name.sheets("FUNDS")
    funds_sheet.range("a1:j5000").value = None
    funds_df = pd.DataFrame(fix_fund_df(api.kite.margins()))
    if funds_df.empty:
        funds_sheet.range("a1").value = "No funding details found"
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
    ohlc_df = df.resample('1min').agg({'ltp': 'ohlc'})
    return ohlc_df[('ltp', 'low')].tolist()


def get_order_id(order_details):
    symbol = order_details[0]
    exchange = order_details[1]
    qty = order_details[2]
    order_type = order_details[3]
    limit_price = order_details[4]
    trigger_price = order_details[5]
    for order in orders.get('data', []):
        if all(
            order["tradingsymbol"] == symbol, 
            order["exchange"] == exchange, 
            order["filled_quantity"] == qty,
            order["transaction_type"] == order_type,
            order["price"] == limit_price,
            order["trigger_price"] == trigger_price
        ): 
            return order["order_id"]
    return None


def get_qty_from_positions(order_details):
    symbol = order_details[0]
    exchange = order_details[1]
    for position in positions.get('data',{}).get('net',[]):
        if position["tradingsymbol"] == symbol and position["exchange"] == exchange:
            return position["quantity"]
    return None

def get_order_id_for_position(order_details):
    symbol = order_details[0]
    exchange = order_details[1]
    # qty = order_details[2]
    # average_price = order_details[3]
    # order_type = order_details[4]
    orders_to_cancel = []
    for order in orders.get('data', []):
        if all(
            order["tradingsymbol"] == symbol, 
            order["exchange"] == exchange, 
            order["status"] not in ('COMPLETE', 'CANCELLED', 'REJECTED') 
        ): 
            orders_to_cancel.append(order["order_id"])
    return orders_to_cancel
    

def get_live():
    """
    READY - 1
    ORDER - 0
    """
    global WS, symbol_in_focus, instrument_token, orders, positions
    excel_name = xw.Book(EXCEL_FILE_NAME)
    live_sheet = excel_name.sheets("LIVE")
    symbol_in_focus = ""
    delay_candle_set_time = pdlm.now()
    candle_gen_time = pdlm.now()
    order_book_refresh_time = pdlm.now()
    position_book_refresh_time = pdlm.now()
    
    computed_candle_data = pd.DataFrame(columns=["time", "ltp"])
    while True:
        if pdlm.now() > order_book_refresh_time.add(seconds=2):
            orders = api.orders
            orders = [order for order in orders.get('data',[]) if order["status"] not in ('COMPLETE', 'CANCELLED', 'REJECTED')]
            order_book_refresh_time = pdlm.now()
        if pdlm.now() > position_book_refresh_time.add(seconds=2):
            positions = api.positions
            positions = pdlm.now()


        # Table 2 
        symbol_in_excel = live_sheet.range("I4").value
        if symbol_in_focus != symbol_in_excel:
            symbol_in_focus = symbol_in_excel
            print(f"Detected new symbol - {symbol_in_excel}")
            try:
                instrument_token = bank_nifty_df[bank_nifty_df["tradingsymbol"] == symbol_in_focus]['instrument_token'].to_list()[0]
            except:
                print(traceback.format_exc())
                break
            live_sheet.range("H4").value = str(instrument_token)
            WS.sym_tkn = [instrument_token]
            live_sheet.range("K4:P4").value = get_historical_low_candle()
            live_sheet.range("Q4:V4").value = get_historical_low_candle()
            delay_candle_set_time = pdlm.now()
            computed_candle_data = pd.DataFrame(columns=["time", "ltp"])
            print(f"Subscribed to token - {instrument_token}")
        if WS.ticks:
            tick = WS.ticks[0]['last_price']
            live_sheet.range("J4").value = tick
            new_row = pd.DataFrame({'time': [pdlm.now()], 'ltp': [tick]})
            if not computed_candle_data.empty:
                computed_candle_data = pd.concat([computed_candle_data, new_row], ignore_index=True)
            else:
                computed_candle_data = new_row.copy()
        if pdlm.now() > candle_gen_time.add(minutes=1):
            print("computing new 1m candle")
            existing_value = live_sheet.range("K4:P4").value
            new_values = get_manual_low_candle(computed_candle_data)
            for val in new_values[::-1]:
                existing_value.insert(0, val)
            existing_value = existing_value[:6]
            live_sheet.range("K4:P4").value = existing_value
            candle_gen_time = pdlm.now()
        if pdlm.now() > delay_candle_set_time.add(seconds=15):
            print("refreshing 15s delay candle")
            live_sheet.range("Q4:V4").value = live_sheet.range("K4:P4").value
            delay_candle_set_time = pdlm.now()

        # Table 1
        shortlisted_detail = len(bank_nifty_df[bank_nifty_df["tradingsymbol"] == symbol_in_focus]['instrument_token'].to_list())
        if len(shortlisted_detail) == 1:
            buy_order_details = live_sheet.range(f"b{4}:e{13}").value
            buy_order_details_changed = False
            # print(buy_order_details)
            for index, order_details in enumerate(buy_order_details):
                # print(index)
                if order_details[3] == 'READY':
                    continue
                if order_details[3] == 'ORDER':
                    qty = order_details[0]
                    price = order_details[1]
                    trigger_price = order_details[2]
                    args = {
                        "variety": api.kite.VARIETY_REGULAR,
                        "exchange": api.kite.EXCHANGE_NFO,
                        "tradingsymbol": symbol_in_focus,
                        "transaction_type": api.kite.TRANSACTION_TYPE_BUY,
                        "quantity": qty,
                        "product": api.kite.PRODUCT_MIS,
                        "order_type": api.kite.ORDER_TYPE_SL if trigger_price else api.kite.ORDER_TYPE_LIMIT,
                        "price": price,
                        "trigger_price": trigger_price,
                        "tag": "EXCEL_TRADE",
                    }
                    _ = api.order_place(args)
                    buy_order_details[index][3] = 'READY'
                    buy_order_details_changed = True
            if buy_order_details_changed:
                live_sheet.range(f"b{4}:e{13}").value = buy_order_details
            # print(buy_order_details)
        

        # Table 3 # Open orders 
        open_order_details = live_sheet.range(f"b{18}:n{29}").value
        open_order_details_changed = False
        # print(open_order_details)
        for index, order_details in enumerate(open_order_details):
            # print(index)
            if order_details[8] == 'READY':
                pass
            elif order_details[8] == 'ORDER':
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
                    _ = api.order_modify(args)
                    open_order_details[index][8] = 'READY'
                    open_order_details_changed = True
            elif order_details[11] == 'READY':
                pass
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
                    _ = api.order_modify(args)
                    open_order_details[index][11] = 'READY'
                    open_order_details_changed = True
            elif order_details[12] == 'READY':
                pass
            elif order_details[12] == 'ORDER':
                order_id = get_order_id(order_details)
                if order_id:
                    args = {
                        "order_id": order_id,
                        "variety": api.kite.VARIETY_REGULAR,
                        "price": 0,
                        "order_type": api.kite.ORDER_TYPE_MARKET,
                    }
                    _ = api.order_modify(args)
                    open_order_details[index][12] = 'READY'
                    open_order_details_changed = True
        if open_order_details_changed:
            live_sheet.range(f"b{18}:n{29}").value = open_order_details
        # print(open_order_details)
        if pdlm.now() > order_book_refresh_time.add(seconds=2):
            orders = api.orders
            orders_in_excel = [
                [order['tradingsymbol'], order['exchange'], order['filled_quantity'], order['transaction_type'], order.get('price', 0), order.get('trigger_price', 0)] 
                for order in orders.get('data',[]) if order["status"] not in ('COMPLETE', 'CANCELLED', 'REJECTED')]
            order_book_refresh_time = pdlm.now()
            live_sheet.range(f"b{18}:g{29}").value = orders_in_excel


        # Table 4 # Open positions
        open_position_details = live_sheet.range(f"q{18}:ab{29}").value
        open_position_details_changed = False
        # print(open_position_details)
        for index, order_details in enumerate(open_position_details):
            # print(index)
            if order_details[7] == 'READY':
                pass
            elif order_details[7] == 'ORDER':
                sl_trigger = order_details[5]
                limit = order_details[6]
                order_ids = get_order_id_for_position(order_details)
                for order_id in order_ids:
                    args = {"order_id": order_id, "variety": api.kite.VARIETY_REGULAR}
                    _ = api.order_cancel(args)
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
                    open_position_details[index][7] = 'READY'
                    open_position_details_changed = True
            elif order_details[10] == 'READY':
                pass
            elif order_details[10] == 'ORDER':
                sl_trigger = order_details[8]
                limit = order_details[9]
                order_ids = get_order_id_for_position(order_details)
                for order_id in order_ids:
                    args = {"order_id": order_id, "variety": api.kite.VARIETY_REGULAR}
                    _ = api.order_cancel(args)
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
            elif order_details[11] == 'READY':
                pass
            elif order_details[11] == 'ORDER':
                order_ids = get_order_id_for_position(order_details)
                for order_id in order_ids:
                    args = {"order_id": order_id, "variety": api.kite.VARIETY_REGULAR}
                    _ = api.order_cancel(args)
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
                    _ = api.order_place(args)
                open_position_details[index][11] = 'READY'
                open_position_details_changed = True
        if open_position_details_changed:
            live_sheet.range(f"q{18}:ab{29}").value = open_position_details
        print(open_position_details)
        if pdlm.now() > position_book_refresh_time.add(seconds=2):
            positions = api.positions
            positions_in_excel = [
                [position['tradingsymbol'], position['exchange'], position['quantity'], position['transaction_type'], position.get('average_price', 0), "BUY"] 
                for position in positions.get('data',{}).get('net',[])]
            position_book_refresh_time = pdlm.now()
            live_sheet.range(f"q{18}:u{29}").value = positions_in_excel


def StartThread():
    try:

        # Define the threads and put them in an array
        threads = []
        threads.append(Thread(target=get_live))
        threads.append(Thread(target=get_orders))
        threads.append(Thread(target=get_positions))
        threads.append(Thread(target=get_holdings))
        threads.append(Thread(target=get_funds))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

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
    global WS
    print(f"Viraj's Excel Based Terminal program initialized")
    if check_api_connectivity() == 1:
        print("Connection Established!!")
        load_bank_nifty_symbol_details()
        print("Loaded bank nifty symbols sheet")
        clear_live_data()
        print("Cleared data in live sheet")
        
        WS = Wsocket(api.kite, [])
        print("Connected to WebSocket...")
        print("Enjoy the automation...")
        StartThread()
        
    else:
        print(
            "Please check the API connection!"
        )

if __name__ == "__main__":
    try:
        main()
    except:
        print(traceback.format_exc())