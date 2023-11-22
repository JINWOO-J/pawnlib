#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
import getpass
import traceback
import inspect
import executing
from contextlib import contextmanager, AbstractContextManager

from pawnlib.typing import converter, date_utils, list_to_oneline_string, const, is_include_list, remove_tags, remove_ascii_color_codes,timestamp_to_string, is_hex
from pawnlib.config import pawnlib_config as pawn, global_verbose
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import Terminal256Formatter
from rich.syntax import Syntax
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich import print as rprint
from typing import Union, Callable
from datetime import datetime
import textwrap
from requests.structures import CaseInsensitiveDict


_ATTRIBUTES = dict(
    list(zip([
        'bold',
        'dark',
        '',
        'underline',
        'blink',
        '',
        'reverse',
        'concealed'
    ],
        list(range(1, 9))
    ))
)
del _ATTRIBUTES['']

_HIGHLIGHTS = dict(
    list(zip([
        'on_grey',
        'on_red',
        'on_green',
        'on_yellow',
        'on_blue',
        'on_magenta',
        'on_cyan',
        'on_white'
    ],
        list(range(40, 48))
    ))
)

_COLORS = dict(
    list(zip([
        'grey',
        'red',
        'green',
        'yellow',
        'blue',
        'magenta',
        'cyan',
        'white',
    ],
        list(range(30, 38))
    ))
)

_RESET = '\033[0m'


def colored(text, color=None, on_color=None, attrs=None):
    """Colorize text.

    Available text colors:
        red, green, yellow, blue, magenta, cyan, white.

    Available text highlights:
        on_red, on_green, on_yellow, on_blue, on_magenta, on_cyan, on_white.

    Available _ATTRIBUTES:
        bold, dark, underline, blink, reverse, concealed.

    Example:
        colored('Hello, World!', 'red', 'on_grey', ['blue', 'blink'])
        colored('Hello, World!', 'green')
    """
    if os.getenv('ANSI_COLORS_DISABLED') is None:
        fmt_str = '\033[%dm%s'
        if color is not None:
            text = fmt_str % (_COLORS[color], text)

        if on_color is not None:
            text = fmt_str % (_HIGHLIGHTS[on_color], text)

        if attrs is not None:
            for attr in attrs:
                if attr is not None:
                    text = fmt_str % (_ATTRIBUTES[attr], text)

        text += _RESET
    return text


def cprint(text, color=None, on_color=None, attrs=None, **kwargs):
    """Print colorize text.
    It accepts arguments of print function.

    :param text:
    :param color:
    :param on_color:
    :param attrs:
    :param kwargs:
    :return:

    Example:
        .. code-block:: python

            cprint("message", "red")  # >>  message

    """

    print((colored(text, color, on_color, attrs)), **kwargs)


class bcolors:
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


