#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict, MedianFinder, StackList, remove_tags
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn


tags = [
    "[b]dssd[/b]",
    "[bold] dssd [/bold]",
    "[bold red] dssd [/bold red]",
    "[BOLD red] dssd [/BOLD red]",
]
for tag in tags:
    print(f"input={tag}, result={remove_tags(tag, case_sensitive='both')}")
