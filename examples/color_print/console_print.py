#!/usr/bin/env python3
import common
from pawnlib.output.color_print import *
from pawnlib.config import pawn

sample_dict = dict(
    aa="sdssdsdsd"
)

sample_list_dict = [
    {"string value": "ccc"},
    {"integer value": 1},
    {"boolean value": True},
    {"float value": 1.11},
]

attrs = [None, 'bold', 'dark', 'underline', 'blink', 'reverse', 'concealed']

data = [
    {
        "address":         "1x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
        "value":         399999999999999966445568,
    },
    {
        "address":         "2x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
        "value":         399999999999999966445568,
    },
    {
        "address":         "3x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
        "value":         399999999999999966445568,
        "only_here":         399999999999999966445568,
    },

]

nested_data = {
    "a": {
        "b": "cccc",
        "sdsd2": {
            "sdsds": {
                "sdsdssd": 2323
            }
        },
        "d": {
            "dd": 1211,
            "cccc": "232323"
        },
        "dd": True,
        "dd2": False,
        "sdsd": None,

    }
}
fmt = [
    ('address',       'address',          10),
    ('value',       'value',          15)
]

depth_1_dict = {
    "sdsd1": "123123",
    "sdsd2": "123123",
    "sdsd3": "123123",
    "sdss4": "123123",
}


dump(data)
dump(nested_data)
dump(attrs)

pawn.set(PAWN_DEBUG=True)
pawn.console.rule("Console logs")
pawn.console.debug("debug message")
pawn.console.debug("debug message", nested_data)
