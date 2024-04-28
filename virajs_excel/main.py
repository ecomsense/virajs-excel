from constants import CNFG, DATA, SETG, logging
from login_and_get_token import get_bypass, get_zerodha
from login_and_get_token import remove_token
from wsocket import Wsocket
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
    if SETG["broker"] == "bypass":
        CRED.update(CNFG["bypass"])
        return get_bypass(CNFG["bypass"], DATA)
    else:
        CRED.update(CNFG["zerodha"])
        return get_zerodha(CNFG["zerodha"], DATA)


def market_watch():
    # TODO get tokens for instruments
    data = [{"exchange": "NSE", "symbol": "SBIN"},
            {"exchange": "NSE", "symbol": "ACC"}]
    df = pd.DataFrame(data)
    return df


def add_token(row):
    exch_sym = row["exchange"] + ":" + row["symbol"]
    resp = API.kite.quote(exch_sym)
    return resp[exch_sym]["instrument_token"]


def candle_data(token):
    to = pdlm.now().strftime("%Y-%m-%d %H:%M:%S")
    kwargs = dict(instrument_token=token, from_date=FM,
                  to_date=to, interval="minute")
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
    df = market_watch()
    df["token"] = df.apply(lambda row: add_token(row), axis=1)
    subscribe = df["token"].tolist()

    instrument = "SBIN"
    token = df.loc[df["symbol"] == instrument]["token"].values[0]
    history = candle_data(token)
    print(history)
    """
    # initiate ws
    ws = Wsocket(API.kite, subscribe)
    while True:
        # TODO get token for an instrument
        instrument = "SBIN"
        if ws.kws.is_connected() and instrument != ws.instrument:
            token = df.loc[df["symbol"] == instrument]["token"].values[0]
            ws.kws.set_mode(ws.kws.MODE_LTP, [token])
            history = candle_data(token)
            print(history)
        # if keyboard interrupt stop the websocket
        try:
            __import__("time").sleep(1)
        except KeyboardInterrupt:
            ws.kws.on_close
            __import__("sys").exit(1)
    """


API = init()
run()
