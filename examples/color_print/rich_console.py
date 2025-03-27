#!/usr/bin/env python3
import common
from pawnlib.utils import log
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import *
from pawnlib.utils import log
import sys
from rich.console import Console


def handle_exception(exc_type, exc_value, exc_traceback):
    pawn.error_logger.error("[Internal] Unexpected exception", exc_info=(exc_type, exc_value, exc_traceback))


LOG_DIR = f"{get_real_path(__file__)}/logs"
APP_NAME = "default_appsss"

pawn.console.log("default printing")

pawn.set(
    PAWN_LINE=True,
)
pawn.console.log("enabled log_path")

pawn.set(
    PAWN_LINE=False,
)
pawn.console.log("disabled log_path")

pawn.set(

    PAWN_CONSOLE=dict(
        log_path=True
    ),
)

pawn.console.log("----------------------------------------------------------------")

rich_console = Console(log_path=False)
rich_console.log("ssssssssssss")
