#!/usr/bin/env python3
import common
from pawnlib.config import pawn, pconf
from pawnlib.typing import set_namespace_default_value


def main():
    pawn.set(
        data={"aaaa": "bbbb"}
    )
    pawn.console.log(pconf())
    undefined_key = set_namespace_default_value(
        namespace=pconf().data,
        key="cccc",
        default="ddddd"
    )
    pawn.console.log(undefined_key)


if __name__ == "__main__":
    main()
