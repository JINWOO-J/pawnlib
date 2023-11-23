import sys
import os
import binascii
import re
import heapq
import json
from termcolor import cprint
import decimal
import math
import base64
from .check import is_int, is_hex
from deprecated import deprecated
from typing import Union, Any, Type
from pawnlib.config.globalconfig import pawnlib_config as pawn
from collections.abc import MutableMapping
from pawnlib import logger
from pawnlib.typing.constants import const
from pawnlib.config.__fix_import import Null
import statistics
from datetime import datetime

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

NO_DEFAULT = object()


class StackList:
    """
    Stack List

    :param max_length: max length size for list

    Example:

        .. code-block:: python

            from pawnlib.typing.converter import StackList

            stack = StackList(max_length=10)
            for i in range(1, 100)
                stack.push(i)

            stack.mean()
            # > 94.5

            stack.median()
            # > 94.5

    """

    def __init__(self, max_length=1000):
        self.max_length = max_length
        self.data = []

    def push(self, item):
        if len(self.data) == self.max_length:
            self.data.pop(0)
        self.data.append(item)

    def median(self):
        return statistics.median(self.data)

    def mean(self):
        return statistics.mean(self.data)

    def max(self):
        return max(self.data)

    def min(self):
        return min(self.data)

    def get_list(self):
        return self.data

    def __repr__(self):
        return str(f"<StackList> {self.data}")

    def __str__(self):
        return str(f"<StackList> {self.data}")

    def reset(self):
        self.data = []


class ErrorCounter:
    """
    A class for counting consecutive errors and calculating dynamic count.

    :param max_consecutive_count: Maximum number of consecutive errors allowed. Default is 10.
    :type max_consecutive_count: int
    :param increase_index: Index for calculating dynamic count. Default is 0.5.
    :type increase_index: float
    :param reset_threshold_rate: Threshold rate for resetting the counter. Default is 80.
    :type reset_threshold_rate: int

    Example:

        .. code-block:: python

            ec = ErrorCounter()
            ec.push(True)
            ec.push(False)
    """

    def __init__(self, max_consecutive_count=10, increase_index=0.5, reset_threshold_rate=80):
        self.max_consecutive_count = max_consecutive_count
        self.increase_index = increase_index
        self.reset_threshold_rate = reset_threshold_rate
        self.consecutive_count = 0
        self.total_count = 0
        self.dynamic_count = 0
        self.stack = StackList(max_length=max_consecutive_count)
        self._hit = 0
        self._hit_rate = 0
        self.last_message = ""
        self.last_hit = False

    def push(self, error_boolean=True):
        """
        Pushes an error boolean to the stack and updates counts.

        :param error_boolean: Boolean indicating if an error occurred. Default is True.
        :type error_boolean: bool
        :return: None

        Example:

            .. code-block:: python

                ec.push(True)
                ec.push(False)

        """
        self.stack.push(
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                error_boolean
            )
        )
        if error_boolean is True:
            self.consecutive_count += 1
            self.total_count += 1
        else:
            self.consecutive_count = 0
        self.calculate_dynamic_count()

    def calculate_dynamic_count(self):
        """
        Calculates the dynamic count and updates hit rate and counter if necessary.

        :return: None

        Example:

            .. code-block:: python

                ec.calculate_dynamic_count()

        """
        self.dynamic_count = self.total_count ** self.increase_index
        if self.dynamic_count % 1 == 0:
            self.last_hit = True
            self._hit += 1
            self._hit_rate = truncate_decimal((self._hit / self.total_count) * 100)

            if self._hit_rate != 100 and self._hit_rate >= self.reset_threshold_rate:
                self._reset_counter()
            self.last_message = f"[red]hit/total={self._hit}/{self.total_count} ({self._hit_rate}%)"
            pawn.console.debug(self.last_message)
        else:
            self.last_hit = False

    def _reset_counter(self):
        """
        Resets the counter.

        :return: None

        Example:

            .. code-block:: python

                ec._reset_counter()

        """
        self.total_count = 0
        self._hit = 0
        self._hit_rate = 0
        self.dynamic_count = 0

    def is_ok(self):
        """
        Checks if the consecutive count is less than the maximum allowed.

        :return: True if the consecutive count is less than the maximum allowed, False otherwise.

        Example:

            .. code-block:: python

                ec.is_ok()

        """
        if self.consecutive_count >= self.max_consecutive_count:
            return False
        return True

    def push_ok(self, error_boolean=True):
        """
        Pushes an error boolean to the stack and checks if it is ok.

        :param error_boolean: Boolean indicating if an error occurred. Default is True.
        :type error_boolean: bool
        :return: True if it is ok, False otherwise.

        Example:

            .. code-block:: python

                ec.push_ok(True)

        """
        self.push(error_boolean)
        return self.is_ok()

    def push_hit(self, error_boolean=True):
        """
        Pushes an error boolean to the stack and returns the last hit.

        :param error_boolean: Boolean indicating if an error occurred. Default is True.
        :type error_boolean: bool
        :return: True if it is a hit, False otherwise.

        Example:

            .. code-block:: python

                ec.push_hit(True)

        """
        self.push(error_boolean)
        return self.last_hit

    def get_data(self):
        """
        Returns the dictionary representation of the object.

        :return:
        """
        return self.__dict__

    def __repr__(self):
        return str(f"<ErrorCounter> consecutive_count={self.consecutive_count}, "
                   f"total_count={self.total_count}, max={self.max_consecutive_count}, is_ok={self.is_ok()}, last_hit={self.last_hit}")

    def __str__(self):
        return self.__repr__()


class MedianFinder:
    """
    A class to find the median of a stream of numbers.

    Example:

        .. code-block:: python

            mf = MedianFinder()
            mf.add_number(1)
            mf.add_number(2)
            mf.median() # 1.5
            mf.add_number(3)
            mf.median() # 2.0

    """

    def __init__(self):
        """
        Initialize the data structure.

        Example:

            .. code-block:: python

                mf = MedianFinder()

        """
        self.max_heap = []
        self.min_heap = []
        self.num_list = []

    def add_number(self, num):
        """
        Add a number to the data structure.

        :param num: An integer to be added to the data structure.
        :type num: int
        :return: None

        Example:

            .. code-block:: python

                mf = MedianFinder()
                mf.add_number(1)
                mf.add_number(2)
                mf.add_number(3)

        """
        self.num_list.append(num)
        if not self.max_heap and not self.min_heap:
            heapq.heappush(self.min_heap, num)
            return
        if not self.max_heap:
            if num > self.min_heap[0]:
                heapq.heappush(self.max_heap, -heapq.heappop(self.min_heap))
                heapq.heappush(self.min_heap, num)
            else:
                heapq.heappush(self.max_heap, -num)
            return
        if len(self.max_heap) == len(self.min_heap):
            if num < -self.max_heap[0]:
                heapq.heappush(self.max_heap, -num)
            else:
                heapq.heappush(self.min_heap, num)
        elif len(self.max_heap) > len(self.min_heap):
            if num < -self.max_heap[0]:
                heapq.heappush(self.min_heap, -heapq.heappop(self.max_heap))
                heapq.heappush(self.max_heap, -num)
            else:
                heapq.heappush(self.min_heap, num)
        else:
            if num > self.min_heap[0]:
                heapq.heappush(self.max_heap, -heapq.heappop(self.min_heap))
                heapq.heappush(self.min_heap, num)
            else:
                heapq.heappush(self.max_heap, -num)

    def median(self):
        """
        Find the median of the numbers in the data structure.

        :return: The median of the numbers in the data structure.
        :rtype: float

        Example:

            .. code-block:: python

                mf = MedianFinder()
                mf.add_number(1)
                mf.add_number(2)
                mf.median() # 1.5
                mf.add_number(3)
                mf.median() # 2.0

        """
        if len(self.max_heap) == len(self.min_heap):
            return (-self.max_heap[0] + self.min_heap[0]) / 2
        elif len(self.max_heap) > len(self.min_heap):
            return -self.max_heap[0]
        else:
            return self.min_heap[0]

    def mean(self):
        """
        Find the mean of the numbers in the data structure.

        :return: The mean of the numbers in the data structure.
        :rtype: float

        Example:

            .. code-block:: python

                mf = MedianFinder()
                mf.add_number(1)
                mf.add_number(2)
                mf.mean() # 1.5
                mf.add_number(3)
                mf.mean() # 2.0

        """
        count = len(self.num_list)
        return sum(self.num_list) / count


