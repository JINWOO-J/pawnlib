#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass
from devtools import debug
from pawnlib.output import *
# from pawnlib import output

filename = "sample.json"

class ErrorClass:
    def __init__(self):
        pass

json_dict = {
    "sdsd": "sdsdsd",
    "error": ErrorClass,
    "sss": 1
}

res = write_json(filename=filename, data=json_dict, force_write=True)
print(f"Write file {filename}, res={res}")
print(f"get_file_path:  {get_file_path(filename)}")
