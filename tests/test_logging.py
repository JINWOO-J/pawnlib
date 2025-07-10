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
import random
from parameterized import parameterized

from pawnlib.output import *
from pawnlib.utils.log import *


from pawnlib.config.globalconfig import pawnlib_config

log_dir = f"{get_parent_path(__file__)}/tests/logs"
log_filename = f"{log_dir}/sample"
cprint(f"Path : {log_filename}", "white")


class TestMethodLogging(unittest.TestCase):

    if os.path.isdir(log_dir) is False:
        os.mkdir(log_dir)
        print("Create a temp directory")

    app_logger, error_logger = AppLogger(app_name="test_logging", log_path=log_dir).get_logger()

    AppLogger(app_name="test_logging", log_path=log_dir)
    print(f"app_logger = {app_logger}")
    print(f"error_logger = {error_logger}")



if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethodLogging)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
