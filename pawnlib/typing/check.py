import copy
import os
import re
import json
import sys
import inspect
from rich.panel import Panel
from pawnlib.config import pawn

try:
    from typing import Any, Union
except ImportError:
    from typing_extensions import Any, Union
from pawnlib.typing.constants import const


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
    if not (isinstance(s, str) and (s.startswith('{') or s.startswith('['))):
        return False
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
    if isinstance(s, float):
        return True
    try:
        float_value = float(s)
        return '.' in str(s) or 'e' in str(s).lower()  # Check if it has a decimal point or scientific notation
    except (TypeError, ValueError):
        return False


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
    if isinstance(s, int):
        return True
    try:
        int_value = int(s)
        return str(int_value) == str(s)  # Ensure the string representation matches the original input
    except (TypeError, ValueError):
        return False


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
    if not isinstance(s, str):
        return False
    if s.startswith(("0x", "0X")):
        s = s[2:]  # Remove '0x' prefix for validation
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
        # r"^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$",
        const.PATTERN_IP_ADDRESS,
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


def is_valid_url(url, strict=True):
    """
    Check if the given url is valid.

    :param url: (str) url to check
    :param strict: If False, URLs without a TLD (e.g., "http://example") are considered valid. Defaults to True.
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
    if not url:
        return False

    if url and not (url.startswith("http://") or url.startswith("https://")):
            url = f"http://{url}"

    # regex = re.compile(
    #     r'^https?://'  # http:// or https://
    #     r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
    #     r'localhost|'  # localhost...
    #     r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}\b)' # ...or ip
    #     r'(?::\d+)?'  # optional port
    #     r'(?:/?|[/?]\S+)',
    #     re.IGNORECASE)


    if strict:
        # Standard regex pattern requiring a TLD
        regex_pattern = (
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}\b)'  # IP 
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)'  # optional path
            )

    else:
        # Regex pattern that allows URLs without a TLD
        regex_pattern = (
            r'^https?://'  # http://  or https://
            r'(?:[A-Z0-9]+(?:[A-Z0-9-]*[A-Z0-9])?\.)?'  #  domain
            r'(?:[A-Z0-9]+(?:[A-Z0-9-]*[A-Z0-9]))'  # parse 
            r'(?:\.[A-Z]{2,6})?'  # TLD (선택사항)
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)?$'  # optional path
            )

    regex = re.compile(regex_pattern, re.IGNORECASE)

    return bool(regex.search(url))


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


def is_valid_icon_keystore_file(keystore=None):
    from pawnlib.typing.converter import flatten
    if not isinstance(keystore, dict):
        return False

    required_keys = [
        "address",
        "crypto.cipher", "crypto.cipherparams.iv",
        "crypto.ciphertext", "crypto.kdf",
        "crypto.kdfparams.dklen",
        "crypto.kdfparams.n",
        "crypto.kdfparams.r",
        "crypto.kdfparams.p",
        "crypto.kdfparams.salt",
        "crypto.mac",
        "id", "version", "coinType",
    ]

    flatten_keystore = flatten(keystore)
    missing_keys = [key for key in required_keys if key not in flatten_keystore]

    if missing_keys:
        missing_keys_str = ", ".join(missing_keys)
        raise ValueError(f"<Invalid Keystore> Missing required key(s): {missing_keys_str}")

    return True


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


def error_and_exit(message, title="Error Occurred", exit_code=1):
    """
    Print an error message with the caller's file name and line number, then exit the program.

    :param message: The error message to display.
    :param title: The error title to display.
    :param exit_code: The exit code to use when terminating the program (default is 1).
    """
    caller_frame = inspect.stack()[1]
    file_name = os.path.basename(caller_frame.filename)
    line_number = caller_frame.lineno
    error_message = f"[bold red]Error:[/bold red] {message}"
    subtitle = f"{file_name}:{line_number}"
    print("")
    pawn.console.print(
        Panel(
            error_message, title=f"[bold red]{title} (-{exit_code})[/bold red]", expand=True, subtitle=subtitle,
            padding=1,
        )
    )
    print("")
    sys.exit(exit_code)


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


def _traverse_keys(element: Union[dict, list], keys: tuple) -> Any:
    """
    Helper function to traverse nested dictionaries and lists using the provided keys.

    :param element: The dictionary or list to traverse.
    :param keys: The keys or indices to traverse in the dictionary or list.
    :return: The value if all keys/indices exist, else raises an exception.
    """
    current_element = element
    for key in keys:
        if isinstance(current_element, list):
            key = int(key)  # Convert key to int if the current element is a list
        current_element = current_element[key]
    return current_element


def keys_exists(element: dict, *keys: str) -> bool:
    """
    Check if **keys** (nested) exist in `element` (dict).

    :param element: The dictionary to search.
    :param keys: The keys to traverse in the dictionary.
    :return: True if all keys exist, False otherwise.

    Example:

        .. code-block:: python

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
    try:
        _traverse_keys(element, keys)
        return True
    except (KeyError, TypeError, IndexError, ValueError):
        return False


def get_if_keys_exist(element: dict, *keys: str, default: Any = None) -> Any:
    """
    Retrieve the value from a nested dictionary if **keys** exists in `element`.

    :param element: The dictionary to search.
    :param keys: The keys to traverse in the dictionary.
    :param default: The default value to return if the keys do not exist.
    :return: The value if all keys exist, else the default value.

    Example:

        .. code-block:: python

            dict_example = {
                "name": "example",
                "description": {
                    "description_2": "222",
                    "description_3": "333",
                },
                "none_value_key": None,
                "nested_list": [{"key1": "value1"}, {"key2": "value2"}]
            }

            get_if_keys_exist(dict_example, 'name')
            # >> 'example'

            get_if_keys_exist(dict_example, 'description', 'description_2')
            # >> '222'

            get_if_keys_exist(dict_example, 'none_value_key')
            # >> None

            get_if_keys_exist(dict_example, 'name', 'none_key')
            # >> None

            get_if_keys_exist(dict_example, 'nested_list', '1', 'key2')
            # >> 'value2'

            get_if_keys_exist(dict_example, 'nested_list', '0', 'key1')
            # >> 'value1'
    """
    try:
        return _traverse_keys(element, keys)
    except (KeyError, TypeError, IndexError, ValueError) as e:
        key_path = ' -> '.join(keys)
        pawn.console.debug(f"Error accessing key/index '{key_path}': {e}")
        return default


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


def check_key_and_type(data, key, expected_type):
    """
    Checks if a specific key exists in a dictionary and if its value is of the expected type.

    :param data: The dictionary to check.
    :param key: The key to check for in the dictionary.
    :param expected_type: The expected type of the value (e.g., list, dict, etc.).
    :return: True if the key exists and its value is of the expected type, False otherwise.

    Examples:

        .. code-block:: python

            result = {
                'res': [1, 2, 3],
                'config': {'option': True},
                'count': 10
            }

            # Check if 'res' exists and is a list
            is_res_list = check_key_and_type(result, 'res', list)
            print(is_res_list)  # Output: True

            # Check if 'config' exists and is a dict
            is_config_dict = check_key_and_type(result, 'config', dict)
            print(is_config_dict)  # Output: True

            # Check if 'count' exists and is a string
            is_count_string = check_key_and_type(result, 'count', str)
            print(is_count_string)  # Output: False

            # Check if 'nonexistent_key' exists and is a list
            is_nonexistent_list = check_key_and_type(result, 'nonexistent_key', list)
            print(is_nonexistent_list)  # Output: False
    """
    if key in data and isinstance(data[key], expected_type):
        return True
    return False