class PrintRichTable:
    """

    Print a table using a rich.table module.

    :param title: Title of table
    :param data: Data of table
    :param columns: Columns of table. Print only column parameter values.
    :param with_idx: Print the row count.
    :param call_value_func: The row value must be a string. If you want to perform other tasks, please add the function name.
    :param call_desc_func: Invoke a function that describes the value.
    :param display_output: Determines whether to print output (default: True)
    :param justify: Alignment value of the console. (default: left)


    Example:

        .. code-block:: python

            from pawnlib.output.color_print import PrintRichTable

            data = [
                {
                    "address":         "1x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
                    "value":         399999999999999966445568,
                },
                {
                    "address":         "2x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
                    "value":         399999999999999966445568,
                },
                {
                    "address":         "3x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
                    "value":         399999999999999966445568,
                }
            ]

            PrintRichTable(title="RichTable", data=data)


            #                                    RichTable
            # ┏━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
            # ┃ idx ┃ address                                    ┃ value                    ┃
            # ┡━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
            # │ 0   │ 1x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08 │ 399999999999999966445568 │
            # ├─────┼────────────────────────────────────────────┼──────────────────────────┤
            # │ 1   │ 2x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08 │ 399999999999999966445568 │
            # ├─────┼────────────────────────────────────────────┼──────────────────────────┤
            # │ 2   │ 3x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08 │ 399999999999999966445568 │
            # └─────┴────────────────────────────────────────────┴──────────────────────────┘
            #
            # PrintRichTable(title="RichTable", data=data, columns=["address"])
            #
            #                               RichTable
            # ┏━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
            # ┃ idx ┃ address                                    ┃
            # ┡━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
            # │ 0   │ 1x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08 │
            # ├─────┼────────────────────────────────────────────┤
            # │ 1   │ 2x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08 │
            # ├─────┼────────────────────────────────────────────┤
            # │ 2   │ 3x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08 │
            # └─────┴────────────────────────────────────────────┘

    """

    def __init__(
            self,
            title: str = "",
            data: Union[dict, list] = None,
            columns: list = None,
            remove_columns: list = None,
            with_idx: bool = True,
            call_value_func=str,
            call_desc_func=None,
            columns_options=None,
            display_output=True,
            justify="left",
            **kwargs
    ) -> None:

        if columns is None:
            columns = list()
        if data is None:
            data = dict()
        self.title = f"[bold cyan] {title}"
        self.table_options = kwargs
        # self.table = Table(title=self.title, **kwargs)
        self.table = None
        self.data = data
        self.table_data = []
        self.columns = columns
        self.remove_columns = remove_columns
        self.rows = []
        self.row_count = 0
        self.with_idx = with_idx
        self.call_value_func = call_value_func
        self.call_desc_func = call_desc_func
        self.display_output = display_output
        self.console_justify = justify

        _default_columns_option = dict(
            key=dict(
                justify="left",
            ),
            value=dict(
                justify="right",
            ),
            description=dict(
                justify="right",
            ),
        )
        self.columns_options = _default_columns_option
        if columns_options:
            self.columns_options.update(columns_options)

        self._check_columns_options()
        self._initialize_table()
        self._set_table_data()
        self._print_table()

    def _check_columns_options(self):
        allowed_columns = ["header_style", "footer_style", "style", "justify", "vertical", "overflow", "width", "min_width", "max_width", "ratio",
                           "no_wrap"]
        for column_name, column_values in self.columns_options.items():
            if isinstance(column_values, dict):
                for column_key, value in column_values.items():
                    if column_key not in allowed_columns:
                        raise ValueError(f"name='{column_name}', key='{column_key}' is not allowed column option, allowed: {allowed_columns}")

    def _initialize_table(self):
        if isinstance(self.data, dict):
            self.table_data = self.data
            if not self.table_options.get('show_header'):
                self.table_options['show_header'] = False
            if self.table_options.get('show_lines', "NOT_DEFINED") == "NOT_DEFINED":
                self.table_options['show_lines'] = False

        elif isinstance(self.data, list):
            self.table_data = self.data
        else:
            self.table_data = []

        self.table = Table(title=self.title, **self.table_options)

    # def _specify_columns
    def _is_showing_columns(self, item):
        if len(self.columns) == 0:
            return True
        if item in self.columns:
            return True
        return False

    def _draw_vertical_table(self):
        pawn.console.debug("Drawing vertical table")
        if self.with_idx:
            self.table.add_column("idx", **self.columns_options.get('idx', {}))
        self.table.add_column("key", **self.columns_options.get('key', {}))
        self.table.add_column("value", **self.columns_options.get('value', {}))
        if self.call_desc_func and callable(self.call_desc_func):
            self.table.add_column("description", **self.columns_options.get('description', {}))

        _count = 0
        row_dict = {}
        for item, value in self.table_data.items():
            if self._is_showing_columns(item):
                row_dict[item] = value
                if callable(self.call_value_func):
                    value = self.call_value_func(value)

                columns = [f"{item}", f"{value}"]
                if self.with_idx:
                    columns.insert(0, f"{_count}")
                if self.call_desc_func and callable(self.call_desc_func):
                    columns.append(self.call_desc_func(*columns, **row_dict))

                self.table.add_row(*columns)
                _count += 1

    def _draw_horizontal_table(self):
        pawn.console.debug("Drawing horizontal table")
        for item in self.table_data:
            if isinstance(item, dict):
                line_row = []
                row_dict = {}
                for column in self.columns:
                    if self.with_idx and column == "idx":
                        value = str(self.row_count)
                    elif column == "desc":
                        value = self.call_desc_func(*line_row, **row_dict)
                    else:
                        try:
                            value = self.call_value_func(item.get(column), **{column: item.get(column)})
                        except Exception:
                            value = self.call_value_func(item.get(column))
                    row_dict[column] = value
                    line_row.append(value)
                self.rows.append(line_row)
            else:
                self.rows.append([f"{self.row_count}", f"{item}"])
            self.row_count += 1

        for col in self.columns:
            self.table.add_column(col, **self.columns_options.get(col, {}))

    def _extract_columns(self):
        # if self.table_data and len(self.columns) == 0 and isinstance(self.table_data[0], dict):
        if self.table_data and len(self.columns) == 0:
            try:
                self.columns = list(self.table_data[0].keys())
            except Exception as e:
                self.columns = ["value"]
        if self.with_idx:
            self.columns.insert(0, "idx")
        if callable(self.call_desc_func):
            self.columns.append("desc")

        if self.columns and isinstance(self.remove_columns, list):
            for r_column in self.remove_columns:
                self.columns.remove(r_column)

    def _set_table_data(self):
        if isinstance(self.table_data, list):
            self._extract_columns()
            self._draw_horizontal_table()
        elif isinstance(self.table_data, dict):
            self._draw_vertical_table()

    def _print_table(self):
        for row in self.rows:
            self.table.add_row(*row)

        if self.display_output:
            if self.table.columns:
                pawn.console.print(self.table, justify=self.console_justify)
            else:
                pawn.console.print(f"{self.title} \n  [i]No data ... [/i]")
        else:
            return self.table

class TablePrinter(object):
    "Print a list of dicts as a table"

    def __init__(self, fmt=[], sep='  ', ul="-"):
        """

        :param fmt: list of tuple(heading, key, width)

                    heading: str, column label \n
                    key: dictionary key to value to print \n
                    width: int, column width in chars \n

        :param sep: string, separation between columns
        :param ul: string, character to underline column label, or None for no underlining

        Example:
            .. code-block:: python

                from pawnlib import output

                data = [
                    {
                        "address":         "1x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
                        "value":         399999999999999966445568,
                    },
                    {
                        "address":         "2x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
                        "value":         399999999999999966445568,
                    },
                    {
                        "address":         "3x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08",
                        "value":         399999999999999966445568,
                    },

                ]
                fmt = [
                    ('address',       'address',          10),
                    ('value',       'value',          15)
                ]
                cprint("Print Table", "white")
                print(output.TablePrinter(fmt=fmt)(data))
                print(output.TablePrinter()(data))

                 address         value
                ----------  ---------------
                1x038bd14d  399999999999999
                2x038bd14d  399999999999999
                3x038bd14d  399999999999999


        """
        super(TablePrinter, self).__init__()
        self._params = {"sep": sep, "ul": ul}

        self.fmt = str(sep).join('{lb}{0}:{1}{rb}'.format(key, width, lb='{', rb='}') for heading, key, width in fmt)
        self.head = {key: heading for heading, key, width in fmt}
        self.ul = {key: str(ul) * width for heading, key, width in fmt} if ul else None
        self.width = {key: width for heading, key, width in fmt}
        self.data_column = []

    def row(self, data, head=False):
        if head:
            return self.fmt.format(**{k: get_bcolors(data.get(k), "WHITE", bold=True, width=w) for k, w in self.width.items()})
        else:
            return self.fmt.format(**{k: str(data.get(k, ''))[:w] for k, w in self.width.items()})

    def get_unique_columns(self):
        self.data_column = []
        for item in self.data:
            self.data_column = self.data_column + list(item.keys())

        self.data_column = list(set(self.data_column))
        self.data_column.sort()

    def __call__(self, data_list):
        if len(self.fmt) == 0:
            sep = self._params.get("sep")
            ul = self._params.get("ul")

            self.data = data_list
            self.get_unique_columns()

            fmt = self.data_column

            width = 12
            self.fmt = str(sep).join('{lb}{0}:{1}{rb}'.format(key, width, lb='{', rb='}') for key in fmt)
            self.width = {key: width for key in fmt}
            self.ul = {key: str(ul) * width for key in fmt} if ul else None
            self.head = {key: key for key in fmt}

        _r = self.row
        res = [_r(data) for data in data_list]
        res.insert(0, _r(self.head, head=True))
        if self.ul:
            res.insert(1, _r(self.ul))
        return '\n'.join(res)


