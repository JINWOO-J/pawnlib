#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output.color_print import *

from pawnlib.utils import http
dump(pawn.to_dict())

pawn.set(PAWN_DEBUG=True)




a = 111

res = http.jequest(url="sdsd")
print(ss)
