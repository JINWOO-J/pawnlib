#!/usr/bin/env python3
from datetime import time

import common
from pawnlib.resource import net
from pawnlib.config import pawn

public_ipaddr = net.get_public_ip()

print(f"public ipaddr: {public_ipaddr}")
print(f"local ipaddr: {net.get_local_ip()}")
print(f"hostname: {net.get_hostname()}")

pawn.console.log(net.get_location(public_ipaddr))

def calculate_time():
    return 1


if __name__ == '__main__':
    print("sdsd")
