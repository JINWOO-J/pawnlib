#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict, FlatterDict, flatten, Flattener
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn
dict_config = {
    "key1": "key1 is value",
    "111": "sdsdsd",
    "1111": "sdsdsd",
    "11111": "sdsdsd",
    "11111-1": {
        "2222-1": "xcxcxc",
        "212222-1": "xcxcxc"
    },
    "list": [
        "list1",
        "list2",
        {"aaaa": "bbbbbbbbbbbbbbbbbbbbbbbb"}
    ]
}

res2 = Flattener(dict_config, delimiter=".")
pawn.console.rule("Print as String")
dump(res2)
pawn.console.rule("Print as dict ")
dump(res2.to_dict())
pawn.console.rule("Print key ")
pawn.console.log(f"Get 11111-1.2222-1 => {res2.get('11111-1.2222-1')}")

list_config = [
        "list1",
        "list2",
        {"aaaa": "bbbbbbbbbbbbbbbbbbbbbbbb"}
    ]

dump(Flattener(list_config))

flatten_dict_test = Flattener(list_config)

pawn.console.rule("Unflatten ")
dump(flatten_dict_test.unflatten())

unflatten_dict = FlatDict(list_config).as_dict()

rpc_response = {
    "jsonrpc": "2.0",
    "result": {
        "block_hash": "db0e18176318217d246ff10aee570f8d31a430cacf8bca2e0b0a97fc622f103f",
        "confirmed_transaction_list": [
            {
                "data": {
                    "result": {
                        "coveredByFee": "0x0",
                        "coveredByOverIssuedICX": "0x0",
                        "issue": "0x201fdfcf45d9425f"
                    }
                },
                "dataType": "base",
                "timestamp": "0x62760444bdf10",
                "txHash": "0xc81ff93eb41f0b762a8342ec62c9bc2a4322586a4cd050d23306d73bbf1392ab",
                "version": "0x3"
            }
        ],
        "height": 8747878,
        "merkle_tree_root_hash": "016a2af5fe5001c053a1856f996ad66f6ae1877f547deb645dee909cac689bd9",
        "peer_id": "hxf2b4ef450c4f158b4611e234bb57f00ad7a615ef",
        "prev_block_hash": "6ae91471d1aea76544e58fe6e222dcc08a73ed90b5a9c679c0a78b08aca2f111",
        "signature": "",
        "time_stamp": 1732144276430608,
        "version": "2.0"
    },
    "id": 2848
}

flatten_rpc = Flattener(rpc_response)
pawn.console.print(flatten_rpc.get("result.time_stamp"))
pawn.console.print(repr(flatten_rpc))

pawn.console.print(flatten_rpc.to_dict())

pawn.console.rule("Keep list")

pawn.console.log(Flattener(rpc_response, keep_lists=True).to_dict())

pawn.console.rule("get 'result'")
pawn.console.log(flatten_rpc.get('result'))

pawn.console.rule("get 'result.prev_block_hash'")
pawn.console.log(flatten_rpc.get('result.prev_block_hash'))

exit()

pawn.console.print(flatten_rpc.unflatten())
pawn.console.print(flatten_rpc.original_value)



