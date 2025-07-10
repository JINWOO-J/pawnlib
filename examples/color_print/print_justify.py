#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.output import dump, syntax_highlight, print_var, pretty_json, print_json, print_aligned_text, align_text, get_bcolors
from pygments.styles import get_all_styles
from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text


transaction_id = "0xc322b66c2ceafcf0af7d7d8c3ddcce6917a1895d982685a83293f97d672ff1bc"

_left_text = f"Check a transaction by {transaction_id}"
_padding_text = f"{'.' * 5}"
_right_text = "[OK]"

left_text = Panel(f"{_left_text}{_padding_text}", expand=False)
right_text = Panel(_right_text, expand=False)
pawn.console.print(Columns([left_text, right_text]))

left_text = Text(f"{_left_text}{_padding_text}", justify="left")
right_text = Text(_right_text, justify="right")

pawn.console.print(Columns([left_text, right_text]))

print(f"{_left_text}{_padding_text} {_right_text: >10}")

left_text = f"Check a transaction by {transaction_id} {'.' * 5}"
right_text = "[OK]"


padding = pawn.console.width - len(left_text) - len(right_text)
full_text = f"{left_text}{' ' * padding}{right_text}"
pawn.console.print(full_text)

print_aligned_text(_left_text, _right_text, ".")

print("----include colored")
print_aligned_text(f"{get_bcolors('<color>', 'OKBLUE')}{_left_text}", _right_text, ".")

print("----include colored & emoji")
print_aligned_text(f"✔{get_bcolors('✔[color]   ', 'OKBLUE')} ✔ {_left_text}", _right_text, ".")

print("----include rich colored & emoji")
print_aligned_text(f"[red]OK[/red] {_left_text}", _right_text, ".")
