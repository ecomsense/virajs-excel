from constants import O_FUTL
from kiteconnect import KiteTicker


def get_bypass(dct, sec_dir):
    from omspy_brokers.bypass import Bypass

    try:
        tokpath = sec_dir + dct["userid"] + ".txt"
        bypass = Bypass(dct["userid"], dct["password"], dct["totp"], tokpath)
        if bypass.authenticate():
            enctoken = bypass.kite.enctoken
            if enctoken:
                with open(tokpath, "w") as tw:
                    tw.write(enctoken)
                return bypass
            print('Either Token is expired or Invalid Details entered.')
    except Exception as e:
        print(f"unable to create bypass object  {e}")


def get_zerodha(fdct, sec_dir):
    try:
        from omspy_brokers.zerodha import Zerodha

        zera = Zerodha(
            userid=fdct["userid"],
            password=fdct["password"],
            totp=fdct["totp"],
            api_key=fdct["api_key"],
            secret=fdct["secret"]            
        )
        if zera.authenticate():           
            return zera
    except Exception as e:
        print(f"exception while creating zerodha object {e}")


def remove_token(tokpath):
    __import__("os").remove(tokpath)


if __name__ == "__main__":
    from constants import O_CNFG, O_SETG, S_DATA

    CRED = {}
    if O_SETG["broker"] == "bypass":
        CRED.update(O_CNFG["bypass"])
        api = get_bypass(O_CNFG["bypass"], S_DATA)
    else:
        CRED.update(O_CNFG["zerodha"])
        api = get_zerodha(O_CNFG["zerodha"], S_DATA)

    positions = api.positions
    print(f"{positions=}")

    orders = api.orders
    print(f"{orders=}")

    holdings = api.kite.holdings()
    print(f"{holdings=}")
