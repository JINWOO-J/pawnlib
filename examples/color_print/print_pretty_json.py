#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.output import dump, syntax_highlight, print_var, pretty_json, print_json
from pygments.styles import get_all_styles

json_dict = {
    "jsonrpc": "2.0",
    "method": "icx_sendTransaction",
    "params": {
        "to": "cx0000000000000000000000000000000000000001",
        "dataType": "call",
        "data": {
            "method": "registerProposal",
            "params": {
                "title": "Revision 17",
                "description": "<h1>Revision 17 Proposal</h1><p>The ICON Foundation submits a Network Proposal" * 2,
                "type": "0x1",
                "value": "0x7b22636f6465223a202230783131222c20226e616d65223a20225265766973696f6e3137227d"
            }
        },
        "value": "0x0",
        "from": "hxcc30b1b952503026955a7be935de95c2fdec6670",
        "nonce": "0x1",
        "version": "0x3",
        "timestamp": "0x609139270457f",
        "nid": "0x53",
        "stepLimit": "0xd3ed78e",
        "signature": "SGfE+R5RpmLGtjBcw8syibDWGzmkp02niCgjgwhSHi8ayc3KT7xHhIIzQIOghh4LFvQKCMo/69tuB4yy/I5iQAE="
    },
    "id": 0
}


for style in get_all_styles():
    pawn.console.rule(f"theme = {style} rich")
    text = pretty_json(json_dict, rich_syntax=True, style=style)
    pawn.console.log(text)

    pawn.console.rule(f"theme = {style} highlight")
    print_json(json_dict, style=style)

pawn.console.rule(f"theme =  print_json, normal ")
print_json(json_dict)
