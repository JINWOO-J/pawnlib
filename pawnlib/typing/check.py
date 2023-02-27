import re
import json
import sys
from pawnlib.config import pawn


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


def is_valid_url(url):
    if "http://" not in url and "https://" not in url:
        url = f"http://{url}"

    regex = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url is not None and regex.search(url)


def is_valid_private_key(text=None):
    private_length = 64
    if text and is_hex(text):
        if text.startswith("0x"):
            text = text[2:]
        if len(text) == private_length:
            return True
    return False


def is_valid_token_address(text=None, prefix="hx"):
    if text and prefix \
            and len(text) == 42 \
            and text.startswith(prefix)\
            and is_hex(text[2:]):
        return True
    return False


def list_depth(l):
    if isinstance(l, list):
        return 1 + max(list_depth(item) for item in l)
    else:
        return 0


def guess_type(s):
    """
    Guess the type of string.

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
    s = str(s)
    if s == "":
        return None
    elif re.match(r"^(\d+)\.(\d+)$", s):
        return float
    elif re.match(r"^(\d)+$", s):
        return int
    elif re.match(r"^(true|false)$", s, re.IGNORECASE):
        return bool
    else:
        return str

    # else:
    #     return type(s)


def _str2bool(v) -> bool:
    """
    this function get the boolean type

    :param v:
    :return:
    """
    if v is None:
        return False
    elif type(v) == bool:
        return v
    if isinstance(v, str):
        if v.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        elif v.lower() in ('no', 'false', 'f', 'n', '0'):
            return False
    elif v == 1:
        return True

    return False


def return_guess_type(value):
    guessed_type = guess_type(value)

    if guessed_type is None or guessed_type == "":
        return value

    if isinstance(guessed_type(), bool):
        return _str2bool(value)
    elif value is not None and value != "":
        return guessed_type(value)
    else:
        return value


def sys_exit(message="", return_code=-1):
    """
    This function executes the sys.exit() method

    :param message: print message
    :param return_code: exit code
    :return:

    """
    if message:
        pawn.console.log(f"[red]\[Exit {return_code}] {message}")
    sys.exit(return_code)


def is_include_list(target=None, include_list=[], ignore_case=True):
    """
    check if target string exists in list
    :param target: target string
    :param include_list: List of strings to check
    :param ignore_case: ignore case sensitive
    :return:
    """
    if target and include_list:
        for include_key in include_list:
            if ignore_case and include_key.lower() in target.lower():
                return True
            if include_key in target:
                return True
    return False
