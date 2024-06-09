from constants import O_FUTL


def get_bypass(dct, sec_dir):
    from omspy_brokers.bypass import Bypass

    try:
        tokpath = sec_dir + dct["userid"] + ".txt"
        enctoken = None
        if not O_FUTL.is_file_not_2day(tokpath):
            print(f"{tokpath} modified today ... reading {enctoken}")
            with open(tokpath, "r") as tf:
                enctoken = tf.read()
                if len(enctoken) < 5:
                    enctoken = None
        print(f"enctoken to broker {enctoken}")
        bypass = Bypass(dct["userid"], dct["password"], dct["totp"], tokpath, enctoken)
        if bypass.authenticate():
            if not enctoken:
                enctoken = bypass.kite.enctoken
                with open(tokpath, "w") as tw:
                    tw.write(enctoken)
    except Exception as e:
        print(f"unable to create bypass object  {e}")
    else:
        return bypass


def get_zerodha(fdct, sec_dir):
    try:
        from omspy_brokers.zerodha import Zerodha

        zera = Zerodha(
            user_id=fdct["userid"],
            password=fdct["password"],
            totp=fdct["totp"],
            api_key=fdct["api_key"],
            secret=fdct["secret"],
            tokpath=sec_dir + fdct["userid"] + ".txt",
        )
        zera.authenticate()
    except Exception as e:
        print(f"exception while creating zerodha object {e}")
    finally:
        return zera


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
