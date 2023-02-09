#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.typing.check import guess_type, return_guess_type

check_list = [
    "1.1",
    1.1,
    1.111,
    23,
    "23",
    23232323,
    0,
    "",
    "2022-02-11",
    "true",
    "True",
    True,

]

for item in check_list:
    pawn.console.log(f"{item} {type(item)} => {guess_type(item)} , return={return_guess_type(item)}")
