import copy
import re
import json
import sys
from pawnlib.config import pawn


def is_json(s) -> bool:
    """
    Check if a string is valid JSON.

    :param s: a string to check if it is valid JSON.
    :return: True if the string is valid JSON, False otherwise.

    Example:

        .. code-block:: python

            check.is_json('{"name": "John", "age": 30, "city": "New York"}')
            # >> True

            check.is_json('{"name": "John", "age": 30, "city": "New York",}')
            # >> False
    """
    try:
        json.loads(s)
    except ValueError:
        return False
    return True


def is_float(s) -> bool:
    """
    Check if a value is float

    :param s: A value to check if it is a float
    :type s: Any
    :return: True if the value is a float, False otherwise
    :rtype: bool

    Example:

        .. code-block:: python

            check.is_float(3.14)
            # >> True

            check.is_float("3.14")
            # >> True

            check.is_float("hello")
            # >> False

    """
    try:
        float(s)
    except (TypeError, ValueError):
        return False
    return True


def is_int(s) -> bool:
    """
    Check if a value is integer.

    :param s: A value to check.
    :type s: Any
    :return: True if the value is an integer, False otherwise.
    :rtype: bool

    Example:

        .. code-block:: python

            check.is_int(1)
            # >> True

            check.is_int(1.0)
            # >> False

            check.is_int("2")
            # >> True

            check.is_int("2.0")
            # >> False

    """
    try:
        int(s)
    except (TypeError, ValueError):
        return False
    return True


def is_hex(s) -> bool:
    """
    Check if a value is hexadecimal

    :param s: string to check
    :return: True if s is hexadecimal, False otherwise

    Example:

        .. code-block:: python

            check.is_hex("1a")
            # >> True

            check.is_hex("g")
            # >> False

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

    Example:

        .. code-block:: python

            check.is_regex_keyword("/hello/", "hello world")
            # >> True

            check.is_regex_keyword("(hello)+", "hello world")
            # >> True

            check.is_regex_keyword("hello", "world")
            # >> False
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

    :param ip: (str) IPv4 address to validate.
    :return: (bool) True if valid IPv4 address, False otherwise.

    Example:

        .. code-block:: python

            check.is_valid_ipv4("192.168.0.1")
            # >> True

            check.is_valid_ipv4("255.255.255.0")
            # >> True

            check.is_valid_ipv4("300.168.0.1")
            # >> False

    """
    pattern = re.compile(
        r"^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$",
        re.VERBOSE | re.IGNORECASE
    )
    return pattern.match(ip) is not None


def is_valid_ipv6(ip):
    """
    Validates IPv6 addresses.

    :param ip: A string representing an IPv6 address.
    :return: True if the given string is a valid IPv6 address, False otherwise.

    Example:

        .. code-block:: python

            check.is_valid_ipv6("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
            # >> True

            check.is_valid_ipv6("2001:0db8:85a3::8a2e:0370:7334")
            # >> True

            check.is_valid_ipv6("2001:0db8:85a3:0:0:8a2e:0370:7334:1234")
            # >> False

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
    """
    Check if the given url is valid.

    :param url: (str) url to check
    :return: (bool) True if valid, False otherwise

    Example:

        .. code-block:: python

            check.is_valid_url("google.com")
            # >> True

            check.is_valid_url("http://google.com")
            # >> True

            check.is_valid_url("https://www.google.com/search?q=python")
            # >> True

            check.is_valid_url("ftp://example.com")
            # >> False

    """
    if "http://" not in url and "https://" not in url:
        url = f"http://{url}"

    regex = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)',
        re.IGNORECASE)
    return url is not None and regex.search(url)


def is_valid_private_key(text=None):
    """
    Validates the Private Key

    :param text: A string of private key text.
    :type text: str
    :return: A boolean value indicating whether the private key is valid or not.
    :rtype: bool

    Example:

        .. code-block:: python

            is_valid_private_key("0x1234567890123456789012345678901234567890123456789012345678901234")
            # >> True

            is_valid_private_key("0x12345678901234567890123456789012345678901234567890123456789012345")
            # >> False

    """
    private_length = 64
    if text and is_hex(text):
        if text.startswith("0x"):
            text = text[2:]
        if len(text) == private_length:
            return True
    return False


def is_valid_token_address(text=None, prefix="hx"):
    """
    Validates the token address.

    :param text: A string representing the token address to be validated.
    :param prefix: A string representing the prefix of the token address. Default value is "hx".
    :return: A boolean value indicating whether the token address is valid or not.

    Example:

        .. code-block:: python

            is_valid_token_address("hx1234567890123456789012345678901234567890")
            # >> True

            is_valid_token_address("tx1234567890123456789012345678901234567890")
            # >> False

    """
    if text and prefix \
            and len(text) == 42 \
            and text.startswith(prefix) \
            and is_hex(text[2:]):
        return True
    return False


def is_valid_tx_hash(text=None):
    """
    Validates the txHash

    :param text: A string of txHash text.
    :type text: str
    :return: A boolean value indicating whether the txHash is valid or not.
    :rtype: bool

    Example:

        .. code-block:: python

            is_valid_tx_hash("0x1234567890123456789012345678901234567890123456789012345678901234")
            # >> True

            is_valid_tx_hash("0x12345678901234567890123456789012345678901234567890123456789012345")
            # >> False

    """
    tx_hash_length = 64
    if text and is_hex(text):
        if text.startswith("0x"):
            text = text[2:]
        if len(text) == tx_hash_length:
            return True
    return False


def list_depth(l):
    """
    Returns the depth count of a list.

    :param l: A list.
    :return: An integer representing the depth count of the list.

    Example:

        .. code-block:: python

            list_depth([1, 2, 3])
            # >> 1

            list_depth([1, [2, 3], [4, [5, 6]]])
            # >> 3

    """
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
    This function returns boolean type of given string.

    :param v: A string to be converted to boolean type.
    :type v: str
    :return: Boolean value of given string.
    :rtype: bool

    Example:

        .. code-block:: python

            >>> _str2bool('True')
            True
            >>> _str2bool('false')
            False
            >>> _str2bool('1')
            True
            >>> _str2bool(None)
            False
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
    """
    This function returns the result of :func:`guess_type` and :func:`_strbool`

    :param value: A value to guess the type of.
    :type value: any
    :return: The guessed type of the input value.
    :rtype: any

    Example:

        .. code-block:: python

            return_guess_type("True")
            # >> <class 'bool'>

            return_guess_type("2.2")
            # >> <class 'float'>

    """
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
    This function executes the sys.exit() method.

    :param message: A message to be printed before exiting. (default="")
    :type message: str
    :param return_code: An exit code to be returned. (default=-1)
    :type return_code: int
    :return: None

    Example:

        .. code-block:: python

            # Example 1: Exit with default return code and message
            sys_exit()

            # Example 2: Exit with custom return code and message
            sys_exit("An error occurred!", 1)

    """
    if message:
        pawn.console.log(f"[red]\[Exit {return_code}] {message}", _stack_offset=2)
    sys.exit(return_code)


