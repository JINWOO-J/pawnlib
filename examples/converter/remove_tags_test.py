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
    "[BOLD] dssd [/BOLD]",
]

for case_sensitive in ['both', "lower", 'upper']:
    pawn.console.rule(f'Remove tags -> case_sensitive = {case_sensitive}')
    for tag in tags:
        print(f"input={tag:>50}, result= {remove_tags(tag, case_sensitive=case_sensitive)}")
