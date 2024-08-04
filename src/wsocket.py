from symbol import dct_sym
from typing import Dict, List

from kiteconnect import KiteTicker

from constants import O_CNFG, logging


def filter_ws_keys(incoming: List[Dict]):
    keys = ["instrument_token", "last_price"]
    new_lst = []
    if incoming and isinstance(incoming, list) and any(incoming):
        for dct in incoming:
            new_dct = {}
            for key in keys:
                if dct.get(key, None):
                    new_dct[key] = dct[key]
                    new_lst.append(new_dct)
    return new_lst


class Wsocket:
    def update_ticks(self, incoming_ticks):
        incoming_ticks = filter_ws_keys(incoming_ticks)

        for incoming_tick in incoming_ticks:
            instrument_token = incoming_tick.get("instrument_token")
            found = False

            for tick in self.ticks:
                if tick.get("instrument_token") == instrument_token:
                    # Update the existing tick's last price
                    tick["last_price"] = incoming_tick.get("last_price")
                    found = True
                    break

            if not found:
                # If no existing tick is found, add the new tick
                self.ticks.append(incoming_tick)

    def __init__(self, kite):
        self.ticks = []
        lst = [dct for dct in dct_sym.values()]
        self.tokens = [dct["instrument_token"] for dct in lst]
        is_broker = O_CNFG.get("broker", None)
        if is_broker is None:
            is_zerodha = O_CNFG.get("zerodha", None)
            is_broker = "zerodha" if is_zerodha else "bypass"

        if is_broker == "bypass":
            self.kws = kite.kws
        elif is_broker == "zerodha":
            self.kws = KiteTicker(api_key=kite.api_key, access_token=kite.access_token)

        self.is_dirty = False

        # Assign the callbacks.
        self.kws.on_ticks = self.on_ticks
        self.kws.on_connect = self.on_connect
        self.kws.on_close = self.on_close
        self.kws.on_error = self.on_error
        self.kws.on_reconnect = self.on_reconnect
        self.kws.on_noreconnect = self.on_noreconnect
        self.kws.on_order_update = self.on_order_update

        # Infinite loop on the main thread. Nothing after this will run.
        # You have to use the pre-defined callbacks to manage subscriptions.
        self.kws.connect(threaded=True)

    def ltp(self, tokens=None):
        if tokens:
            tokens = [dct["instrument_token"] for dct in tokens]
            self.tokens = list(set(self.tokens + tokens))
        return self.ticks

    def on_ticks(self, ws, ticks):
        if self.tokens is not None:
            ws.subscribe(self.tokens)
        self.update_ticks(ticks)

    def on_connect(self, ws, response):
        # Callback on successful connect.
        # Subscribe to a list of instrument_tokens.
        ws.subscribe(self.tokens)
        ws.set_mode(ws.MODE_LTP, self.tokens)

    def on_close(self, ws, code, reason):
        # On connection close stop the main loop
        # Reconnection will not happen after executing `ws.stop()`
        ws.stop()

    def on_error(self, ws, code, reason):
        # Callback when connection closed with error.
        logging.info(
            "Connection error: {code} - {reason}".format(code=code, reason=reason)
        )

    def on_reconnect(self, ws, attempts_count):
        # Callback when reconnect is on progress
        logging.info("Reconnecting: {}".format(attempts_count))

    # Callback when all reconnect failed (exhausted max retries)

    def on_noreconnect(self, ws):
        logging.info("Reconnect failed.")

    def on_order_update(self, ws, data):
        print(f"order updates: {data}")
        self.is_dirty = True


if __name__ == "__main__":
    from constants import O_CNFG, S_DATA, logging
    from login import get_bypass, get_zerodha

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

    try:
        api = init()
        print("logged in successfully")
        WS = Wsocket(api.kite)
        # Some time required to initialize ws connection.
        resp = None
        while not resp:
            resp = WS.ltp()
            __import__("time").sleep(1)
            print("Connecting...")
        else:
            print(resp)
    except Exception as e:
        print(f"main: {e}")
        SystemExit(1)
