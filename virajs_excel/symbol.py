import pandas as pd
import re
from toolkit.fileutils import Fileutils
from typing import List, Union
from traceback import print_exc

dct_sym = {
    "NIFTY": {
        "diff": 50,
        "index": "Nifty 50",
        "exch": "NSE",
        "token": "256265",
        "depth": 16,
    },
    "BANKNIFTY": {
        "diff": 100,
        "index": "Nifty Bank",
        "exch": "NSE",
        "token": "260105",
        "depth": 25,
    },
    "MIDCPNIFTY": {
        "diff": 100,
        "index": "NIFTY MID SELECT",
        "exch": "NSE",
        "token": "288009",
        "depth": 21,
    },
    "FINNIFTY": {
        "diff": 50,
        "index": "Nifty Fin Services",
        "exch": "NSE",
        "token": "257801",
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
            return dict(zip(df["tradingsymbol"], df["instrument_token"]))
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


"""
    def find_closest_premium(
        self, quotes: Dict[str, float], premium: float, contains: str
    ) -> Optional[str]:
        contains = self.expiry + contains
        # Create a dictionary to store symbol to absolute difference mapping
        symbol_differences: Dict[str, float] = {}

        for symbol, ltp in quotes.items():
            if re.search(re.escape(contains), symbol):
                difference = abs(ltp - premium)
                symbol_differences[symbol] = difference

        # Find the symbol with the lowest difference
        closest_symbol = min(
            symbol_differences, key=symbol_differences.get, default=None
        )

        return closest_symbol

    def find_symbol_in_moneyness(self, tradingsymbol, ce_or_pe, price_type):
        def find_strike(ce_or_pe):
            search = self.symbol + self.expiry + ce_or_pe
            # find the remaining string in the symbol after removing search
            strike = re.sub(search, "", tradingsymbol)
            return search, int(strike)

        search, strike = find_strike(ce_or_pe)
        if ce_or_pe == "C":
            if price_type == "ITM":
                return search + str(strike - dct_sym[self.symbol]["diff"])
            else:
                return search + str(strike + dct_sym[self.symbol]["diff"])
        else:
            if price_type == "ITM":
                return search + str(strike + dct_sym[self.symbol]["diff"])
            else:
                return search + str(strike - dct_sym[self.symbol]["diff"])

    def calc_straddle_value(self, atm: int, quotes: list):
        ce = self.symbol + self.expiry + "C" + str(atm)
        pe = self.symbol + self.expiry + "P" + str(atm)
        return quotes[ce] + quotes[pe]

    def find_option_type(self, tradingsymbol):
        option_pattern = re.compile(rf"{self.symbol}{self.expiry}([CP])\d+")
        match = option_pattern.match(tradingsymbol)
        if match:
            return match.group(1)  # Returns 'C' for call, 'P' for put
        else:
            return False

    def find_option_by_distance(
        self, atm: int, distance: int, c_or_p: str, dct_symbols: dict
    ):
        match = {}
        if c_or_p == "C":
            find_strike = atm + (distance * dct_sym[self.symbol]["diff"])
        else:
            find_strike = atm - (distance * dct_sym[self.symbol]["diff"])
        option_pattern = self.symbol + self.expiry + c_or_p + str(find_strike)
        for k, v in dct_symbols.items():
            if v == option_pattern:
                match.update({"symbol": v, "token": k.split("|")[-1]})
                break
        if any(match):
            return match
        else:
            raise Exception("Option not found")

"""
