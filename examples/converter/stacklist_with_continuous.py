#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict, MedianFinder, StackList, ErrorCounter
from pawnlib.config import pawnlib_config as pawn
import random
import numpy as np

# pawn.console.log("StackList Number")
# ec = ErrorCounter(max_length=5)
# pawn.console.rule("StackList")
# for i in range(1, 30):
#     if i > 10:
#         value = random.choice([True, False])
#     else:
#         value = True
#     ec.push(value)
#     pawn.console.log(f"[{i}][{value}] is_ok={ec.is_ok()}, {ec.consecutive_count}")
#     # pawn.console.log(cc)


pawn.console.rule("StackList")

# np.set_printoptions(formatter={'float_kind': lambda x: "{0:0.2f}".format(x)})
# np.set_printoptions(precision=3)


def find_best_index():
    for index in np.arange(0, 5, 0.01):
        ec = ErrorCounter(max_consecutive_count=10, increase_index=index)
        for i in range(1, 10000):
            value = True
            ec.push_hit(value)
        if ec._hit > 10:
            pawn.console.log(f"increase_index={index:.2f}, msg={ec.last_message}")


def simulate_index(index=0.1):
    count = 0
    last_consecutive_count = 0
    ec = ErrorCounter(max_consecutive_count=10, increase_index=index)
    for i in range(1, 10000):
        # pawn.console.log(ec.push_check())
        # pawn.console.log(ec)
        if ec.push_hit():
            pawn.console.log(f"SENT [{i}] is_ok={ec.is_ok()}, {ec.consecutive_count} , {ec.consecutive_count-last_consecutive_count}")
            count += 1
            last_consecutive_count = ec.consecutive_count
    pawn.console.log(f"increase_index: {index:.2f} / {ec.last_message}, count={count}")


# find_best_index()
simulate_index(1.50)
