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
    # url="https://httpbin.org/get",
    url="https://httpbin.org/response-headers?test_header=jinwoo",
    # url="https://naver.com",
    method="get",
    timeout=3000,
    raise_on_failure=False,
    # success_criteria=["status_code", ">=", "200"]
    success_criteria=[http.AllowsKey.status_code, "==", "200"]
).run()

# pawn.console.log(f"res={res.response}, success={res.response.success}")
pawn.console.log(f"res={res.response}")
pawn.console.log(f"res={res}")


