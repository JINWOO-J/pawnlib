#!/usr/bin/env python3
import common
# import config_settings
from pawnlib.config.globalconfig import pawnlib_config


def logging_func():
    res = pawnlib_config.conf()
    print(f"[child] logging_func --- {res}")
    print(f"[child] logging_func --- {pawnlib_config.to_dict()}")
    # conf().app_logger.info("[main()] start")


# print(f"config_child = {config()}")
logging_func()

# print(f"[outside] {pawnlib_config.conf()}")
# config()



