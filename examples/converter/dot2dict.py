#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn
config = {
    "111": "sdsdsd",
    "1111": "sdsdsd",
    "11111": "sdsdsd",
    "11111-1": {
        "2222-1": "xcxcxc",
        "212222-1": "xcxcxc"
    },

}

res2 = FlatDict(config, delimiter=".")

dump(res2.get('11111-1.2222-1'))
