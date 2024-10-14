#!/usr/bin/env python3
import unittest

try:
    import common
except:
    pass

from parameterized import parameterized
from pawnlib.typing.constants import const
import  re


def valid_pattern(pattern, value):
    result = re.match(pattern, value)
    return True if result else False


class TestPattern(unittest.TestCase):
    @parameterized.expand([
        ("Valid IP (Simple)", valid_pattern, [const.PATTERN_IP_ADDRESS, "192.168.0.1"], True),
        ("Valid IP (Upper Range)", valid_pattern, [const.PATTERN_IP_ADDRESS, "255.255.255.255"], True),
        ("Valid IP (Lower Range)", valid_pattern, [const.PATTERN_IP_ADDRESS, "0.0.0.0"], True),
        ("Valid IP (Mixed Digits)", valid_pattern, [const.PATTERN_IP_ADDRESS, "172.16.254.1"], True),

        ("Invalid IP (Out of Range)", valid_pattern, [const.PATTERN_IP_ADDRESS, "256.100.100.100"], False),
        ("Invalid IP (Negative Number)", valid_pattern, [const.PATTERN_IP_ADDRESS, "-1.100.100.100"], False),
        ("Invalid IP (Too Few Digits)", valid_pattern, [const.PATTERN_IP_ADDRESS, "192.168.0"], False),
        ("Invalid IP (Extra Dot)", valid_pattern, [const.PATTERN_IP_ADDRESS, "192.168.0.1."], False),
        ("Invalid IP (Non-Numeric)", valid_pattern, [const.PATTERN_IP_ADDRESS, "192.abc.0.1"], False),
        ("Invalid IP (Leading Zero)", valid_pattern, [const.PATTERN_IP_ADDRESS, "01.02.03.04"], False),
        ("Invalid IP (More than 4 octets)", valid_pattern, [const.PATTERN_IP_ADDRESS, "192.168.0.1.1"], False),
        ("Invalid IP (Empty String)", valid_pattern, [const.PATTERN_IP_ADDRESS, ""], False),
        ("Invalid IP (Whitespace)", valid_pattern, [const.PATTERN_IP_ADDRESS, "   "], False),

        ("Invalid IP (Partial Octet Missing)", valid_pattern, [const.PATTERN_IP_ADDRESS, "192..168.1"], False),
        ("Invalid IP (Leading/Trailing Whitespace)", valid_pattern, [const.PATTERN_IP_ADDRESS, " 192.168.0.1 "], False),
        ("Invalid IP (Large Numbers)", valid_pattern, [const.PATTERN_IP_ADDRESS, "999.999.999.999"], False),
        ("Invalid IP (Space Between Octets)", valid_pattern, [const.PATTERN_IP_ADDRESS, "192.168 .0.1"], False),
        ("Invalid IP (Letters Before)", valid_pattern, [const.PATTERN_IP_ADDRESS, "abc192.168.0.1"], False),
        ("Invalid IP (Letters After)", valid_pattern, [const.PATTERN_IP_ADDRESS, "192.168.0.1xyz"], False),
        ("Invalid IP (Trailing Dot Only)", valid_pattern, [const.PATTERN_IP_ADDRESS, "192.168.0."], False),
        ("Invalid IP (Special Characters)", valid_pattern, [const.PATTERN_IP_ADDRESS, "@192.168.0.1!"], False),

        ("Valid Email", valid_pattern, [const.PATTERN_EMAIL, "example@test.com"], True),
        ("Invalid Email", valid_pattern, [const.PATTERN_EMAIL, "example.com"], False),

        ("Valid URL", valid_pattern, [const.PATTERN_URL, "https://www.example.com"], True),
        ("Invalid URL", valid_pattern, [const.PATTERN_URL, "htp://invalid-url"], False),

        ("Valid Phone", valid_pattern, [const.PATTERN_PHONE, "+12345678901"], True),
        ("Invalid Phone", valid_pattern, [const.PATTERN_PHONE, "12345"], False),

        ("Valid Postal Code", valid_pattern, [const.PATTERN_POSTAL_CODE, "12345"], True),
        ("Invalid Postal Code", valid_pattern, [const.PATTERN_POSTAL_CODE, "123456"], False),

        ("Valid Credit Card", valid_pattern, [const.PATTERN_CREDIT_CARD, "4111111111111111"], True),
        ("Invalid Credit Card", valid_pattern, [const.PATTERN_CREDIT_CARD, "1234567890123456"], False),

        ("Valid IPv6 Address", valid_pattern, [const.PATTERN_IPV6_ADDRESS, "2001:0db8:85a3:0000:0000:8a2e:0370:7334"], True),
        ("Invalid IPv6 Address", valid_pattern, [const.PATTERN_IPV6_ADDRESS, "1234"], False),

        ("Valid HTML Tag", valid_pattern, [const.PATTERN_HTML_TAG, "<a href='test'>Link</a>"], True),
        ("Invalid HTML Tag", valid_pattern, [const.PATTERN_HTML_TAG, "No HTML"], False),

        ("Valid Slug", valid_pattern, [const.PATTERN_SLUG, "valid-slug"], True),
        ("Invalid Slug", valid_pattern, [const.PATTERN_SLUG, "Invalid Slug"], False),

        ("Valid Integer", valid_pattern, [const.PATTERN_INTEGER, "-123"], True),
        ("Invalid Integer", valid_pattern, [const.PATTERN_INTEGER, "12.34"], False),

        ("Valid Float", valid_pattern, [const.PATTERN_FLOAT, "-123.45"], True),
        ("Invalid Float", valid_pattern, [const.PATTERN_FLOAT, "abc123"], False),

        ("Valid Date", valid_pattern, [const.PATTERN_DATE_YYYY_MM_DD, "2023-09-10"], True),
        ("Invalid Date", valid_pattern, [const.PATTERN_DATE_YYYY_MM_DD, "23-09-10"], False),

        ("Valid Time", valid_pattern, [const.PATTERN_TIME_HH_MM_SS, "14:32:00"], True),
        ("Invalid Time", valid_pattern, [const.PATTERN_TIME_HH_MM_SS, "14:32"], False),
    ])
    def test_ipaddress(self, name, function=None, param=None, expected_value=None):
        result = function(*param)
        # print(f"{name}, {function.__name__}({param}) result => {result}")
        status = "PASS" if result == expected_value else "FAIL"
        print(f"Test: {name} | Input: {param[1]} | Expected: {expected_value} | Actual: {result} | Status: {status}")
        self.assertEqual(result, expected_value)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPattern)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
