#!/usr/bin/env python3
import time

import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number

disable_ssl_warnings()

# res = icon_rpc_call(
#     url="https://lisbon.net.solidwallet.io",
#     method="icx_getTotalSupply",
# )
#
#
# pawn.console.log(hex_to_number("0x232322322222232323232", is_comma=True))
#
# res['dddd'] = {"sdsd": "sdsd"}
# dump(convert_dict_hex_to_int(res, debug=True, is_comma=True))


icon_rpc = IconRpcHelper(url="https://sejong.net.solidwallet.io")
res2 = icon_rpc.get_balance(address="hx5a05b58a25a1e5ea0f1d5715e1f655dffc1fb30a", is_comma=True)
res3 = icon_rpc.get_tx(tx_hash="0x2175d5b307b657d1bada071d721b011462c0772e4ac3a4c9f9723a9f1f9de7c0", return_key="result")
# res3 = icon_rpc.get_tx(tx_hash="0x2175d5b307b657d1bada071d721b011462c0772e4ac3a4c9f9723a9f1f9de7c0")
# res2 = icon_rpc.get_balance()

dump(convert_dict_hex_to_int(res3, ignore_keys=["blockHash", "txHash"]))
dump(convert_dict_hex_to_int(res3, ignore_keys=["blockHash", 'txHash'], is_comma=True, debug=True, ansi=True))

pawn.console.log(f"balance = {res2} ICX")

# dump(convert_dict_hex_to_int(res3))


#

icon_rpc.get_tx_wait(tx_hash="0x2175d5b307b657d1bada071d721b011462c0772e4ac3a4c9f9723a9f1f9de7c0")

