import random
import string
import os
import binascii
from termcolor import cprint
from typing import Union, Type
import math
from .check import *

from deprecated import deprecated

# from lib import defines
# def check_value_type(key, value):
#     if defines.default_structure.get(key) == "string":
#         return_value = str(value)
#     elif defines.default_structure.get(key) == "int":
#         return_value = int(value)
#     elif defines.default_structure.get(key) == "float":
#         return_value = float(value)
#         # return_value = round(value, 2)
#     elif defines.default_structure.get(key) == "boolean":
#         return_value = str2bool(value)
#     elif defines.default_structure.get(key) == "array":
#         return_value = str(value).split(",")
#     elif defines.default_structure.get(key) == "list":
#         return_value = str(value).split(",")
#     else:
#         return_value = value
#     return return_value

from typing import Union, Any

#https://pypi.org/project/Deprecated/
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
    # TINT_VALUE = 1000000000000000000
    TINT_VALUE = 10 ** 18
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

                if int_value >= TINT_VALUE:
                    int_value = int_value / TINT_VALUE
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


def convert_dict_hex_to_int(data: Any, is_comma: bool = False, debug: bool = False):
    """
    This function recursively converts hex to int.

    :param data:
    :param is_comma:
    :param debug:
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
                return_list.append(hex_to_number(value))
        return return_list

    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                return_data[key] = convert_dict_hex_to_int(value, is_comma, debug)
            elif isinstance(value, list):
                print(">>>> list")
                return_data[key] = convert_dict_hex_to_int(value, is_comma, debug)
            else:
                return_data[key] = hex_to_number(value)
    else:
        return_data = hex_to_number(data)
    return return_data


def hex_to_number(hex_value="", is_comma: bool = False, debug: bool = False):
    """
    this function will change the hex to number(int)
    :param hex_value:
    :param is_comma:
    :param debug:
    :return:
    """
    TINT_VALUE = 10 ** 18
    changed = False
    changed_text = "(org)"
    if is_int(hex_value):
        converted_value = int(hex_value)
        changed = True
    elif is_hex(hex_value):
        converted_value = int(hex_value, 16)
        changed = True
    else:
        converted_value = hex_value

    if changed:
        if converted_value >= TINT_VALUE:
            converted_value = converted_value / TINT_VALUE
            changed_text = "(tint)"

        if is_comma:
            converted_value = f"{converted_value:,}"
    else:
        changed_text = "(not changed)"

    if debug:
        if hex_value == converted_value:
            hex_value = ""
        return f"{converted_value} {changed_text} {hex_value}".strip()
    else:
        return converted_value


def get_size(file_path, attr=False):
    """
    Returns the size of the file.

    :param file_path:
    :param attr:
    :return:
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
    """

    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


# def str2bool(v) -> bool:
#     """
#     this function get the boolean type
#     :param v:
#     :return:
#     """
#     true_list = ("yes", "true", "t", "1", "True", "TRUE")
#     if type(v) == bool:
#         return v
#     if type(v) == str:
#         return v.lower() in true_list
#     return eval(f"{v}") in true_list


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


def dict_to_line(dict_param: dict, quotes: bool = False) -> str:
    """
    This function converts a dict to a line.


    :param dict_param:
    :param quotes:
    :return:

    Example:
        .. code-block:: python

            # >> {"a": "1234", "b": "1235"} => "a=1234,b=1235"
    """
    return_value = ""
    for k, v in sorted(dict_param.items()):
        if quotes:
            return_value += f"{k}=\"{v}\","
        else:
            return_value += f"{k}={v},"
    return return_value.rstrip(",")


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
        return_value += value
        if len(list_param) - 1 > idx:
            return_value += split_str
    return return_value