class FlatDict(MutableMapping):
    """:class:`~flatdict.FlatDict` is a dictionary object that allows for
    single level, delimited key/value pair mapping of nested dictionaries.
    The default delimiter value is ``.`` but can be changed in the constructor
    or by calling :meth:`FlatDict.set_delimiter`.


    Example:

        .. code-block:: python

            from pawnlib.typing.converter import FlatDict

            config = {
                "1": "2",
                "1-2": {
                    "2-1": "3-1"
                },
            }

            dot_dict = FlatDict(config)

            dot_dict.get('1-2.2-1')

            # >> '3-1'

    """
    _COERCE = dict

    def __init__(self, value=None, delimiter='.', dict_class=dict):
        super(FlatDict, self).__init__()
        self._values = dict_class()
        self._delimiter = delimiter
        self.update(value)

    def __contains__(self, key):
        """Check to see if the key exists, checking for both delimited and
        not delimited key values.
        :param mixed key: The key to check for
        """
        if self._has_delimiter(key):
            pk, ck = key.split(self._delimiter, 1)
            return pk in self._values and ck in self._values[pk]
        return key in self._values

    def __delitem__(self, key):
        """Delete the item for the specified key, automatically dealing with
        nested children.
        :param mixed key: The key to use
        :raises: KeyError
        """
        if key not in self:
            raise KeyError
        if self._has_delimiter(key):
            pk, ck = key.split(self._delimiter, 1)
            del self._values[pk][ck]
            if not self._values[pk]:
                del self._values[pk]
        else:
            del self._values[key]

    def __eq__(self, other):
        """Check for equality against the other value
        :param other: The value to compare
        :type other: FlatDict
        :rtype: bool
        :raises: TypeError
        """
        if isinstance(other, dict):
            return self.as_dict() == other
        elif not isinstance(other, self.__class__):
            raise TypeError
        return self.as_dict() == other.as_dict()

    def __ne__(self, other):
        """Check for inequality against the other value
        :param other: The value to compare
        :type other: dict or FlatDict
        :rtype: bool
        """
        return not self.__eq__(other)

    def __getitem__(self, key):
        """Get an item for the specified key, automatically dealing with
        nested children.
        :param mixed key: The key to use
        :rtype: mixed
        :raises: KeyError
        """
        values = self._values
        key = [key] if isinstance(key, int) else key.split(self._delimiter)
        for part in key:
            values = values[part]
        return values

    def __iter__(self):
        """Iterate over the flat dictionary key and values
        :rtype: Iterator
        :raises: RuntimeError
        """
        return iter(self.keys())

    def __len__(self):
        """Return the number of items.
        :rtype: int
        """
        return len(self.keys())

    def __reduce__(self):
        """Return state information for pickling
        :rtype: tuple
        """
        return type(self), (self.as_dict(), self._delimiter)

    def __repr__(self):
        """Return the string representation of the instance.
        :rtype: str
        """
        return '<{} id={} {}>"'.format(self.__class__.__name__, id(self),
                                       str(self))

    def __setitem__(self, key, value):
        """Assign the value to the key, dynamically building nested
        FlatDict items where appropriate.
        :param mixed key: The key for the item
        :param mixed value: The value for the item
        :raises: TypeError
        """
        if isinstance(value, self._COERCE) and not isinstance(value, FlatDict):
            value = self.__class__(value, self._delimiter)
        if self._has_delimiter(key):
            pk, ck = key.split(self._delimiter, 1)
            if pk not in self._values:
                self._values[pk] = self.__class__({ck: value}, self._delimiter)
                return
            elif not isinstance(self._values[pk], FlatDict):
                raise TypeError(
                    'Assignment to invalid type for key {}'.format(pk))
            self._values[pk][ck] = value
        else:
            self._values[key] = value

    def __str__(self):
        """Return the string value of the instance.
        :rtype: str
        """
        return '{{{}}}'.format(', '.join(
            ['{!r}: {!r}'.format(k, self[k]) for k in self.keys()]))

    def as_dict(self):
        """Return the :class:`~flatdict.FlatDict` as a :class:`dict`
        :rtype: dict
        """
        out = dict({})
        for key in self.keys():
            if self._has_delimiter(key):
                pk, ck = key.split(self._delimiter, 1)
                if self._has_delimiter(ck):
                    ck = ck.split(self._delimiter, 1)[0]
                if isinstance(self._values[pk], FlatDict) and pk not in out:
                    out[pk] = {}
                if isinstance(self._values[pk][ck], FlatDict):
                    out[pk][ck] = self._values[pk][ck].as_dict()
                else:
                    out[pk][ck] = self._values[pk][ck]
            else:
                out[key] = self._values[key]
        return out

    def clear(self):
        """Remove all items from the flat dictionary."""
        self._values.clear()

    def copy(self):
        """Return a shallow copy of the flat dictionary.
        :rtype: flatdict.FlatDict
        """
        return self.__class__(self.as_dict(), delimiter=self._delimiter)

    def get(self, key, d=None):
        """Return the value for key if key is in the flat dictionary, else
        default. If default is not given, it defaults to ``None``, so that this
        method never raises :exc:`KeyError`.
        :param mixed key: The key to get
        :param mixed d: The default value
        :rtype: mixed
        """
        try:
            return self.__getitem__(key)
        except KeyError:
            return d

    def items(self):
        """Return a copy of the flat dictionary's list of ``(key, value)``
        pairs.

        .. note::
            CPython implementation detail: Keys and values are listed in
            an arbitrary order which is non-random, varies across Python
            implementations, and depends on the flat dictionary's history of
            insertions and deletions.

        :rtype: list

        """
        return [(k, self.__getitem__(k)) for k in self.keys()]

    def iteritems(self):
        """Return an iterator over the flat dictionary's (key, value) pairs.
        See the note for :meth:`flatdict.FlatDict.items`.
        Using ``iteritems()`` while adding or deleting entries in the flat
        dictionary may raise :exc:`RuntimeError` or fail to iterate over all
        entries.
        :rtype: Iterator
        :raises: RuntimeError
        """
        for item in self.items():
            yield item

    def iterkeys(self):
        """Iterate over the flat dictionary's keys. See the note for
        :meth:`flatdict.FlatDict.items`.
        Using ``iterkeys()`` while adding or deleting entries in the flat
        dictionary may raise :exc:`RuntimeError` or fail to iterate over all
        entries.
        :rtype: Iterator
        :raises: RuntimeError
        """
        for key in self.keys():
            yield key

    def itervalues(self):
        """Return an iterator over the flat dictionary's values. See the note
        :meth:`flatdict.FlatDict.items`.
        Using ``itervalues()`` while adding or deleting entries in the flat
        dictionary may raise a :exc:`RuntimeError` or fail to iterate over all
        entries.
        :rtype: Iterator
        :raises: RuntimeError
        """
        for value in self.values():
            yield value

    def keys(self):
        """Return a copy of the flat dictionary's list of keys.
        See the note for :meth:`flatdict.FlatDict.items`.
        :rtype: list
        """
        keys = []

        for key, value in self._values.items():
            if isinstance(value, (FlatDict, dict)):
                nested = [
                    self._delimiter.join([str(key), str(k)])
                    for k in value.keys()]
                keys += nested if nested else [key]
            else:
                keys.append(key)

        return keys

    def pop(self, key, default=NO_DEFAULT):
        """If key is in the flat dictionary, remove it and return its value,
        else return default. If default is not given and key is not in the
        dictionary, :exc:`KeyError` is raised.
        :param mixed key: The key name
        :param mixed default: The default value
        :rtype: mixed
        """
        if key not in self and default != NO_DEFAULT:
            return default
        value = self[key]
        self.__delitem__(key)
        return value

    def setdefault(self, key=None, default=None):
        """If key is in the flat dictionary, return its value. If not,
        insert key with a value of default and return default.
        default defaults to ``None``.
        :param mixed key: The key name
        :param mixed default: The default value
        :rtype: mixed
        """
        if key not in self:
            self.__setitem__(key, default)
        return self.__getitem__(key)

    def set_delimiter(self, delimiter):
        """Override the default or passed in delimiter with a new value. If
        the requested delimiter already exists in a key, a :exc:`ValueError`
        will be raised.
        :param str delimiter: The delimiter to use
        :raises: ValueError
        """
        for key in self.keys():
            if delimiter in key:
                raise ValueError('Key {!r} collides with delimiter {!r}', key,
                                 delimiter)
        self._delimiter = delimiter
        for key in self._values.keys():
            if isinstance(self._values[key], FlatDict):
                self._values[key].set_delimiter(delimiter)

    def update(self, other=None, **kwargs):
        """Update the flat dictionary with the key/value pairs from other,
        overwriting existing keys.
        ``update()`` accepts either another flat dictionary object or an
        iterable of key/value pairs (as tuples or other iterables of length
        two). If keyword arguments are specified, the flat dictionary is then
        updated with those key/value pairs: ``d.update(red=1, blue=2)``.
        :param iterable other: Iterable of key, value pairs
        :rtype: None
        """
        [self.__setitem__(k, v) for k, v in dict(other or kwargs).items()]

    def values(self):
        """Return a copy of the flat dictionary's list of values. See the note
        for :meth:`flatdict.FlatDict.items`.
        :rtype: list
        """
        return [self.__getitem__(k) for k in self.keys()]

    def _has_delimiter(self, key):
        """Checks to see if the key contains the delimiter.
        :rtype: bool
        """
        return isinstance(key, str) and self._delimiter in key


