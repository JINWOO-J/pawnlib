#!/usr/bin/env python3
import common
# from pawnlib.output.color_print import
from pawnlib.typing.generator import Counter, increase_token_address, increase_hex, generate_hex, generate_token_address
from pawnlib.config import pawn


for i in Counter(start=0, step=1, stop=4):
    pawn.console.print(f"Counter => {i}")

for i in Counter(start=0, step=1, stop=4, convert_func=generate_token_address):
    pawn.console.print(f"Counter => {i}")


for i in Counter(start=0, step=1, stop=4, convert_func=generate_hex, kwargs={"zfill": 10}):
    pawn.console.print(f"Counter => {i}")
