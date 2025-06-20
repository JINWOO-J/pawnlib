#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config as pwn, PawnlibConfig
from pawnlib.output import *
from pawnlib.utils.log import AppLogger, CustomLog
from pawnlib.utils import http
import config_child
import config_child_another_call_config
import sys


def app_init():
    log_dir = f"{get_real_path(__file__)}/logs"
    app_logger, error_logger = AppLogger(
        app_name="app_logger",
        log_path=log_dir,
        stdout=True,
    ).get_logger()
    pwn.set(
        PAWN_APP_LOGGER=app_logger,
        PAWN_ERROR_LOGGER=error_logger,
        app_name="app_logging program",
        version="0.0.1",
        app_data={"aaa": "cccc"}
    )


def main():
    from pawnlib.config.globalconfig import pawnlib_config as pawn
    from pawnlib.utils import log

    log.AppLogger(
        app_name="app",
        log_path="./logs",
        stdout=True
    ).set_global()

    pawn.app_logger.info("This is a info message")
    pawn.error_logger.error("This is a info message")

    sys.exit()
    app_init()


    pwn.app_logger.info("sdsdsd")
    pwn.error_logger.info("aaaaa")
    pwn.set(aaaa="sdsdsdsd")
    dump(pwn.to_dict())

    kvPrint("pawnlib_config", pwn)
    cprint("pawnlib_config.to_dict()", "green", end="")
    dump(pwn.to_dict())

    pwn.app_logger.info("Start Main()")

    print(config_child.logging_func())

    config_child.child_app_logging_func("sssss")

    http.jequest("INVALID_URL")
    pwn.app_logger.debug("this is DEBUG message")


    config_child_another_call_config.child_app()


if __name__ == "__main__":
    main()
