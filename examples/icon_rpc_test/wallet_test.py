#!/usr/bin/env python3
import time

import common
from pawnlib.config import pawnlib_config as pawn, pconf, NestedNamespace
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing import is_include_list, random_private_key
from pawnlib.utils import icx_signer, http
from pawnlib import output
from pawnlib.input import PromptWithArgument, PrivateKeyValidator, StringCompareValidator, PrivateKeyOrJsonValidator
import json
import glob
import sys

# private_key = random_private_key()
private_key = "6572c6f2641b2ad1335b918e49db0309cc123602064c7f30de8fa48b55e08667"

wallet = icx_signer.load_wallet_key(
    private_key
)
pawn.console.log(wallet)


def wallet_clit_new_init(self, args=None):
    self._args = args
    self._wallet = ""

icx_signer.WalletCli.__init__ = wallet_clit_new_init

pawn.console.log(icx_signer.generate_keys())#


wallet_cli = icx_signer.WalletCli(args=NestedNamespace(base_dir="sdsdsdsssd"))

pawn.console.log(wallet_cli._args)
