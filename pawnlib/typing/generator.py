"""Generators which yield an id to include in a JSON-RPC request."""
import sys
import os
import itertools
from random import choice
from string import ascii_lowercase, digits
from typing import Iterator, Union, Dict, Any, Tuple

from uuid import uuid4
import string
from pawnlib.typing.converter import UpdateType, replace_ignore_char, flatten_dict
import math
import random
import json

from functools import reduce, partial
from typing import Any, Dict, Iterator, Tuple, Union, Callable, Type
import binascii


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


class Counter:
    def __init__(self,
                 start: Union[float, int] = 1,
                 stop: Union[float, int] = 10,
                 count: Union[float, int] = 1,
                 convert_func: Union[Type[str], Type[int], Type[float]] = int):
        """
        Count up

        :param start:
        :param stop:
        :param count:
        :param convert_func:
        """
        self.start = start
        self.stop = stop
        self.count = count
        self.convert_func = convert_func

    def __iter__(self):
        return self

    def __str__(self):
        element_count = math.ceil((self.stop - self.start) / self.count)
        return f"<Counter> start={self.start}, stop={self.stop}, " \
               f"count={self.count}, " \
               f"element_count={element_count}, convert_func={self.convert_func}"

    def __next__(self):
        if self.start < self.stop:
            r = self.start
            self.start += self.count
            if isinstance(self.convert_func, type):
                return self.convert_func(r)
            return r
        else:
            raise StopIteration


class GenMultiMetrics:

    def __init__(self, tags, measurement, is_flatten=True, is_debug=False, structure_types=None, ignore_fields=None, uid=None):
        self.tags = tags
        self.measurement = measurement
        if uid is None:
            self.uid = id_generator()
        else:
            self.uid = uid
        self.is_flatten = is_flatten
        self.is_debug = is_debug
        self.structure_types = structure_types
        # if self.structure_types is None:
        #     self.structure_types = defines.default_structure
        self.update_type = UpdateType(structure_types=self.structure_types)
        self.ignore_fields = ignore_fields
        self.return_value = {}
        return

    def _set_default_metric(self):
        default_metric = {
            "measurement": self.measurement,
            # "tags": self.tags,
            "tags": {},
            "fields": {},
        }
        default_metric['tags'].update(self.tags)
        return default_metric

    def push(self, metric_key, key, value, tags=None):
        uid_key = f'{metric_key}_{self.uid}'
        key = replace_ignore_char(key)
        value = replace_ignore_char(value, replace_str="")

        if not value:
            value = 0

        if self.return_value.get(uid_key) is None:
            self.return_value[uid_key] = self._set_default_metric()
            if tags:
                self.return_value[uid_key]["tags"].update(tags)

        if self.ignore_fields is not None and key in self.ignore_fields:
            pass
        elif value or value == 0:
            if self.is_flatten and isinstance(value, dict):
                value = flatten_dict({key: value}, "_")
                self.return_value[uid_key]["fields"].update(value)
            else:
                value = self.update_type.assign_kv(key, value)
                if self.is_debug:
                    value = f"{value} ({type(value)})"
                self.return_value[uid_key]["fields"][key] = value

    def get(self):
        return list(self.return_value.values())


def generate_number_list(start=10000, count=100, convert_func=int):
    result = []
    end = start + count + 1
    for i in range(start, end):
        numbering = convert_func(i)
        result.append(numbering)
    return result


def id_generator(size=8, chars=string.ascii_uppercase + string.digits):
    """
    this function will be generated random id

    :param size:
    :param chars:
    :return:

    :Example

        .. code-block:: python

            # >> 00ZP5YRLRT1Y
    """
    return ''.join(random.choice(chars) for _ in range(size))


def uuid_generator(size: int = 8, count: int = 4, separator: str = "-"):
    """
    this function will be generated random uuid

    :param size:
    :param count:
    :param separator:
    :return:

    :Example

        .. code-block:: python

            # >> KFXSYSVJHPE6-83KZTPKY9NL3-ZHRFUV7QRWWJ-GRWVPB6C5SM8

    """
    return separator.join([id_generator(size) for i in range(count)])


def decimal(start: int = 1) -> Iterator[int]:
    """
    Increments from `start`.
    e.g. 1, 2, 3, .. 9, 10, 11, etc.

    :param start: start: The first value to start with.
    :return:
    """

    return itertools.count(start)


def hexadecimal(start: int = 1) -> Iterator[str]:
    """
    Incremental hexadecimal numbers.
    e.g. 1, 2, 3, .. 9, a, b, etc.

    :param start: The first value to start with.
    """

    while True:
        yield "%x" % start
        start += 1


# def random(length: int = 8, chars: str = digits + ascii_lowercase) -> Iterator[str]:
#     """
#     A random string.
#     Not unique, but has around 1 in a million chance of collision (with the default 8
#     character length).
#     Example:
#         'fubui5e6'
#     Args:
#         length: Length of the random string.
#         chars: The characters to randomly choose from.
#     """
#     while True:
#         yield "".join([choice(chars) for _ in range(length)])


def uuid() -> Iterator[str]:
    """
    Unique uuid ids.

    Example:

        '9bfe2c93-717e-4a45-b91b-55422c5af4ff'
    """
    while True:
        yield str(uuid4())


