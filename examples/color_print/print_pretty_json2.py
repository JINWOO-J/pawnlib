#!/usr/bin/env python3
import common
import json
from pawnlib.config import pawnlib_config as pawn, console as p_console, PawnlibConfig

from pawnlib.output.color_print import dump, syntax_highlight, print_var, pretty_json, print_json, json_compact_dumps
from rich.syntax import Syntax
from rich.panel import Panel
import shutil
from pygments.styles import get_all_styles
from rich.console import Console
import textwrap


def wrap_text(text, width):
    """Wrap text to the specified width."""
    wrapped_lines = []
    for line in text.splitlines():
        wrapped_lines.extend(textwrap.wrap(line, width=width, replace_whitespace=False))
    return "\n".join(wrapped_lines)


json_dict = {
    "jsonrpc": "2.0",
    "method": "icx_sendTransaction",
    "params": {
        "to": "cx0000000000000000000000000000000000000001",
        "dataType": "call",
        "data": {
            "method": "registerProposal",
            "params": {
                "title": "Revision 17",
                "description": "<h1>Revision 17 Proposal</h1><p>The ICON Foundation submits a Network Proposal " * 10,
                "type": "0x1",
                "value": "0x7b22636f6465223a202230783131222c20226e616d65223a20225265766973696f6e3137227d"
            }
        },
        "value": "0x0",
        "from": "hxcc30b1b952503026955a7be935de95c2fdec6670",
        "nonce": "0x1",
        "version": "0x3",
        "timestamp": "0x609139270457f",
        "nid": "0x53",
        "stepLimit": "0xd3ed78e",
        "signature": "SGfE+R5RpmLGtjBcw8syibDWGzmkp02niCgjgwhSHi8ayc3KT7xHhIIzQIOghh4LFvQKCMo/69tuB4yy/I5iQAE="
    },
    "id": 0
}

terminal_width = shutil.get_terminal_size().columns
pawn.console.log(f"terminal_width={terminal_width}, pawn.console.width={pawn.console.width}")
pawn.console.rule("Raw-level printing")
json_text = json.dumps(json_dict, indent="  ")
json_compact_text = json_compact_dumps(json_dict, indent="  ")
syntax = Syntax(json_text, "json", theme="monokai", line_numbers=False, word_wrap=True)
panel = Panel(syntax, title="JSON Code", expand=True)
pawn.console.print(panel)

pawn.console.rule("print_json()")
print_json(json_dict)

pawn.console.rule("print_var()")
print_var(json_dict)

pawn.console.rule("print_var()")
ssss = "ssssssssss"
print_var(ssss)
print_var(ssss, title="print only value, align left", title_align="left", detail=False)

syntax_str = Syntax(json_text, "json", theme="monokai", line_numbers=True, word_wrap=True)
panel = Panel(syntax_str, title="JSON", expand=True, width=terminal_width)

pawn.console.print(panel)
pawn.console.print(syntax_highlight(json_dict, rich=True))


# for style in get_all_styles():
#     pawn.console.rule(f"theme = {style} rich")
#     text = pretty_json(json_dict, rich_syntax=True, style=style)
#     pawn.console.print(text)

# pawn.console.rule(f"theme =  print_json, normal ")
# # print_json(json_dict)
#
# print_var(json_dict)
# pawn.console.print(json_dict)
#
#
