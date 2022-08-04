#!/usr/bin/env python3
import common
from pawnlib.utils import log
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import *
from pawnlib.utils import log
import sys


def handle_exception(exc_type, exc_value, exc_traceback):
    pawn.error_logger.error("[Internal] Unexpected exception", exc_info=(exc_type, exc_value, exc_traceback))


LOG_DIR = f"{get_real_path(__file__)}/logs"
APP_NAME = "default_appsss"


# PawnApp(
#     PAWN_LOGGER=dict(
#         # app_name=APP_NAME,
#         log_path=LOG_DIR,
#         stdout=True,
#     ),
#     PAWN_DEBUG=True,
#     app_name=APP_NAME,
#     app_data={},
# )

pawn.set(
    # PAWN_APP_LOGGER=app_logger,
    # PAWN_ERROR_LOGGER=error_logger,
    PAWN_LOGGER=dict(
        # app_name=APP_NAME,
        log_path=LOG_DIR,
        stdout=True,
        use_hook_exception=True,
        # exception_handler=handle_exception

    ),
    # PAWN_DEBUG=True,
    app_name=APP_NAME,
    app_data={},
)



# pawn.console = Console(
#     redirect=True,  # <-- not supported by rich.console.Console
#     record=True,
#     soft_wrap=True,
#     force_terminal=True
#
sys.stdout.write('json =>  {"sds":"sdsd"}')
# pawn.console.log("sdsd")
# pawn.console.log("sdsd", [1, 2, 3])
# pawn.console.log("[blue underline]Looks like a link")
#
# pawn.console.log(pawn)
# pawn.console.out("Local", locals() )
# pawn.console.log("sdsd")
# pawn.console.log("sdsd")
# sys.stdout.write('rich text => [blue underline]Looks like a link')

data = {"sdsd": "sdsd"}

pawn.app_logger.info("sdsd", data)
pawn.console.log("console.log() test")

i = 0
num = 1/i


