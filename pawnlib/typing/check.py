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



