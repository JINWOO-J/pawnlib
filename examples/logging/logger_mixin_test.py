#!/usr/bin/env python3
import datetime
import common
from pawnlib.typing.constants import const
from pawnlib.config.globalconfig import pawnlib_config as pawn

from pawnlib.utils.http import jequest
from pawnlib.output import *
from pawnlib import logger
from pawnlib.utils.log import print_logger_configurations
from pawnlib.config.logging_config import (
    setup_app_logger, LoggerMixin, ConsoleLoggerAdapter, LoggerMixinVerbose, create_app_logger,
    LoggerFactory, ConsoleLoggerHandler, verbose_to_log_level, CleanAndDetailTimeFormatter, TimedRotatingFileHandler,
    change_propagate_setting
)

from rich.console import Console
from typing import Optional, Union
import logging
import os
from contextlib import contextmanager

from pawnlib.typing import converter


class ConsoleLoggerTest:
    def __init__(self, logger=None, verbose=0):
        self.logger = ConsoleLoggerAdapter(logger_name=f"{self.__module__}.{self.__class__.__name__}", verbose=verbose)
        self.logger.info("Start")


class LoggerMixinTest(LoggerMixinVerbose):
    def __init__(self, logger=None, verbose=0):
        self.init_logger(logger=logger, verbose=verbose)
        # print_var(self.logger)
        self.logger.info("LoggerMixinTest Start")

class LoggerChildTest(LoggerMixinTest):
    def __init__(self, logger=None, verbose=0):
        self.init_logger(logger=logger, verbose=verbose)
        # print_var(self.logger)
        self.logger.info("LoggerChildTest Start")
        self.logger.warning("LoggerChildTest Start")
        self.logger.critical("LoggerChildTest Start")


class LoggerMixinAnotherTest(LoggerMixinVerbose):
    def __init__(self, logger=None, verbose=-1):
        self.init_logger(logger=logger, verbose=verbose)
        # print_var(self.logger)
        pawn.console.log(self.logger)

        self.logger.warning("1. LoggerMixinAnotherTest Start")
        self.logger.info("2. LoggerMixinAnotherTest Start")
        self.logger.critical("3. LoggerMixinAnotherTest Start")
        self.logger.error("4. LoggerMixinAnotherTest Start")
        self.logger.trace("5. LoggerMixinAnotherTest Start")


def main():
    main_logger = LoggerFactory.create_app_logger(log_type="console",  app_name="icon_tools", propagate=False)
    main_logger.info("Root")
    main_logger.info("main()")

    pawn.console.rule("LoggerMixin")
    # LoggerMixinTest(verbose=1)
    # LoggerChildTest(verbose=0)
    LoggerMixinAnotherTest(verbose=-1)
    LoggerMixinAnotherTest(verbose=0)
    LoggerMixinAnotherTest(verbose=1)
    LoggerMixinAnotherTest(verbose=2)
    LoggerMixinAnotherTest(verbose=3)

    # change_propagate_setting(propagate=True, propagate_scope="all", log_level=logging.DEBUG)

    # LoggerFactory.set_global_log_level(verbose=3, use_global=True)


    print_logger_configurations()


if __name__ == "__main__":
    main()
