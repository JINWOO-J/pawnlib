#!/usr/bin/env python3
import unittest

try:
    import common
except:
    pass

from pawnlib.typing.constants import const


class TestConstants(unittest.TestCase):
    def test_date_namespace(self, name=None, function=None, param=None, expected_value=None):
        self.assertEqual(const.MINUTE_IN_SECONDS, 60)
        self.assertEqual(const.HOUR_IN_SECONDS, 3600)
        self.assertEqual(const.DAY_IN_SECONDS, 86400)
        self.assertEqual(const.WEEK_IN_SECONDS, 604800)
        self.assertEqual(const.MONTH_IN_SECONDS, 2592000)
        self.assertEqual(const.YEAR_IN_SECONDS, 31536000)
        self.assertEqual(const.TRUE, 1)
        self.assertEqual(const.FALSE, 0)

    def test_rewrite(self, name=None, function=None, param=None, expected_value=None):
        with self.assertRaises(Exception):
            const.MINUTE_IN_SECONDS = 3


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestConstants)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
