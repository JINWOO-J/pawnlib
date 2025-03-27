#!/usr/bin/env python3
import time
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump, syntax_highlight, print_var
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing import generator
from pawnlib.utils import icx_signer, http

disable_ssl_warnings()
icx_signer.compressed = False

try:
    wallet = icx_signer.load_wallet_key(
        file_or_object="hxfb0a14bf26bfa2e0411be2551aec6f4293017dc1_20230428-103032420.json",
        password="WRONG_PASSWORD",
    )
except Exception as e:
    pawn.console.log(e)


wallet = icx_signer.load_wallet_key(
    file_or_object="hxfb0a14bf26bfa2e0411be2551aec6f4293017dc1_20230428-103032420.json",
    password="WRONG_PASSWORD",
)

