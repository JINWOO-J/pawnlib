#!/usr/bin/env python3
import common
from pawnlib.resource import server
from pawnlib.output.color_print import rprint
from pawnlib.config import pawn

print(server.get_default_route_and_interface())
print(server.get_interface_ips())
rprint(server.get_mem_info("MB"))
rprint(server.get_netstat_count())
