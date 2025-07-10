#!/usr/bin/env python3
import common
from pawnlib.output.color_print import *
from pygments.styles import get_all_styles

import json
from rich.syntax import Syntax
from rich.console import Console
console = Console()



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


# pawn.console.log(syntax_highlight(data=nested_data, rich=True))


styles = get_all_styles()
for style in styles:
    options = dict(style=style, rich=True, line_numbers=True)
    print()
    pawn.console.rule(f"options => {options}")
    # print(syntax_highlight(nested_data, style=style))
    # print(syntax_highlight("<html><head><meta name='viewport' content='width'>", "html", style=style))

    # syntax = Syntax(json.dumps(nested_data, indent=4), "json",  line_numbers=True, theme=style)

    print_syntax(data=nested_data, **options)

    # pawn.console.tprint(syntax)
    # pawn.console.print("sdsdsd", show_path=False)



