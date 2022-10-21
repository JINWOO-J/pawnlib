#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.utils.http import jequest
from pawnlib.output import *
from pawnlib import logger
import logging

from pawnlib.typing import converter


def app_init():
    log_dir = f"{get_real_path(__file__)}/logs"
    pawn.set(
        PAWN_LOGGER=dict(
            log_path=log_dir,
            log_level="DEBUG",
            stdout_level="DEBUG",
            stdout=True,
            use_hook_exception=True,
        ),
        PAWN_DEBUG=True,
        app_name="app_logging",
        version="0.0.1",
        app_data={"aaa": "cccc"}
    )


def main():
    app_init()
    # pawn.app_logger.addHandler(logging.getLogger('PAWNLIB-LOGGER'))
    # logging.addHandler()

    # pawn_logger = logging.getLogger('PAWNS')
    # pawn_logger.propagate = 0
    # pawn_logger.addHandler(pawn.app_logger)

    # logger.addHandler(pawn.app_logger)
    # logger.setLevel('DEBUG')
    # logger.addHandler(pawn.app_logger)

    # set_logger("DEBUG", handler, formatter)

    # pawn.console.log("START")
    # pawn.app_logger.info("info")
    # pawn.app_logger.info("App logger initializing")
    # pawn.app_logger.debug("Debug logger initializing")
    # pawn.error_logger.error("Error logger initializing")
    # dump(logging.Logger.manager.loggerDict)

    # printout()
    # logging.getLogger('PAWNLIB-LOGGER')
    # pawn.app_logger.addHandler(logger)
    jequest("http")
    # converter.UpdateType()
    #
    # from rich.text import Text
    #
    from rich.markup import render
    #
    from rich.markup import render
    text = f"[bold]Bold[italic] bold and italic [/bold]italic[/italic]"

    # logger.info("[bold]EXITING...[/bold]", extra=dict(markup=True))
    logger.info("[bold]EXITING...[/bold]")

    pawn.console.log(render(text))

    #
    # rendered_text = render(text)
    # pawn.console.log(rendered_text)

    # pawn.console.debug("sdssd")


if __name__ == "__main__":
    main()


def set_debug_logger(logger_name=None, get_logger_name='PAWNS', level='DEBUG'):
    __logger = logging.getLogger(get_logger_name)
    __logger.propagate = 0
    __logger.setLevel(level)
    __logger.addHandler(logger_name)
