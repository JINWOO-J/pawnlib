#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.typing.check import guess_type, return_guess_type

check_list = [
    "1.1",
    1.1,
    "23",
    22,
    0,
    "",
    "2022-02-11",
    "true",
    "True",
    True,

]


for item in check_list:
    pawn.console.log(f"{item:<10} {str(type(item)):<16}-> {str(guess_type(item)):<16}, "
                     f"return={str(return_guess_type(item)):<15}, type={type(return_guess_type(item))}")
