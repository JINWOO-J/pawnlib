#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass

from parameterized import parameterized
from devtools import debug
from pawnlib.typing import *
from pawnlib.output.color_print import dump


class TestMethodRequest(unittest.TestCase):
    complex_dict = {
        "a": 3,
        "a__": {
            "aaaa": 5
        },
        "b": {
            "bb": {
                "bbb": 3
            }
        },
        "d": {
            "dd": {
                "ddd": False
            }
        }
    }
    print("==== Before")
    dump(complex_dict)
    print("==== After")
    flatten_dict_obj = flatten_dict(complex_dict, separator=".")
    dump(flatten_dict_obj)

    def test_dict_dot_query(self):
        res = self.flatten_dict_obj.get("a__.aaaa")
        self.assertEqual(res, 5)

    def test_dict_dot_query2(self):
        res = self.flatten_dict_obj.get("b.bb.bbb")
        self.assertEqual(res, 3)

    def test_dict_dot_query3(self):
        res = self.flatten_dict_obj.get("c")
        self.assertEqual(res, None)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethodRequest)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
