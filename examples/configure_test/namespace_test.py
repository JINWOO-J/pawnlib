#!/usr/bin/env python3
import common
from pawnlib.config import pawn, pconf, NestedNamespace
from pawnlib.typing import set_namespace_default_value


def main():
    pawn.set(
        data={"aaaa": "bbbb"},
        asdf=NestedNamespace(**{"ssss": 1222})
    )
    print(pawn.to_dict())
    pawn.console.log(pconf())
    undefined_key = set_namespace_default_value(
        namespace=pconf().data,
        key="cccc",
        default="ddddd"
    )
    pawn.console.log(f"undefined_key={undefined_key}")
    _pconf = pconf()
    pconf().data.ddd = "sdsds"
    pconf().data.ccc = "sdsds"
    pawn.console.log(pconf().data)

    _pconf.asdf.sdsd = "sdsd"

    pawn.console.log(_pconf)

    pawn.console.log(pconf())


if __name__ == "__main__":
    main()
