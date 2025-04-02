#!/usr/bin/env python3
import time
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump, syntax_highlight, print_var, print_json
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing import generator
from pawnlib.utils import icx_signer, http
import json
import requests

disable_ssl_warnings()
icx_signer.compressed = False

private_key = "0x32cf8c963178b1dc15abe5628ce098ce067d7afc8cffa0f27405edd3afa90810"
pawn.console.log(private_key)

network_info = NetworkInfo(network_name="icontest", network_api="http://icontest01:9000", nid="0x53")
dump(network_info.to_dict())


icon_rpc = IconRpcHelper(
    network_info=network_info,
    wallet=icx_signer.load_wallet_key(private_key),
    raise_on_failure=False,
)

pawn.console.rule("Sequential execution - create_deploy_payload, sign_tx, sign_send")

pawn.console.rule("1. Create deploy payload")
payload = icon_rpc.create_deploy_payload(
    src="SCORE/hello-world/build/libs/hello-world-0.1.0-optimized.jar",
    params={"name": "jinwoo"},
)
print_json(payload)

pawn.console.rule("2. Calculate Fee")
pawn.console.log(f"Fee = {icon_rpc.get_fee(payload, symbol=True)}")

pawn.console.rule("3. Sign the Transaction")
signed_payload = icon_rpc.sign_tx(payload=payload)
icon_rpc.print_request()

pawn.console.rule("4. Send the Transaction")
icon_rpc.rpc_call(payload=signed_payload)
icon_rpc.print_response()

pawn.console.rule("5. Wait the Transaction")
icon_rpc.get_tx_wait()
icon_rpc.print_response()
