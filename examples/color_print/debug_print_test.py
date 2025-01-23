#!/usr/bin/env python3
import common
from pawnlib.output.color_print import *
from pygments.styles import get_all_styles
import requests
from devtools import debug
from pawnlib.utils import jequest

nested_data = {
    "a": {
        "b": "cccc",
        "sdsd": {
            "sdsds": {
                "sdsdssd": 2323
            }
        },
        "d": {
            "dd": [1211, 22323232, 2323223, 2323223, 2323223, 2323, 232,23,2,32,32,32,2,32,3],
            "aa": [
                {"sdsd": "sdsd222"},
                {"111": "sdsd222"},
                [1,3,3,3,3,3 , {"sdsdsd": "232323"}, {"sdsdsdsd": "232323"}]

            ],
            "cccc": "232323"
        }
    }
}

print_var(nested_data)


res = requests.get("https://httpbin.org/")
print(res.headers)
debug(res.headers)
print_var(dict(res.headers))


res = jequest("https://httpbin.org/get")
debug(res)

print_var(res)
pawn.console.log(res)
