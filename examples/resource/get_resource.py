#!/usr/bin/env python3
from datetime import time

import common
from pawnlib.resource import net

print(f"public ipaddr: {net.get_public_ip()}")
print(f"local ipaddr: {net.get_local_ip()}")
print(f"hostname: {net.get_hostname()}")


def calculate_time():
    return 1


if __name__ == '__main__':
    print("sdsd")
