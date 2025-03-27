#!/usr/bin/env python3
import common
from pawnlib.utils import log
from pawnlib.config.globalconfig import pawnlib_config as pawn, pconf
from pawnlib.output.color_print import *
from pawnlib.typing import converter


from pawnlib.typing.converter import recursive_operate_dict, lower_case, ordereddict_to_dict
import configparser


def callback_schema():
    return "callback_result"


default_schema = {
    "default__timeout": {
        "type": "int",
        "default": 3
    },
    "default__db_type": {
        "type": "string",
        "default": "influxdb_v2",
    },
    "default": {
        "ServerAliveInterval": {
            "type": "int",
            "default": 1
        },
        "verAliveInterval": {
            "type": "float",
            "default": 1
        },
        "Compression": {
            "type": "boolean",
            "default": True
        },
        "ForwardX11": {
            "type": "boolean",
            "default": True
        },

        "CompressionLevel": {
            "type": "int",
            "default": True
        },
        "Function_Key": {
            "type": "function",
            "default": "__main__.callback_schema",
        },
        "Function_Key2": {
            "type": "function",
            "default": callback_schema,
        }
    }
}


pawn.set(
    PAWN_DEBUG=True,
    PAWN_TIMEOUT=0,
    app_name="sssd",
    PAWN_CONFIG_FILE="config_t_1.ini",
    data={"sdsd": "sdsd"}
)

dump(pawn.to_dict())

print(pawn.get_path())

config_data = pconf().data

pawn.console.log(config_data.get_nested(["sdsd"]))