def get_bcolors(text, color, bold=False, underline=False, width=None):
    """

    Returns the color from the bcolors object.

    :param text:
    :param color:
    :param bold:
    :param underline:
    :param width:
    :return:
    """
    if width and len(text) <= width:
        text = text.center(width, ' ')
    return_text = f"{getattr(bcolors, color)}{text}{bcolors.ENDC}"
    if bold:
        return_text = f"{bcolors.BOLD}{return_text}"
    if underline:
        return_text = f"{bcolors.UNDERLINE}{return_text}"
    return str(return_text)


def colored_input(message, password=False, color="WHITE"):
    input_message = get_bcolors(text=message, color=color, bold=True, underline=True) + " "
    if password:
        return getpass.getpass(input_message)
    return input(input_message)


def get_colorful_object(v):
    if type(v) == bool:
        value = f"{bcolors.ITALIC}"
        if v is True:
            value += f"{bcolors.GREEN}"
        else:
            value += f"{bcolors.FAIL}"
        value += f"{str(v)}{bcolors.ENDC}"
    elif type(v) == int or type(v) == float:
        value = f"{bcolors.CYAN}{str(v)}{bcolors.ENDC}"
    elif type(v) == str:
        value = f"{bcolors.WARNING}'{str(v)}'{bcolors.ENDC}"
    elif v is None:
        value = f"{bcolors.FAIL}{str(v)}{bcolors.ENDC}"
    else:
        value = f"{v}"
    return value


def dump(obj, nested_level=0, output=sys.stdout, hex_to_int=False, debug=True, _is_list=False, _last_key=None, is_compact=False):
    """
    Print a variable for debugging.

    :param obj:
    :param nested_level:
    :param output:
    :param hex_to_int:
    :param debug:
    :param _is_list:
    :param _last_key:
    :param is_compact:
    :return:
    """
    spacing = '   '
    def_spacing = '   '
    format_number = lambda n: n if n % 1 else int(n)

    ignore_keys = ["Hash"]

    if type(obj) == dict:
        if nested_level == 0 or _is_list:
            print('%s{' % (def_spacing + (nested_level) * spacing))
        else:
            print("{")

        for k, v in obj.items():
            if hasattr(v, '__iter__'):
                print(bcolors.OKGREEN + '%s%s: ' % (def_spacing + (nested_level + 1) * spacing, k) + bcolors.ENDC, end="")
                dump(v, nested_level + 1, output, hex_to_int, debug, _last_key=k, is_compact=is_compact)
            else:
                if debug:
                    v = f"{get_colorful_object(v)} {bcolors.HEADER} {str(type(v)):>20}{bcolors.ENDC}{bcolors.DARK_GREY} len={len(str(v))}{bcolors.ENDC}"
                print(bcolors.OKGREEN + '%s%s:' % (def_spacing + (nested_level + 1) * spacing, k) + bcolors.WARNING + ' %s ' % v + bcolors.ENDC,
                      file=output)
        print('%s}' % (def_spacing + nested_level * spacing), file=output)
    elif type(obj) == list:
        if is_compact:
            end = ' '
        else:
            end = '\n'

        print('%s[' % (def_spacing + (nested_level) * spacing), file=output, end=end)
        for v in obj:
            if hasattr(v, '__iter__'):
                dump(v, nested_level + 1, output, hex_to_int, debug, _is_list=True, is_compact=is_compact)
            else:
                if is_compact:
                    spacing = ""
                    def_spacing = ''
                    end = ', '
                else:
                    end = '\n'
                # print(bcolors.WARNING + '%s%s' % (def_spacing + (nested_level + 1) * spacing, get_colorful_object(v)) + bcolors.ENDC, file=output)
                print(bcolors.WARNING + '%s%s' % (def_spacing + (nested_level + 1) * spacing, get_colorful_object(v)) + bcolors.ENDC, file=output,
                      end=end)
        print('%s]' % (def_spacing + (nested_level) * spacing), file=output)
    else:
        if debug:
            converted_hex = ""

            if hex_to_int and converter.is_hex(obj) and not is_include_list(target=_last_key, include_list=ignore_keys, ignore_case=False):
                if _last_key == "timestamp":
                    t_value = round(int(obj, 16) / 1_000_000)
                    converted_str = f"(from {_last_key})"
                    converted_date = datetime.fromtimestamp(format_number(t_value)).strftime('%Y-%m-%d %H:%M:%S')
                    converted_hex = f"{converted_date} {converted_str}"

                elif isinstance(obj, str) and len(obj) >= 60:
                    pass
                else:
                    if len(obj) < 14:
                        TINT = 1
                        TINT_STR = ""
                    else:
                        TINT = const.TINT
                        TINT_STR = f"(from TINT) {_last_key}"

                    converted_float = format_number(round(int(obj, 16) / TINT, 4))
                    converted_hex = f"{converted_float:,} {TINT_STR}"

            obj = f"{get_colorful_object(obj)}  " \
                  f"{bcolors.ITALIC}{bcolors.LIGHT_GREY}{converted_hex}{bcolors.ENDC}" \
                  f"{bcolors.HEADER} {str(type(obj)):>20}{bcolors.ENDC}" \
                  f"{bcolors.DARK_GREY} len={len(str(obj))}{bcolors.ENDC}"
        print(bcolors.WARNING + '%s%s' % (def_spacing + nested_level * spacing, obj) + bcolors.ENDC)


