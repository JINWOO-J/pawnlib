#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config, PawnlibConfig
# from pawnlib.utils.log import AppLogger
from pawnlib.output import *
# import config_settings
# import config_child
import sys


def main():
    config = PawnlibConfig(global_name="ssss")

    print(f"main= {pawnlib_config.to_dict()}")

    dump(pawnlib_config.to_dict(), debug=False)

    pawnlib_config.set(hello="world")
    print(f"main= {pawnlib_config.to_dict()}")

    pawnlib_config.make_config(hello="world")
    dump(pawnlib_config.to_dict())


if __name__ == "__main__":
    main()
