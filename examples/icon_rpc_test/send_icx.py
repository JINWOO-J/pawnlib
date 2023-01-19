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
import sys


disable_ssl_warnings()

# icon_rpc = IconRpcHelper(url="https://sejong.net.solidwallet.io")
# res2 = icon_rpc.get_balance(address="hx5a05b58a25a1e5ea0f1d5715e1f655dffc1fb30a", is_comma=True)
# res3 = icon_rpc.get_tx(tx_hash="0x2175d5b307b657d1bada071d721b011462c0772e4ac3a4c9f9723a9f1f9de7c0", return_key="result")
# # res3 = icon_rpc.get_tx(tx_hash="0x2175d5b307b657d1bada071d721b011462c0772e4ac3a4c9f9723a9f1f9de7c0")
# # res2 = icon_rpc.get_balance()
#
# dump(convert_dict_hex_to_int(res3, ignore_keys=["blockHash", "txHash"]))
# dump(convert_dict_hex_to_int(res3, ignore_keys=["blockHash", 'txHash'], is_comma=True, debug=True, ansi=True))
#
# pawn.console.log(f"balance = {res2} ICX")


private_key = generator.random_private_key()

private_key = "0xe88c5dc27eadd2f5b7b30214e23699e8ce9e97744655fae7f8320fca65b41da3"

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

singer.store("./keyfile.json", "password")

import json
pawn.console.log(f"transaction = {json.dumps(transaction)}")
# tx_hash_bytes = icx_signer.get_tx_hash("icx_sendTransaction", res['params'])
#
# print(tx_hash_bytes)
#
# singer.sign(bytes.fromhex(private_key[2:]), )

import requests

res = requests.post(url="https://sejong.net.solidwallet.io/api/v3", json=transaction)

print(res.text)

