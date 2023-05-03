#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import *
from pawnlib.utils import http
from pawnlib.resource import net

import requests
response = requests.Response()

http.disable_ssl_warnings()

pawn.console.rule("Invalid request")
res = http.CallHttp(
    url="https://httpbin.org/status/400",
    method="get",
    timeout=8000,
    raise_on_failure=False,
    # success_criteria=None
    # success_criteria=[http.AllowsKey.status_code, "<", "399"]
    # success_criteria=[http.AllowsKey.status_code, ">=", "200"]
    # success_criteria="status_code>500"

).run()
pawn.console.log(f"Result = {res} , response={res.response}")

pawn.console.log(res.response.__dict__)
pawn.console.log(f"error={res.response.error}")

pawn.console.rule("Valid request")
res = http.CallHttp(
    url="https://httpbin.org/get",
    # url="https://naver.com",
    method="get",
    timeout=3000,
    raise_on_failure=False,
    success_criteria=[http.AllowsKey.status_code, "==", "200"]
).run()

pawn.console.log(f"res={res.response}")
pawn.console.log(f"error={res.response.error}")
# pawn.console.log(f"res={res.response}, success={res.response.success}")


