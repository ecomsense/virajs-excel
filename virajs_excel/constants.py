from toolkit.logger import Logger
from toolkit.fileutils import Fileutils

O_FILS = Fileutils()
DATA = "../data/"
S_LOG = DATA + "log.txt"

if not O_FILS.is_file_not_2day(S_LOG):
    pass
logging = Logger(10)
CNFG = O_FILS.get_lst_fm_yml("../../excel-virajs.yml")
SETG = O_FILS.get_lst_fm_yml(DATA + "settings.yml")
