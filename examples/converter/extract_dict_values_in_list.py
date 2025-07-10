#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict, MedianFinder, StackList, extract_values_in_list
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn


sample_list = [
    {
        "name": "John Doe",
        "age": 30,
        "height": 1.75,
        "weight": 70,
    },{
        "name": "John",
        "age": 32,
        "height": 1.71,
        "weight": 71,
    }
]


def extract_key_in_list(key, list_of_dicts):
    result = []
    if isinstance(list_of_dicts, list):
        for _dict in list_of_dicts:
            if _dict.get(key):
                result.append(_dict.get(key))
    return result


print(extract_values_in_list("age", sample_list))
print(extract_values_in_list("none_key", sample_list))