# def dump(obj, nested_level=1, output=sys.stdout, hex_to_int=False, debug=True, _last_key=None, is_compact=False):
#     """
#     Print a variable for debugging.
#
#     :param obj:
#     :param nested_level:
#     :param output:
#     :param hex_to_int:
#     :param debug:
#     :param _last_key:
#     :param is_compact:
#     :return:
#     """
#     if isinstance(obj, (dict, list)):
#         _print_iterable(obj, nested_level, output, hex_to_int, debug, _last_key, is_compact)
#     else:
#         _print_value(obj, '   ' * nested_level, _last_key, hex_to_int, debug)
#
#
# def _print_iterable(obj, nested_level, output, hex_to_int, debug, _last_key, is_compact):
#     spacing = '   ' * nested_level
#     print(f"{spacing}{'{' if isinstance(obj, dict) else '['}", end=("" if is_compact and isinstance(obj, list) else "\n"))
#     for k, v in (obj.items() if isinstance(obj, dict) else enumerate(obj)):
#         if isinstance(obj, dict):
#             print(f"{spacing}   {bcolors.OKGREEN}{k}: {bcolors.ENDC}", end="")
#         if isinstance(v, (dict, list)):
#             dump(v, nested_level + 1, output, hex_to_int, debug, _last_key=(k if isinstance(obj, dict) else _last_key), is_compact=is_compact)
#         else:
#             _print_value(v, spacing + '   ', (k if isinstance(obj, dict) else _last_key), hex_to_int, debug)
#         if is_compact and isinstance(obj, list):
#             print(", ", end="")
#     print(f"{' ' if is_compact and isinstance(obj, list) else spacing}{'}' if isinstance(obj, dict) else ']'}", end=("" if is_compact and isinstance(obj, list) else "\n"), file=output)
#
#
# def _print_value(v, spacing, _last_key, hex_to_int, debug):
#     output_value = _process_value(v, _last_key, hex_to_int)
#     if debug:
#         output_value += f" {bcolors.HEADER} {str(type(v)):>20}{bcolors.ENDC}{bcolors.DARK_GREY} len={len(str(v))}{bcolors.ENDC}"
#     print(f"{bcolors.WARNING}{spacing}{output_value}{bcolors.ENDC}")
#
#
# def _process_value(value, _last_key=None, hex_to_int=False):
#     _convert_based_key_dict = {
#         "time_stamp": timestamp_to_string
#     }
#
#     if hex_to_int and is_hex(value) and _last_key is not None:
#         return f"'{value}' {_process_hex(value, _last_key)}"
#     elif _convert_based_key_dict.get(_last_key):
#         _function = _convert_based_key_dict.get(_last_key)
#         return f"{get_colorful_object(value)}\t{_function(value)} (from {_last_key})"
#     else:
#         return get_colorful_object(value)
#
#
# def _process_hex(obj, _last_key):
#     format_number = lambda n: n if n % 1 else int(n)
#     if _last_key == "timestamp":
#         t_value = round(int(obj, 16) / 1_000_000)
#         converted_date = datetime.fromtimestamp(format_number(t_value)).strftime('%Y-%m-%d %H:%M:%S')
#         return f" {bcolors.ITALIC}{bcolors.LIGHT_GREY}{converted_date} (from {_last_key}){bcolors.ENDC}"
#     elif isinstance(obj, str) and len(obj) < 60:
#         TINT = 1 if len(obj) < 14 else 10 ** 18
#         TINT_STR = "" if len(obj) < 14 else f"(from TINT) {_last_key}"
#         converted_float = format_number(round(int(obj, 16) / TINT, 4))
#         return f" {bcolors.ITALIC}{bcolors.LIGHT_GREY}{converted_float:,} {TINT_STR}{bcolors.ENDC}"
#     else:
#         return ""


def debug_print(text, color="green", on_color=None, attrs=None, view_time=True, **kwargs):
    """Print colorize text.

    It accepts arguments of print function.
    """
    module_name = ''
    stack = inspect.stack()
    parent_frame = stack[1][0]
    module = inspect.getmodule(parent_frame)
    if module:
        module_pieces = module.__name__.split('.')
        module_name = list_to_oneline_string(module_pieces)
    function_name = stack[1][3]
    full_module_name = f"{module_name}.{function_name}({stack[1].lineno})"

    module_text = ""
    time_text = ""
    try:
        module_text = get_bcolors(f"[{full_module_name:<25}]", "WARNING")
    except:
        pass

    if view_time:
        time_text = "[" + get_bcolors(f"{date_utils.todaydate('log')}", "WHITE") + "]"
    main_text = (colored(str(text), color, on_color, attrs))
    print(f"{time_text}{module_text} {main_text}", **kwargs)


