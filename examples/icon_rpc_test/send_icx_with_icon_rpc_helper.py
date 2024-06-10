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
# icx_signer.compressed = False

private_key = "0x32cf8c963178b1dc15abe5628ce098ce067d7afc8cffa0f27405edd3afa90810"
pawn.console.log(private_key)
network_info = NetworkInfo(network_name="jw-test", network_api="http://20.20.4.129:9000")

wallet = icx_signer.load_wallet_key(private_key)

singer = icx_signer.IcxSigner(data=private_key)
singer_org = icx_signer.IcxSigner(data=private_key)

icon_rpc = IconRpcHelper(
    network_info=network_info,
    wallet=wallet,
    raise_on_failure=True,
    wait_sleep=0.01,
    tx_method='icx_getTransactionByHash',
)

pawn.console.log(network_info)
payload = generator.json_rpc(
    method="icx_sendTransaction",
    params={
        'version': "0x3",
        'nid': "0x53",
        'to': generator.random_token_address(),
        'value': hex(icx_signer.icx_to_wei(0.1)),
        # 'fee': hex(icx_to_wei(fee)),
        # 'stepLimit': hex(2000000),
        # 'timestamp': hex(icx_signer.get_timestamp_us())
    }
)


signed_transaction = icon_rpc.sign_tx(payload=payload)
print_var(signed_transaction)
tx_result = icon_rpc.sign_send(is_block_time=True)
pawn.console.print(f"tx_result={tx_result}, elapsed={icon_rpc.get_total_elapsed()}, elapsed={icon_rpc.get_elapsed().sum()}")

print_var(tx_result)

# icon_rpc.analyze_tx_block_time()


print("END---")
