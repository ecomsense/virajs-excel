import os
import time
from symbol import Symbol, dct_sym
from traceback import print_exc

import pandas as pd
import pendulum as pdlm
import xlwings as xw
from toolkit.kokoo import timer

from constants import O_CNFG, O_SETG, S_DATA
from login import get_bypass, get_zerodha
from wsocket import Wsocket

EXCEL_FILE_NAME = "VirajExcel.xlsm"
EXCEL_FILE = S_DATA + EXCEL_FILE_NAME


def cp_xls_file():
    # 1. checks for excel file in data folder.
    if not os.path.exists(EXCEL_FILE):
        if not os.path.exists(EXCEL_FILE_NAME):
            print(
                "Excel file not found, i think you have deleted it, Contact The Creator."
            )
            exit(1)
        # move file to data folder.
        try:
            shutil = __import__("shutil")
            shutil.copy2(EXCEL_FILE_NAME, EXCEL_FILE)
        except Exception as e:
            print(
                f"[{time.ctime()}] Error while copying excel file to data folder: {e}"
            )
    return xw.Book(EXCEL_FILE)


excel_name = cp_xls_file()


def _get_orders(api, status=None, update=False):
    try:
        global orders
        if update:
            orders = api.orders
        if orders is None:
            return None

        if status is None:
            return orders
        elif status.lower() == "open":
            oders = [
                order
                for order in orders
                if order
                and order.get("status") not in ("COMPLETE", "CANCELED", "REJECTED")
            ]
            return oders
        elif status.lower() == "close":
            oders = [
                order
                for order in orders
                if order
                and order.get("status", "") in ("COMPLETE", "CANCELED", "REJECTED")
            ]
            return oders
    except Exception as e:
        print(f"Error while getting Orders: {e}.")


def _get_positions(api, status=None, update=False):
    try:
        global positions
        if update:
            positions = api.positions
        if positions is None:
            return []

        if status is None:
            return positions
        elif status.lower() == "open":
            poss = [pos for pos in positions if pos and pos.get("quantity") != 0]
            return poss
        elif status.lower() == "close":
            poss = [pos for pos in positions if pos and pos.get("quantity") == 0]
            return poss
    except Exception as e:
        print(f"Error while getting Positions: {e}.")


def _format_funds(fund_json):
    output = []
    for k, v in fund_json.items():
        o = {}
        o["type"] = k
        for k, _v in v.items():
            if isinstance(_v, dict):
                for _k, __v in _v.items():
                    o[k + "-" + _k] = __v
            else:
                o[k] = _v
        output.append(o)
    return pd.DataFrame(output)


def show_msg(err_txt, msg_type=False):
    excel_name = xw.Book(EXCEL_FILE)
    live_sheet = excel_name.sheets("LIVE")
    sheet_range = live_sheet.range("a1")
    sheet_range.color = (146, 208, 80) if msg_type else (234, 99, 70)
    sheet_range.value = str(err_txt)


def get_kite():
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


def clear_sheets():
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

    # clearing BANKNIFTY_SYMBOL_DETAILS
    symbol_sheet = excel_name.sheets("BANKNIFTY_SYMBOL_DETAILS")
    # TODO
    symbol_sheet.range("A1:C100").value = None


def save_symbol_sheet(WS):
    try:
        resp = None
        while not resp:
            resp = WS.ltp()
            print("Waiting for data...")
            timer(1)
        BASE = O_SETG["base"]
        setg = O_SETG[BASE]
        instrument_token = dct_sym[BASE]["instrument_token"]
        sym = Symbol(setg["exchange"], BASE, setg["expiry"])
        ltp = [
            dct["last_price"]
            for dct in resp
            if dct["instrument_token"] == instrument_token
        ][0]
        atm = sym.calc_atm_from_ltp(ltp)
        lst = sym.find_token_from_dump(atm)
        # get instrument token from the first item
        instrument_token = lst[0]["instrument_token"]

        is_found = False
        while not is_found:
            resp = WS.ltp(lst)
            is_found = any(
                [dct["instrument_token"] == instrument_token for dct in resp]
            )
            show_msg("waiting for data", is_found)
            timer(1)

        df_symbols = pd.DataFrame(lst)
        df_quotes = pd.DataFrame(resp)
        df_merged = pd.merge(df_symbols, df_quotes, on="instrument_token")
        symbol_sheet = excel_name.sheets("BANKNIFTY_SYMBOL_DETAILS")
        symbol_sheet.range("a1").options(index=False, header=True).value = df_merged
        excel_name.save()

    except Exception as e:
        print("[{}] Error while saving symbol sheet: {}".format(time.ctime(), e))


