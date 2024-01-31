#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict, FlatterDict, flatten
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn
dict_config = {
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

res2 = FlatDict(dict_config, delimiter=".")
dump(res2)
pawn.console.log(f"Get 11111-1.2222-1 => {res2.get('11111-1.2222-1')}")
dump(flatten(dict_config))


list_config = [
        "list1",
        "list2",
        {"aaaa": "bbbbbbbbbbbbbbbbbbbbbbbb"}
    ]

dump(FlatDict(list_config))
dump(FlatDict(list_config).as_dict())
