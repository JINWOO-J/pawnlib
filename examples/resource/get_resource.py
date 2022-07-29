#!/usr/bin/env python3
import common
from pawnlib.resource import net

print(net.get_public_ip())
print(net.get_local_ip())
print(net.get_hostname())
