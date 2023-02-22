#!/usr/bin/env python3
import common
from pawnlib.output.color_print import *

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

styles = ['default', 'emacs', 'friendly', 'colorful', 'autumn', 'murphy', 'manni',
'material', 'monokai', 'perldoc', 'pastie', 'borland', 'trac', 'native',
'fruity', 'bw', 'vim', 'vs', 'tango', 'rrt', 'xcode', 'igor', 'paraiso-light',
'paraiso-dark', 'lovelace', 'algol', 'algol_nu', 'arduino', 'rainbow_dash',
'abap', 'solarized-dark', 'solarized-light', 'sas', 'stata', 'stata-light',
'stata-dark', 'inkpot', 'zenburn', 'material']

for style in styles:
    print(f"style name = {style}")
    print(syntax_highlight(nested_data, style=style))
    print(syntax_highlight("<html><head><meta name='viewport' content='width'>", "html", style=style))

