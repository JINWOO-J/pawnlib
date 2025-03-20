#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass
from pawnlib.config import pawn
from pawnlib.typing import const

pawn.console.log(const.REGIONS.get('us-east-1'))
pawn.console.log(const.REGIONS.keys())

pawn.console.log(const.get_aws_region_list())
pawn.console.log(const.get_aws_region_name('us-east-1'))
pawn.console.log(const.get_aws_region_name('us-east-32'))

