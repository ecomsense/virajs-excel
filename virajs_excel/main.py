from constants import O_FILS, DATA

if O_FILS.is_file_not_2day(DATA + "settings.yml"):
    print("settings file is not modified today")


SETG = O_FILS.get_lst_fm_yml(DATA + "settings.yml")
if SETG:
    print(SETG)
else:
    print("no settings found")
