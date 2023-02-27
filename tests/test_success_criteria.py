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

from pawnlib.output import dump, classdump
from pawnlib.config import pawn

import requests
from pawnlib.utils.http import CallHttp, SuccessResponse, SuccessCriteria

class TestMethodRequest(unittest.TestCase):
    _response = None
    def _prepare_response(self):
        self._response = requests.models.Response()
        self._response.status_code = 200
        self._response.elapsed = 123
        self._response.success = False
        self._response.headers = {
            'Date': 'Thu, 30 Mar 2023 05:11:59 GMT',
            'Content-Type': 'application/json',
            'Content-Length': '310',
            'Connection': 'keep-alive',
            'Server': 'gunicorn/19.9.0',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        }

        return self._response

    def do_success_criteria(self, success_criteria=[], success_operator=""):
        self._prepare_response()
        call_http = CallHttp(url="")
        call_http.response = self._response
        call_http.fetch_criteria(success_criteria=success_criteria, success_operator=success_operator)
        pawn.console.print(f"[{call_http.is_success()}] success_criteria={success_criteria}, success_operator={success_operator} -> ", end="")
        return call_http


    @parameterized.expand([
        ("check status_code", do_success_criteria, ["status_code", "==", "200"], "and", True),
        ("check status_code", do_success_criteria, ["status_code", "!=", "200"], "and", False),
        ("check status_code", do_success_criteria, ["status_code", ">=", "200"], "and", True),
        ("check status_code", do_success_criteria, ["status_code", ">=", "100"], "and", True),
        ("check status_code", do_success_criteria, ["status_code", "<=", "300"], "and", True),
        ("check status_code", do_success_criteria, ["status_code", "<", "201"], "and", True),
        ("check status_code", do_success_criteria, ["status_code", ">", "199"], "and", True),
        ("check status_code", do_success_criteria, ["status_code", "==", "200"], "and", True),
    ])
    def test_01_success_criteria_operator(self, name=None, function=None, success_criteria=[], success_operator="", expected_value=""):
        result = function(self, success_criteria, success_operator)
        self.assertEqual(result.is_success(), expected_value)


    @parameterized.expand([
        ("check string status_code", do_success_criteria, "status_code==200", "and", True),
        ("check string status_code", do_success_criteria, "status_code!=200", "and", False),
        ("check string status_code", do_success_criteria, "status_code>=200", "and", True),
        ("check string status_code", do_success_criteria, "status_code>=100", "and", True),
        ("check string status_code", do_success_criteria, "status_code<=300", "and", True),
        ("check string status_code", do_success_criteria, "status_code<201", "and", True),
        ("check string status_code", do_success_criteria, "status_code>199", "and", True),
        ("check string status_code", do_success_criteria, "status_code==200", "and", True),
    ])
    def test_02_success_criteria_string_operator(self, name=None, function=None, success_criteria=None, success_operator="", expected_value=""):
        result = function(self, success_criteria, success_operator)
        self.assertEqual(result.is_success(), expected_value)

    @parameterized.expand([
        ("check flatten header", do_success_criteria, ["headers.Server", "==", "gunicorn/19.9.0"], "and", True),
        ("check flatten header", do_success_criteria, ["headers.Server", "==", "gunicorn/20.9.1"], "and", False),
        ("check flatten header", do_success_criteria, ["headers.Content-Length", ">=", 300], "and", True),
        ("check flatten header", do_success_criteria,
         [
             ["headers.Content-Length", ">=", 300],
             ["headers.Content-Length", ">=", 500],

         ], "and", False
         ),
        ("check flatten header", do_success_criteria,
         [
             ["headers.Content-Length", ">=", 300],
             ["headers.Content-Length", ">=", 500],

         ], "or", True
         ),
    ])
    def test_03_success_criteria_flatten(self, name=None, function=None, success_criteria=[], success_operator="", expected_value=""):
        result = function(self, success_criteria, success_operator)
        self.assertEqual(result.is_success(), expected_value)




if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethodRequest)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
