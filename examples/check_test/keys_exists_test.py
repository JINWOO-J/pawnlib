#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict, MedianFinder, StackList
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn
from pawnlib.typing.check import keys_exists, get_if_keys_exist
import statistics
import random
from pawnlib.typing.converter import flatten

dict_example = {
    "name": "example",
    "description": {
        "description_2": "222",
        "description_3": "333",
        "description_4": {
            "description_5": "aaaaaaa"
        }
    },
    "none_value_key": None,
    "a": {
        "sss": []
    },
    "b": {
        "b-1": {
            "b-2" : "sss"
        }
    },
    "nested_list": [{"key1": "value1"}, {"key2": "value2"}],
}
pawn.console.log(f"exists => {keys_exists(dict_example, 'name')}")
pawn.console.log(f"exists => {keys_exists(dict_example, 'b', 'b-1', 'b-2')}")

pawn.console.log(f"exists => {keys_exists(dict_example, 'description', 'description_4', 'description_5')}")
pawn.console.log(f"exists key => {keys_exists(dict_example,  'description', 'description_2')}")
pawn.console.log(f"exists key and none value => {keys_exists(dict_example, 'name', 'none_value_key')}")
pawn.console.log(f"none key => {keys_exists(dict_example, 'name', 'none_key')}")
pawn.console.log(f"none key => {keys_exists(dict_example, 'name', 'descriion')}")
pawn.console.log(f"none key => {keys_exists(dict_example, 'a', 'sss' )}")

pawn.console.log(f"none key => {keys_exists(dict_example, 'nested_list', '0' )}")
pawn.console.log(f"none key => {get_if_keys_exist(dict_example, 'nested_list', '0' )}")
pawn.console.log(f"none key => {get_if_keys_exist(dict_example, 'nested_list', '10' , default='___NONE____')}")


flatten_dict = flatten(dict_example)
print(flatten_dict.get('b.b-1.b-2'))
