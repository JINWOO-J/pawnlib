#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass

from parameterized import parameterized
from devtools import debug
from pawnlib.typing import *


class TestMethodRequest(unittest.TestCase):
    @parameterized.expand([
        ("valid integer", is_int, 1, True),
        ("valid integer", is_int, 1000, True),
        ("valid integer", is_int, "1000", True),
        ("valid integer", is_int, "01000", True),
        ("invalid integer", is_int, "a", False),
        ("invalid integer", is_int, "111a", False),
    ]
    )
    def test_int(self, name, function=None, param=None, expected_value=None):
        result = function(param)
        print(f"{function.__name__}({param}) <{type(param)}> result => {result}")
        self.assertEqual(result, expected_value)

    @parameterized.expand([
        ("valid hex", is_hex, "0x1", True),
        ("invalid hex", is_hex, 111, False),
        ("invalid hex", is_hex, "1x222", False),
        ("invalid hex", is_hex, 4334, False),
    ]
    )
    def test_hex(self, name, function=None, param=None, expected_value=None):
        result = function(param)
        print(f"{function.__name__}({param}) <{type(param)}> result => {result}")
        self.assertEqual(result, expected_value)

    @parameterized.expand([
        ("is regex single keyword ok", is_regex_keywords, dict(keywords="/sdsd/", value="sdsd"), True),
        ("is regex multiple keyword ok", is_regex_keywords, dict(keywords=["/sdsd/", "/sd/"], value="sdsd"), True),
        ("is regex multiple keyword fail", is_regex_keywords, dict(keywords=["/sdsd/", "/sd/"], value="ssssss"), False),
        ("is regex date range keyword ok", is_regex_keywords, dict(keywords=[r"((\d+)(-|h|d)$)"], value="1h"), True),
        ("is regex date range keyword ok", is_regex_keywords, dict(keywords=[r"((\d+)(-|h|d)$)"], value="34d"), True),
        ("is regex date range keyword fail", is_regex_keywords, dict(keywords=[r"((\d+)(-|h|d)$)"], value="2323day"), False),
        ("is regex date terms keyword ok", is_regex_keywords, dict(keywords=[r"((\d+)(\-|h|d|m|s)$)"], value="2323m"), True),
    ]
    )
    def test_is_regex_keyword(self, name, function=None, params={}, expected_value=None):
        result = function(**params)
        print(f"{function.__name__}({params}) <{type(params)}> result => {result}")
        self.assertEqual(result, expected_value)

    @parameterized.expand([
        ("hex ok", hex_to_number, dict(hex_value="0x232323"), 2302755),
        ("hex is_comma ok", hex_to_number, dict(hex_value="0x232323", is_comma=True), "2,302,755"),
        ("not hex debug ok", hex_to_number, dict(hex_value="0x232323", is_comma=True, debug=True), "2,302,755 (org) 0x232323"),
        ("not hex ok", hex_to_number, dict(hex_value="IS_NOT_HEX"), "IS_NOT_HEX"),
        ("not hex debug ok", hex_to_number, dict(hex_value="IS_NOT_HEX", debug=True), "IS_NOT_HEX (not changed)"),
        ("large(tint) hex ok", hex_to_number, dict(hex_value="0x2961fff8ca1a62327300000"), 800459999.9991555),
        ("large(tint) hex ok", hex_to_number, dict(hex_value="0x2961fff8ca1a62327300000", is_comma=True), "800,459,999.9991555"),
        ("large(tint) hex ok", hex_to_number, dict(hex_value="0x2961fff8ca1a62327300000", debug=True), "800459999.9991555 (tint) 0x2961fff8ca1a62327300000"),
    ]
    )
    def test_hex_to_number(self, name, function=None, params={}, expected_value=None):
        result = function(**params)
        print(f"{function.__name__}({params}) <{type(params)}> result => {result}")
        debug(result)
        self.assertEqual(result, expected_value)

    @parameterized.expand([
        (
                "dict convert hex to int ok", convert_dict_hex_to_int, dict(data={"hex_ex": "0x13200023"}, is_comma=False),
                {"hex_ex": 320864291}
        ),
        (
                "dict convert hex to int ok", convert_dict_hex_to_int, dict(data={"hex_ex": ["0x132233d", "0x132233d"]}, is_comma=False),
                {"hex_ex": [20063037, 20063037]}
        ),
        (
                "dict convert hex to int ok", convert_dict_hex_to_int, dict(data={"hex_ex": ["0x132233d", {"aaa": "0x13223d"}]}, is_comma=False),
                {"hex_ex": [20063037, {"aaa": 1253949}]}
        ),
        (
                "dict convert hex to int ok", convert_dict_hex_to_int, dict(data={"hex_ex": {"aaaa": ["0x132233d", {"aaa": "0x13223d"}]}}, is_comma=False),
                {'hex_ex': {'aaaa': [20063037, {'aaa': 1253949}]}}
        )
    ]
    )
    def test_convert_hex_to_int(self, name, function=None, params={}, expected_value=None):
        result = function(**params)
        print(f"{function.__name__}({params}) <{type(params)}> result => {result}")
        self.assertEqual(result, expected_value)

    def test_convert_bytes(self,):
        self.assertEqual(convert_bytes(10_000), "9.8 KB")
        self.assertEqual(convert_bytes(100_000), "97.7 KB")
        self.assertEqual(convert_bytes(100_000_000), "95.4 MB")
        self.assertEqual(convert_bytes(10_000_000_000), "9.3 GB")
        self.assertEqual(convert_bytes(10_000_000_000_000), "9.1 TB")

    def test_str2bool_true_ok(self, name=None, function=None, param=None, expected_value=None):
        true_list = ("yes", "true", "t", "1", "True", "TRUE")
        for true_string in true_list:
            self.assertEqual(str2bool(true_string), True)

    def test_str2bool_false_ok(self, name=None, function=None, param=None, expected_value=None):
        false_list = ("false", "FFF", "false", False, 0)
        for false_string in false_list:
            self.assertEqual(str2bool(false_string), False)

    def test_flatten_list(self, name=None, function=None, param=None, expected_value=None):
        complex_list = ["1_depth`", ["2_depth-1", "2_depth-2", "2_depth-3", "2_depth-dup", ["3_depth", "2_depth-dup"]]]
        compare_target = ['1_depth`', '2_depth-1', '2_depth-2', '2_depth-3', '2_depth-dup', '3_depth', '2_depth-dup']
        res = flatten_list(complex_list)
        self.assertEqual(res, compare_target)

    ## TODO checking unique - cant set the ordering
    # def test_flatten_uniq_list(self, name=None, function=None, param=None, expected_value=None):
    #     complex_list = ["1_depth`", ["2_depth-1", "2_depth-2", "2_depth-3", "2_depth-dup", ["3_depth", "2_depth-dup"]]]
    #     compare_target = ['1_depth`', '2_depth-1', '2_depth-2', '2_depth-3', '2_depth-dup', '3_depth']
    #     res = flatten_list(complex_list, uniq=True)
    #     self.assertEqual(res, compare_target)

    def test_flatten_dict(self, name=None, function=None, param=None, expected_value=None):
        complex_dict = {
            "aa": {
                "bb": {
                    "cc": "here"
                }
            }
        }
        compare_target = {'aa｡bb｡cc': 'here'}
        res = flatten_dict(complex_dict)
        self.assertEqual(res, compare_target)

    def test_id_generator(self, name=None, function=None, param=None, expected_value=None):
        size = 8
        res = id_generator(size=size)
        self.assertEqual(len(res), size)

    def test_dict_to_line(self, name=None, function=None, param=None, expected_value=None):
        dict_item = {"a": "1234", "b": "1235"}
        res = dict_to_line(dict_item)
        expected_value = "a=1234,b=1235"
        self.assertEqual(res, expected_value)


# import sys
# debug(list_to_oneline_string(["111", "222", "333"]))
# sys.exit()

    # complex_list = ["1_depth`", ["2_depth-1", "2_depth-2", "2_depth-3", "2_depth-dup", ["3_depth", "2_depth-dup"]]]
    #
    # @parameterized.expand([
    #     (
    #             "complex not uniq ok", flatten_list,
    #             complex_list,
    #             ['1_depth`', '2_depth-1', '2_depth-2', '2_depth-3', '2_depth-dup', '3_depth', '2_depth-dup']
    #     ),
    #     (
    #             "complex uniq ok", flatten_list,
    #             complex_list,
    #             ['1_depth`', '2_depth-1', '2_depth-2', '2_depth-3', '2_depth-dup', '3_depth', '2_depth-dup']
    #     ),
    # ]
    # )
    # def test_flatten_list(self, name, function=None, param=None, expected_value=None):
    #     result = function(param)
    #     print(f"{function.__name__}({param}) <{type(param)}> result => {result}")
    #     self.assertEqual(result, expected_value)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethodRequest)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
