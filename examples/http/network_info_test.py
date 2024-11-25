#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import *
from pawnlib.utils import NetworkInfo

network_info = NetworkInfo(force=True)

pawn.console.rule("Force=True")
pawn.console.log(NetworkInfo(force=True))

for platform in network_info.get_platform_list():
    for network_name in network_info.get_network_list():
        pawn.console.rule(f"platform={platform}, network_name={network_name}")
        try:
            _network_info = NetworkInfo(network_name=network_name, platform=platform)
            pawn.console.log(_network_info)
        except Exception as e:
            pawn.console.log(f"[ERROR] {e}")

pawn.console.rule("Select  the new network information")
network_info.set_network(network_name="cdnet", platform="icon")
pawn.console.log(network_info)


pawn.console.rule("Add  the new network information")
network_info.add_network(network_name="AWE", platform="icon", network_api="http://sdsdsd.com", nid="0x15")

pawn.console.log(network_info.get_platform_info())
network_info.set_network(network_name="AWE")
pawn.console.log(network_info)