def is_include_list(target=None, include_list=[], ignore_case=True):
    """
    Check if target string exists in list.

    :param target: Target string to check.
    :type target: str
    :param include_list: List of strings to check.
    :type include_list: list
    :param ignore_case: If True, ignore case sensitive. Default is True.
    :type ignore_case: bool

    :return: Return True if target string exists in include_list, else False.
    :rtype: bool

    Example:
        .. code-block:: python

            result = is_include_list("hello world", ["hello", "world"])
            # >> True

            result = is_include_list("hello world", ["hello", "world"], ignore_case=False)
            # >> False
    """
    if target and include_list:
        for include_key in include_list:
            if ignore_case and include_key.lower() in target.lower():
                return True
            if include_key in target:
                return True
    return False


def keys_exists(element, *keys):
    """
    Check if **keys** (nested) exists in `element` (dict).
    You don't have to implement it like this.

    [X] if response.get('json') and response['json'].get('result') and response['json']['result'].get('tx_hash'): \n
    [O] if keys_exists(response, 'json', 'result', 'tx_hash'): \n

    :param element: dictionary value
    :param keys: The keys you want to find in the dictionary.
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing.check import keys_exists

            dict_example = {
                "name": "example",
                "description": {
                    "description_2": "222",
                    "description_3": "333",
                },
                "none_value_key": None,

            }

            keys_exists(dict_example, 'name', 'description')
            # >> True

            keys_exists(dict_example, 'name', 'none_value_key')
            # >> True

            keys_exists(dict_example, 'name', 'none_key')
            # >> False

    """
    not_defined = "__NOT_DEFINED__"
    next_element = ""
    for index, key in enumerate(keys):
        if next_element:
            _element = next_element
        else:
            _element = copy.deepcopy(element)
        if isinstance(_element, dict):
            if _element.get(key, not_defined) != not_defined:
                next_element = _element.pop(key, not_defined)
            else:
                return False
        else:
            return False
    return True


def detect_encoding(byte_data, default_encode="utf8"):
    """
    Detects the encoding of byte data.

    :param byte_data: The byte data to be decoded.
    :type byte_data: bytes
    :param default_encode: The default encoding to be used if no suitable encoding is found. Defaults to "utf8".
    :type default_encode: str
    :return: The detected encoding.
    :rtype: str
    :raises UnicodeDecodeError: If the byte data cannot be decoded using any of the available encodings.

    Examples:

        Detect the encoding of byte data:

        .. code-block:: python

            byte_data = b"\x41\x42\x43"
            detect_encoding(byte_data)
            # Output: 'ascii'

            byte_data = b"\xea\xb0\x80\xeb\x82\x98\xeb\x8b\xa4"
            detect_encoding(byte_data)
            # Output: 'utf8'

            byte_data = b"\xb0\xa1\xb1\xe2\xc6\xae"
            detect_encoding(byte_data)
            # Output: 'euc-kr'
    """

    encodings = ["ascii", "utf8", "euc-kr", "iso2022_jp", "euc_jp", "shift_jis", "cp932", "latin1"]
    for encoding in encodings:
        try:
            byte_data.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            pass
    return default_encode

