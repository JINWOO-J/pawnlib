#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import *
from pawnlib.utils import http as http_utils
from pawnlib.resource import net
from pawnlib.cli import http
import argparse
from unittest import mock

# parser  = http.get_parser()
# parser.parse_args(['--slack-url', 'sdsds'])
# args, unknown = parser.parse_known_args()
# print(args)

# response = requests.Response()
http_utils.disable_ssl_warnings()
#

res = http_utils.CallHttp(
    # url="https://httpbin.org/get",
    url="https://httpbin.org/response-headers?test_header=jinwoo",
    # url="https://naver.com",
    method="get",
    timeout=3000,
    raise_on_failure=False,
    # success_criteria=["status_code", ">=", "200"]
    success_criteria=[http_utils.AllowsKey.status_code, "==", "200"]
).run()

# pawn.console.log(f"res={res.response}, success={res.response.success}")
pawn.console.log(res.response.__dict__)
pawn.console.log(f"res={res.response.elapsed}")

