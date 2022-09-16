#!/usr/bin/env python3
import common
from pawnlib.output.color_print import *
from pawnlib.typing.generator import *

for i in range(1, 100):
    rpc = json_rpc(method="icx_sendTransaction", params={"data": "ddddd"})
    pawn.console.log(f"{rpc} {type(rpc)}")

for i in range(1, 100):
    rpc = generate_json_rpc(method="icx_sendTransaction", params={"data": "ddddd"})
    pawn.console.log(f"{rpc} {type(rpc)}")

