#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict, MedianFinder, StackList
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn
from pawnlib.typing.check import keys_exists
import statistics
import random


dict_example = {
    "name": "example",
    "description": {
        "description_2": "222",
        "description_3": "333",
    },
    "none_value_key": None,

}
pawn.console.log(f"exists => {keys_exists(dict_example, 'name', 'description')}")
pawn.console.log(f"exists key and none value => {keys_exists(dict_example, 'name', 'none_value_key')}")
pawn.console.log(f"none key => {keys_exists(dict_example, 'name', 'none_key')}")