class Sentinel:
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"<{sys.intern(str(self.name)).rsplit('.', 1)[-1]}>"


# NOID = Sentinel("NoId")
# NOID = "sdsd"


def compose(*fs: Callable[..., Any]) -> Callable[..., Any]:
    def compose2(f: Callable[..., Any], g: Callable[..., Any]) -> Callable[..., Any]:
        return lambda *a, **kw: f(g(*a, **kw))
    return reduce(compose2, fs)


def request_pure(
        id_generator_func: Iterator[Any],
        method: str,
        params: Union[Dict[str, Any], Tuple[Any, ...]],
        id: Any,
) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "method": method,
        **(
            {"params": list(params) if isinstance(params, tuple) else params}
            if params
            else {}
        ),
        "id": id if id != "<NO_ID>" else next(id_generator_func),
    }


def request_impure(
        id_generator_func: Iterator[Any],
        method: str,
        params: Union[Dict[str, Any], Tuple[Any, ...], None] = None,
        id: Any = "<NO_ID>",
) -> Dict[str, Any]:
    return request_pure(
        id_generator_func or decimal(), method, params or (), id
    )


def json_rpc(
        method: str = "",
        params: Union[Dict[str, Any], Tuple[Any, ...], None] = None,
        id: Any = "<NO_ID>",
        dumps: bool = False,
):
    """

    :param method:
    :param params:
    :param id:
    :param dumps: to json string
    :return:


    Example:

        .. code-block:: python

            from pawnlib.typing import generator

            generator.json_rpc(method="icx_sendTransaction", params={"data": "ddddd"})
            # >  {'jsonrpc': '2.0', 'method': 'icx_sendTranscation', 'params': {'data': 'ddddd'}, 'id': 0}

            generator.json_rpc(method="icx_sendTransaction", params={"data": "ddddd"})
            # >  {'jsonrpc': '2.0', 'method': 'icx_sendTranscation', 'params': {'data': 'ddddd'}, 'id': 1}


    """

    if id != "<NO_ID>":
        pass
    else:
        id = increase_number(),

    if isinstance(id, tuple):
        id = id[0]

    return_dict = {
        "jsonrpc": "2.0",
        "method": method,
        **(
            {"params": list(params) if isinstance(params, tuple) else params}
            if params
            else {}
        ),
        "id": id
    }

    if dumps:
        return json.dumps(return_dict)

    return return_dict


def increase_number(c=itertools.count()):
    return next(c)


def increase_hex(c=itertools.count(), prefix="", zfill=0, remove_prefix=True):
    """

    Returns increase hex value
    :param c: itertools.count()
    :param prefix:
    :param zfill: adds zeros (0) at the beginning of the string, until it reaches the specified length.
    :param remove_prefix: remove prefix '0x' string
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import generator

            generator.increase_hex()
            >> '0'

            generator.increase_hex()
            >> '1'


    """
    if remove_prefix:
        return f"{prefix}{hex(next(c)).removeprefix('0x').zfill(zfill)}"
    else:
        return f"{prefix}{hex(next(c)).zfill(zfill)}"


def increase_token_address(c=itertools.count(), prefix="hx", zfill=40, remove_prefix=True):
    """

    Returns increase token address

    :param c: itertools.count()
    :param prefix: prefix address
    :param zfill: adds zeros (0) at the beginning of the string, until it reaches the specified length.
    :param remove_prefix: remove prefix '0x' string

    Example:

        .. code-block:: python

            from pawnlib.typing import generator

            generator.increase_address()
            >> 'hx0000000000000000000000000000000000000000'

            generator.increase_address()
            >> 'hx0000000000000000000000000000000000000001'


    """
    return increase_hex(c, prefix=prefix, zfill=zfill, remove_prefix=remove_prefix)


def random_token_address(prefix="hx", nbytes=20):
    """

    Return a random hx address for icon network

    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import generator

            generator.random_token_address()
            >>> 'hxa85cfbf976afba6fd5880c89372cf9f253c4a1c9'


    """
    return f"{prefix}{token_hex(nbytes)}"


def random_private_key(nbytes=32):
    """
    :return:
    """
    # key = b"-B\x99\x99...xedy" + os.urandom(18)
    bytes_key = os.urandom(nbytes)
    return bytes_key.hex()


def token_bytes(nbytes):
    """
    Return a random byte string containing *nbytes* bytes.
    If *nbytes* is ``None`` or not supplied, a reasonable
    default is used.

    :param nbytes:
    :return:


     Example:

        .. code-block:: python

            from pawnlib.typing import generator

            generator.token_bytes(16)
            >>> b'\\xebr\\x17D*t\\xae\\xd4\\xe3S\\xb6\\xe2\\xebP1\\x8b'

    """
    return os.urandom(nbytes)


def token_hex(nbytes):
    """

    Return a random text string, in hexadecimal.
    The string has *nbytes* random bytes, each byte converted to two
    hex digits.  If *nbytes* is ``None`` or not supplied, a reasonable
    default is used.

    :param nbytes:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import generator
            generator.token_hex(16)
            >>> 'f9bf78b9a18ce6d46a0cd2b0b86df9da'

    """

    return binascii.hexlify(token_bytes(nbytes)).decode('ascii')


request_natural = partial(request_impure, decimal())
generate_json_rpc = compose(json.dumps, request_natural)
