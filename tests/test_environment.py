#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass
import os
from pawnlib.output import get_parent_path, cprint
from pawnlib.input.prompt import *
from parameterized import parameterized


class TestMethodRequest(unittest.TestCase):

    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ = {
            "OK_STRING": "SSSS",
            "OK_INT": "12",
            "INVALID_INT": 12,
            "OK_LIST_1": '["item1", "item2"]',
            "OK_LIST_2": "item1, item2",
            "OK_LIST_3": "[\"item1\", \"item2\"]",
        }

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    @parameterized.expand([
            ('EnvTest ', get_environment, dict(key="OK_STRING", default="SSSS", func=None), "SSSS"),
            ('EnvTest', get_environment, dict(key="UNKNOWN_ENV", default="DEFAULT", func=None), "DEFAULT"),
            ('EnvTest', get_environment, dict(key="OK_INT", default=0, func=int), 12),
            ('EnvTest', get_environment, dict(key="OK_LIST_1", default=[], func=None), ["item1", "item2"]),
            ('EnvTest', get_environment, dict(key="OK_LIST_2", default=[], func=None), ["item1", "item2"]),
            ('EnvTest', get_environment, dict(key="OK_LIST_3", default=[], func=None), ["item1", "item2"]),
        ]
    )
    def test_01_environment(self, name, function=None, params=None, expected_value=None):
        result = function(**params)
        cprint(f"{function.__name__}(), result={result}, expected={expected_value}")
        self.assertEqual(result, expected_value)

    @parameterized.expand([
            ('Testing environment ', get_environment, dict(key="INVALID_INT", default=0, func=int), "Environment variables must be strings. - 12"),
        ]
    )
    def test_02_environment_raise(self, name, function=None, params=None, expected_value=None):

        with self.assertRaises(ValueError) as cm:
            function(**params)

        raised_exception = cm.exception
        raised_exception_string = str(raised_exception)
        cprint(f"{function.__name__}(), raised_exception_string='{raised_exception_string}', expected='{expected_value}'")
        #
        self.assertEqual(raised_exception_string, expected_value)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethodRequest)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
