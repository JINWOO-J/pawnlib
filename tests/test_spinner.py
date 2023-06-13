#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass

from pawnlib.utils.log import *
from pawnlib.utils.operate_handler import *
from pawnlib.utils.operate_handler import Spinner

tasks = [f"task {n}" for n in range(1, 5)]
#
with pawn.console.status("[bold green]Working on tasks...") as status:
    while tasks:
        task = tasks.pop(0)
        time.sleep(0.1)
        pawn.console.log(f"{task} complete")
        status.update(f"{task} complete")