def classdump(obj):
    """
    For debugging, Print the properties of the class are shown.
    :param obj:
    :return:
    """
    for attr in dir(obj):
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            print(bcolors.OKGREEN + f"obj.{attr} = " + bcolors.WARNING + f"{value}" + bcolors.ENDC)


def kvPrint(key, value):
    """
    print the  {key: value} format.

    :param key:
    :param value:
    :return:
    """
    key_width = 9
    key_value = 3
    print(bcolors.OKGREEN + "{:>{key_width}} : ".format(key, key_width=key_width) + bcolors.ENDC, end="")
    print(bcolors.WARNING + "{:>{key_value}} ".format(str(value), key_value=key_value) + bcolors.ENDC)


def print_json(obj, syntax=True, line_indent="", style="material",  **kwargs):
    """
    Print a JSON object with optional syntax highlighting and indentation.

    :param obj: The JSON object to print.
    :param syntax: Whether to use syntax highlighting (default: True).
    :param line_indent: The indentation for each line (default: "").
    :param style: Style for syntax highlighting (default: "material")
    :param kwargs: Additional keyword arguments for json.dumps().

    Example:

        .. code-block:: python

            data = {
                "name": "John",
                "age": 30,
                "city": "New York"
            }

            print_json(data)
            # >> {
            # >>     "name": "John",
            # >>     "age": 30,
            # >>     "city": "New York"
            # >> }

            print_json(data, syntax=False)
            # >> {"name": "John", "age": 30, "city": "New York"}

    """
    print(pretty_json(obj, syntax=syntax, line_indent=line_indent, style=style, **kwargs))


def pretty_json(obj, syntax=True, rich_syntax=False, style="one-dark", line_indent="", **kwargs):
    """
      Return a prettified JSON string with optional syntax highlighting.

      :param obj: JSON object to prettify
      :param syntax: If True, apply syntax highlighting (default: True)
      :param rich_syntax: If True, use rich library for syntax highlighting (default: False)
      :param style: Style name for syntax highlighting (default: "one-dark")
      :param line_indent: Custom line indentation (default: "")
      :param kwargs: Additional keyword arguments for json.dumps

      Example:

          .. code-block:: python

              data = {"name": "John", "age": 30, "city": "New York"}
              print(pretty_json(data))
              # {
              #     "name": "John",
              #     "age": 30,
              #     "city": "New York"
              # }

              print(pretty_json(data, syntax=False))
              # {"name": "John", "age": 30, "city": "New York"}

      """

    if syntax and isinstance(kwargs, dict):
        kwargs.setdefault("indent", 4)
        line_indent = " " * 4 if not line_indent else line_indent

    def json_to_string(_obj):
        if isinstance(_obj, str):
            _obj = json.loads(_obj)

        if isinstance(_obj, (dict, list)):
            return json.dumps(_obj, **kwargs)
        else:
            return _obj

    json_string = json_to_string(obj).strip()

    if syntax:
        if rich_syntax:
            return Syntax(json_string, "json", line_numbers=False, theme=style)
        else:
            return syntax_highlight(json_string, name="json", line_indent=line_indent, style=style).strip()
    else:
        return json_string


def debug_logging(message, dump_message=None):
    """
    print debug_logging

    :param message:
    :param dump_message:
    :return:

    Example:

        .. code-block:: python

            from pawnlib import output

            output.debug_logging("message")

            [2022-07-25 16:35:15.105][DBG][/Users/jinwoo/work/python_prj/pawnlib/examples/asyncio/./run_async.py main(33)] : message

    """
    stack = traceback.extract_stack()
    filename, code_line, func_name, text = stack[-2]

    def_msg = f"[{date_utils.todaydate('log')}][DBG][{filename} {func_name}({code_line})]"
    kvPrint(def_msg, message)
    if dump_message:
        dump(dump_message)


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, bar_length=100, overlay=True):
    """
    Print progress bar

    :param iteration:
    :param total:
    :param prefix:
    :param suffix:
    :param decimals:
    :param bar_length:
    :param overlay:
    :return:

    Example:

        .. code-block:: python

            from pawnlib import output

            for i in range(1, 100):
                time.sleep(0.05)
                output.print_progress_bar(i, total=100, prefix="start", suffix="suffix")

            # >> start |\#\#\#\#\#\#\#\| 100.0% suffix

    """
    iteration = iteration + 1
    format_str = "{0:." + str(decimals) + "f}"
    percent = format_str.format(100 * (iteration / float(total)))
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = '#' * filled_length + '-' * (bar_length - filled_length)

    if overlay:
        sys.stdout.write("\033[F")  # back to previous line
        sys.stdout.write("\033[K")  # clear line
    sys.stdout.write('%s |%s| %s%s %s \n' %
                     (prefix, bar, percent, '%', suffix)),

    if iteration == total:
        sys.stdout.write('\n')


