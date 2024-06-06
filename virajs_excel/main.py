from constants import O_CNFG, S_DATA, O_SETG, logging
from toolkit.kokoo import timer
from login import get_bypass, get_zerodha
from wsocket import Wsocket
from symbol import Symbol, dct_sym
import pendulum as pdlm
import pandas as pd


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
                    history = candle_data(API, tick["instrument_token"])
                    print(history)
        except KeyboardInterrupt:
            # if keyboard interrupt stop the websocket
            WS.kws.on_close
            __import__("sys").exit(1)
        except Exception as e:
            print(e)
        finally:
            __import__("time").sleep(1)


def main():
    API = init()
     = O_SETG["base"]
    SYM = Symbol("NSE")
    dct = SYM.last_price()
    # get more info of the universe
    SYM = Symbol("NFO", O_SETG["base"], O_SETG["base"]["expiry"])
    # what is the universe we are going to trade today

    lst_of_exchsym = ["NSE:SBIN", "NSE:RELIANCE", "NSE:INFY", "NSE:ICICIBANK"]
    dct_of_token = SYM.tokens(lst_of_exchsym)
    subscribe = list(dct_of_token.vales())

    # initialize websocket
    WS = Wsocket(API.kite, subscribe)
    run(API, WS)


main()
