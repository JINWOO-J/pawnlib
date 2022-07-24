#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass
from devtools import debug
from pawnlib.output import *
from pawnlib.config.globalconfig import pawnlib_config
from pawnlib.utils.operate_handler import *
from pawnlib.typing.check import Null


def main():
    debug_logging("start main()")

    dump(pawnlib_config.to_dict())
    cprint(f"1. Use Null() :: \n\n pawnlib_config.app_logger type = {type(pawnlib_config.app_logger)}", "green")

    pawnlib_config.app_logger = Null()
    pawnlib_config.app_logger.info("asdsdsd")

    print("\n\n")

    pawnlib_config.app_logger = None
    cprint(f"2. Use None :: \n\n pawnlib_config.app_logger type = {type(pawnlib_config.app_logger)}", "green")
    try:
        cprint(" It will be occurred error", "red")
        pawnlib_config.app_logger.info("asdsdsd")
    except Exception as e:
        cprint(f" Exception :: Error Occurred - {e}", "red")


if __name__ == "__main__":
    main()
