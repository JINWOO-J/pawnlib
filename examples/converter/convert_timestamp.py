#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict, MedianFinder, StackList
from pawnlib.typing.date_utils import timestamp_to_string

from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn
import statistics
import random
mf = MedianFinder()

number_list = []

for unixtime_stamp in [1646060400000000, 1646060400]:
    pawn.console.log(f"Local Time Zone: {timestamp_to_string(unixtime_stamp)}")
    pawn.console.log(f"UTC Time Zone: {timestamp_to_string(unixtime_stamp, tz='UTC')}")
