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


@timing
def slow_function(param=None):
    debug_logging("slow func")
    time.sleep(0.2)


def main():
    debug_logging("start main()")
    slow_function()


if __name__ == "__main__":
    main()
