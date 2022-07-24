import re


class Null(object):
    """
    A Null object class as part of the Null object design pattern.
    """
    def __init__(self, *args, **kwargs):
        """
        Do nothing.
        """
        pass

    def __call__(self, *args, **kwargs):
        """
        Do nothing.
        @return: This object instance.
        @rtype: Null
        """
        return self

    def __getattr__(self, name):
        """
        Do nothing.
        @return: This object instance.
        @rtype: Null
        """
        return self

    def __setattr__(self, name, value):
        """
        Do nothing.
        @return: This object instance.
        @rtype: Null
        """
        return self

    def __delattr__(self, name):
        """
        Do nothing.
        @return: This object instance.
        @rtype: Null
        """
        return self

    def __repr__(self):
        """
        Null object string representation is the empty string.
        @return: An empty string.
        @rtype: String
        """
        return ''

    def __str__(self):
        """
        Null object string representation is the empty string.
        @return: An empty string.
        @rtype: String
        """
        return ''

    def __bool__(self):
        """
        Null object evaluates to False.
        @return: False.
        @rtype: Boolean
        """
        return False

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



