#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass
from devtools import debug
from pawnlib.output import *
# from pawnlib import output


filename = "sample.txt"

res = write_file(filename="sample.txt", data="*"*1000)
print(f"Write file {filename}, res={res}")
print(f"get_file_path:  {get_file_path(filename)}")
