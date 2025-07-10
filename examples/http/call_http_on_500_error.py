#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import *
from pawnlib.utils import http
from pawnlib.resource import net

import requests
response = requests.Response()
http.disable_ssl_warnings()

res = http.CallHttp(
    # url="https://httpbin.org/status/500",
    url="http://localhost:8000",
    method="get",
    timeout=3000,
    raise_on_failure=False,
    success_criteria=["status_code", ">=", "200"]
    # success_criteria=[http.AllowsKey.status_code, "==", "200"]
).run()

# pawn.console.log(f"res={res.response}, success={res.response.success}")
pawn.console.log(f"rrrrres={res.response}")
pawn.console.log(f"result={res.success}")

print("END")
