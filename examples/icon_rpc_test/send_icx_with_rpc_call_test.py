#!/usr/bin/env python3
import time

import common
from pawnlib.config import pawnlib_config as pawn, pconf, NestedNamespace
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing import is_include_list
from pawnlib.utils import icx_signer, http
from pawnlib import output
from pawnlib.input import PromptWithArgument, PrivateKeyValidator, StringCompareValidator, PrivateKeyOrJsonValidator
import json
import glob
import sys

# icx_signer.compressed = False
# try:
#     wallet = icx_signer.load_wallet_key(
#         "hxfb0a14bf26bfa2e0411be2551aec6f4293017dc1_20230428-103032420.json", "123", raise_on_failure=True,
#     )
#     print(wallet)
# except:
#     pass

wallet = icx_signer.load_wallet_key(
    "hxfb0a14bf26bfa2e0411be2551aec6f4293017dc1_20230428-103032420.json", "123", raise_on_failure=True,
)
print(wallet)

# wallet = icx_signer.WalletCli()
# print(wallet)
#
# disable_ssl_warnings()
# icon_rpc = IconRpcHelper(
#     network_info=NetworkInfo(network_name="cdnet", platform="icon")
# )
#
# icon_rpc.sign_tx(wallet=wallet)
print(f"LAST = {getattr(sys, 'tracebacklimit', 1000)}")
t/sd
