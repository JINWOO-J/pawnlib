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
from pawnlib.config.globalconfig import pawnlib_config
from pawnlib.utils.log import AppLogger
from pawnlib.output import *
from pawnlib.utils import operate_handler
from pawnlib.output import file

import random
from parameterized import parameterized

log_dir = f"{get_parent_path(__file__)}/tests/logs"
log_filename = f"{log_dir}/sample"
cprint(f"Path : {log_filename}", "white")


class TestMethodRequest(unittest.TestCase):

    AppLogger(app_name="test_logging", log_path=log_dir, stdout=True).set_global()
    dump(pawnlib_config)
    res = operate_handler.run_execute(cmd="ls -al")

    # print(res)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethodRequest)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
