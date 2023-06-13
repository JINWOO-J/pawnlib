#!/usr/bin/env python3
import time
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing import generator
from pawnlib.utils import icx_signer, http
import json
import requests

disable_ssl_warnings()
# private_key = generator.random_private_key()
icx_signer.compressed = False

private_key = "0x32cf8c963178b1dc15abe5628ce098ce067d7afc8cffa0f27405edd3afa90819"
pawn.console.log(private_key)
singer = icx_signer.IcxSigner(data=private_key)
pawn.console.log(singer.get_hx_address())

res = generator.json_rpc(
    method="icx_sendTransaction",
    params={
        'version': "0x3",
        'nid': "0x53",
        'from': singer.get_hx_address(),
        'to': generator.random_token_address(),
        'value': hex(icx_signer.icx_to_wei(0.1)),
        # 'fee': hex(icx_to_wei(fee)),
        'stepLimit': hex(2000000),
        'timestamp': hex(icx_signer.get_timestamp_us())
    }
)
transaction = singer.sign_tx(tx=res)
# singer.store("./keyfile.json", "password")


pawn.console.log(f"transaction = {json.dumps(transaction)}")
# tx_hash_bytes = icx_signer.get_tx_hash("icx_sendTransaction", res['params'])
#
# print(tx_hash_bytes)
#
# singer.sign(bytes.fromhex(private_key[2:]), )

# res = requests.post(url="https://sejong.net.solidwallet.io/api/v3", json=transaction)
res = requests.post(url="http://20.20.1.122:9000/api/v3", json=transaction)

print(res.text)

