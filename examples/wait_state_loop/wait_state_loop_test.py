#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass
from devtools import debug
from pawnlib.output import *
from pawnlib.config.globalconfig import pawnlib_config
from pawnlib.utils.operate_handler import *
from pawnlib.typing.generator import Null

import random

from functools import partial


def check_func(param=None):
    time.sleep(0.2)
    random_int = random.randint(1, 1000)
    # print(f"param= {param}, random_int = {random_int}")
    return random_int


def loop_exit_func(result):
    if result % 10 == 1.5:
        return True
    return False


def main():
    debug_logging("start main()")

    dump(pawnlib_config.to_dict())

    WaitStateLoop(
        loop_function=partial(check_func, "param_one"),
        exit_function=loop_exit_func,
        timeout=10
    ).run()

    # spinner = Spinner("sdsds")
    # spinner.start()
    #
    # time.sleep(1)
    #
    # spinner.stop()

    # with Spinner(text="Wait message") as spinner:
    #     while True:
    #         res = check_func()
    #         spinner.title(f"new message {res}")
    # wait_state_loop(
    #     wait_state=check_func,
    #     func_args=[],
    #
    # )

if __name__ == "__main__":
    main()
