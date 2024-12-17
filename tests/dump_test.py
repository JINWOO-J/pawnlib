#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass
from pawnlib.output import dump
from pawnlib.typing.converter import is_hex

tx = {
    "id": 2848,
    "jsonrpc": "2.0",
    "method": "icx_sendTransaction",
    "params": {
        "from": "",
        "to": "hx5b34243a275ecdbceda6286615ed3f8aec9053b9",
        "stepLimit": "0x4a817c800",
        "value": "0x38d7ea4c68000",
        "nid": "0x110",
        "nonce": "0x8",
        "version": "0x3"
    }
}


dump(tx, hex_to_int=False)
dump(tx, hex_to_int=True)

# for k,v in tx['params'].items():
#     print(f"k={k}, v={v}, {type(v)}, hex?= {is_hex(v)}")
