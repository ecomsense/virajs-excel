from traceback import print_exc
import pathlib

try:
    from toolkit.logger import Logger
except ModuleNotFoundError:
    __import__("os").system("pip install git+https://github.com/pannet1/toolkit")
    __import__("time").sleep(5)
    from toolkit.logger import Logger

from toolkit.fileutils import Fileutils

O_FUTL = Fileutils()
S_DATA = "../data/"
S_LOG = S_DATA + "log.txt"
if not O_FUTL.is_file_exists(S_LOG):
    print("creating data dir")
    O_FUTL.add_path(S_LOG)


def yml_to_obj(arg=None):
    try:
        if not arg:
            fname = "-".join(pathlib.Path.cwd().parent.name.split("_"))
            file = f"../../{fname}.yml"
        else:
            file = S_DATA + arg

        flag = O_FUTL.is_file_exists(file)
        if not flag and arg:
            print(f"using default {file} file")
            O_FUTL.copy_file("./", "../data/", "settings.yml")
        elif not flag and arg is None:
            print(f"fill the {file=} and try again")
            exit(1)

        return O_FUTL.get_lst_fm_yml(file)
    except Exception as e:
        print(e)
        print_exc()


def os_and_objects():
    try:
            O_CNFG = yml_to_obj()
            O_SETG = yml_to_obj("settings.yml")
    except Exception as e:
        print(e)
        print_exc()
        __import__("sys").exit(1)
    else:
        return O_CNFG, O_SETG


O_CNFG, O_SETG = os_and_objects()
# print(O_CNFG, O_SETG)


def set_logger():
    level = O_SETG.get("log_level", 10)
    if O_SETG.get("show_log", False):
        return Logger(level)
    return Logger(level, S_LOG)


logging = set_logger()
