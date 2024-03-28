#!/usr/bin/env python3
import  common
from pawnlib.utils.genesis import *
from pawnlib.output import get_fi
from pawnlib.utils import in_memory_zip

def genesis_json():
    return {
        "accounts": [
            {
                "address": "cx0000000000000000000000000000000000000001",
                "name": "governance",
                "score": {
                    "contentId": "hash:{{ziphash:governance}}",
                    "contentType": "application/zip",
                    "owner": "hx6e1dd0d4432620778b54b2bbc21ac3df961adf89",
                }
            },
            {
                "address": "cx1100000000000000000000000000000000000000",
                "name": "vault",
                "balance": "0x1043561a8829300000",
                "score": {
                    "contentId": "hash:{{hash:governance-2.1.3-optimized.jar}}",
                    "contentType": "application/java",
                    "owner": "hx54f021fc4a755a2a2c9fdda47a16ce4cd3f3b43e",
                }
            }
        ],
        "chain": {
            "revision": "0xd",
            "validatorList": [],
            "blockInterval": "0x7d0", # 2 secs
            "roundLimitFactor": "0x3",
            "fee": {
                "stepPrice": "0x2e90edd00",
                "stepLimit": {
                    "invoke": "0x9502f900",
                    "query": "0x2faf080"
                },
                "stepCosts": {
                    "apiCall": "0x2710",
                    "contractCall": "0x61a8",
                    "contractCreate": "0x3b9aca00",
                    "contractSet": "0x3a98",
                    "contractUpdate": "0x3b9aca00",
                    "default": "0x186a0",
                    "delete": "-0xf0",
                    "deleteBase": "0xc8",
                    "get": "0x19",
                    "getBase": "0xbb8",
                    "input": "0xc8",
                    "log": "0x64",
                    "logBase": "0x1388",
                    "schema": "0x1",
                    "set": "0x140",
                    "setBase": "0x2710"
                }
            },

        },
        "message": "Genesis",
        "nid":  "0x79"
    }

cid = genesis_generator(genesis_json_or_dict=genesis_json(), genesis_filename="icon_genesis.zip")
pawn.console.log(f"cid = {cid}")



res = create_cid_from_genesis_zip("icon_genesis.zip")
pawn.console.log(f"cid = {res}, {type(res)}")

