#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass
from parameterized import parameterized
from devtools import debug
import datetime
from pawnlib.typing import *


class TestMethodRequest(unittest.TestCase):
    def test_convert_unix_timestamp(self, name=None, function=None, params={}, expected_value=None):
        target_date = datetime.datetime.strptime("2020-08-09", "%Y-%m-%d")
        expected_value = 1596898800
        res = convert_unix_timestamp(target_date)
        self.assertEqual(res, expected_value)

    def test_get_range_day_of_month(self, name=None, function=None, params={}, expected_value=None):
        res = get_range_day_of_month(year=2022, month=3, return_unix=False)
        expected_value = ('2022-3-01 00:00:00', '2022-03-31 23:59:59')
        self.assertEqual(res, expected_value)

    def test_get_range_day_of_month_unix(self, name=None, function=None, params={}, expected_value=None):
        res = get_range_day_of_month(year=2022, month=3, return_unix=True)
        expected_value = (1646060400, 1648738799)
        self.assertEqual(res, expected_value)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethodRequest)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
