#!/usr/bin/env python3
import time

import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, json_rpc
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing.constants import const

disable_ssl_warnings()
icon_rpc = IconRpcHelper(url="https://sejong.net.solidwallet.io")
checked_balance = icon_rpc.get_balance(address="hx5a05b58a25a1e5ea0f1d5715e1f655dffc1fb30a", is_comma=True)


pawn.console.log(f"balance = {checked_balance} ICX")

# dump(convert_dict_hex_to_int(res3))

step_price = icon_rpc.get_step_price()

pawn.console.log(f"step_price={hex_to_number(step_price, debug=True)}")
# pawn.console.log(f"get_step_cost={icon_rpc.get_step_costs()}")
pawn.console.log(convert_dict_hex_to_int(icon_rpc._get_step_costs(), debug=True))


estimate_payload = json_rpc(
    method="icx_sendTransaction",
    params={
        "from": "hx5a05b58a25a1e5ea0f1d5715e1f655dffc1fb30a",
        "to": "hx5a05b58a25a1e5ea0f1d5715e1f655dffc1fb30a",
        "timestamp": "0x563a6cf330136",
        "version": "0x3",
        "nid": "0x1",
        "data": {
            "1": "sdsd",
            "2": "sdsd",
            "3": "sdsd",
            "4": "sdsd",
        }
    }
)
estimate = icon_rpc.get_estimate_step(tx=estimate_payload)
step_cost = hex_to_number(icon_rpc.get_step_cost())

icx_fee = hex_to_number(estimate) * hex_to_number(step_price) / const.TINT
step_limit = hex(hex_to_number(estimate) + hex_to_number(step_cost))

pawn.console.log(f"icx_fee => estimate[i]({hex_to_number(estimate, debug=True)})[/i] * "
                 f"step_price[i]({hex_to_number(step_price, debug=True)})[/i] = {icx_fee}")
pawn.console.log(f"step_limit => {hex_to_number(step_limit, debug=True)}")


pawn.console.log(icon_rpc.get_step_limit(tx=estimate_payload))
# icon_rpc.get_tx_wait(tx_hash="0x2175d5b307b657d1bada071d721b011462c0772e4ac3a4c9f9723a9f1f9de7c0")