def filter_lows(api, instrument_token):
    def get_history(API, token):
        try:
            lst = []
            FM = (
                pdlm.now()
                .subtract(days=2)
                .set(hour=9, minute=15, second=0)
                .strftime("%Y-%m-%d %H:%M:%S")
            )
            to = pdlm.now().strftime("%Y-%m-%d %H:%M:%S")
            kwargs = dict(
                instrument_token=token, from_date=FM, to_date=to, interval="minute"
            )
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
            show_msg(e)
            print_exc()
        finally:
            return lst

    try:
        data = get_history(api, instrument_token)[::-1]
        data_to_return = ["-", "-", "-", "-", "-", "-"]
        if any(data):
            for i, candle in enumerate(data):
                if i >= 6:
                    break
                data_to_return[i] = candle.get("low", "-")
        return data_to_return
    except Exception as e:
        show_msg(e)
        print_exc()


def update_sheet_data(api):
    name = excel_name.sheets.active.name
    sheets = ("FUNDS", "HOLDINGS", "POSITIONS", "ORDERS")
    if name not in sheets:
        return

    lname = DATA.get("lname")
    if lname == name:
        return
    DATA["lname"] = name

    def get_funds():
        try:
            funds_sheet = excel_name.sheets("FUNDS")
            funds_sheet.range("a1:z50").font.size = 11
            funds_sheet.range("a1:z50").value = None
            funds_df = pd.DataFrame(_format_funds(api.kite.margins()))
        except Exception as e:
            print(
                f"[{time.ctime()}] Something is Wrong while updating Funds Sheet: {e}."
            )
            return
        if funds_df.empty:
            funds_sheet.range("f3").font.size = 30
            funds_sheet.range("f3").value = "No funding details found"
        else:
            funds_sheet.range("a1").options(index=False, header=True).value = funds_df

    def get_holdings():
        try:
            holdings_sheet = excel_name.sheets("HOLDINGS")
            holdings_sheet.range("a1:aj900").font.size = 11
            holdings_sheet.range("a1:aj900").value = None
            lst = api.kite.holdings()
            if lst is not None and any(lst):
                holdings_df = pd.DataFrame(lst)
                if holdings_df.empty:
                    holdings_sheet.range("f3").font.size = 30
                    holdings_sheet.range("f3").value = "No holding details found"
                else:
                    holdings_sheet.range("a1").options(
                        index=False, header=True
                    ).value = holdings_df
        except Exception as e:
            print(
                f"[{time.ctime()}] Something is Wrong while updating Holdings Sheet: {e}."
            )
            return

    def get_positions():
        try:
            positions_sheet = excel_name.sheets("POSITIONS")
            positions_sheet.range("a1:aj900").font.size = 11
            positions_sheet.range("a1:aj900").value = None
            positions_df = pd.DataFrame(api.positions)
        except Exception as e:
            print(
                f"[{time.ctime()}] Something is Wrong while updating Positions Sheet: {e}."
            )
            return
        if positions_df.empty:
            cell = positions_sheet.range("f3")
            cell.font.size = 30
            cell.value = "No position details found"
        else:
            cell = positions_sheet.range("a1").options(index=False, header=True)
            cell.value = positions_df

    def get_orders(orders=None):
        try:
            orders_sheet = excel_name.sheets("ORDERS")
            orders_sheet.range("a1:aj900").font.size = 11
            orders_sheet.range("a1:aj900").value = None
            if not orders:
                orders = _get_orders(api, update=True)
            orders_df = pd.DataFrame(orders)
        except Exception as e:
            print(
                f"[{time.ctime()}] Something is Wrong while updating Orders Sheet: {e}."
            )
            return
        if orders_df.empty:
            cell = orders_sheet.range("f3")
            cell.font.size = 30
            cell.value = "No order details found"
        else:
            orders_df.drop(columns=["meta"], inplace=True)
            cell = orders_sheet.range("a1").options(index=False, header=True)
            cell.value = orders_df

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


