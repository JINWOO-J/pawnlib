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
        "value":         399999999999999966445568,
    },
    {
        "address":         "2x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
        "value":         399999999999999966445568,
    },
    {
        "address":         "3x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
        "value":         399999999999999966445568,
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
