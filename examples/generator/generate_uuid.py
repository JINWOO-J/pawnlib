#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.typing.generator import uuid_generator

pawn.console.log("start")
for _ in range(100):
    uuid = uuid_generator(size=8, count=3)
    pawn.console.log(f"uuid: {uuid}")
