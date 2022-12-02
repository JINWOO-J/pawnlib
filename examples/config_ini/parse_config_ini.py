#!/usr/bin/env python3
import common
from pawnlib.utils import log
from pawnlib.config.globalconfig import pawnlib_config as pawn
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
    PAWN_CONFIG_FILE="config_t_1.ini"
)


dump(pawn.to_dict())


sys.exit()

# def ConfigSectionMap(section):
#     dict1 = {}
#     options = Config.options(section)
#     for option in options:
#         try:
#             dict1[option] = Config.get(section, option)
#             if dict1[option] == -1:
#                 DebugPrint("skip: %s" % option)
#         except:
#             print("exception on %s!" % option)
#             dict1[option] = None
#     return dict1


config = ConfigFileParser()
config.read('config_t_1.ini')
sec = config.sections()

pawn.console.log(config.__dict__)


sections = config.sections()
for section in sections:
    pawn.console.log(f"section = {section}")
    res = config.options(section=section)
    pawn.console.log(res)

config_file = config.as_dict()
pawn.console.log(config_file)

# res = converter.UpdateType(default_schema=default_schema, is_debug=True)
res = converter.UpdateType(default_schema=default_schema, is_debug=True)
res2 = res.assign_dict(input_schema=config.as_dict(), use_section=True, is_flatten=False)


# pawn.console.log(res.find_parent_type(key="ServerAliveInterval"))
