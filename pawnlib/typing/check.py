import re


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


def is_regex_keywords(keywords, value):
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
            if len(keyword) > 0:
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
    return False


def is_valid_ipv4(ip):
    """
    Validates IPv4 addresses.

    :param ip:
    :return:

    """
    pattern = re.compile(
        r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$",
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
