#!/usr/bin/env python3
import common
# import config_settings
from pawnlib.config.globalconfig import pawnlib_config
from pawnlib.output import *


def logging_func():
    res = pawnlib_config.conf()
    print(f"[child] logging_func --- {res}")
    print(f"[child] logging_func --- {pawnlib_config.to_dict()}")
    # conf().app_logger.info("[main()] start")


def child_app_logging_func(message=None):
    debug_logging(pawnlib_config)
    pawnlib_config.app_logger.info(message)

# print(f"config_child = {config()}")
# logging_func()

# print(f"[outside] {pawnlib_config.conf()}")
# config()



