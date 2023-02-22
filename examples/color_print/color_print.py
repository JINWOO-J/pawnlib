#!/usr/bin/env python3
import common
from pawnlib.output.color_print import *
import time


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
highlights = [None, 'on_grey', 'on_red', 'on_green', 'on_yellow', 'on_blue', 'on_magenta', 'on_cyan', 'on_white']
colors = [None, 'grey', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']

for attr in attrs:
    for highlight in highlights:
        for color in colors:
            print(f"color={color}, on_color={highlight} attrs={attr} ", end="")
            cprint(f"Message", color=color, on_color=highlight, attrs=[attr])

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
        "sdsd": {
            "sdsds": {
                "sdsdssd": 2323
            }
        },
        "d": {
            "dd": 1211,
            "cccc": "232323"
        }
    }
}
fmt = [
    ('address',       'address',          10),
    ('value',       'value',          15)
]
cprint("\n\nPrint Table", "white")
print(TablePrinter(fmt=fmt)(data))
print(TablePrinter()(data))

debug_print("color message", "red")
cprint("message on the blue", on_color="on_blue")

cprint("\n\n dump()", "white")
dump(nested_data)


cprint("\n\n classdump()", "white")
classdump(bcolors)

for i in range(1, 100):
    time.sleep(0.05)
    print_progress_bar(i, total=100, prefix="start", suffix="suffix")


for style in range(8):
    for fg in range(30,38):
        s1 = ''
        for bg in range(40,48):
            format = ';'.join([str(style), str(fg), str(bg)])
            s1 += '\x1b[%sm %s \x1b[0m' % (format, format)
        print(s1)
    print('\n')
