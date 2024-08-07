#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass

from parameterized import parameterized
from devtools import debug
from pawnlib.typing import converter
import os
from pawnlib.output import *
import random
from parameterized import parameterized

from pawnlib.output import *
from pawnlib.utils.http import *
from pawnlib.typing.generator import *


class TestMethodRequest(unittest.TestCase):

    def test_01_jequest(self, name=None, function=None, params={}):
        res = jequest(
            url="http://httpbin.or"
        )
        dump(res)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethodRequest)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
