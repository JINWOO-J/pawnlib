#!/usr/bin/env python3
import unittest
import os
try:
    import common
except:
    pass
from devtools import debug
from pawnlib.output.file import Tail

async def callback(line):
    print(f"Captured log: {line}")

def custom_formatter(line):
    return f"[Formatted] {line}"


tail = Tail(
    log_file_paths="tail.log",
    filters=["ERROR", "WARNING"],
    callback=callback,
    async_mode=False,
)
tail.follow()
