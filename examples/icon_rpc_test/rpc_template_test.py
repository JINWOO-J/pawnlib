#!/usr/bin/env python3
import time

import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing import is_include_list, const

disable_ssl_warnings()
icon_rpc = IconRpcHelper(url="https://sejong.net.solidwallet.io")


network_info_args = [
    {
        "network_name": "mainnet",
        "platform": "havah",
    },
    {
        "network_name": "MainNet",
        "platform": "icon"
    },
    {
        "network_name": "denea",
        "platform": "havah",
        "force": True,
    },
]

for network_dict in network_info_args:
    info = NetworkInfo(
        network_name=network_dict.get('network_name'),
        platform=network_dict.get('platform'),
        force=network_dict.get('force', False),
    )

    pawn.console.log(f"{info.platform}, {info.network_name}, {info} , valid={info.valid_network}")


rpc_helper = IconRpcHelper(network_info=NetworkInfo(network_name="mainnet"))

# response = rpc_helper.rpc_call(method="icx_getScoreApi", params={"address": const.GOVERNANCE_ADDRESS})
# rpc_helper.print_response()
response = rpc_helper.get_governance_api()
# dump(response)

