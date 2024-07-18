import pendulum
from constants import logging, O_CNFG
from kiteconnect import KiteTicker


class Wsocket:
    def __init__(self, kite, sym_tkn=None):
        self.instrument = ""
        self.ticks = []
        if O_CNFG["broker"] == "bypass":
            self.kws = kite.kws()
        else:
            self.kws = KiteTicker(api_key=kite.api_key, access_token=kite.access_token)

        if isinstance(sym_tkn, list):
            self.sym_tkn = sym_tkn
        else:
            self.sym_tkn = []
        # Assign the callbacks.
        self.kws.on_ticks = self.on_ticks
        self.kws.on_connect = self.on_connect
        self.kws.on_close = self.on_close
        self.kws.on_error = self.on_error
        self.kws.on_reconnect = self.on_reconnect
        self.kws.on_noreconnect = self.on_noreconnect

        # Infinite loop on the main thread. Nothing after this will run.
        # You have to use the pre-defined callbacks to manage subscriptions.
        self.kws.connect(threaded=True)

    def on_ticks(self, ws, ticks):
        # Callback to receive ticks.
        if ticks:
            ticks[0]['ltp'] = ticks[0].pop('last_price')
            ticks[0].update({'time': pendulum.now()})
            self.ticks = ticks

    def on_connect(self, ws, response):
        # Callback on successful connect.
        # Subscribe to a list of instrument_tokens.
        if self.sym_tkn:
            ws.set_mode(ws.MODE_LTP, self.sym_tkn)

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

    def subscribe(self, tokens: list[int], mode='ltp'):
        if isinstance(tokens, int):
            tokens = [tokens]
        if mode.lower() not in ('ltp', 'quote', 'full'):
            mode = 'quote'
        self.sym_tkn.extend(tokens)
        self.kws.set_mode(mode, tokens)

    def unsubscribe(self, tokens: list[int]):
        if isinstance(tokens, int):
            tokens = [tokens]
        if self.kws.unsubscribe(tokens):
            for t in tokens:
                if t in self.sym_tkn: 
                    self.sym_tkn.remove(t)
            return True

    def unsubsribe_all(self):
        if not isinstance(self.sym_tkn, list): return
        # Unsubscribe All tokens.
        if self.kws.unsubscribe(self.sym_tkn):
            self.sym_tkn = []
            return True
