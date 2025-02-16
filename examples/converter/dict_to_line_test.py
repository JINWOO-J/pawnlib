#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict, FlatterDict, flatten, dict_to_line
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


result = dict_to_line(dict_config)

pawn.console.log(result)