def refresh_books(api):
    live_sheet = excel_name.sheets("LIVE")
    oders = _get_orders(api, status="open", update=True)
    if oders is not None:
        # symbol, exchange, filled/qty, side, price, triggerPrice.
        orders_to_excel = [
            [
                order.get("symbol"),
                order.get("exchange"),
                "{}/{}".format(order.get("filled_quantity"), order.get("quantity")),
                order.get("side"),
                order.get("price", 0),
                order.get("trigger_price", 0),
            ]
            for order in oders
            if order
        ]
        if len(orders_to_excel) != 12:
            orders_to_excel += [[None, None, None, None, None, None]] * (
                12 - len(orders_to_excel)
            )
        # Updating Table 3: Open Orders.
        live_sheet.range("C22:H33").value = orders_to_excel

        # To update PositionBook.
        position = _get_positions(api, "open", True)
        if position:
            # symbol, exchange, qty, average_price, side.
            pos_to_excel = [
                [
                    pos.get("symbol"),
                    pos.get("exchange"),
                    pos.get("quantity"),
                    pos.get("average_price", 0),
                    pos.get("side", "BUY"),
                ]
                for pos in position
                if pos
            ]
            if len(pos_to_excel) != 12:
                pos_to_excel += [[None, None, None, None, None]] * (
                    12 - len(pos_to_excel)
                )
            # Updating Table 4: Open Positions.
            live_sheet.range("R22:V33").value = pos_to_excel


def get_order_id(order_details):
    symbol = order_details[0]
    exchange = order_details[1]
    qty = order_details[2]
    order_type = order_details[3]
    limit_price = order_details[4]
    trigger_price = order_details[5]

    for order in orders:
        if all(
            (
                order["symbol"] == symbol,
                order["exchange"] == exchange,
                order["filled_quantity"] == qty,
                order["side"] == order_type,
                order["price"] == limit_price,
                order["trigger_price"] == trigger_price,
            )
        ):
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
        if all(
            (
                order["symbol"] == symbol,
                order["exchange"] == exchange,
                order["status"] not in ("COMPLETE", "CANCELED", "REJECTED"),
            )
        ):
            orders_to_cancel.append(order["order_id"])
    return orders_to_cancel


def update_ltp(WS, symbol_df):
    resp = False
    while not resp:
        resp = WS.ltp()
        timer(1)
    # update last_price column  for  if resp list of dictionary key == instrument_token
    symbol_lst = symbol_df.to_dict(orient="records")
    for symbol in symbol_lst:
        symbol["last_price"] = [
            dct["last_price"]
            for dct in resp
            if dct["instrument_token"] == symbol["instrument_token"]
        ][0]
    symbol_df = pd.DataFrame(symbol_lst)
    return symbol_df


