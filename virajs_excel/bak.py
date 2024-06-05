from constants import O_CNFG, S_DATA, O_SETG, logging
from login_and_get_token import get_bypass, get_zerodha
from login_and_get_token import remove_token
from wsocket import Wsocket
from symbol import Symbol
import pendulum as pdlm
import pandas as pd


CRED = {}
FM = (
    pdlm.now()
    .subtract(days=2)
    .set(hour=9, minute=15, second=0)
    .strftime("%Y-%m-%d %H:%M:%S")
)


def init():
    if O_SETG["broker"] == "bypass":
        CRED.update(O_CNFG["bypass"])
        return get_bypass(O_CNFG["bypass"], S_DATA)
    else:
        CRED.update(O_CNFG["zerodha"])
        return get_zerodha(O_CNFG["zerodha"], S_DATA)




def candle_data(token):
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
    return lst


def run():
    # find tokens
    #
    INS = ["NSE:SBIN"]
    SYM = Symbol("NSE")
    SYM.token(df)
    subscribe = df["token"].tolist()
    # initiate ws
    ws = Wsocket(API.kite, subscribe)
    while True:
        try:
            # TODO get token for an instrument
            instrument = "SBIN"
            if ws.kws.is_connected() and instrument != ws.instrument:
                token = df.loc[df["symbol"] == instrument]["token"].values[0]
                ws.kws.set_mode(ws.kws.MODE_LTP, [token])
                """
                history = candle_data(token)
                print(history)
                """
            else:
                __import__("time").sleep(1)
        except KeyboardInterrupt:
            # if keyboard interrupt stop the websocket
            ws.kws.on_close
            __import__("sys").exit(1)
        except Exception as e:
            print(e)


API = init()
run()
