#!/usr/bin/env python3
import common
from pawnlib.typing.date_utils import todaydate, TimeCalculator
from pawnlib.config import pawn
import datetime

pawn.console.log(todaydate("ms_unix", timezone="Asia/Seoul"))
pawn.console.log(todaydate("ms_unix", timezone="Asia/Seoul", target_datetime=datetime.datetime(2025, 3, 26, 13, 34, 12, 450000)))

tc = TimeCalculator(1224411.5)
pawn.console.log(repr(tc))  # "14 days, 04:06:51"
pawn.console.log(tc.to_strings())  # "14 days, 04:06:51"
pawn.console.log(tc.to_strings(include_ms=True))  # "14 days, 04:06:51.500"
pawn.console.log(tc.to_strings(format_type="detailed"))  # "14 days 4 hours 6 minutes 51 seconds"
pawn.console.log(tc.to_minutes())  # 20406
pawn.console.log(tc.to_days())  # 14
tc.set_seconds(3600)
pawn.console.log(tc.to_strings())  # "01:00:00"
tc2 = TimeCalculator.from_hhmmss("01:00:00")
pawn.console.log(tc2.to_seconds())  # 3600
pawn.console.log(tc2._seconds)  # 3600
