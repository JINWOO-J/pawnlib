#!/usr/bin/env python3
import common
from pawnlib.config import pawn
import socket
import ssl
import datetime

from pawnlib.utils.http import CheckSSL
from pawnlib.utils.network import disable_requests_ssl_warnings

disable_requests_ssl_warnings()


domains_url = [
    # "devnote.in",
    # "naver.com",
    "parametacorp.com",
    # "coupang.com",
    # "devnote_wrong.in",
    # "stackoverflow.com",
    # "stackoverflow.com/status/404"
]


if __name__ == "__main__":
    for value in domains_url:
        now = datetime.datetime.now()
        try:
            checker = CheckSSL(host=value)
            pawn.console.log(checker.ssl_info)
            checker.analyze_ssl()

            # # expire = ssl_expiry_datetime(value)
            # expire = checker.ssl_expiry_datetime()
            # diff = expire - now
            #
            # pawn.console.log(checker.ssl_info)

            # print ("Domain name: {} Expiry Date: {} Expiry Day: {}".format(value, expire.strftime("%Y-%m-%d"), diff.days))
        except Exception as e:
            print(e)

