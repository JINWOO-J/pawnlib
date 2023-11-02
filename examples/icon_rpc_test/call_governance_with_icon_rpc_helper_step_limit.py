#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import  disable_ssl_warnings, IconRpcHelper, NetworkInfo
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump, syntax_highlight, print_var, pretty_json
from pawnlib.typing.converter import json_to_hexadecimal, hexadecimal_to_json
from pawnlib.utils import icx_signer, http

disable_ssl_warnings()
icx_signer.compressed = False

private_key = "89d1d2860bec9163e3473adc14d8e7d4938a6003074f61b6bf97a7faa21cd570"
pawn.console.log(private_key)

network_info = NetworkInfo(nid="0x53", network_api="http://100.91.150.17:9000", platform="icon")
pawn.console.log(f"{network_info}")
pawn.console.log(f"nid = {network_info.nid}, network_api = {network_info.network_api}")
wallet = icx_signer.load_wallet_key(
    file_or_object=private_key,
)
icon_helper = IconRpcHelper(
    wallet=wallet,
    network_info=network_info,
    # debug=True,
)
pawn.console.print(icon_helper)
pawn.console.tprint(icon_helper.network_info)
pawn.console.log(icon_helper.network_info)

_hex_value = json_to_hexadecimal({'code': '0x11', 'name': 'Revision17'})
print(hexadecimal_to_json(_hex_value))

pawn.console.rule("Case OK ")
icon_helper.governance_call(
    method="registerProposal",
    # sign=False,
    step_limit=hex(222222222),
    params={
            "title": "Revision 17",
            "description": "<h1>Revision 17 Proposal</h1><p>The ICON Foundation submits a Network Proposal",
            "type": "0x1",
            "value": _hex_value
    },
)

pawn.console.rule("Case Fail ")
icon_helper.governance_call(
    method="registerProposal",
    # sign=False,
    step_limit=hex(222222222),
    params={
        "title": "Revision 17",
        "description": "<h1>Revision 17 Proposal</h1><p>The ICON Foundation submits a Network Proposal",
        "type": "0x1",
        "value": f"{_hex_value}sss"
    },
)

pawn.console.rule("Case OK ")
icon_helper.governance_call(
    method="registerProposal",
    # sign=False,
    step_limit=hex(222222222),
    params={
        "title": "Revision 17",
        "description": "<h1>Revision 17 Proposal</h1><p>The ICON Foundation submits a Network Proposal",
        "type": "0x1",
        "value": _hex_value
    },
)
# icon_helper.print_request()
# icon_helper.print_response()