def _patched_make_iterencode(markers, _default, _encoder, _indent, _floatstr,
                             _key_separator, _item_separator, _sort_keys, _skipkeys, _one_shot,
                             ## HACK: hand-optimized bytecode; turn globals into locals
                             ValueError=ValueError,
                             dict=dict,
                             float=float,
                             id=id,
                             int=int,
                             isinstance=isinstance,
                             list=list,
                             str=str,
                             tuple=tuple,
                             _intstr=int.__repr__,
                             ):
    if _indent is not None and not isinstance(_indent, str):
        _indent = ' ' * _indent

    def _iterencode_list(lst, _current_indent_level):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        buf = '['
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + _indent * _current_indent_level
            # separator = _item_separator + newline_indent
            separator = ", "
            buf += newline_indent

        else:
            newline_indent = None
            separator = _item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf = separator
            if isinstance(value, str):
                yield buf + _encoder(value)
            elif value is None:
                yield buf + 'null'
            elif value is True:
                yield buf + 'true'
            elif value is False:
                yield buf + 'false'
            elif isinstance(value, int):
                # Subclasses of int/float may override __repr__, but we still
                # want to encode them as integers/floats in JSON. One example
                # within the standard library is IntEnum.
                yield buf + _intstr(value)
            elif isinstance(value, float):
                # see comment above for int
                yield buf + _floatstr(value)
            else:
                yield buf
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):

                    chunks = _iterencode_dict(value, _current_indent_level)

                else:
                    chunks = _iterencode(value, _current_indent_level)
                yield from chunks
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + _indent * _current_indent_level
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(dct, _current_indent_level):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + _indent * _current_indent_level
            item_separator = _item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = _item_separator
        first = True
        if _sort_keys:
            items = sorted(dct.items())
        else:
            items = dct.items()
        for key, value in items:
            if isinstance(key, str):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                # see comment for int/float in _make_iterencode
                key = _floatstr(key)
            elif key is True:
                key = 'true'
            elif key is False:
                key = 'false'
            elif key is None:
                key = 'null'
            elif isinstance(key, int):
                # see comment for int/float in _make_iterencode
                key = _intstr(key)
            elif _skipkeys:
                continue
            else:
                raise TypeError(f'keys must be str, int, float, bool or None, '
                                f'not {key.__class__.__name__}')
            if first:
                first = False
            else:
                yield item_separator
            yield _encoder(key)
            yield _key_separator
            if isinstance(value, str):
                yield _encoder(value)
            elif value is None:
                yield 'null'
            elif value is True:
                yield 'true'
            elif value is False:
                yield 'false'
            elif isinstance(value, int):
                # see comment for int/float in _make_iterencode
                yield _intstr(value)
            elif isinstance(value, float):
                # see comment for int/float in _make_iterencode
                yield _floatstr(value)
            else:
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                yield from chunks
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + _indent * _current_indent_level
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(o, _current_indent_level):
        if isinstance(o, str):
            yield _encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, int):
            # see comment for int/float in _make_iterencode
            yield _intstr(o)
        elif isinstance(o, float):
            # see comment for int/float in _make_iterencode
            yield _floatstr(o)
        elif isinstance(o, (list, tuple)):
            yield from _iterencode_list(o, _current_indent_level)

        elif isinstance(o, dict):
            yield from _iterencode_dict(o, _current_indent_level)
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            o = _default(o)
            yield from _iterencode(o, _current_indent_level)
            if markers is not None:
                del markers[markerid]

    return _iterencode


def json_compact_dumps(data, indent=4, monkey_patch=True):
    if monkey_patch:
        json.encoder._make_iterencode = _patched_make_iterencode
    return json.dumps(data, indent=indent)


class NoIndent(object):
    """ Value wrapper. """

    def __init__(self, value):
        self.value = value


class NoListIndentEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        # Save copy of any keyword argument values needed for use here.
        super(NoListIndentEncoder, self).__init__(*args, **kwargs)

    def iterencode(self, o, _one_shot=False):
        list_lvl = 0
        for s in super(NoListIndentEncoder, self).iterencode(o, _one_shot=_one_shot):
            if s.startswith('['):
                list_lvl += 1
                s = s.replace('\n', '').rstrip()
                s = s.replace(' ', '')
            elif 0 < list_lvl:
                s = s.replace('\n', '').rstrip()
                s = s.replace(' ', '')
                if s and s[-1] == ',':
                    s = s[:-1] + self.item_separator
                elif s and s[-1] == ':':
                    s = s[:-1] + self.key_separator
            if s.endswith(']'):
                list_lvl -= 1
            s = s.replace(",", ", ")
            yield s


class ProgressTime(Progress):
    def __init__(self, **kwargs):
        if kwargs.get('transient', "__NOT_DEFINED__") == "__NOT_DEFINED__":
            kwargs['transient'] = True

        super().__init__(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=pawn.console,
            **kwargs
        )


def print_syntax(data, name="json", indent=4, style="material", oneline_list=True, line_indent='', rich=True, **kwargs):
    """
    Print the syntax of the data.

    :param data: The data to print.
    :param name: The name of the syntax. Default is "json".
    :param indent: The number of spaces for indentation. Default is 4.
    :param style: The style of the syntax. Default is "material".
    :param oneline_list: Whether to print the list in one line. Default is True.
    :param line_indent: The indentation for each line. Default is ''.
    :param rich: Whether to use rich for printing. Default is True.
    :param kwargs: Other keyword arguments.

    Example:

        .. code-block:: python

            data = {"name": "John", "age": 30, "city": "New York"}
            print_syntax(data)
            # >> {
            # >>     "name": "John",
            # >>     "age": 30,
            # >>     "city": "New York"
            # >> }

            print_syntax(data, name="xml", style="monokai", rich=False)
            # >> <name>John</name>
            # >> <age>30</age>
            # >> <city>New York</city>

    """
    if rich:
        _syntax = syntax_highlight(data, name=name, style=style, rich=True, **kwargs)
        rprint(_syntax)
    else:
        print(syntax_highlight(data, name, indent, style, oneline_list, line_indent))



