#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.typing.check import is_valid_url
from pawnlib.utils.http import append_http, append_ws

url_list = [
    ("http://20.20.1.122", True, True),
    ("http://20.20.1.122:9000", True, True),
    ("http://test.com", True, True),
    ("http://test", False, True),
    ("http://test", True, False),
    ("http://test:9000", True, False),
    ("http://google.com", True, True),
    ("https://naver.com", True, True),
    ("google.com", True, True),
    ("google.comhttp://", False, True),
]

for url, expected_value, strict  in url_list:
    pawn.console.log(f"url={url}, expected={expected_value}, strict={strict}, result={is_valid_url(url, strict=strict)}")

required_protocol_url_list = [
    "caa.com",
    "http://caa.com",
    "https://caa.com",
]

for url in required_protocol_url_list:
    pawn.console.log(f"url => append_http: {append_http(url)}, append_ws: {append_ws(url)}")

print(is_valid_url("http://test", strict=False))
