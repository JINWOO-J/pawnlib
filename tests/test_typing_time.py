#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass
from parameterized import parameterized
import datetime
from pawnlib.typing.date_utils import convert_unix_timestamp, get_range_day_of_month, timestamp_to_string, TimeCalculator, todaydate
from pawnlib.output import cprint
import time
import os
os.environ['TZ'] = 'Asia/Seoul'
time.tzset()



class TestMethodRequest(unittest.TestCase):
    def test_convert_unix_timestamp(self, name=None, function=None, params={}, expected_value=None):
        target_date = datetime.datetime.strptime("2020-08-09", "%Y-%m-%d")
        expected_value = 1596898800
        res = convert_unix_timestamp(target_date)
        self.assertEqual(res, expected_value)

    def test_get_range_day_of_month(self, name=None, function=None, params={}, expected_value=None):
        res = get_range_day_of_month(year=2022, month=3, return_unix=False)
        expected_value = ('2022-3-01 00:00:00', '2022-03-31 23:59:59')
        self.assertEqual(res, expected_value)

    def test_get_range_day_of_month_unix(self, name=None, function=None, params={}, expected_value=None):
        res = get_range_day_of_month(year=2022, month=3, return_unix=True)
        expected_value = (1646060400, 1648738799)
        self.assertEqual(res, expected_value)

    @parameterized.expand([
        (
                'second unix timestamp', timestamp_to_string,
                dict(unix_timestamp=1646060400),
                "2022-03-01 00:00:00"
        ),
        (
                'milli second unix timestamp', timestamp_to_string,
                dict(unix_timestamp=1646060400000000),
                "2022-03-01 00:00:00"
        ),
        (
                'modified milli second unix timestamp', timestamp_to_string,
                dict(unix_timestamp=1646060401234000, str_format="%Y-%m-%d %H:%M:%S.%f"),
                "2022-03-01 00:00:01.234000"
        ),

        (
                'invalid timestamp', timestamp_to_string,
                dict(unix_timestamp=16460604012340, str_format="%Y-%m-%d %H:%M:%S.%f"),
                ValueError("invalid timestamp")
        ),

    ]
    )
    def test_timestamp_to_string(self, name=None, function=None, params={}, expected_value=None):

        if isinstance(expected_value, ValueError):
            self.assertRaises(ValueError,function, **params )
        else:
            result = function(**params)
            self.assertEqual(result, expected_value)

            cprint(f"{function.__name__}({params}), result={result}")

        # ts_second = timestamp_to_string(1646060400)
        # ts_milli_second = timestamp_to_string(1646060400000000)
        # ts_second_modify_string = timestamp_to_string(1646060401234000, str_format="%Y-%m-%d %H:%M:%S.%f")

    def test_TimeCalculator(self, name=None, function=None, params={}, expected_value=None):
        time_calculator = TimeCalculator(1224411)
        print(f"time_calculator = {time_calculator}")
        self.assertEqual(str(time_calculator), "14 days, 04:06:51")
        self.assertEqual(time_calculator.to_strings(), "14 days, 04:06:51")
        self.assertEqual(time_calculator.to_days(), 14)
        self.assertEqual(time_calculator.to_hours(), 340)
        self.assertEqual(time_calculator.to_minutes(), 20406)

    def test_todaydate(self):
        fixed_now = datetime.datetime(2025, 3, 26, 13, 34, 12, 450000)                 
        test_cases = [
            ("file", fixed_now.strftime("%Y%m%d_%H%M")),
            ("md", fixed_now.strftime("%m%d")),
            ("time", fixed_now.strftime("%H:%M:%S.%f")[:-3]),
            ("time_sec", fixed_now.strftime("%H:%M:%S")),
            ("hour", fixed_now.strftime("%H%M")),
            ("ms", fixed_now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]),
            ("log", fixed_now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]),
            ("log_ms", fixed_now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]),
            ("ms_text", fixed_now.strftime("%Y%m%d-%H%M%S%f")[:-3]),
            ("unix", hex(int(fixed_now.timestamp()))),
            ("ms_unix", hex(int(fixed_now.timestamp() * 1_000_000))),
        ]

        for date_type, expected in test_cases:
            with self.subTest(date_type=date_type):
                result = todaydate(date_type, fixed_now)                
                cprint(f"todaydate({date_type}), result={result}")
                self.assertEqual(result, expected)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethodRequest)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
