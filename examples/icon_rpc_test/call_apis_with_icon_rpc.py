#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo, IconRpcTemplates
from pawnlib.output.color_print import json_compact_dumps
from pawnlib.utils import icx_signer, http
from rich.syntax import Syntax
from rich.console import Console

disable_ssl_warnings()
icx_signer.compressed = False

platform_info = {
    "icon": "lisbon",
    "havah": "vega",
}

console = Console(width=100)

for platform_name, network_name in platform_info.items():
    network_info = NetworkInfo(platform=platform_name, network_name=network_name)
    pawn.console.debug(f"{network_info.platform.upper()}, {network_info.network_name}, nid={network_info.nid}, network_api={network_info.network_api}")
    icon_helper = IconRpcHelper(network_info=network_info)

    governance_apis = icon_helper.get_governance_api(return_method_only=True)
    # print_syntax(f"class {network_info.platform.upper()}Constants:\n"
    #              f"\t{network_info.platform.upper()}_METHODS = {json_compact_dumps(governance_apis )}",
    #              name="python", line_indent="", rich=True
    #              )

    syntax_code = Syntax(f"class {network_info.platform.upper()}Constants:\n"
                         f"\t{network_info.platform.upper()}_METHODS = {json_compact_dumps(governance_apis)}",
                         "python", word_wrap=True)

    console.print(syntax_code)
    print()
    print()