def syntax_highlight(data, name="json", indent=4, style="material", oneline_list=True, line_indent='', rich=False, **kwargs):
    """
    Syntax highlighting function

    :param data:
    :param name:
    :param indent:
    :param style:
    :param oneline_list:
    :param line_indent:
    :param rich:
    :return:

    Example:

        .. code-block:: python

            from pawnlib import output

            print(output.syntax_highlight("<html><head><meta name='viewport' content='width'>", "html", style=style))

    """
    # styles available as of pygments 2.8.1.
    # ['default', 'emacs', 'friendly', 'colorful', 'autumn', 'murphy', 'manni',
    # 'material', 'monokai', 'perldoc', 'pastie', 'borland', 'trac', 'native',
    # 'fruity', 'bw', 'vim', 'vs', 'tango', 'rrt', 'xcode', 'igor', 'paraiso-light',
    # 'paraiso-dark', 'lovelace', 'algol', 'algol_nu', 'arduino', 'rainbow_dash',
    # 'abap', 'solarized-dark', 'solarized-light', 'sas', 'stata', 'stata-light',
    # 'stata-dark', 'inkpot', 'zenburn']
    if name == "json" and isinstance(data, (dict, list)):
        data = data_clean(data)
        code_data = json_compact_dumps(data, indent=indent, monkey_patch=oneline_list)
    elif data:
        code_data = data
    else:
        code_data = ""

    if line_indent:
        code_data = textwrap.indent(code_data, line_indent)

    if rich:
        return Syntax(code_data, name, theme=style, **kwargs)
    else:
        return highlight(
            code=code_data,
            lexer=get_lexer_by_name(name),
            formatter=Terminal256Formatter(style=style))


def print_here():
    from inspect import currentframe, getframeinfo
    frame_info = getframeinfo(currentframe().f_back)
    filename = frame_info.filename.split('/')[-1]
    line_number = frame_info.lineno
    # loc_str = '%s:%d' % (filename, line_number)
    location_str = f"{filename}:{line_number}"
    print(location_str)


def print_frames(frame_list):
    module_frame_index = [i for i, f in enumerate(frame_list) if f.function == '<module>'][0]
    for i in range(module_frame_index):
        d = frame_list[i][0].f_locals
        local_vars = {x: d[x] for x in d}
        print("  [Frame {} '{}': {}]".format(module_frame_index - i, frame_list[i].function, local_vars))
    print("  [Frame '<module>']\n")


def get_debug_here_info():
    """
    Get debug information from the previous frame.

    This function uses the inspect module to get information about the previous frame, including the filename, line number, function name, lines of context, and index.

    Returns:
        dict: A dictionary containing the debug information.
    """
    filename, line_number, function_name, ln, index = inspect.getframeinfo(inspect.currentframe().f_back.f_back)
    return {
        "filename": filename,
        "line_number": line_number,
        "function_name": function_name,
        "ln": ln,
        "index": index
    }


def get_variable_name_list(var=None):
    """
    Retrieve the name of var.

    :param var: variable to get name from
    :return: name of var

    Example:

        .. code-block:: python

            a = 5
            get_variable_name_list(a)
            # >> ['a']

    """
    callers_local_vars = inspect.currentframe().f_back.f_locals.items()
    return [var_name for var_name, var_val in callers_local_vars if var_val is var]


def get_variable_name(var=None):
    """
    Retrieve the name of the variable.

    :param var: variable to get the name from, defaults to None
    :type var: Any, optional
    :return: name of the variable
    :rtype: str

    Example:

        .. code-block:: python

            a = 10
            get_variable_name(a)
            # >> 'a'

    """
    stacks = inspect.stack()
    try:
        func = stacks[0].function
        code = stacks[1].code_context[0]
        s = code.index(func)
        s = code.index("(", s + len(func)) + 1
        e = code.index(")", s)
        return code[s:e].strip()
    except:
        return ""


def dict_clean(data):
    """
    Clean the dictionary data.

    This function iterates over the items in the dictionary. If the value is an instance of CaseInsensitiveDict, it converts it to a regular dictionary. If the value is None, it converts it to an empty string.

    :param data: The dictionary to clean.
    :type data: dict
    :return: The cleaned dictionary.
    :rtype: dict

    Example:

        .. code-block:: python

            data = {"key1": "value1", "key2": None, "key3": CaseInsensitiveDict({"subkey": "subvalue"})}
            dict_clean(data)
            # >> {"key1": "value1", "key2": "", "key3": {"subkey": "subvalue"}}

    """
    result = {}
    for key, value in data.items():
        if isinstance(value, CaseInsensitiveDict):
            value = dict(value)
        elif value is None:
            value = ''
        result[key] = value
    return result


def list_clean(data):
    """
    Clean the list data.

    This function iterates over the items in the list. If the value is None, it converts it to an empty string.

    :param data: The list to clean.
    :type data: list
    :return: The cleaned list.
    :rtype: list

    Example:

        .. code-block:: python

            data = [None, 'hello', None, 'world']
            list_clean(data)
            # >> ['', 'hello', '', 'world']

    """
    result = []
    for value in data:
        if value is None:
            value = ''
        result.append(value)
    return result


def data_clean(data):
    """
    Clean the data.

    This function checks the type of the data. If the data is a dictionary, it cleans it using the dict_clean function. If the data is a list, it cleans it using the list_clean function.

    :param data: The data to clean.
    :type data: Any
    :return: The cleaned data.
    :rtype: Any

    Example:

        .. code-block:: python

            data = {'name': ' John ', 'age': ' 25 '}
            clean_data = data_clean(data)
            # >> {'name': 'John', 'age': '25'}

            data = [' John ', ' 25 ']
            clean_data = data_clean(data)
            # >> ['John', '25']

    """
    if isinstance(data, dict):
        return dict(dict_clean(data))
    elif isinstance(data, list):
        return list(list_clean(data))
    return data


