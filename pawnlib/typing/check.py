import re


def is_int(s) -> bool:
    try:
        int(s)
    except TypeError:
        return False
    except ValueError:
        return False
    return True


def is_hex(s) -> bool:
    try:
        int(s, 16)
    except TypeError:
        return False
    except ValueError:
        return False
    return True


def is_regex_keywords(keywords, value):
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



