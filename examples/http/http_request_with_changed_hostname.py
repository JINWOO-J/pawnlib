#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import *
from pawnlib.utils import http
from pawnlib.resource import net
from pawnlib.config import pawn

http.disable_ssl_warnings()

res = http.jequest("http://undefined_domain.com", timeout=1)
pawn.console.log(f"[FAIL] Timeout Test - undefined domain  \n result={res}")


res2 = http.jequest("https://www.naver.com", ipaddr="20.20.1.23", timeout=1)
pawn.console.log(f"[FAIL] Timeout Test - undefined ipaddr  \n result={res2}")


res3 = http.jequest("https://www.naver.com", ipaddr="223.130.200.104", timeout=1)
pawn.console.log(f"[OK] Timeout Test - undefined ipaddr  \n result={res3.get('status_code')}")

res4 = http.jequest("http://www.naver.com")
pawn.console.log(f"[OK] Timeout Test \n result={res4.get('status_code')}")
