#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.resource import net

url_list = ["https://httpbin.org", "http://httpbin.org", "https://httpbin.org:2222", "httpbin.org:222", "sss.com"]
for url in url_list:
    try:
        pawn.console.log(net.check_port(host=url, timeout=1))
    except Exception as e:
        pawn.console.log(e)

pawn.console.log(net.check_port(host="INVALID___.com", timeout=1))
