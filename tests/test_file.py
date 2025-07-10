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

temp_dir = f"{get_parent_path(__file__)}/tests/temp"
filename = f"{temp_dir}/sample"
cprint(f"Path : {filename}", "white")
random_data = "*" * random.randint(10, 1000)
random_dict = {
    "data": "*" * random.randint(10, 1000)
}

print(f"size: random_data={len(random_data)}, random_dict_data={len(str(random_data))}")
permit = '644'


class TestMethodRequest(unittest.TestCase):

    if os.path.isdir(temp_dir) is False:
        os.mkdir(temp_dir)
        print("Create a temp directory")

    # def test_01_write_file(self, name=None, function=None, params={}, expected_value=None):
    #     result = write_file(filename=self.filename, data=self.random_data)
    #     print(f"Write file {self.filename}, result='{result}'")
    #     file_size = os.stat(self.filename).st_size
    #     expected_value = len(self.random_data)
    #     self.assertEqual(file_size, expected_value)
    #
    # def test_02_write_json(self):
    #     result = write_json(filename=self.json_filename, data=self.random_dict, permit=self.permit)
    #     print(f"Write json file {self.json_filename}, result='{result}'")
    #     os_stat = os.stat(self.json_filename)
    #
    #     st_mode = oct(os_stat.st_mode)[-3:]
    #     self.assertEqual(st_mode, self.permit)
    #
    #     file_size = os_stat.st_size
    #     expected_value = len(str(self.random_dict))
    #     self.assertEqual(file_size, expected_value)

    @parameterized.expand([
        (
                'txt', write_file, dict(filename=filename, data=random_data, permit='664'),
        ),
        (
                "json", write_json, dict(filename=filename, data=random_dict, permit='664'),
        ),
        (
                "yaml", write_yaml, dict(filename=filename, data=random_dict, permit='664'),
        ),
    ]
    )
    def test_01_write(self, name, function=None, params={}):
        params['filename'] = f"{params['filename']}.{name}"
        result = function(**params)
        cprint(f"{function.__name__}(), result={result}")
        os_stat = os.stat(params.get('filename'))
        st_mode = oct(os_stat.st_mode)[-3:]
        file_size = os_stat.st_size
        self.assertEqual(st_mode, params.get('permit'))
        expected_value = len(str(params.get('data')))

        if name == "yaml":
            expected_value = expected_value - 3
        self.assertEqual(file_size, expected_value)

    @parameterized.expand([
        (
                'txt', open_file, dict(filename=filename), random_data
        ),
        (
                'json', open_json, dict(filename=filename), random_dict
        ),
        (
                'yaml', open_yaml_file, dict(filename=filename), random_dict
        ),

    ]
    )
    def test_02_open(self, name, function=None, params={}, expected_value=None):
        params['filename'] = f"{params['filename']}.{name}"
        result = function(**params)
        result_size = len(str(result))
        expected_size = len(str(expected_value))
        cprint(f"{function.__name__}(), result={result}, size={result_size}")
        self.assertEqual(result_size, expected_size)

    @parameterized.expand([
        ('Specified file', is_file, dict(filename=f"{filename}.txt"), True),
        ('No such file', is_file, dict(filename=filename), False),
        ('Wildcard file', is_file, dict(filename=f"{filename}*"), True),
        ]
    )
    def test_03_is_file(self, name, function, params={}, expected_value=None ):
        result = function(**params)
        cprint(f"{function.__name__}({params}), result={result}")
        self.assertEqual(result, expected_value)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethodRequest)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
