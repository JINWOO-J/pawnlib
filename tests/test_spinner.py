#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass

import sys
from parameterized import parameterized
from devtools import debug
# from pawnlib.typing import converter
# from pawnlib.config import pawnlib_config as pawn

import os
import random
from parameterized import parameterized

from pawnlib.output import *
from pawnlib.utils.log import *
from pawnlib.utils.operate_handler import *
from pawnlib.utils.operate_handler import Spinner


STDOUT = True
pawn.set(
    # PAWN_LOGGER=dict(
    #     stdout=STDOUT,
    #     stdout_level="ERROR",
    #     use_hook_exception=True,
    # ),
    PAWN_DEBUG=False, # Don't use production, because it's not stored exception log.
    app_data={}
)

pawn.console.log("sdsd")
pawn.console.debug("sdsd")


with Spinner(text="Simple Wait message") as spinner:
    time.sleep(1)
    spinner.stop()


tasks = [f"task {n}" for n in range(1, 11)]
#
with pawn.console.status("[bold green]Working on tasks...") as status:
    while tasks:
        task = tasks.pop(0)
        time.sleep(1)
        pawn.console.log(f"{task} complete")
        status.update(f"{task} complete")


# WaitStateLoop(
#     loop_function=partial(check_port, interface, 8000),
#     exit_function=check,
#     timeout=10,
#     delay=1,
#     text="Wait for "
# ).run()

