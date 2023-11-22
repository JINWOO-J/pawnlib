#!/usr/bin/env python3
import time
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump, syntax_highlight, print_var
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing import generator
from pawnlib.utils import icx_signer_org,  icx_signer_v2, icx_signer
import  hashlib
import base64
import json
import requests

disable_ssl_warnings()
def sign_tester(icx_signer):
    icx_signer.compressed = False

    private_key = "0x32cf8c963178b1dc15abe5628ce098ce067d7afc8cffa0f27405edd3afa90810"
    pawn.console.log(private_key)
    network_info = NetworkInfo(network_name="cdnet")

    singer = icx_signer.IcxSigner(data=private_key)

    pawn.console.log(network_info)

    payload = generator.json_rpc(
        method="icx_sendTransaction",
        params={
            'version': "0x3",
            'nid': "0x53",
            'from': "hx408db35d5fe9ed1c179f38b3d5fe193041a8e7fd",
            'to': "hx8fdb2cf4b50fe4c4bec18ae76bb437eb42c3fb8f",
            'value': hex(icx_signer.icx_to_wei(0.1)),
            # 'fee': hex(icx_to_wei(fee)),
            'stepLimit': hex(2000000),
            'timestamp': "0x60ab87fe3da8e"
        }
    )


    signed_transaction = singer.sign_tx(tx=payload)
    print_var(signed_transaction)
    #
    # msg_hash = icx_signer.serialize(payload['params'])
    # tx_hash_bytes = icx_signer.get_tx_hash(payload['params'])
    #
    #
    # print(f"singer.get_pubkey_bytes() = {singer.get_pubkey_bytes()}")
    # verifier = icx_signer.IcxSignVerifier(singer.get_pubkey_bytes())
    # print(f"get_address=> {verifier.get_address()}")
    #
    #
    # exit()
    #
    # signature_bytes = base64.b64decode(signed_transaction['params']['signature'])
    #
    # print_var(signature_bytes)
    # print_var(msg_hash)
    #
    # # is_valid = verifier.verify(msg_hash, signature_bytes)
    # print(verifier)


# sign_tester(icx_signer=icx_signer_org)
sign_tester(icx_signer=icx_signer)
