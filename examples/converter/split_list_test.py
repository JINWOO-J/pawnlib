#!/usr/bin/env python3
import common
from pawnlib.typing.converter import split_every_n
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn
import statistics
import random

st = []
for i in range(1, 100):
    st.append(i)

res = split_every_n(st, 3)
print(res)

