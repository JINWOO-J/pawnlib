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

private_key = "0x32cf8c963178b1dc15abe5628ce098ce067d7afc8cffa0f27405edd3afa90819"
pawn.console.log(private_key)

network_info = NetworkInfo(nid="0x8361", network_api="http://20.20.5.116:9000", platform="havah")
pawn.console.log(f"{network_info}")
pawn.console.log(f"nid = {network_info.nid}, network_api = {network_info.network_api}")
wallet = icx_signer.load_wallet_key(
    file_or_object="0x72008441959d04329d349ba523205aff794d43ed97f78c0c2e94cd6dbeca8c89",
)
icon_helper = IconRpcHelper(
    wallet=wallet,
    network_info=network_info
)
pawn.console.log(icon_helper)
pawn.console.log(icon_helper.network_info)

icon_helper.governance_call(
    method="registerValidator",
    sign=None,
    params={
        "owner": "hx3ece50aaa01f7c4d128c029d569dd86950c34215",
        "nodePublicKey": "0x03921d018c1302f9be67e0aca8e583f8970af127e18727d68af4e7caa81c8eb2b1",
        "grade": "sub",
        "name": "ABC node"
    }
)
icon_helper.print_request()
icon_helper.print_response()
