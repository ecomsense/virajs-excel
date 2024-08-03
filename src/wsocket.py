import pendulum
from constants import logging
from pydantic.dataclasses import dataclass
from kiteconnect import KiteTicker
from typing import Optional, Dict
from omspy_brokers.bypass import Bypass
from omspy_brokers.zerodha import Zerodha
import threading


@dataclass
class Ltp:
    ltp: float
    time: pendulum.DateTime


class Symbol:
    def __init__(self, token: int, name: str=None) -> None:
        self.token: int = token
        self.name: str = name
        self.ltps: list = []
        self.lock = threading.Lock()
        self.last_update = None

    def add_ltp(self, ltp: float, time: pendulum.DateTime):
        try:
            with self.lock:
                if len(self.ltps) > 2000:
                    del self.ltps[:500]
                tick = Ltp(ltp=ltp, time=time)
                self.ltps.append(tick)
                self.last_update = pendulum.now()
        except Exception as e:
            import traceback
            print(f'Error in add_ltp: {self.name}, {e}.')
            print(f'Error Data: ', self.token, self.name, len(self.ltps), ltp, time)
            traceback.print_exc()

    def get_ltp(self, n=-1) -> Optional[Ltp]:
        """
        It will return ltp object, n means no of old data. n=-1 means latest ltp.
        """
        try:
            with self.lock:
                if len(self.ltps) == 0: return None
                elif not(n < 0 and len(self.ltps) >= abs(n)):
                    n = -1
                tick = self.ltps[n]
                tick.token = self.token
                tick.symbol = self.name
                return tick
        except Exception as e:
            print(f'Error in get_ltp: {self.name}, {e}.')


class DataStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.data: Dict[int, Symbol] = {}


    def get_symbol(self, token: int) -> Optional[Symbol]:
        with self.lock:
            return self.data.get(token)

    def create_symbol(self, symbol: str=None, token: int=None) -> Symbol:
        sym = self.get_symbol(token=token)
        if not sym:
            sym = Symbol(name=symbol, token=token)
            with self.lock:
                self.data[token] = sym
        return sym
    
    def _add_ltp(self, ltp: float, time: pendulum.DateTime, token: int):
        sym = self.get_symbol(token)
        if not sym:
            sym = self.create_symbol(token=token)
        sym.add_ltp(ltp=ltp, time=time)

    def process_tick(self, ticks: list, time=None):
        """
        It will process the incoming tick data.
        """
        if not time:
            time = pendulum.now()
        for tick in ticks:
            if isinstance(tick, dict):
                self._add_ltp(ltp=tick.get('last_price'), time=time, token=tick.get('instrument_token'))
            elif isinstance(tick, Tick):
                self._add_ltp(ltp=tick.ltp, time=time, token=tick.token)

    def get_ltp(self, token: int=None) -> Optional[Ltp]:
        sym = self.get_symbol(token=token)
        if sym:
            return sym.get_ltp()


@dataclass
class Tick:
    tradable: bool
    mode: str
    instrument_token: int
    last_price: float
    time: pendulum.DateTime = pendulum.now()
    
    @property
    def token(self):
        return self.instrument_token

    @property
    def ltp(self):
        return self.last_price


class Wsocket:
    def __init__(self, api, sym_tkn=None):
        self.instrument = ""
        self.ticks = []
        self.ltp_store = DataStore()

        kite = api.kite
        if isinstance(api, Bypass):
            self.kws = kite.kws()
        elif isinstance(api, Zerodha):
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
            time = pendulum.now()
            # Converting tick into Tick object.
            data = [Tick(**i) for i in ticks]
            self.ltp_store.process_tick(ticks=data, time=time)
            self.last_tick = pendulum.now()
        else:
            print(f'Not found a tick, {ticks}.')


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

    # Callback when all reconnect failed (exhausted max retries)
    def on_reconnect(self, ws, attempts_count):
        # Callback when reconnect is on progress
        logging.info("Reconnecting: {}".format(attempts_count))


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
