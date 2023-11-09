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
import json
import requests

disable_ssl_warnings()
icx_signer.compressed = False

private_key = "0x32cf8c963178b1dc15abe5628ce098ce067d7afc8cffa0f27405edd3afa90810"
pawn.console.log(private_key)

network_info = NetworkInfo(network_name="icontest", network_api="http://100.91.150.17:9000", nid="0x53")
dump(network_info.to_dict())


icon_rpc = IconRpcHelper(
    network_info=network_info,
    wallet=icx_signer.load_wallet_key(private_key),
    raise_on_failure=True,
)

pawn.console.rule("Sequential execution - create_deploy_payload, sign_tx, sign_send")

icon_rpc.create_deploy_payload(
    src="SCORE/hello-world/build/libs/hello-world-0.1.0-optimized.jar",
    params={"name": "jinwoo"},
)
icon_rpc.sign_tx()
response = icon_rpc.sign_send()

pawn.console.log(f"[OK] score_address = {response['result'].get('scoreAddress')}")

pawn.console.rule("deploy_score")

response = icon_rpc.deploy_score(
    src="SCORE/hello-world/build/libs/hello-world-0.1.0-optimized.jar",
    params={"name": "jinwoo"},
    is_confirm_send=False,
)

pawn.console.log(f"[OK] score_address = {response['result'].get('scoreAddress')}")
