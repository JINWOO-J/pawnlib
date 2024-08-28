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

    @parameterized.expand([
        ("append api v3 path with normal url", append_api_v3, dict(url="asd.com"), "http://asd.com/api/v3"),
        ("append api v3 path with normal url", append_api_v3, dict(url="http://asd.com"), "http://asd.com/api/v3"),
        ("url already contains api v3", append_api_v3, dict(url="http://asd.com/api/v3"), "http://asd.com/api/v3"),
        ("url already contains api v3", append_api_v3, dict(url="asd.com/api/v3"), "http://asd.com/api/v3"),
        ("url already contains api v3d", append_api_v3, dict(url="asd.com/api/v3d"), "http://asd.com/api/v3d"),
    ])

    def test_02_append_api_v3(self, name, function=None, params={}, expected_value=None):
        result = function(**params)
        print(f"{function.__name__}({params}) <{type(params)}> result => {result}")
        self.assertEqual(result, expected_value)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethodRequest)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
