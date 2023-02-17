#!/usr/bin/env python3
import common
from pawnlib.utils import log
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import *
from pawnlib.utils import log
import sys

from pawnlib.output.color_print import TablePrinter, PrintRichTable

data = [
    {
        "address":         "1x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
        "value":         "[red]399999999999999966445568[/red]",
        "value2":         399999999999999966445561,
    },
    {
        "address":         "2x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
        "value":         399999999999999966445568,
    },
    {
        "address":         "3x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
        "value":         399999999999999966445568,
        "value2":         399999999999999966445568,
    }
]
fmt = [
    ('address',       'address',          10),
    ('value',       'value',          15)
]
cprint("Print Table (formatting)", "white")
print(TablePrinter(fmt=fmt)(data))

cprint("\nPrint Table", "white")

print(TablePrinter()(data))

PrintRichTable(title="RichTable", data=data, columns=["address"], with_idx=False)

PrintRichTable(title="RichTable", data=data[0], with_idx=False)


from rich import print
from rich.table import Table

grid = Table.grid(expand=True)
grid.add_column()
grid.add_column(justify="right")
grid.add_row("Raising shields", "[bold magenta]COMPLETED [green]:heavy_check_mark:")

print(grid)
