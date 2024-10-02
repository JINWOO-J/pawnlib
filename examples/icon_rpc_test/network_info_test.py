#!/usr/bin/env python3
import time

from scapy.interfaces import network_name

import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing import is_include_list

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

pawn.console.rule("Valid Network information")
for network_dict in network_info_args:
    info = NetworkInfo(
        network_name=network_dict.get('network_name'),
        platform=network_dict.get('platform'),
        force=network_dict.get('force', False),
    )

    pawn.console.log(f"{info.platform}, {info.network_name}, {info} , valid={info.valid_network}")


pawn.console.rule("Invalid Network information")
for network_name in ["vega", "veganet", "sdsd"]:
    try:
        network_info = NetworkInfo(network_name=network_name, platform="havah")
        pawn.console.log(f"network_name='{network_name}' , {network_info}")
    except Exception as e:
        pawn.console.log(f"[red][FAIL] network_name='{network_name}' , {e}")


pawn.console.rule("Custom Network information")

custom_info = NetworkInfo(
    network_name="JinwooNet",
    network_api="http://localhost:9000",
    platform="icon",
)

pawn.console.log(f"({type(custom_info)}){custom_info}")
pawn.console.log(f"({type(custom_info.to_dict())}){custom_info.to_dict()}")

