from traceback import print_exc
import pandas as pd


class OptionChain:
    def __init__(self, df_symbol: pd.DataFrame, index: str, indexToken: int, depth: int=20, diff: float=None) -> None:
        self.index = index.upper()
        self.indexToken = indexToken
        if not depth: 
            depth = 10
        self.depth = depth
        self.diff = diff
        self.symbols = self._filter_symbols(df_symbol)

    def _filter_symbols(self, df: pd.DataFrame) -> pd.DataFrame:
        if not(isinstance(df, pd.DataFrame) and not df.empty):
            # Here, can add feature to download the symbols list and then filter it.
            print('Either df is None or empty in optionChain.py>_filter_symbols()...')
            return
        # Filtering by the index & sorting expiry + strike.
        df = df[(df['name'].str.upper() == self.index.upper())].sort_values(by=['expiry', 'strike']).copy(deep=True)
        # Getting 1st expiry.
        expiry = df.expiry.unique()[0]
        # Filtering to 1st expiry.
        df = df[df.expiry == expiry]
        df = df.reset_index(drop=True)
        return df

    def calc_atm_from_ltp(self, ltp) -> int:
        try:
            df = self.symbols.copy()
            df['diff'] = abs(df['strike'] - ltp)
            atm_strike = df.loc[df['diff'].idxmin(), 'strike']
            return atm_strike
        except Exception as e:
            print(f'Calc atm error: {e}.')
            print_exc()

    def get_strikes(self, strike: int):
        df: pd.DataFrame = self.symbols
        df = df[df['strike'] == strike]
        return df

    def build_option_strikes(self, ltp: float):
        df: pd.DataFrame = self.symbols
        if not isinstance(df, pd.DataFrame):
            print('dataframe is not found: ',df)
            exit(1)
        # Find the ATM strike & depth for each moneyness.
        atm = self.calc_atm_from_ltp(ltp=ltp)
        eqdep = int(abs(int(self.depth)/2))
        # Select unique ITM and OTM strikes around the ATM strike
        strikes = df["strike"].unique()
        itms = strikes[strikes < atm][-eqdep:].tolist()
        otms = strikes[strikes > atm][:eqdep].tolist()
        # Combine ITM, ATM and OTM strikes.
        strikes = itms + [atm] + otms
        # Filter the DataFrame based on the selected strikes.
        fdf = df[df["strike"].isin(strikes)].reset_index(drop=True)      
        return fdf