def count_nested_dict_len(d):
    """
    Count the length of a nested dictionary.

    This function counts the number of items in a dictionary. If a value in the dictionary is also a dictionary, it recursively counts the number of items in that dictionary as well.

    Args:
        d (dict): The dictionary to count the length of.

    Returns:
        int: The length of the dictionary.
    """

    length = len(d)
    for key, value in d.items():
        if isinstance(value, dict):
            length += count_nested_dict_len(value)
    return length


def get_var_name():
    """
    Get the variable name from the call frame.

    This function uses the sys._getframe() function to get the call frame, and then uses the executing library to get the variable name from the call frame.

    Returns:
        str: The variable name if it can be found, otherwise an empty string.
    """

    try:
        call_frame = sys._getframe(2)
        source = executing.Source.for_frame(call_frame)
        ex = source.executing(call_frame)
        func_ast = ex.node
        for ast in func_ast.args:
            if getattr(ast, 'id', ''):
                return ast.id
    except Exception:
        return ""


def get_data_length(data):
    """
    Get the length of the data.

    This function tries to get the length of the data. If the data is a dictionary, it gets the nested dictionary length. If the data is not a dictionary, it gets the length of the data.

    Args:
        data (Any): The data to get the length of.

    Returns:
        str: A string representing the length of the data. If the length cannot be found, it returns an empty string.
    """

    try:
        if isinstance(data, dict):
            return f"nested_dict_len={count_nested_dict_len(data)}"
        else:
            return f"len={len(data)}"
    except Exception:
        return ""


def print_var(data=None, title='', **kwargs):
    """
    Print the variable.

    This function prints the variable with its name, type, and length. It also prints the data if it is a dictionary or a list.

    Args:
        data (Any, optional): The data to print. Defaults to None.
        title (str, optional): The title to print. Defaults to ''.
        **kwargs: Arbitrary keyword arguments.

    Keyword Args:
        line_indent (str): The line indent to use when printing the data. Defaults to '      '.
    """

    kwargs.setdefault('line_indent', '      ')
    var_name = get_var_name()
    data_length = get_data_length(data)
    _title = f"[yellow bold]{title}[/yellow bold]" if title else ""

    pawn.console.log(f"🎁 [[blue bold]{var_name}[/blue bold]] {_title}"
                     f"\t[italic] ({type(data).__name__}), {data_length}", _stack_offset=2)
    if isinstance(data, dict) or isinstance(data, list):
        print(syntax_highlight(data, **kwargs))
    else:
        pawn.console.print(f"\t[white bold]{data}\n")


def print_aligned_text(left_text, right_text, filler='.'):
    """
    Print left and right text aligned with filler in between.

    :param left_text: The text to be aligned on the left side.
    :param right_text: The text to be aligned on the right side.
    :param filler: The character used to fill the space between left and right text. Default is '.'.

    Example:

        .. code-block:: python

            print_aligned_text("Left Text", "Right Text")
            # Left Text...........................................Right Text

            print_aligned_text("Chapter 1", "Page 10", filler='*')
            # Chapter 1********************************************Page 10

    """
    full_text = align_text(left_text, right_text, filler)
    pawn.console.print(full_text)


def align_text(left_text: str = '', right_text: str = '', filler: str = '.', offset: int = 2):
    """
    Aligns text to the left and right with a filler in between.

    :param left_text: The text to align to the left.
    :param right_text: The text to align to the right.
    :param filler: The character to use as filler between the left and right text.
    :param offset: The number of spaces to offset the right text from the right edge.

    Example:

        .. code-block:: python

            align_text('Hello', 'World', filler='-', offset=3)
            # >> 'Hello ---------------------------- World'

            align_text('Left', 'Right', filler='*', offset=5)
            # >> 'Left ************************** Right'

    """
    cleaned_left_text = remove_ascii_color_codes(left_text)
    cleaned_right_text = remove_ascii_color_codes(right_text)

    cleaned_left_text = remove_tags(cleaned_left_text, case_sensitive='lower')
    cleaned_right_text = remove_tags(cleaned_right_text, case_sensitive='lower')

    padding_length = pawn.console.width - len(cleaned_left_text) - len(cleaned_right_text) - offset
    padding = filler * padding_length
    full_text = f"{left_text} {padding} {right_text}"
    return full_text


@contextmanager
def disable_exception_traceback():
    """
    All traceback information is suppressed and only the exception type and value are printed
    """
    default_value = getattr(sys, "tracebacklimit", 1000)  # `1000` is a Python's default value
    sys.tracebacklimit = 0
    yield
    sys.tracebacklimit = default_value  # revert changes
    # try:
    #     sys.tracebacklimit = 0
    #     yield
    # finally:
    #     sys.tracebacklimit = default_value  # revert changes


class NoTraceBackException(Exception):
    def __init__(self, msg):
        try:
            line_no = sys.exc_info()[-1].tb_lineno
            filename = sys.exc_info()[-1].tb_filename
        except AttributeError:
            previous_frame = inspect.currentframe().f_back
            line_no = inspect.currentframe().f_back.f_lineno
            (filename, line_number,
             function_name, ln, index) = inspect.getframeinfo(previous_frame)
        # self.args = "<{0.__name__}> ({2} line {2}): \n {3}".format(type(self), filename, line_no, msg),
        # self.args = "{0}<{1.__name__}>{2} ({3} line {4}): \n {5}".format(bcolors.FAIL, type(self), bcolors.ENDC, filename, line_no, msg),
        # self.args = "<{0.__name__}>({1} line {2}): \n {3}".format(type(self), filename, line_no, msg),
        self.args = "<{0.__name__}> {1}".format(type(self), msg),
        # ex_type, ex_value, traceback = sys.exc_info()
        raise Exception(self)