class FlatterDict(FlatDict):
    """Like :class:`~flatdict.FlatDict` but also coerces lists and sets
     to child-dict instances with the offset as the key. Alternative to
     the implementation added in v1.2 of FlatDict.
    """
    _COERCE = list, tuple, set, dict, FlatDict
    _ARRAYS = list, set, tuple

    def __init__(self, value=None, delimiter=':', dict_class=dict):
        self.original_type = type(value)
        if self.original_type in self._ARRAYS:
            value = {str(i): v for i, v in enumerate(value)}
        super(FlatterDict, self).__init__(value, delimiter, dict_class)

    def __setitem__(self, key, value):
        """Assign the value to the key, dynamically building nested
        FlatDict items where appropriate.
        :param mixed key: The key for the item
        :param mixed value: The value for the item
        :raises: TypeError
        """
        if isinstance(value, self._COERCE) and \
                not isinstance(value, FlatterDict):
            value = self.__class__(value, self._delimiter)
        if self._has_delimiter(key):
            pk, ck = key.split(self._delimiter, 1)
            if pk not in self._values:
                self._values[pk] = self.__class__({ck: value}, self._delimiter)
                return
            if getattr(self._values[pk], 'original_type',
                       None) in self._ARRAYS:
                try:
                    k, cck = ck.split(self._delimiter, 1)
                    int(k)
                except ValueError:
                    raise TypeError(
                        'Assignment to invalid type for key {}{}{}'.format(
                            pk, self._delimiter, ck))
                self._values[pk][k][cck] = value
                return
            elif not isinstance(self._values[pk], FlatterDict):
                raise TypeError(
                    'Assignment to invalid type for key {}'.format(pk))
            self._values[pk][ck] = value
        else:
            self._values[key] = value

    def as_dict(self):
        """Return the :class:`~flatdict.FlatterDict` as a nested
        :class:`dict`.
        :rtype: dict
        """
        out = {}
        for key in self.keys():
            if self._has_delimiter(key):
                pk, ck = key.split(self._delimiter, 1)
                if self._has_delimiter(ck):
                    ck = ck.split(self._delimiter, 1)[0]
                if isinstance(self._values[pk], FlatterDict) and pk not in out:
                    if self._values[pk].original_type == tuple:
                        out[pk] = tuple(self._child_as_list(pk))
                    elif self._values[pk].original_type == list:
                        out[pk] = self._child_as_list(pk)
                    elif self._values[pk].original_type == set:
                        out[pk] = set(self._child_as_list(pk))
                    elif self._values[pk].original_type == dict:
                        out[pk] = self._values[pk].as_dict()
            else:
                if isinstance(self._values[key], FlatterDict):
                    out[key] = self._values[key].original_type()
                else:
                    out[key] = self._values[key]
        return out

    def _child_as_list(self, pk, ck=None):
        """Returns a list of values from the child FlatterDict instance
        with string based integer keys.
        :param str pk: The parent key
        :param str ck: The child key, optional
        :rtype: list
        """
        if ck is None:
            subset = self._values[pk]
        else:
            subset = self._values[pk][ck]
        # Check if keys has delimiter, which implies deeply nested dict
        keys = subset.keys()
        if any(self._has_delimiter(k) for k in keys):
            out = []
            split_keys = {k.split(self._delimiter)[0] for k in keys}
            for k in sorted(split_keys, key=lambda x: int(x)):
                if subset[k].original_type == tuple:
                    out.append(tuple(self._child_as_list(pk, k)))
                elif subset[k].original_type == list:
                    out.append(self._child_as_list(pk, k))
                elif subset[k].original_type == set:
                    out.append(set(self._child_as_list(pk, k)))
                elif subset[k].original_type == dict:
                    out.append(subset[k].as_dict())
            return out

        # Python prior 3.6 does not guarantee insertion order, remove it after
        # EOL python 3.5 - 2020-09-13
        if sys.version_info[0:2] < (3, 6):  # pragma: nocover
            return [subset[k] for k in sorted(keys, key=lambda x: int(x))]
        else:
            return [subset[k] for k in keys]


def base64_decode(text):
    """
    Decode the text to base64.

    :param text:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter

            decoded_base64 = converter.base64_decode("ampqampqag==")

            # >> jjjjjjj

    """

    return base64.b64decode(text).decode('utf-8')


def base64ify(bytes_or_str):
    """
    Helper method to perform base64 encoding across Python 2.7 and Python 3.X

    :param bytes_or_str:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter

            encoded_base64 = converter.base64ify("jjjjjjj")

            # >> ampqampqag==

    """

    if sys.version_info[0] >= 3 and isinstance(bytes_or_str, str):
        input_bytes = bytes_or_str.encode('utf8')
    else:
        input_bytes = bytes_or_str

    output_bytes = base64.urlsafe_b64encode(input_bytes)
    if sys.version_info[0] >= 3:
        return output_bytes.decode('ascii')
    else:
        return output_bytes


# https://pypi.org/project/Deprecated/
@deprecated(version="1.0.0", reason="You should use another function=> convert_dict_hex_to_int")
def convert_hex_to_int(data: Any, is_comma: bool = False):
    """
    It will be changed to convert_dict_hex_to_int

    :param data: data
    :param is_comma: human-readable notation
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter
            data = {"aaa": "0x1323"}

            converter.convert_hex_to_int(data)
            # >> {"aaa": 4899}

    """
    return_data = {}

    if type(data) == list:
        return_list = []
        for index, value in enumerate(data):
            if type(value) == dict:
                return_list.append(convert_hex_to_int(value))
            elif is_hex(value):
                return_list.append(int(value, 16))
        return return_list

    elif isinstance(data, dict):
        for key, value in data.items():
            # for key, value in enumerate(data):
            if type(value) == dict:
                return_data[key] = convert_hex_to_int(value)

            elif type(value) == list:
                return_data[key] = convert_hex_to_int(value)

            elif is_int(value):
                return_data[key] = int(value)

            elif is_hex(value):
                int_value = int(value, 16)
                con_res = ""
                # if args.verbose > 1 and args.write is None:
                #     con_res = f"\t\t(convert from f{value})"

                if int_value >= const.TINT:
                    int_value = int_value / const.TINT
                    # if args.verbose > 1 and args.write is None:
                    #     con_res += f"(tint) from {int_value}"
                if is_comma:
                    return_data[key] = f"{int_value:,} {con_res}"
                else:
                    return_data[key] = int_value
            else:
                # if args.verbose > 1 and args.write is None:
                #     return_data[key] = f"{value} (org)"
                #     return_data[key] = f"{value} (org)"
                # else:
                return_data[key] = value
    return return_data