def long_to_bytes(val, endianness='big'):
    """

    Use :ref:`string formatting` and :func:`~binascii.unhexlify` to
    convert ``val``, a :func:`long`, to a byte :func:`str`.

    :param long val: The value to pack
    :param str endianness: The endianness of the result. ``'big'`` for
    big-endian, ``'little'`` for little-endian.
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


def ordereddict_to_dict(value):
    """
    Change the order of the keys in the dictionary.


    :param value:
    :return:
    """
    for k, v in value.items():
        if isinstance(v, dict):
            value[k] = ordereddict_to_dict(v)
            print(v)
    return dict(value)


class UpdateType:
    def __init__(self, is_debug=False, use_env=False, structure_types={}):
        # if structure_types is None:
        #     structure_types = default_structure
        self.return_value = ""
        self.return_dict = {}
        self.structure_types = structure_types
        self.is_debug = is_debug
        self.use_env = use_env
        return

    def find_parent_type(self, key):
        find_key = None
        for struct_key, struct_value in self.structure_types.items():
            if struct_key == key:
                find_key = struct_value.get('default')
        return self.structure_types[find_key]['type']

    def assign_kv(self, key, value):
        compare_struct = self.structure_types.get(key)
        # compare_type = self.structure_types.get(key)
        compare_type = None
        is_none = False

        orgin_value = value
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

            if compare_type == "same_value":
                compare_type = self.find_parent_type(key)

            if compare_type == "string":
                self.return_value = str(value)
            elif compare_type == "int":
                self.return_value = int(value)
            elif compare_type == "float":
                self.return_value = float(value)
            elif compare_type == "boolean":
                self.return_value = str2bool(value)
            elif compare_type == "list":
                self.return_value = [value.strip() for value in str(value).split(",")]
            elif compare_type == "url":
                if "http://" not in value and "https://" not in value:
                    self.return_value = f"http://{value}"
                else:
                    self.return_value = value
            else:
                self.return_value = value

            if is_none:
                self.return_value = compare_struct.get("default", "")

        except Exception as e:
            cprint(f"Invalid data type: key='{key}', value='{value}', required_type='{compare_type}', {e}", "red")
            raise

        if self.is_debug:
            cprint(f"key={key}, value={value} (origin:{orgin_value}), type={type(self.return_value)}", "yellow")
        return self.return_value

    # def return_type(self):

    def fill_default(self, section_separator="__"):
        for default_key, default_value in self.structure_types.items():
            if section_separator is not None and section_separator != "" and section_separator in default_key:
                [section_name, section_key] = default_key.split(section_separator)
            else:
                section_name = "default"
                section_key = default_key

            if self.return_dict.get(section_name) is None:
                self.return_dict[section_name] = {}

            value = None
            fill_type = None

            if section_name == "default" and os.getenv(section_key):
                value = os.getenv(section_key)
                fill_type = "set default section[env] "

            elif os.getenv(section_key):
                value = os.getenv(f"{section_name}{section_separator}{section_key}")
                fill_type = f"set {section_name} section[env] "

            elif self.return_dict[section_name].get(section_key, None) is None and default_value.get("default", "NULL") != "NULL": # False 처리때문에
                if default_value.get('type') == "function":
                    try:
                        value = execute_function(default_value['default'])
                    except:
                        value = None
                        cprint(f"{default_value['default']} is not function", "red")

                elif default_value.get('type') == "same_value":
                    [new_key, new_value] = default_value['default'].split(section_separator)
                    value = self.return_dict[new_key].get(new_value)
                else:
                    value = default_value['default']

                fill_type = f"set {section_name} section[def] "

            if self.is_debug and fill_type:
                cprint(f"{fill_type}::  {section_name}, {section_key}, {value}", "blue")

            if value or value is False or value == '' or value == 0:
                self.return_dict[section_name][section_key] = self.assign_kv(f"{section_name}{section_separator}{section_key}", value)

    def assign_dict(self, dict_obj, structure_types=None, is_flatten=True, use_section=False, separator="_", section_separator="__"):
        if structure_types:
            self.structure_types = structure_types
        elif self.structure_types:
            pass
        else:
            self.structure_types = defines.default_structure
        if isinstance(dict_obj, dict):
            for key, value in dict_obj.items():
                if use_section:
                    section_name = key
                    self.return_dict[section_name] = {}
                    for section_key, section_value in value.items():
                        self.return_dict[section_name][section_key] = self.assign_kv(f"{section_name}{section_separator}{section_key}", section_value)
                else:
                    self.return_dict[key] = self.assign_kv(key, value)

            if use_section:
                self.fill_default()

        if is_flatten:
            return flatten_dict(self.return_dict, separator=separator)

        return self.return_dict


def execute_function(module_func):
    """
    Run under the name of the module name of the module.

    :param module_func:
    :return:
    """
    if "." in module_func:
        [module_name, function_name] = module_func.split(".")
        # module = __import__(f"lib.{module_name}", fromlist=["lib", "..", "."])
        module = __import__(f"{module_name}")
        func = getattr(module, function_name)
        return func()
    return globals()[module_func]()


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
    remove the all space from value
    influxdb data not allowed space

    :param value:
    :param replace_str:
    :return:
    """
    if len(str(value)) == 0:
        return 0

    if isinstance(value, str):
        return value.replace(" ", replace_str).strip()
    return value


def replace_ignore_char(value, patterns=None, replace_str="_"):
    """
    Remove the ignoring character for add to InfluxDB

    :param value:
    :param patterns:
    :param replace_str:
    :return:
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


def split_every_n(data, n):
    return [data[i:i + n] for i in range(0, len(data), n)]


def class_extract_attr_list(obj, attr_name="name"):
    if isinstance(obj, list):
        return_list = []
        for item in obj:
            return_list.append(getattr(item, attr_name))
        return return_list
    else:
        return getattr(obj, attr_name)


def append_zero(value):
    if value < 10:
        value = f"0{value}"
    return value


def camel_case_to_space_case(s):
    """
    Convert a string from camelcase to spacecase.

    :param s:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.typing import converter
            converter.camelcase_to_underscore('HelloWorld')
            # >> 'Hello world'

    """

    if s == '': return s
    process_character = lambda c: (' ' + c.lower()) if c.isupper() else c
    return s[0] + ''.join(process_character(c) for c in s[1:])


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

