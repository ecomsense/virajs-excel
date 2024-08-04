from traceback import print_exc
from typing import List, Union

import pandas as pd
from toolkit.fileutils import Fileutils

dct_sym = {
    "NIFTY": {
        "diff": 50,
        "trading_symbol": "Nifty 50",
        "exch": "NSE",
        "instrument_token": 256265,
        "depth": 16,
    },
    "BANKNIFTY": {
        "diff": 100,
        "trading_symbol": "Nifty Bank",
        "exch": "NSE",
        "instrument_token": 260105,
        "depth": 25,
    },
    "MIDCPNIFTY": {
        "diff": 100,
        "trading_symbol": "NIFTY MID SELECT",
        "exch": "NSE",
        "instrument_token": 288009,
        "depth": 21,
    },
    "FINNIFTY": {
        "diff": 50,
        "trading_symbol": "Nifty Fin Services",
        "exch": "NSE",
        "instrument_token": 257801,
        "depth": 16,
    },
}


class Symbol:
    """
    Class to get symbols from finvasia

    Parameters
    ----------
    exchange : str
        Exchange
    symbol : str
        Symbol
    expiry : str
        Expiry

    """

    def __init__(self, exchange: str, symbol: str, expiry: str):
        self.exchange = exchange
        self.symbol = symbol
        self.expiry = expiry
        self.csvfile = f"../data/{self.exchange}_symbols.csv"
        self.dump_master_by_exchange()

    def dump_master_by_exchange(self):
        try:
            if Fileutils().is_file_not_2day(self.csvfile):
                url = f"https://api.kite.trade/instruments/{self.exchange}"
                df = pd.read_csv(url)
                df.drop(columns=["name", "last_price"], inplace=True)
                df.to_csv(self.csvfile, index=False)
        except Exception as e:
            print(e)
            print_exc()
            SystemExit(1)

    def find_token_from_dump(self, args: Union[List[str], int]):
        """
        finds token from data dir csv dump
        parameter:
            input: list of exchange:symbols or atm as integer
            output: dictionary with symbol key and token as value
        """
        try:
            df = pd.read_csv(self.csvfile)
            lst = []
            if isinstance(args, list):
                for args in args:
                    exch = args.split(":")[0]
                    sym = args.split(":")[1]
                    if exch == self.exchange:
                        lst.append(sym)
            elif isinstance(args, int):
                lst.append(self.symbol + self.expiry + str(args) + "CE")
                lst.append(self.symbol + self.expiry + str(args) + "PE")
                for v in range(1, dct_sym[self.symbol]["depth"]):
                    lst.append(
                        self.symbol
                        + self.expiry
                        + str(args + v * dct_sym[self.symbol]["diff"])
                        + "CE"
                    )
                    lst.append(
                        self.symbol
                        + self.expiry
                        + str(args + v * dct_sym[self.symbol]["diff"])
                        + "PE"
                    )
                    lst.append(
                        self.symbol
                        + self.expiry
                        + str(args - v * dct_sym[self.symbol]["diff"])
                        + "CE"
                    )
                    lst.append(
                        self.symbol
                        + self.expiry
                        + str(args - v * dct_sym[self.symbol]["diff"])
                        + "PE"
                    )
            else:
                raise ValueError(f"str({args}) must be list or int")
            df = df[df["tradingsymbol"].isin(lst)]
            #return dict(zip(df["tradingsymbol"], df["instrument_token"]))
            # keep only required columns
            df = df[["instrument_token", "tradingsymbol"]]
            return df.to_dict(orient="records")
            
        except Exception as e:
            print(f"find_token_from_dump: {e}")
            print_exc()
            SystemExit(1)

    def calc_atm_from_ltp(self, ltp) -> int:
        current_strike = ltp - (ltp % dct_sym[self.symbol]["diff"])
        next_higher_strike = current_strike + dct_sym[self.symbol]["diff"]
        if ltp - current_strike < next_higher_strike - ltp:
            return int(current_strike)
        return int(next_higher_strike)

if __name__ == "__main__":
    sym = Symbol("NFO", "BANKNIFTY", "24807")
    atm = sym.calc_atm_from_ltp(54501)
    lst = sym.find_token_from_dump(atm)
    print("symbols", lst)
    lst = [dct for dct in dct_sym.values()]
    lst = [dct["instrument_token"] for dct in lst]
    print(lst)