def run(WS, api):
    global symbol_in_focus, instrument_token, orders, positions, DATA
    symbol_in_focus = None
    DATA = {}
    orders = positions = []
    live_sheet = excel_name.sheets("LIVE")

    symbol_sheet = excel_name.sheets("BANKNIFTY_SYMBOL_DETAILS")
    symbol_df = symbol_sheet.range("A1:C190").options(pd.DataFrame).value
    # remove columns and rows that are empty
    symbol_df.dropna(axis=0, how="all", inplace=True)
    delay_candle_set_time = candle_gen_time = pdlm.now()
    show_msg("HAPPY TRADING", True)

    while True:
        try:
            # To Update Data in sheets...
            update_sheet_data(api)

            if WS.is_dirty:
                refresh_books(api)
                WS.is_dirty = False

            # Table 2: To Update last_price & candle data.
            symbol_df = update_ltp(WS, symbol_df)
            symbol_sheet("A1:C100").value = symbol_df

            """
            symbol_in_excel = live_sheet.range("I6").value
            if symbol_in_excel is not None and symbol_in_focus != symbol_in_excel:
                symbol_in_focus = symbol_in_excel
                try:
                    fdf = (
                        bank_nifty_df[bank_nifty_df.tradingsymbol == symbol_in_excel]
                        .reset_index(drop=True)
                        .head(1)
                    )
                    # Unsubscribing Unnecessary Old Symbols.
                    if fdf.empty:
                        print(f"Wrong Symbol: {symbol_in_excel}")
                        live_sheet.range("G6:V6").value = None
                        symbol_in_focus = WS.ticks = None
                        continue
                    print(f"Detected new symbol: {symbol_in_focus}")
                    instrument_token = int(fdf.instrument_token[0])
                except Exception as e:
                    msg = f"[{time.ctime()}] Error : {e}"
                    show_msg(msg)
                    print_exc()

        """
            # Tick Processing
            if symbol_in_focus is not None:
                # Candle Data Processing...

                cad_cell1 = live_sheet.range("K6:P6")
                if pdlm.now() > delay_candle_set_time.add(minutes=1, seconds=15):
                    print(f"[{time.ctime()}] refreshing 1min candle with 15s delay")
                    live_sheet.range("Q6:V6").value = cad_cell1.value
                    delay_candle_set_time = pdlm.now()

            # Table 1: To Place Requested Orders.
            if symbol_in_focus:
                for row in live_sheet.range("B6:E15").rows:
                    order_details = row.value
                    if order_details[3] == "ORDER":
                        qty = order_details[0]
                        price = order_details[1]
                        trigger_price = order_details[2]
                        if not isinstance(qty, float):
                            show_msg("Error: Not valid qty.")
                        else:
                            args = {
                                "variety": api.kite.VARIETY_REGULAR,
                                "exchange": api.kite.EXCHANGE_NFO,
                                "tradingsymbol": symbol_in_focus,
                                "transaction_type": api.kite.TRANSACTION_TYPE_BUY,
                                "quantity": int(qty),
                                "product": api.kite.PRODUCT_MIS,
                                "order_type": api.kite.ORDER_TYPE_SL
                                if trigger_price
                                else api.kite.ORDER_TYPE_LIMIT,
                                "price": price,
                                "trigger_price": trigger_price,
                                "tag": "EXCEL_TRADE",
                            }
                            show_msg(args, True)
                            try:
                                d = api.order_place(**args)
                            except Exception as e:
                                msg = f"[{time.ctime()}] Error while placing order: {e}"
                                show_msg(msg)
                            else:
                                msg = f"[{time.ctime()}] Order Placed Successfully, OrderId: {d}"
                                show_msg(msg, True)

                        # It will reset the button.
                        row[3].value = "READY"

            # Table 3: To Modify Open Orders.
            for row in live_sheet.range("C22:O33").rows:
                order_details = row.value
                if order_details[8] == "ORDER":
                    order_details[2] = int(str(order_details[2]).split("/")[0])
                    sl_trigger = order_details[6]
                    limit = order_details[7]
                    order_id = get_order_id(order_details)
                    order_type = (
                        api.kite.ORDER_TYPE_SL
                        if sl_trigger
                        else api.kite.ORDER_TYPE_LIMIT
                    )
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
                            show_msg(msg, True)

                    # It will clear the data & reset the button.
                    row[6:11].value = None
                    row[8].value = "READY"

                elif order_details[11] == "ORDER":
                    order_details[2] = int(str(order_details[2]).split("/")[0])
                    sl_trigger = order_details[9]
                    limit = order_details[10]
                    order_id = get_order_id(order_details)
                    order_type = (
                        api.kite.ORDER_TYPE_SL
                        if sl_trigger
                        else api.kite.ORDER_TYPE_LIMIT
                    )
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
                            show_msg(msg, True)

                    # It will clear the data & reset the button.
                    row[8:12].value = ["READY", None, None, "READY"]

                elif order_details[12] == "ORDER":
                    order_details[2] = int(str(order_details[2]).split("/")[0])
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
                            print(msg, True)

                    # It will reset the button.
                    row[8:13].value = ["READY", None, None, "READY", "READY"]

            # Table 4 # To Modify Open Positions.
            for row in live_sheet.range("R22:AC33").rows:
                if "ORDER" not in [row.value[7], row.value[10], row.value[11]]:
                    continue
                order_details = row.value

                if order_details[7] == "ORDER":
                    sl_trigger = order_details[5]
                    limit = order_details[6]
                    # 1. Cancel open orders of the symbol.
                    order_ids = get_order_id_for_position(order_details)
                    for order_id in order_ids:
                        args = {
                            "order_id": order_id,
                            "variety": api.kite.VARIETY_REGULAR,
                        }
                        try:
                            _ = api.order_cancel(**args)
                        except Exception as e:
                            msg = f"[{time.ctime()}] Error while cancelling open order: {e}"
                            show_msg(msg)
                            print_exc()

                    # 2. Place Sell Order to close position.
                    qty_ = get_qty_from_positions(order_details)
                    if qty_ > 0:
                        order_type = (
                            api.kite.ORDER_TYPE_SL
                            if sl_trigger
                            else api.kite.ORDER_TYPE_LIMIT
                        )
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
                            show_msg(msg, True)
                    # It will clear the data & reset the button.
                    row[5:8].value = [None, None, "READY"]

                elif order_details[10] == "ORDER":
                    sl_trigger = order_details[8]
                    limit = order_details[9]
                    order_ids = get_order_id_for_position(order_details)
                    # 1. Cancel Open Orders of the symbol.
                    for order_id in order_ids:
                        args = {
                            "order_id": order_id,
                            "variety": api.kite.VARIETY_REGULAR,
                        }
                        try:
                            _ = api.order_cancel(args)
                        except Exception as e:
                            msg = f"[{time.ctime()}] Error while cancelling open order: {e}"
                            show_msg(msg)

                    # 2. Place Sell Order to close position.
                    qty_ = get_qty_from_positions(order_details)
                    if qty_ > 0:
                        order_type = (
                            api.kite.ORDER_TYPE_SL
                            if sl_trigger
                            else api.kite.ORDER_TYPE_LIMIT
                        )
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
                            show_msg(msg, True)
                    # It will clear the data & reset the button.
                    row[8:11].value = [None, None, "READY"]

                elif order_details[11] == "ORDER":
                    order_ids = get_order_id_for_position(order_details)
                    # 1. Cancel open orders of the symbol.
                    for order_id in order_ids:
                        args = {
                            "order_id": order_id,
                            "variety": api.kite.VARIETY_REGULAR,
                        }
                        try:
                            _ = api.order_cancel(**args)
                        except Exception as e:
                            msg = f"[{time.ctime()}] Error while cancelling open order: {e}"
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
                            show_msg(msg, True)

                    # It will reset the button.
                    row[7:12].value = ["READY", None, None, "READY", "READY"]

            timer(0.8)
        except Exception as e:
            show_msg(e)
            print_exc()


def init():
    try:
        # Icons -
        # 🟢, 🛈, ℹ , 🔔, 🚀 ...
        print("Zerodha Excel Based Terminal program initialized")
        print(f"📌 Process id: {os.getpid()}.")
        api = get_kite()
        if api:
            print("🟢 Logged in Successfully")
            clear_sheets()
            WS = Wsocket(api.kite)
            save_symbol_sheet(WS)
            run(WS, api)
            print("🚀 Enjoy the automation...")

        else:
            print(
                "Please check the API connection or Either your access token is expired!"
            )
            print("Try Again, By Restarting your program!")
    except KeyboardInterrupt:
        print("Exiting the program...")
        __import__("sys").exit(0)


if __name__ == "__main__":
    try:
        init()
    except Exception as e:
        print(f" excepion in main {e}")
        print_exc()
