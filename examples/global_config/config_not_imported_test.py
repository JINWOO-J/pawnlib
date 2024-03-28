#!/usr/bin/env python3
import time
from devtools import debug
import common
import sys
import os
from pawnlib.config.globalconfig import pawnlib_config
from pawnlib.utils import http
import config_settings
import config_child
from configparser import ConfigParser

from pawnlib.utils.operate_handler import *


@timing
def timing_task():
    time.sleep(1)


def main():
    # pawnlib_default_config()
    http.disable_ssl_warnings()

    print(f"main = {pawnlib_config.conf()}")

    print(pawnlib_config.get("PAWN_APP_LOGGER"))
    print(pawnlib_config.set(PAWN_APP_LOGGER="aaa"))
    print(pawnlib_config.get("PAWN_APP_LOGGER"))

    # config = dict(ConfigParser())
    #
    print(pawnlib_config.conf())

    timing_task()

    # res = http.jequest("http://naver.com")
    # print("start daemon")


if __name__ == "__main__":
    main()
