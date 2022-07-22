#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass

from parameterized import parameterized
from devtools import debug
from pawnlib.typing.generator import *


class TestGenerator(unittest.TestCase):
    def test_id_generator(self, name=None, function=None, param=None, expected_value=None):
        size = 8
        res = id_generator(size=size)
        self.assertEqual(len(res), size)

    def test_json_rpc_generator(self, name=None, function=None, param=None, expected_value=None):
        json_rpc = {}
        for i in range(1, 10):
            json_rpc = generate_json_rpc(
                method="icx_getLastBlock",
                params={"p_k": "p_v"},
            )
        expected_value = json.dumps({"jsonrpc": "2.0", "method": "icx_getLastBlock", "params": {"p_k": "p_v"}, "id": 9})
        self.assertEqual(json_rpc, expected_value)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGenerator)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
