#!/usr/bin/env python3
from datetime import time

import common
from pawnlib.resource import net

print(net.get_public_ip())
print(net.get_local_ip())
print(net.get_hostname())


def calculate_time():
    return 1


if __name__ == '__main__':
    print("sdsd")
