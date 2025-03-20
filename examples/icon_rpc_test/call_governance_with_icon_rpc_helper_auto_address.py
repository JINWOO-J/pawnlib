#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config as pawn
import time
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo, IconRpcTemplates
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump, syntax_highlight, print_var
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing import generator
from pawnlib.utils import icx_signer, http
from pawnlib.typing import const

disable_ssl_warnings()
icx_signer.compressed = False


platform_info = {
    "icon": "lisbon",
    "havah": "vega",
}

for platform, network_name in platform_info.items():
    network_info = NetworkInfo(network_name=network_name, platform=platform)

    pawn.console.log(f"{network_info}")
    pawn.console.log(f"nid = {network_info.nid}, network_api = {network_info.network_api}")
    icon_helper = IconRpcHelper(
        network_info=network_info
    )
    pawn.console.log(icon_helper)
    pawn.console.log(icon_helper.network_info)

    icon_helper._set_governance_address(method="registerProposal")
    auto_address_lookup = icon_helper.governance_address

    pawn.console.log(f"auto_address_lookup={auto_address_lookup}")

    icon_tpl = IconRpcTemplates()

    governance_apis = icon_helper.get_governance_api(return_method_only=True)

    for address, methods in governance_apis.items():
        for method in methods:
            icon_helper._set_governance_address_with_const(method=method)
            auto_address_lookup = icon_helper.governance_address
            pawn.console.debug(f"method={method}, auto_address_lookup={auto_address_lookup}")
            if auto_address_lookup != address:
                pawn.console.log(f"[red] method={method} is not matching. {auto_address_lookup} != {address}")