def convert_dict_hex_to_int(data: Any, is_comma: bool = False, debug: bool = False, ignore_keys: list = [], ansi: bool = False):
    """
    This function recursively converts hex to int.

    :param data:
    :param is_comma:
    :param debug:
    :param ignore_keys:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter
            data = {"aaa": "0x1323"}
            converter.convert_dict_hex_to_int(data)
            # >> {"aaa": 4899}

    """
    return_data = {}
    if isinstance(data, list):
        return_list = []
        for index, value in enumerate(data):
            if isinstance(value, list) or isinstance(value, dict):
                return_list.append(convert_dict_hex_to_int(value, is_comma, debug))
            else:
                return_list.append(hex_to_number(value, is_comma, debug))
        return return_list

    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                return_data[key] = convert_dict_hex_to_int(value, is_comma, debug)
            elif isinstance(value, list):
                return_data[key] = convert_dict_hex_to_int(value, is_comma, debug)
            else:
                change = True
                if key in ignore_keys:
                    change = False
                # else:
                return_data[key] = hex_to_number(value, is_comma, debug, change, ansi=ansi)
    else:
        return_data = hex_to_number(data, is_comma, debug, ansi=ansi)
    return return_data


class __bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    GREEN = '\033[32;40m'
    CYAN = '\033[96m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    ITALIC = '\033[1;3m'
    UNDERLINE = '\033[4m'
    WHITE = '\033[97m'
    DARK_GREY = '\033[38;5;243m'
    LIGHT_GREY = '\033[37m'


def hex_to_number(hex_value: str = "", is_comma: bool = False, debug: bool = False, change: bool = False, ansi: bool = False, is_tint: bool = False):
    """

    this function will change the hex to number(int)

    :param ansi:
    :param hex_value:
    :param is_comma:
    :param debug:
    :param change:
    :param is_tint:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter

            converter.hex_to_number("0x22223232d")
            # >> 9162662701

            converter.hex_to_number("0x22223232d", is_comma=True)
            # >> '9,162,662,701'

            converter.hex_to_number("0x2386f26fc10000", is_tint=True)
            # >> 0.01

    """
    _changed = False
    _not_change = False

    if not ansi:
        _bcolors = Null()
    else:
        _bcolors = __bcolors()

    changed_text = f"(org)"
    if is_int(hex_value):
        converted_value = int(hex_value)
        _changed = True
    elif is_hex(hex_value):
        converted_value = int(hex_value, 16)
        _changed = True
    else:
        converted_value = hex_value
    if (_changed and change) or is_int(converted_value):
        if converted_value >= const.TINT or is_tint:
            converted_value = converted_value / const.TINT
            changed_text = f"{_bcolors.WARNING}(tint){_bcolors.ENDC}"

        if is_comma:
            converted_value = f"{converted_value:,}"

        if ansi:
            converted_value = f"{_bcolors.CYAN}{converted_value}{_bcolors.ENDC}"

    else:
        changed_text = f"{_bcolors.FAIL}(not changed){_bcolors.ENDC}"
        _not_change = True

    if debug:
        if hex_value == converted_value or _not_change:
            hex_value = ""
        return f"{converted_value} {_bcolors.ITALIC}{changed_text} {hex_value}{_bcolors.ENDC}".strip()
    else:
        return converted_value


def get_size(file_path: str = '', attr=False):
    """

    Returns the size of the file.

    :param file_path:
    :param attr:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter

            converter.get_size("./requirements.txt")
            # > '373.0 bytes'

            converter.get_size("./requirements.txt", attr=True)
            # > ['373.0 bytes', 'FILE']


    """
    return_size, file_attr = ["", ""]
    if os.path.isdir(file_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(file_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return_size = convert_bytes(total_size)
        file_attr = "DIR"
    elif os.path.isfile(file_path):
        file_info = os.stat(file_path)
        return_size = convert_bytes(file_info.st_size)
        file_attr = "FILE"

    if attr:
        return [return_size, file_attr]

    return return_size


def convert_bytes(num: Union[int, float]) -> str:
    """

    this function will convert bytes to MB.... GB... etc

    :param num:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter

            converter.convert_bytes(2323223232323)
            # > '2.1 TB'

            converter.convert_bytes(2323223232.232)
            # > '2.2 GB'

    """

    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


def str2bool(v) -> bool:
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


def flatten(dictionary, parent_key=False, separator='.'):
    """
    Turn a nested dictionary into a flattened dictionary

    :param dictionary: The dictionary to flatten
    :param parent_key: The string to prepend to dictionary's keys
    :param separator: The string used to separate flattened keys
    :return: A flattened dictionary
    """

    items = []
    for key, value in dictionary.items():
        new_key = str(parent_key) + separator + key if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(flatten(value, new_key, separator).items())
        elif isinstance(value, list):
            for k, v in enumerate(value):
                items.extend(flatten({str(k): v}, new_key).items())
        else:
            items.append((new_key, value))
    return dict(items)


def flatten_list(list_items: list, uniq=False) -> list:
    """
    this function will convert complex list to  flatten list


    :param list_items:
    :param uniq:
    :return:

    Example:

        .. code-block:: python

            # >>> [ 1, 2,[ 3, [4, 5, 6], 7]] => [1, 2, 3, 4, 5, 6, 7]
    """
    return_result = []
    for item in list_items:
        if isinstance(item, list):
            return_result = return_result + flatten_list(item)
        else:
            return_result.append(item)
    if uniq:
        return list(set(return_result))
    return return_result


def flatten_dict(init: dict, separator: str = '｡', lkey: str = '') -> dict:
    """

    this function will convert complex dict to flatten dict

    :param init:
    :param separator:
    :param lkey:
    :return:


    Example:

        .. code-block:: python

            # >>
                {
                    "aa": {
                        "bb": {
                            "cc": "here"
                        }
                    }
                }
                => {'aa｡bb｡cc': 'here'}
    """
    ret = {}
    for rkey, val in init.items():
        if separator == '':
            key = rkey
        else:
            key = lkey + rkey
        if isinstance(val, dict):
            ret.update(flatten_dict(val, separator, key + separator))
        elif isinstance(val, list):
            for i, value in enumerate(val):
                # ret[f"{key}[{i}]"] = value
                if isinstance(value, dict):
                    new_value = {}
                    for k, v in value.items():
                        new_value[f"[{i}]{separator}{k}"] = v
                    ret.update(flatten_dict(new_value, separator, key + separator))
                else:
                    ret[f"{key}{separator}{i}"] = value
        else:
            ret[key] = val
    return ret


def dict_to_line(dict_param: dict, quotes: bool = False, separator: str = "=", end_separator: str = ",") -> str:
    """
    This function converts a dict to a line.

    :param dict_param:
    :param quotes:
    :param separator:
    :param end_separator:
    :return:

    Example:

        .. code-block:: python

            # >> {"a": "1234", "b": "1235"} => "a=1234,b=1235"

    """
    return_value = ""
    for k, v in sorted(dict_param.items()):
        if quotes:
            return_value += f"{k}{separator}\"{v}\"{end_separator}"
        else:
            return_value += f"{k}{separator}{v}{end_separator}"
    return return_value.rstrip(end_separator)


def dict_none_to_zero(data: dict) -> dict:
    """
    Convert the None type of the dictionary to zero.


    :param data:
    :return:

    Example:

        .. code-block:: python

            # >> {"sdsdsds": None} => {"sdsdsds": 0}


    """

    return_dict = {}
    for key, value in data.items():
        if value is None:
            value = 0
        return_dict[key] = value
    return return_dict


def recursive_update_dict(source_dict: dict = None, target_dict: dict = None) -> dict:
    """

    :param source_dict:
    :param target_dict:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter

            source_dict = {
                "aaa": {
                    "1111": 1111,
                    "ssss": 1111,
                    "i_need_one": 2222
                }
            }
            target_dict = {
                "aaa": {
                    "i_need_one": "CHANGED_VALUE",
                }
            }
            converter.recursive_update_dict(source_dict, target_dict)

            # >>   {
                    "aaa": {
                            "1111": 1111,
                            "ssss": 1111,
                            "i_need_one": "CHANGED_VALUE"
                        }
                    }



    """
    if isinstance(target_dict, dict):
        for k, v in target_dict.items():
            if isinstance(v, dict):
                recursive_update_dict(source_dict[k], v)
            else:
                source_dict[k] = target_dict[k]
    return source_dict


def list_to_oneline_string(list_param: list, split_str: str = "."):
    """
    Convert the list to a string of one line.

    :param list_param: List
    :param split_str: String to separate
    :return:

    Example:

        .. code-block:: python

            # >> ["111", "222", "333"] => "111.222.333"


    """
    return_value = ''
    for idx, value in enumerate(list_param):
        return_value += f"{value}"
        if len(list_param) - 1 > idx:
            return_value += split_str
    return return_value


def long_to_bytes(val, endianness='big'):
    """

    Use :ref:`string formatting` and :func:`~binascii.unhexlify` to
    convert ``val``, a :func:`long`, to a byte :func:`str`.

    :param long val: The value to pack
    :param str endianness: The endianness of the result. ``'big'`` for big-endian, ``'little'`` for little-endian.
        If you want byte- and word-ordering to differ, you're on your own.
        Using :ref:`string formatting` lets us use Python's C innards.

    """
    # one (1) hex digit per four (4) bits
    width = val.bit_length()

    # unhexlify wants an even multiple of eight (8) bits, but we don't
    # want more digits than we need (hence the ternary-ish 'or')
    width += 8 - ((width % 8) or 8)

    # format width specifier: four (4) bits per hex digit
    fmt = '%%0%dx' % (width // 4)

    # prepend zero (0) to the width, to zero-pad the output
    s = binascii.unhexlify(fmt % val)

    if endianness == 'little':
        # see http://stackoverflow.com/a/931095/309233
        s = s[::-1]

    return s


def ordereddict_to_dict(obj, reverse=False):
    """
    Change the order of the keys in the dictionary.

    :param obj: (OrderedDict) The dictionary to change the order of keys.
    :param reverse: (bool) Whether to sort in reverse order. Default is False.
    :return: (dict) A new dictionary with the keys sorted in the specified order.

    Example:

        .. code-block:: python

            from collections import OrderedDict

            # Create an ordered dictionary
            od = OrderedDict([('c', 3), ('b', 2), ('a', 1)])

            # Change the order of the keys in the dictionary
            new_dict = ordereddict_to_dict(od)

            # Print the new dictionary
            print(new_dict)
            # >> {'a': 1, 'b': 2, 'c': 3}

    """
    return_result = {}
    for k, v in sorted(obj.items(), reverse=reverse):
        if isinstance(v, dict):
            return_result[k] = ordereddict_to_dict(v)
        else:
            return_result[k] = v
    return return_result


def recursive_operate_dict(obj, fn, target="key"):
    """


    :param obj:
    :param fn:
    :param target:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter

            obj = {
                "LLLLLL": "AAAAAAAA",
                "AAAAAA": "AAAAAAAA",
                "DDDDDD": 11111,
                "DDDDSD": {
                    "ASDFASDF": 111,
                    "ZXCZXCZXC": "DDDDDDDD"
                }
            }

           #  recursive_operate_dict(obj, fn=lower_case, target="key")
           #
           #  {
           #    llllll:       'AAAAAAAA'         <class 'str'> len=8
           #    aaaaaa:       'AAAAAAAA'         <class 'str'> len=8
           #    dddddd: 11111         <class 'int'> len=5
           #    ddddsd: {
           #       asdfasdf: 111         <class 'int'> len=3
           #       zxczxczxc:          'DDDDDDDD'         <class 'str'> len=8
           #  }
           #
           #  recursive_operate_dict(obj, fn=lower_case, target="value")
           #
           # {
           #    LLLLLL:       'aaaaaaaa'         <class 'str'> len=8
           #    AAAAAA:       'aaaaaaaa'         <class 'str'> len=8
           #    DDDDDD:       '11111'         <class 'str'> len=5
           #    DDDDSD: {
           #       ASDFASDF:          '111'         <class 'str'> len=3
           #       ZXCZXCZXC:          'dddddddd'         <class 'str'> len=8
           #    }
           # }

    """
    return_result = {}
    for key, value in obj.items():
        input_key = key
        input_value = value

        if target == "key":
            input_key = fn(key)
        elif target == "value":
            input_value = fn(value)

        if isinstance(value, dict):
            input_value = recursive_operate_dict(obj=value, fn=fn, target=target)

        return_result[input_key] = input_value
    return return_result


class UpdateType:
    def __init__(self, is_debug=False, use_env=False, default_schema={}, input_schema={}):
        # if structure_types is None:
        #     structure_types = default_structure
        self.return_value = ""
        self.return_dict = {}
        # self.default_schema = {k.lower(): v for k, v in default_schema.items()}
        self.default_schema = default_schema
        self.input_schema = input_schema
        self.is_debug = is_debug
        self.use_env = use_env
        self.section_separator = "__"

        self._lower_dict_keys()
        pawn.console.debug(f"default_schema={self.default_schema}")

    def _proc_section_separator(self):
        tmp_default_schema = {}
        if self.section_separator:
            for key, value in self.default_schema.items():
                if self.section_separator in key:
                    section_name, conf_key = key.split(self.section_separator)
                    if tmp_default_schema.get(section_name, None) is None:
                        tmp_default_schema[section_name] = {}

                    tmp_default_schema[section_name][conf_key] = value
                else:
                    if isinstance(value, dict):
                        for conf_key, conf_value in value.items():
                            if tmp_default_schema.get(key, None) is None:
                                tmp_default_schema[key] = {}
                            tmp_default_schema[key][conf_key] = conf_value
            self.default_schema = tmp_default_schema

    def _lower_dict_keys(self):
        self._proc_section_separator()
        self.default_schema = recursive_operate_dict(obj=self.default_schema, fn=lower_case, target="key")
        self.input_schema = recursive_operate_dict(obj=self.input_schema, fn=lower_case, target="key")

    def find_parent_type(self, key):
        find_key = None
        for struct_key, struct_value in self.default_schema.items():
            if struct_key == key:
                find_key = struct_value.get('default')
        return self.default_schema[find_key]['type']

    def fill_default(self):
        for section_name, section_data in self.default_schema.items():
            for default_key, default_value in section_data.items():
                if self.section_separator is not None and self.section_separator != "" and self.section_separator in default_key:
                    [section_name, section_key] = default_key.split(self.section_separator)
                else:
                    section_name = "default"
                    section_key = default_key

                if self.return_dict.get(section_name) is None:
                    self.return_dict[section_name] = {}

                value = None
                fill_type = None
                logger.info(f"[blue]  {section_name}, {section_key}")
                if section_name == "default" and os.getenv(section_key):
                    value = os.getenv(section_key)
                    fill_type = "set default section[env] "

                elif os.getenv(section_key):
                    value = os.getenv(f"{section_name}{self.section_separator}{section_key}")
                    fill_type = f"set {section_name} section[env] "

                elif self.return_dict[section_name].get(section_key, None) is None and default_value.get("default", "NULL") != "NULL":  # False 처리때문에
                    if default_value.get('type') == "function":
                        try:
                            value = execute_function(default_value['default'])
                        except Exception as e:
                            value = None
                            cprint(f"{default_value['default']} is not function , {e}", "red")

                    elif default_value.get('type') == "same_value":
                        [new_key, new_value] = default_value['default'].split(self.section_separator)
                        value = self.return_dict[new_key].get(new_value)
                    else:
                        value = self._convert_to_strict_type(value=default_value['default'], compare_type=default_value['type'])

                    fill_type = f"set {section_name} section[def] "

                if self.is_debug and fill_type:
                    cprint(f"{fill_type}::  {section_name}, {section_key}, {value}", "blue")

                if value or value is False or value == '' or value == 0:
                    self.return_dict[section_name][section_key] = self.assign_kv(f"{section_name}{self.section_separator}{section_key}", value)

    def _convert_to_strict_type(self, key=None, value=None, compare_type=None):

        if compare_type == "same_value" and key:
            compare_type = self.find_parent_type(key)

        if compare_type == "string":
            return_value = str(value)
        elif compare_type == "int":
            return_value = int(value)
        elif compare_type == "float":
            return_value = float(value)
            # return_value = round(value, 2)
        elif compare_type == "boolean":
            return_value = str2bool(value)
        elif compare_type == "array":
            return_value = [value.strip() for value in str(value).split(",")]
        elif compare_type == "list":
            return_value = [value.strip() for value in str(value).split(",")]
        elif compare_type == "url":
            if "http://" not in value and "https://" not in value:
                return_value = f"http://{value}"
            else:
                return_value = value
        elif compare_type == "function":
            try:
                return_value = execute_function(compare_type)
            except Exception as e:
                return_value = None
                pawn.console.debug(f"{compare_type} is not function , {e}", "red")
        else:
            return_value = value
        return return_value

    def assign_kv(self, key, value, section_name="default"):
        if self.default_schema.get(section_name):
            compare_struct = self.default_schema[section_name.lower()].get(key.lower())
        else:
            compare_struct = self.default_schema.get(key.lower())
        pawn.console.debug(f"compare_struct={compare_struct}, key={key}, value={value}")

        compare_type = None
        is_none = False
        origin_value = value
        if compare_struct:
            try:
                if isinstance(compare_struct, dict) and compare_struct.get("type"):
                    compare_type = compare_struct.get("type")
                else:
                    compare_type = compare_struct

                if value is None:
                    value = 0
                    is_none = True

                if self.use_env and os.getenv(key):
                    value = os.getenv(key)
                    if self.is_debug:
                        cprint(f"Environment variables have high priority => {key}={value} (None ? {is_none})", "green")

                return_value = self._convert_to_strict_type(key, value, compare_type=compare_type)

                if is_none:
                    return_value = compare_struct.get("default", "")

            except Exception as e:
                pawn.console.debug(f"[red]Invalid data type: key='{key}', value='{value}', required_type='{compare_type}', {e}")
                raise
        else:
            # cprint(f"cannot find default struct schema - {key}", "red")
            return_value = value

        if self.is_debug:
            if compare_struct:
                pawn.console.debug(f"[OK] key={key}, value={value} (origin:{origin_value}), type={type(return_value)}")
            else:
                pawn.console.debug(f"[red][NOT FOUND] key={key}, value={value} (origin:{origin_value}), type={type(return_value)}")
        return return_value

    # def return_type(self):
    def assign_dict(self, input_schema=None, default_schema=None, is_flatten=True, use_section=False, separator="_", section_separator="__"):

        if default_schema:
            self.default_schema = default_schema

        if input_schema:
            self.input_schema = input_schema

        self._lower_dict_keys()

        if isinstance(self.input_schema, dict):
            for key, value in self.input_schema.items():
                if use_section:
                    section_name, section_key = self._parse_section_name(key)
                    pawn.console.debug(f"section_name={section_name} ,key={section_key}, value={value}")
                    self.return_dict[section_name] = {}
                    if isinstance(value, dict):
                        for section_key, section_value in value.items():
                            assign_value = self.assign_kv(section_key, section_value, section_name=section_name)
                            pawn.console.debug(f"section_key={section_key}, section_value={section_value}, assign_value={type(assign_value)}")
                            self.return_dict[section_name][section_key] = self.assign_kv(section_key, section_value, section_name=section_name)
                    else:
                        self.return_dict[section_name][section_key] = self.assign_kv(section_key, value, section_name=section_name)
                else:
                    self.return_dict[key] = self.assign_kv(key, value)

            if use_section:
                self.fill_default()

        if is_flatten:
            return flatten_dict(self.return_dict, separator=separator)

        return self.return_dict

    def _parse_section_name(self, name=None):
        if self.section_separator in name:
            section_name, section_key = name.split(self.section_separator)
            return section_name, section_key

        return "default", name


def execute_function(module_func):
    """
    Run the specified function or method.

    :param module_func: The name of the function or method to be executed.
                        If the function is a method of a class, the format should be "module.class.method".
                        If the function is a top-level function, the format should be "module.function".
    :type module_func: str
    :return: The return value of the executed function or method.
    :rtype: any

    Example:

        .. code-block:: python

            # Execute a top-level function
            execute_function("os.getcwd")
            # >> '/Users/username'

            # Execute a method of a class
            execute_function("requests.Session.get")
            # >> <Response [200]>
    """

    if isinstance(module_func, str):
        if "." in module_func:
            [module_name, function_name] = module_func.split(".")
            # module = __import__(f"lib.{module_name}", fromlist=["lib", "..", "."])
            module = __import__(f"{module_name}")
            func = getattr(module, function_name)
            return func()
        return globals()[module_func]()
    else:
        return module_func()


def influxdb_metrics_dict(tags, measurement):
    """
    Default data set used by influxdb

    :param tags:
    :param measurement:
    :return:
    """
    return {
        "fields": {},
        "tags": tags,
        "measurement": measurement
    }


def metrics_key_push(data, key, tags, measurement):
    if data.get(key) is None:
        data[key] = influxdb_metrics_dict(tags=tags, measurement=measurement)
        data[key]['tags']['channel'] = key


def dict2influxdb_line(data):
    measurement = data.get("measurement")
    tags = ",".join(f"{replace_ignore_char(tag_key)}={replace_ignore_char(tag_value)}" for tag_key, tag_value in data.get('tags').items())
    fields = ",".join(
        f"{replace_ignore_char(fields_key)}={replace_ignore_char(fields_value)}" for fields_key, fields_value in data.get('fields').items())
    unixtime = data.get("time", "")
    return f"{measurement},{tags} {fields} {unixtime}".strip()


def rm_space(value, replace_str="_"):
    """
    Remove all spaces from the given value.
    InfluxDB does not allow spaces

    :param value: The value to remove spaces from.
    :type value: str or any
    :param replace_str: The string to replace the spaces with. Default is "_".
    :type replace_str: str
    :return: The value without spaces.
    :rtype: str or any

    Example:

        .. code-block:: python

            # Removing spaces from a string
            assert rm_space("hello world") == "hello_world"

            # Replacing spaces with a custom string
            assert rm_space("hello world", "-") == "hello-world"

            # Removing spaces from a non-string value
            assert rm_space(1234) == 1234

            # Removing spaces from an empty string
            assert rm_space("") == 0
    """
    if len(str(value)) == 0:
        return 0

    if isinstance(value, str):
        return value.replace(" ", replace_str).strip()
    return value


def replace_ignore_char(value, patterns=None, replace_str="_"):
    """
    Remove the ignoring character for adding to InfluxDB.

    :param value: A value to remove ignoring characters.
    :type value: str, float, or int
    :param patterns: A list of ignoring characters to remove. Default is [" ", ","].
    :type patterns: list
    :param replace_str: A string to replace the ignoring characters. Default is "_".
    :type replace_str: str
    :return: A value without ignoring characters.
    :rtype: str, float, or int

    Example:

        .. code-block:: python

            # example 1
            >>> replace_ignore_char("hello world")
            'hello_world'

            # example 2
            >>> replace_ignore_char("1,234.56")
            '1_234.56'

            # example 3
            >>> replace_ignore_char(1234)
            1234

    """
    if patterns is None:
        patterns = [" ", ","]

    if isinstance(value, float) or isinstance(value, int):
        return value

    if len(str(value)) == 0:
        return ""

    if isinstance(value, str):
        for replace_pattern in patterns:
            value = value.replace(replace_pattern, replace_str).strip()
    return value



# def replace_ignore_dict_kv(dict_data, pattern=None, replace_str="_"):
def replace_ignore_dict_kv(dict_data, *args, **kwargs):
    """

    Replaces a string of patterns in a dictionary.

    :param dict_data:
    :param args:
    :param kwargs:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter
            tags = {
                "aaaa___": "aaa",
                "vvvv ": "vvvv",
                " s sss": "12222"
            }

            print(converter.replace_ignore_dict_kv(dict_data=tags, patterns=["___"], replace_str=">"))

            #> {'aaaa>': 'aaa', 'vvvv': 'vvvv', 's sss': '12222'}


    """
    new_dict_data = {}
    for key, value in dict_data.items():
        if isinstance(key, str):
            new_key = replace_ignore_char(key, *args, **kwargs)
        else:
            new_key = key

        if isinstance(value, str):
            new_value = replace_ignore_char(value, *args, **kwargs)
        else:
            new_value = value
        new_dict_data[new_key] = new_value
    return new_dict_data


def influx_key_value(key_values: dict, sep: str = ",", operator: str = "="):
    """

    Convert the dictionary to influxdb's key=value format.

    :param key_values:
    :param sep:
    :param operator:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter
            tags = {
                "a": "value1",
                "b ": "value3",
                "c": "value4"
            }

            print(converter.influx_key_value(tags))

            # >> a=value1,b_=value3,c=value4

    """

    result = ""
    count = 0
    for key, value in key_values.items():
        count += 1
        key = key.replace(" ", "_").strip()
        value = value.replace(" ", "_").strip()
        result += f"{key}{operator}{value}"
        if count < len(key_values):
            result += sep
    return result


def extract_values_in_list(key: Any, list_of_dicts: list = []):
    """
    Extract the values from a list of dictionaries.

    :param key:
    :param list_of_dicts:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter
            sample_list = [
                {
                    "name": "John Doe",
                    "age": 30,
                    "height": 1.75,
                    "weight": 70,
                },{
                    "name": "John",
                    "age": 32,
                    "height": 1.71,
                    "weight": 71,
                }
            ]

            print(extract_values_in_list("age", sample_list))
            # [30, 32]

            print(extract_values_in_list("none_key", sample_list))
            # []

    """
    result = []
    if isinstance(list_of_dicts, list):
        for _dict in list_of_dicts:
            if _dict.get(key):
                result.append(_dict.get(key))
    return result


def split_every_n(data, n):
    """
     Split a list into sublists of length n.

     :param data: (list) The list to split.
     :param n: (int) The length of each sublist.
     :return: (list) A list of sublists.

     Example:

         .. code-block:: python

             data = [1, 2, 3, 4, 5, 6, 7, 8, 9]
             split_every_n(data, 3)
             # >> [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

             data = ['a', 'b', 'c', 'd', 'e', 'f']
             split_every_n(data, 2)
             # >> [['a', 'b'], ['c', 'd'], ['e', 'f']]
     """
    return [data[i:i + n] for i in range(0, len(data), n)]


def class_extract_attr_list(obj, attr_name="name"):
    """
    Extract a list of attributes from a list of objects or a single object.

    :param obj: A list of objects or a single object.
    :type obj: list or object
    :param attr_name: The name of the attribute to extract. Default is "name".
    :type attr_name: str
    :return: A list of attributes.
    :rtype: list

    Example:

        .. code-block:: python

            class Person:
                def __init__(self, name, age):
                    self.name = name
                    self.age = age

            people = [Person("Alice", 25), Person("Bob", 30), Person("Charlie", 35)]

            # Extract names from a list of objects
            names = class_extract_attr_list(people, "name")
            # >> ["Alice", "Bob", "Charlie"]

            # Extract age from a list of objects
            ages = class_extract_attr_list(people, "age")
            # >> [25, 30, 35]

            # Extract name from a single object
            name = class_extract_attr_list(Person("David", 40), "name")
            # >> "David"
    """
    if isinstance(obj, list):
        return_list = []
        for item in obj:
            return_list.append(getattr(item, attr_name))
        return return_list
    else:
        return getattr(obj, attr_name)


def append_zero(value):
    """
    Append zero to the value if it is less than 10.

    :param value: (int) The value to check.
    :return: (str) The value with zero appended if it is less than 10.

    Example:

        .. code-block:: python

            append_zero(5)
            # >> '05'

            append_zero(15)
            # >> 15
    """
    if value < 10:
        value = f"0{value}"
    return value


def append_suffix(text=None, suffix=None):
    """
     Append suffix to the end of the given text if it does not already end with the suffix.

     :param text: (str) The text to which the suffix will be appended.
     :param suffix: (str) The suffix to be appended to the text.
     :return: (str) The text with the suffix appended.

     Example:

         .. code-block:: python

             text = "example"
             suffix = "_test"
             append_suffix(text, suffix)
             # >> "example_test"

             text = "example_test"
             suffix = "_test"
             append_suffix(text, suffix)
             # >> "example_test"
     """
    if suffix and not text.endswith(suffix):
        return f"{text}{suffix}"
    return text


def append_prefix(text=None, prefix=None):
    """
     Add a prefix to the given text if it doesn't already start with the prefix.

     :param text: (str) The text to add prefix to.
     :param prefix: (str) The prefix to add to the text.
     :return: (str) The text with the prefix added.

     Example:

         .. code-block:: python

             text = "world"
             prefix = "hello_"
             append_prefix(text, prefix)
             # >> "hello_world"

             text = "hello_world"
             prefix = "hello_"
             append_prefix(text, prefix)
             # >> "hello_world"
     """
    if prefix and not text.startswith(prefix):
        return f"{prefix}{text}"
    return text


def camel_case_to_space_case(s):
    """
    Convert a camel case string to a space separated string.

    :param s: (str) The camel case string to convert.
    :return: (str) The space separated string.

    Example:

        .. code-block:: python

            print(camel_case_to_space_case("helloWorld"))
            # >> "hello world"

            print(camel_case_to_space_case("thisIsAReallyLongString"))
            # >> "this is a really long string"

    """
    if s == '':
        return s
    process_character = lambda c: (' ' + c.lower()) if c.isupper() else c
    return s[0] + ''.join(process_character(c) for c in s[1:])


def camelcase_to_underscore(name):
    """
    Convert camelCase string to underscore_case string.

    :param name: A string in camelCase format.
    :return: A string in underscore_case format.

    Example:

        .. code-block:: python

            camelcase_to_underscore("camelCaseString")
            # >> 'camel_case_string'

            camelcase_to_underscore("anotherExample")
            # >> 'another_example'

    """
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def lower_case(s):
    """
    Convert string to lower case.
    :param s:
    :return:

    Example:

         .. code-block:: python

            from pawnlib.typing import lower_case
            converter.lower_case('DDDDDDDDDDDDDDDD')
            # >> 'dddddddddddddddd'

    """
    return str(s).lower()


def upper_case(s):
    """
    Convert string to uppercase.

    :param s: string to convert
    :type s: str
    :return: uppercase string
    :rtype: str

    Example:

        .. code-block:: python

            print(upper_case("hello world"))
            # >> "HELLO WORLD"

            print(upper_case("Python"))
            # >> "PYTHON"

    """
    return str(s).upper()


def snake_case(s):
    """
    Convert a string to snake_case.

    :param s: (str) The string to convert.
    :return: (str) The snake_case version of the string.

    Example:

        .. code-block:: python

            snake_case("HelloWorld")
            # >> 'hello_world'

            snake_case("hello-world")
            # >> 'hello_world'

            snake_case("snake_case")
            # >> 'snake_case'

    """
    return '_'.join(
        re.sub('([A-Z][a-z]+)', r' \1',
               re.sub('([A-Z]+)', r' \1',
                      s.replace('-', ' '))).split()).lower()


def camel_case_to_lower_case(s):
    """
    Convert a string from camelcase to spacecase.

    :param s:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter
            converter.camel_case_to_lower_case('HelloWorld')
            # >> 'hello_world'

    """

    return re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', '_\\1', s). \
        lower().strip('_')


def lower_case_to_camel_case(s):
    """
    Convert a string from camelcase to spacecase.

    :param s:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter
            converter.lower_case_to_camel_case('HelloWorld')
            # >> 'HelloWorld'

    """

    s = s.capitalize()
    while '_' in s:
        head, tail = s.split('_', 1)
        s = head + tail.capitalize()
    return s


def camel_case_to_upper_case(s):
    """
    Convert a string from camelcase to spacecase.

    :param s:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter
            converter.camel_case_to_upper_case('HelloWorld')
            # >> 'HELLO_WORLD'

    """

    return camel_case_to_lower_case(s).upper()


def upper_case_to_camel_case(s):
    """
    Convert a string from camelcase to spacecase.

    :param s:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter
            converter.upper_case_to_camel_case('HelloWorld')
            # >> 'HelloWorld'

    """

    return lower_case_to_camel_case(s.lower())


def shorten_text(text="", width=None, placeholder='[...]', shorten_middle=False):
    """
    Shortens a text string to the specified width and placeholders.

    :param text: text to shorten
    :param width: maximum width of the string
    :param placeholder: placeholder string of the text
    :param shorten_middle: True if the text is to be shortened in the middle
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing.converter import truncate_float

            shorten_text("Hello, world!", width=5, placeholder='...')
            # >> "He...d!"

            shorten_text("Hello, world!", width=5, placeholder='...', shorten_middle=True)
            # >> "H...d!"

    """

    _text = str(text)
    if not width or not text:
        return text

    if shorten_middle and width == 1:
        return f"{_text[0]}{placeholder}"

    total_length = len(_text)
    max_length = total_length - len(placeholder)

    if _text and max_length >= width:
        if shorten_middle:
            half_width = width // 2
            return f"{_text[:half_width]}{placeholder}{_text[-half_width:]}"
        else:
            return f"{_text[:width]} {placeholder}"
    return text


# def shorten_text(text="", width=None, placeholder='[...]', shorten_middle=False):
#     """
#     Shortens a text string to the specified width and placeholders.
#
#     :param text: text to shorten
#     :param width: maximum width of the string
#     :param placeholder: placeholder string of the text
#     :param shorten_middle: True if the text is to be shortened in the middle
#     :return:
#
#     Example:
#
#         .. code-block:: python
#
#             shorten_text("Hello World", width=5, placeholder='...')
#             # >> "He..."
#
#             shorten_text("Hello World", width=10, placeholder='...', shorten_middle=True)
#             # >> "Hel...rld"
#
#     """
#     _text = str(text)
#     if not width or not text:
#         return text
#
#     if width <= len(placeholder):
#         return placeholder
#
#     if shorten_middle:
#         half_width = width // 2
#         return f"{_text[:half_width]}{placeholder}{_text[-half_width:width]}"
#     else:
#         return f"{_text[:width]}{placeholder}"

def truncate_float(number, digits=2) -> float:
    """
    Truncate a float to a specified number of decimal places.

    :param number: float number to be truncated.
    :param digits: number of decimal places to truncate to. Default is 2.
    :return: float truncated to the specified number of decimal places.

    Example:

        .. code-block:: python

            from pawnlib.typing.converter import truncate_float

            truncate_float(16.42413, 3)
            # >> 16.424

            truncate_float(-1.13034, 2)
            # >> -1.13

    """
    nb_decimals = len(str(number).split('.')[1])
    if nb_decimals <= digits:
        return number
    stepper = 10.00 ** digits
    return math.trunc(stepper * number) / stepper


def truncate_decimal(number, digits: int = 2) -> decimal.Decimal:
    """
    Truncate a decimal number to the specified number of decimal places without rounding.

    :param number: The decimal number to be truncated.
    :param digits: The number of decimal places to truncate the number to. Default is 2.
    :return: The truncated decimal number.

    Example:

        .. code-block:: python

            from pawnlib.typing.converter import truncate_decimal

            truncate_decimal(3.14159, 2)
            # >> 3.14

            truncate_decimal(3.14159, 4)
            # >> 3.1415

    """
    round_down_ctx = decimal.getcontext()
    round_down_ctx.rounding = decimal.ROUND_DOWN
    new_number = round_down_ctx.create_decimal(number)
    return round(new_number, digits)


def remove_zero(int_value):
    """
    Remove zero from the end of a float number if it's an integer.

    :param int_value: The value to remove zero from.
    :return: The value without trailing zero if it's a float number and is an integer, otherwise the original value.

    Example:

        .. code-block:: python

            remove_zero(5.0)
            # >> 5

            remove_zero(5.5)
            # >> 5.5

    """
    if isinstance(int_value, float) and int(int_value) == int_value:
        return int(int_value)
    return int_value


def remove_tags(text,
                case_sensitive: Literal["lower", "upper", "both"] = "lower",
                tag_style: Literal["angle", "square"] = "square") -> str:
    """
    Remove specific tags from given text based on case sensitivity and tag style options.

    :param text: The input text from which tags need to be removed.
    :param case_sensitive: The case sensitivity option for tags, default is "lower". Available options are "lower", "upper", and "both".
    :param tag_style: The tag style to be removed, default is "square". Available options are "angle" and "square".
    :return: The cleaned text after specific tags have been removed.

    Example:

        .. code-block:: python

            from pawnlib.typing.converter import remove_tags

            remove_tags("<b>Hello</b> [WORLD]", case_sensitive="both", tag_style="angle")
            # >> "Hello [WORLD]"

            remove_tags("<b>Hello</b> [WORLD]", case_sensitive="both", tag_style="square")
            # >> "<b>Hello</b> "

    """
    if case_sensitive == "lower":
        case_pattern = r'[a-z\s]'
    elif case_sensitive == "upper":
        case_pattern = r'[A-Z\s]'
    else:
        case_pattern = r'[\w\s]'

    if tag_style == "angle":
        tag_pattern = r'<(/?' + case_pattern + '+)>'
    else:
        tag_pattern = r'\[(?:/?' + case_pattern + '+)\]'
    cleaned_text = re.sub(tag_pattern, '', text)
    return cleaned_text

def remove_tags(text,
                case_sensitive: Literal["lower", "upper", "both"] = "lower",
                tag_style: Literal["angle", "square"] = "square") -> str:
    """
    Remove specific tags from given text based on case sensitivity and tag style options.

    :param text: The input text from which tags need to be removed.
    :param case_sensitive: The case sensitivity option for tags, default is "lower". Available options are "lower", "upper", and "both".
    :param tag_style: The tag style to be removed, default is "square". Available options are "angle" and "square".
    :return: The cleaned text after specific tags have been removed.
    """

    if case_sensitive == "lower":
        case_pattern = r'[a-z\s]'
    elif case_sensitive == "upper":
        case_pattern = r'[A-Z\s]'
    else:
        case_pattern = r'[A-Za-z\s]'

    if tag_style == "angle":
        tag_pattern = r'<(/?' + case_pattern + '+)>'
    else:
        tag_pattern = r'\[(?:/?' + case_pattern + '+)\]'

    cleaned_text = re.sub(tag_pattern, '', text)
    return cleaned_text


def remove_ascii_color_codes(text):
    """
    Remove ASCII color codes from a string.

    :param text: string to remove ASCII color codes from
    :return: string without ASCII color codes

    Example:

        .. code-block:: python

            from pawnlib.typing.converter import remove_ascii_color_codes

            remove_ascii_color_codes("\x1b[31mHello\x1b[0m")
            # >> "Hello"

    """
    return re.sub(r'\x1b\[\d+m', '', text)


def json_to_hexadecimal(json_value):
    """
    Encode a JSON value to a hexadecimal string.

    :param json_value: The JSON value to be encoded.
    :return: A hexadecimal string representation of the input JSON value.

    Example:

        .. code-block:: python

            json_value = {"name": "Alice", "age": 30}
            json_to_hexadecimal(json_value)
            # >> '0x7b226e616d65223a2022416c696365222c2022616765223a2033307d'

            json_value = [1, 2, 3, 4, 5]
            json_to_hexadecimal(json_value)
            # >> '0x5b312c20322c20332c20342c20355d'

    """
    json_string = json.dumps(json_value)
    json_bytes = json_string.encode('utf-8')
    hexadecimal_string = json_bytes.hex()
    return "0x" + hexadecimal_string


def hexadecimal_to_json(hexadecimal_string):
    """
    Decode a hexadecimal string to a JSON object.

    :param hexadecimal_string: A hexadecimal string to be decoded.
    :return: A JSON object decoded from the hexadecimal string.

    Example:

        .. code-block:: python

            decoded_json = hexadecimal_to_json("0x7b2268656c6c6f223a2022776f726c64227d")
            # >> {"hello": "world"}

            decoded_json = hexadecimal_to_json("7b2268656c6c6f223a2022776f726c64227d")
            # >> {"hello": "world"}

    """
    if hexadecimal_string.startswith("0x"):
        hexadecimal_string = hexadecimal_string[2:]
    hexadecimal_bytes = bytes.fromhex(hexadecimal_string)
    json_string = hexadecimal_bytes.decode('utf-8')
    return json.loads(json_string)


def format_hex(input_str):
    if input_str.startswith('0x'):
        return input_str
    elif input_str.startswith('0'):
        return '0x' + input_str[1:]
    else:
        return '0x' + input_str
