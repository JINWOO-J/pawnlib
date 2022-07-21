#!/usr/bin/env python3
import time
from devtools import debug
import common
import sys
import os
from pawnlib.config.globalconfig import pawnlib_config
import config_settings
import config_child
from pawnlib.utils.operate_handler import Daemon


class MainProc(Daemon):
    """
    You should override this method when you subclass Daemon.
    It will be called after the process has been
    daemonized by start() or restart().
    """
    def run(self):
        main()


def main():
    # pawnlib_default_config()
    while True:
        print(f"main = {pawnlib_config.conf()}")
        print("start daemon")
        time.sleep(1)


if __name__ == "__main__":
    daemon = Daemon(
        pidfile="/tmp/jmon_agent.pid",
        func=main
    )

    pawnlib_config.put_config(b="bb")
    daemon.start()
    # daemon.stop()
    # daemon = MainProc("/tmp/jmon_agent.pid").start()

