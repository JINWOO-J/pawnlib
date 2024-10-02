#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass
from devtools import debug
from pawnlib.config import pawn
from pawnlib.output.file import get_file_list
from pawnlib.input.prompt import select_file_prompt


print(get_file_list(pattern="*.py*", recursive=True))

selected_file = select_file_prompt(
    pattern="*.py*",
    recursive=True,
    # invalid_message="sdsd",
    # multiselect=True
)

pawn.console.log(f"selected_file => '{selected_file}'")
