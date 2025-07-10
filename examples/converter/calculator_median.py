#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict, MedianFinder, StackList
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn
import statistics
import random
mf = MedianFinder()

number_list = []

for i in range(1, 10):
    for ii in range(1, 100):
        rnd = random.randint(1, 1000000)
        mf.add_number(rnd)
        number_list.append(rnd)

    pawn.console.log(f"[{i}] median = {mf.median():<20}, statics={statistics.median(number_list)}")
    pawn.console.log(f"[{i}] mean   = {mf.mean():<20}, statics={statistics.mean(number_list)}")


st = StackList(max_length=10)
for i in range(1, 100):
    st.push(i)


pawn.console.log(st.mean())
pawn.console.log(st.median())
