#!/usr/bin/env python3
import common
from pawnlib.config.configure import *

conf = Configure()
conf.name = "sdsd"

import config_child_v1


def main():
    print(f"[HERE are Main], name={conf.name}")


if __name__ == "__main__":
    main()
