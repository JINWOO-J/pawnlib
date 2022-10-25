#!/usr/bin/env python3
import common
import sys
from pawnlib.config import pawnlib_config as pawn
from pawnlib.output import dump


def init():
    pawn.set(
        stack="stack_value",
        PAWN_LOGGER=dict(
            log_level="INFO",
            stdout_level="INFO",
            use_hook_exception=True,
        ),
        PAWN_DEBUG=True,# Don't use production, because it's not stored exception log.
        # dict_stack={
        #     "sdsd": 111,
        #     "sssss": 222,
        # },
        # data=111
        data={
            "lkas": "OLD_VALUE",
            "aaa": 1111,
        }
    )


def get_namespace():
    pawn.console.log(f"pawn.namespace = {pawn.data}")
    pawn.data.sss = 1111


def main():
    init()
    pawn.console.log(f"1. to_dict() : {pawn.to_dict()}")
    pawn.console.log(f"2. stack => {pawn.get('data')}")

    pawn.console.log(f"Try to changing NS, type=> {type(pawn.data)}")
    pawn.data.aaa = "NEW_VALUE"

    dump(pawn.to_dict())

    pawn.console.log(f">> pawn.data = {pawn.data}")
    pawn.console.log(f">> pawn.data.aaa = {pawn.data.aaa}")

    pawn.data.aaa = 111
    pawn.data.aaa += 10

    pawn.console.log(f"pawn.namespace = {pawn.data}")
    pawn.console.log(f"pawn.namespace = {pawn.data.__dict__}")

    pawn.console.log("Try to changing NS -> string")
    pawn.data = "STRING"


if __name__ == "__main__":
    main()
