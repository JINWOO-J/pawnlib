#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict, MedianFinder, StackList
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn
import statistics
import random
mf = MedianFinder()

number_list = []

pawn.console.log("StackList Number")
st = StackList(max_length=10)
for i in range(1, 100):
    st.push(i)

pawn.console.log(st)
pawn.console.log(st.mean())
pawn.console.log(st.median())


pawn.console.log("StackList dictionary")
for i in range(1, 100):
    st.push({"key": i})

pawn.console.log(st)
# pawn.console.log(st.mean())
# pawn.console.log(st.median())


