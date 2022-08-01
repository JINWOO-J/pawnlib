#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import *
from pawnlib.utils import http
from pawnlib.resource import net

http.disable_ssl_warnings()

print("timeout test")
res = http.jequest("http://undefined_domain.com", timeout=1)
print(res)


print("timeout test")
res2 = http.jequest("https://www.naver.com", ipaddr="20.20.1.23")
dump(res2)

res2 = http.jequest("http://www.naver.com")
dump(res2.get("status_code"))
# dump(res)
