#!/usr/bin/env python3
import common
# import config_settings
from pawnlib.config.globalconfig import PawnlibConfig
from pawnlib.output import *


def child_app(message=None):
    pwn = PawnlibConfig(global_name="sdsd").init_with_env()
    pwn.set(asdfff="sdssdsd")

    debug_logging("import another location", pwn)

# print(f"config_child = {config()}")
# logging_func()

# print(f"[outside] {pawnlib_config.conf()}")
# config()



