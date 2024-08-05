#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump, syntax_highlight, print_var
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing import generator
from pawnlib.utils import icx_signer, http
from pawnlib.typing import const

disable_ssl_warnings()
icx_signer.compressed = False

private_key = "fe3baee452b2ea01ea76e98c00fa206bdde74a6894b5e0f5e67a88427d27c3bb"
pawn.console.log(private_key)
network_info = NetworkInfo(network_name="icontest", network_api="http://icontest01:9000", nid="0x53")

pawn.console.log(f"{network_info}")
pawn.console.log(f"nid = {network_info.nid}, network_api = {network_info.network_api}")
wallet = icx_signer.load_wallet_key(
    file_or_object=private_key,
)
icon_helper = IconRpcHelper(
    wallet=wallet,
    network_info=network_info
)
pawn.console.log(icon_helper)
pawn.console.log(icon_helper.network_info)

response = icon_helper.governance_call(
    method="registerProposal",
    sign=True,
    value=hex(100*const.TINT),
    params=   {
        "title": "Revision 21 Proposal",
        "description": "<h1>Revision 21 Proposal</h1>",
        "value": "0x5b7b226e616d65223a20227265766973696f6e222c202276616c7565223a207b227265766973696f6e223a202230783135227d7d5d",
    },
    is_wait=False,
)
icon_helper.print_request(message="registerProposal payload")
icon_helper.print_response(message="registerProposal response")

icon_helper.get_tx_wait()
