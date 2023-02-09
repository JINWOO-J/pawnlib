import re
import json
import datetime


def is_json(s) -> bool:
    """
    Check if a string is valid JSON
    :param s:
    :return:

    """
    try:
        json.loads(s)
    except ValueError:
        return False
    return True


def is_float(s) -> bool:
    """
    Check if a value is float

    :param s:
    :return:
    """
    try:
        float(s)
    except TypeError:
        return False
    except ValueError:
        return False
    return True


def is_int(s) -> bool:
    """
    Check if a value is integer

    :param s:
    :return:
    """
    try:
        int(s)
    except TypeError:
        return False
    except ValueError:
        return False
    return True


def is_hex(s) -> bool:
    """
    Check if a value is hexadecimal

    :param s:
    :return:
    """
    try:
        int(s, 16)
    except TypeError:
        return False
    except ValueError:
        return False
    return True


def is_regex_keyword(keyword: str, value: str) -> bool:
    """
    The is_regex_keyword function takes two strings, a keyword and a value.
    If the keyword starts with / and ends with /, then it is treated as a regex pattern.
    The function checks if the regex pattern is contained within the value string.
    If so, True is returned; otherwise False.

    :param keyword:str: Check if the value:str parameter matches the keyword
    :param value:str: Check if the keyword is in the value
    :return: True if the keyword is a regex and matches
    """

    if len(keyword) <= 0 or len(value) <= 0:
        return False

    if keyword[0] == "/" and keyword[-1] == "/":
        keyword = keyword.replace("/", "")
        if keyword in value:
            return True
    elif keyword[0] == "(" and keyword[-1] == ")":
        if re.findall(keyword, value):
            return True
    else:
        if keyword == value:
            return True



def is_regex_keywords(keywords, value)-> bool:
    """
    Check the value of the keyword regular expression.


    :param keywords:
    :param value:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import check

            check.is_regex_keywords(keywords="/sdsd/", value="sdsd")
            # >> True

            check.is_regex_keywords(keywords="/ad/", value="sdsd")
            # >> False

    """
    if not isinstance(keywords, list):
        keywords = [keywords]

    if isinstance(keywords, list):
        for keyword in keywords:
            result = is_regex_keyword(keyword, value)
            if result:
                return True
    return False


def is_valid_ipv4(ip):
    """
    Validates IPv4 addresses.

    :param ip:
    :return:

    """
    pattern = re.compile(
        r"^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$",
        re.VERBOSE | re.IGNORECASE
    )
    return pattern.match(ip) is not None


def is_valid_ipv6(ip):
    """
    Validates IPv6 addresses.

    :param ip:
    :return:

    """
    pattern = re.compile(r"""
        ^
        \s*                         # Leading whitespace
        (?!.*::.*::)                # Only a single whildcard allowed
        (?:(?!:)|:(?=:))            # Colon iff it would be part of a wildcard
        (?:                         # Repeat 6 times:
            [0-9a-f]{0,4}           #   A group of at most four hexadecimal digits
            (?:(?<=::)|(?<!::):)    #   Colon unless preceeded by wildcard
        ){6}                        #
        (?:                         # Either
            [0-9a-f]{0,4}           #   Another group
            (?:(?<=::)|(?<!::):)    #   Colon unless preceeded by wildcard
            [0-9a-f]{0,4}           #   Last group
            (?: (?<=::)             #   Colon iff preceeded by exacly one colon
             |  (?<!:)              #
             |  (?<=:) (?<!::) :    #
             )                      # OR
         |                          #   A v4 address with NO leading zeros 
            (?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)
            (?: \.
                (?:25[0-4]|2[0-4]\d|1\d\d|[1-9]?\d)
            ){3}
        )
        \s*                         # Trailing whitespace
        $
    """, re.VERBOSE | re.IGNORECASE | re.DOTALL)
    return pattern.match(ip) is not None


def list_depth(l):
    if isinstance(l, list):
        return 1 + max(list_depth(item) for item in l)
    else:
        return 0


def guess_type(s):
    """
    Guess the type of a string.

    :param s:
    :return:

    Example:

    .. code-block:: python

        from pawnlib.typing import check

        check.guess_type("True")
        # >> <class 'bool'>

        check.guess_type("2.2")
        # >> <class 'float'>

    """
    if isinstance(s, str):
        if s == "":
            return None
        elif re.match("^(\d+)\.(\d+)$", s):
            return float
        elif re.match("^(\d)+$", s):
            return int
        ## 2019-01-01 or 01/01/2019 or 01/01/19
        # elif re.match("^(\d){4}-(\d){2}-(\d){2}$", s) or \
        #         re.match("^(\d){2}/(\d){2}/((\d){2}|(\d){4})$", s):
        #     return datetime.date
        elif re.match("^(true|false)$", s, re.IGNORECASE):
            return bool
        else:
            return str
    else:
        return type(s)


def return_guess_type(value):
    guessed_type = guess_type(value)
    if guessed_type:
        return guessed_type(value)
    else:
        return value
