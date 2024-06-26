from constants import O_CNFG, S_DATA, O_SETG, logging
from toolkit.kokoo import timer
from login import get_bypass, get_zerodha
from wsocket import Wsocket
from symbol import Symbol, dct_sym
import pendulum as pdlm
import pandas as pd
from traceback import print_exc


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


def main():
    try:
        API = init()
        last_price = ltp(API)

        # get more info of the universe
        base = O_SETG["base"]
        SYM = Symbol("NFO", base, O_SETG[base]["expiry"])
        args = SYM.calc_atm_from_ltp(last_price)

        # what is the universe we are going to trade today
        dct_of_token = SYM.find_token_from_dump(args)
        subscribe = list(dct_of_token.values())
        logging.debug("subscribe: {}".format(subscribe))
        # initialize websocket
        WS = Wsocket(API.kite, subscribe)
        run(API, WS)
    except Exception as e:
        logging.error(f"main: {e}")
        print_exc()


main()
