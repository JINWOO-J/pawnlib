#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
import getpass
import traceback
import inspect
from contextlib import contextmanager, AbstractContextManager

from pawnlib.typing import (
    converter, date_utils, list_to_oneline_string, const, is_include_list, remove_tags,
    remove_ascii_color_codes, timestamp_to_string, is_hex, is_json
)
from pawnlib.config import pawnlib_config as pawn, global_verbose
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import Terminal256Formatter
from dataclasses import is_dataclass, asdict
from rich.syntax import Syntax
from rich.table import Table
from rich.pretty import Pretty
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.console import Group, Console
from rich.tree import Tree
from rich.text import Text
from rich import print as rprint
from typing import Union, Callable
from datetime import datetime
import textwrap
from requests.structures import CaseInsensitiveDict

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal  # pragma: no cover

AlignMethod = Literal["left", "center", "right"]
VerticalAlignMethod = Literal["top", "middle", "bottom"]

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
    RESET = '\033[0m'
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
            no_wrap: bool = False,
            overflow="fold",
            justify="left",
            **kwargs
    ) -> None:

        if columns is None:
            columns = list()
        if data is None:
            data = dict()
        self.title = f"[bold dark_orange3] {title}"
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

        self.overflow = overflow
        self.no_wrap = no_wrap

        _default_columns_option = dict(
            key=dict(
                justify="left",
                overflow=self.overflow,
                no_wrap=self.no_wrap
            ),
            value=dict(
                justify="right",
                overflow=self.overflow,
                no_wrap=self.no_wrap
            ),
            description=dict(
                justify="right",
                overflow=self.overflow,
                no_wrap=self.no_wrap
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

        # for col in self.columns:
        #     self.table.add_column(col, **self.columns_options.get(col, {"no_wrap": self.no_wrap}))
        for col in self.columns:
            column_options = self.columns_options.get(col, {})
            no_wrap = column_options.get('no_wrap', self.no_wrap)
            overflow = column_options.get('overflow', self.overflow)

            self.table.add_column(
                col,
                **column_options,
                no_wrap=no_wrap,
                overflow=overflow
            )

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


def print_json(obj, syntax=True, line_indent="", rich_syntax=True, style="material", **kwargs):
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
    if rich_syntax is True:
        pawn.console.print(pretty_json(obj, syntax=syntax, rich_syntax=True, line_indent=line_indent, style=style, **kwargs))
    else:
        print(pretty_json(obj, syntax=syntax, rich_syntax=True, line_indent=line_indent, style=style, **kwargs))


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
            return Syntax(json_string, "json", line_numbers=False, background_color="rgb(40,40,40)", theme=style)
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


def syntax_highlight(data, name="json", indent=4, style="material", oneline_list=True, line_indent='', rich=False, word_wrap=True, **kwargs):
    """
    Syntax highlighting function

    :param data: The data to be highlighted.
    :param name: The name of the lexer to use for highlighting.
    :param indent: The number of spaces to use for indentation.
    :param style: The style to use for highlighting.
    :param oneline_list: Whether to compact lists into one line.
    :param line_indent: The string to use for line indentation.
    :param rich: Whether to use rich text formatting.
    :param word_wrap: Whether to enable word wrapping.
    :return: The highlighted code as a string.

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
    print(data)
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
        return Syntax(code_data, name, theme=style, word_wrap=word_wrap, **kwargs)
    else:
        return highlight(
            code=code_data,
            lexer=get_lexer_by_name(name),
            formatter=Terminal256Formatter(style=style))


def syntax_highlight(data, name="json", indent=4, style="material", oneline_list=True, line_indent='', rich=False, word_wrap=True, **kwargs):
    """
    Syntax highlighting function with support for class instance representation instead of serialization.

    :param data: The data to be highlighted.
    :param name: The name of the lexer to use for highlighting.
    :param indent: The number of spaces to use for indentation.
    :param style: The style to use for highlighting.
    :param oneline_list: Whether to compact lists into one line.
    :param line_indent: The string to use for line indentation.
    :param rich: Whether to use rich text formatting.
    :param word_wrap: Whether to enable word wrapping.
    :return: The highlighted code as a string.
    """

    def convert_non_serializable(obj):
        """
        Convert non-serializable objects to a debug-friendly representation.
        """
        if hasattr(obj, '__class__'):
            return f"<{obj.__class__.__name__}> {obj.__dict__}"
        return str(obj)

    # JSON serialization with custom handling of non-serializable objects
    if name == "json" and isinstance(data, (dict, list)):
        try:
            # Using json.dumps with a custom default converter to keep classes represented by their type and attributes.
            code_data = json.dumps(data, indent=indent, default=convert_non_serializable)
        except TypeError as e:
            print(f"Serialization error: {e}")
            code_data = json.dumps(data, indent=indent, default=convert_non_serializable)
    elif data:
        code_data = data
    else:
        code_data = ""

    if line_indent:
        code_data = textwrap.indent(code_data, line_indent)

    # Use Rich's syntax highlighting or fallback to terminal highlighting
    if rich:
        return Syntax(code_data, name, theme=style, word_wrap=word_wrap, **kwargs)
        # syntax = Syntax(code_data, name, theme=style, word_wrap=word_wrap, **kwargs)
        # Convert rich Syntax to plain text for consistent rendering in Panel
        # with pawn.console.capture() as capture:
        #     pawn.console.print(syntax)
        # return capture.get()

    else:
        return highlight(
            code=code_data,
            lexer=get_lexer_by_name(name),
            formatter=Terminal256Formatter(style=style)
        )


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
   Count the total number of keys in a nested dictionary.

   :param d: Dictionary to count keys in.
   :type d: dict
   :return: Total number of keys in the dictionary, including nested dictionaries.
   :rtype: int

   Example:

       .. code-block:: python

           nested_dict = {
               'a': 1,
               'b': {'c': 2, 'd': {'e': 3}},
               'f': {'g': 4}
           }

           count_nested_dict_len(nested_dict)
           # >> 6

           count_nested_dict_len({'x': {'y': {'z': {}}}})
           # >> 3

           count_nested_dict_len({})
           # >> 0
    """

    length = len(d)
    for key, value in d.items():
        if isinstance(value, dict):
            length += count_nested_dict_len(value)
    return length


def get_var_name(var):
    """
    Get the variable name from the call frame.
    This function uses the inspect and ast modules to get the variable name from the call frame.

    :param var: The variable whose name is to be retrieved.
    :return: The name of the variable as a string.

    Example:

        .. code-block:: python

            my_var = 10
            get_var_name(my_var)
            # >> 'my_var'

            class MyClass:
                def __init__(self):
                    self.attr = 5

            instance = MyClass()
            get_var_name(instance.attr)
            # >> 'instance.attr'
    """
    import ast
    try:
        frame = inspect.currentframe().f_back.f_back
        code_context = inspect.getframeinfo(frame).code_context
        if not code_context:
            return ""
        call_line = code_context[0].strip()
        tree = ast.parse(call_line)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for arg in node.args:
                    if isinstance(arg, ast.Name):
                        if eval(arg.id, frame.f_globals, frame.f_locals) is var:
                            return arg.id
                    elif isinstance(arg, ast.Attribute):
                        attr_names = []
                        while isinstance(arg, ast.Attribute):
                            attr_names.append(arg.attr)
                            arg = arg.value
                        if isinstance(arg, ast.Name):
                            attr_names.append(arg.id)
                            full_name = '.'.join(reversed(attr_names))
                            if eval(full_name, frame.f_globals, frame.f_locals) is var:
                                return full_name
    except Exception as e:
        pawn.console.log(f"Exception occurred in get_var_name: {e}")

    return ""


def get_data_length(data):
    """
    Get the length of the data. If the data is a dictionary, it calculates the nested dictionary length.

    :param data: The input data which can be of any type.
    :return: A string representing the length of the data.

    Example:

        .. code-block:: python

             get_data_length([1, 2, 3])
             # >> 'len=3'

             get_data_length({'a': 1, 'b': {'c': 2}})
             # >> 'dict_len=2'

             get_data_length("hello")
             # >> 'len=5'

    """
    try:
        if isinstance(data, dict):
            return f"dict_len={count_nested_dict_len(data)}"
        else:
            return f"len={len(data)}"
    except Exception:
        return ""


def print_var(
        data=None,
        title: str = '',
        line_indent: str = ' ',
        detail: bool = True,
        title_align: AlignMethod = "center",
        **kwargs
):
    """
    Print the variable name and its value on the same line with optional details.

    :param data: The variable to be printed.
    :param title: Optional title for the output.
    :param line_indent: String used for indentation.
    :param detail: Whether to include detailed information.
    :param title_align: Alignment method for the title. Can be "left", "center", or "right". Default is "center".
    :param kwargs: Additional keyword arguments.

    Example:

        .. code-block:: python

            dict_var = {"key": "value"}

            print_var(dict_var)
            print_var(data={"key": "value"}, title="Example Dict")
            print_var(data=[1, 2, 3], title="Example List")
            print_var(data=42, title="Example Int")
            print_var(data="Hello, World!", title="Example String")

    """

    var_name = get_var_name(data)
    data_length = get_data_length(data)

    if not title:
        title = var_name

    _title = f"[yellow bold]{title}[/yellow bold]" if title else ""

    # Print the variable name and its value on the same line
    bg_color = "rgb(40,40,40)"
    styled_value = ""

    if "style" not in kwargs:
        kwargs['style'] = "native"
        kwargs['background_color'] = bg_color

    details = ""
    if hasattr(data, '__dict__'):  # Check if it's an instance of a class
        attributes = vars(data)
        for attr, value in attributes.items():
            styled_attr_value = style_value(value)
            # details += f"{line_indent}[cyan]{var_name}.{attr}[/cyan] = {styled_attr_value} [italic]({type(value).__name__})[/italic]\n"
            details += f"{line_indent}[cyan]{var_name}.{attr}[/cyan] = {styled_attr_value}\n"
    elif isinstance(data, (dict, list)):
        syntax_str = syntax_highlight(data, rich=True, line_indent=line_indent, **kwargs)
        details = syntax_str
    else:
        styled_value = style_value(data)

    if detail:
        output = f"🎁 [blue bold]{var_name}[/blue bold] = [italic]{styled_value} ({type(data).__name__}) {data_length}[/italic]\n"
        # output = f"🎁 [blue bold]{var_name}[/blue bold] = [italic]{styled_value} ({type(data).__name__}) [/italic]\n"
    else:
        output = styled_value

    if details:
        panel_content = Group(output, details)
    else:
        panel_content = output

    panel = Panel(panel_content, title=_title, title_align=title_align, expand=True, style=f"on {bg_color}")
    console = Console()
    console.print(panel)


def print_var2(data=None, title: str = '', line_indent: str = ' ', detail: bool = True, title_align: AlignMethod = "center", **kwargs):
    """
    Print variable content with type and length info for dict, list, class, or basic types.

    :param data: Variable to be printed.
    :param title: Optional title for the output.
    :param line_indent: String used for indentation.
    :param detail: Whether to include detailed information.
    :param title_align: Title alignment (left, center, or right).
    """
    var_name = get_var_name(data)

    if not title:
        title = var_name

    type_length_info = get_type_length_info_style(data)
    output = f"🎁 [blue bold]{var_name}[/blue bold] {type_length_info}\n"

    if isinstance(data, dict) or isinstance(data, list):
        syntax_str = syntax_highlight(data, rich=True, line_indent=line_indent, **kwargs)
        panel_content = Group(output, syntax_str)

    elif hasattr(data, '__dict__') or is_dataclass(data):
        tree = Tree(output)
        class_name = data.__class__.__name__
        attributes = asdict(data) if is_dataclass(data) else vars(data)
        for attr, value in attributes.items():
            add_node(tree, f"{class_name}.{attr}", value, detail)
        panel_content = tree

    else:
        panel_content = f"🎁 [blue bold]{var_name}[/blue bold] = {style_value(data)}"

    panel = Panel(panel_content, title=f"[yellow bold]{title or var_name}[/yellow bold]", title_align=title_align, expand=True, style="on rgb(40,40,40)")
    pawn.console.print(panel)


def add_node(tree, key, value, detail):
    """Recursively add nodes to the tree with syntax_highlight for dict and list."""
    type_length_info = f"[dim]({type(value).__name__}) len={len(value)}[/dim]" if hasattr(value, '__len__') else ""

    if isinstance(value, dict) or isinstance(value, list):
        syntax_str = syntax_highlight(value, rich=True)
        tree.add(f"[cyan]{key}[/cyan] {type_length_info}\n{syntax_str}")
    elif hasattr(value, '__dict__') or is_dataclass(value):
        branch = tree.add(f"[cyan]{key}[/cyan] [green]{type_length_info}[/green]")
        if detail:
            attributes = asdict(value) if is_dataclass(value) else vars(value)
            for attr, attr_value in attributes.items():
                add_node(branch, attr, attr_value, detail)
    else:
        tree.add(f"[cyan]{key}[/cyan] = {style_value(value)}")


def get_type_length_info_style(value):
    """
    Get the type and length information as a styled string based on the value's type.
    """
    value_type = type(value).__name__
    length_info = f"len={len(value)}" if hasattr(value, '__len__') else ""
    type_length_info = f"[dim]({value_type}) {length_info}[/dim]"

    # 색상 스타일 지정
    if isinstance(value, dict):
        return f"[cyan]{type_length_info}[/cyan]"  # 딕셔너리는 청록색
    elif isinstance(value, list):
        return f"[magenta]{type_length_info}[/magenta]"  # 리스트는 자홍색
    elif hasattr(value, '__dict__') or is_dataclass(value):
        return f"[green]{type_length_info}[/green]"  # 클래스 인스턴스는 초록색
    else:
        return f"[white]{type_length_info}[/white]"  # 기본값은 흰색


def style_value(value):
    """
    Apply different styles based on the value's type or value.
    """
    type_length_info = get_type_length_info_style(value)
    if isinstance(value, bool):
        return f"[green]{value}[/green]" if value else f"[red]{value}[/red]"
    elif isinstance(value, (int, float)):
        return f"[cyan]{value} {type_length_info}[/cyan]"
    elif isinstance(value, str):
        return f"[yellow]{value} {type_length_info}[/yellow]"
    else:
        return f"[white]{value} {type_length_info}[/white]"


def create_kv_table(padding=0, key_ratio=2, value_ratio=7, overflow="fold"):
    table = Table(
        padding=padding,
        pad_edge=False,
        expand=True,  # 테이블이 전체 화면에 맞춰 늘어나도록 설정
        show_header=False,
        show_footer=False,
        show_edge=False,
        show_lines=False,
        box=None,
    )

    table.add_column("Key", no_wrap=False, justify="left", style="bold yellow", min_width=padding, ratio=key_ratio, overflow=overflow)
    table.add_column("Separator", no_wrap=False, justify="left", width=3)
    table.add_column("Value", no_wrap=False, justify="left", ratio=value_ratio, max_width=None, overflow=overflow)  # max_width 제한 해제
    table.add_column("Debug Info", justify="right", style="grey84")

    return table


# def get_pretty_value(value):
#     if isinstance(value, (dict, list)):
#         pawn.console.log(value)
#         return Syntax(json.dumps(value, indent=4), "json", theme="material", line_numbers=False)
#     else:
#         if value and is_json(value):
#             __loaded_json = json.loads(value)
#             return Pretty(json.loads(value))
#         return value


def get_pretty_value(value, is_force_syntax=False):
    if isinstance(value, (dict, list)):
        if is_force_syntax:
            return Syntax(json.dumps(value, indent=4), "json", theme="material", line_numbers=False)
        pretty_value = Pretty(value, expand_all=True)
        with pawn.console.capture() as capture:
            pawn.console.print(pretty_value)
        return capture.get()
    else:
        if value and is_json(value):
            __loaded_json = json.loads(value)
            pretty_value = Pretty(__loaded_json, expand_all=True)
            with pawn.console.capture() as capture:
                pawn.console.print(pretty_value)
            return capture.get()
        return value


def print_kv(key="", value="", symbol="░", separator=":", padding=1, key_ratio=1, value_ratio=7, is_force_syntax=True):
    """
    Print a key-value pair with a symbol, padding, and value size information.

    :param key: The key to print. Defaults to an empty string.
    :param value: The value associated with the key. Defaults to an empty string.
    :param symbol: A symbol to prepend to the key. Defaults to a star emoji.
    :param separator: The separator between the key and the value. Defaults to a colon.
    :param padding: The padding between columns. Defaults to 5.
    :param key_ratio: The ratio of the table width allocated for keys. Defaults to 1z.
    :param value_ratio: The ratio of the table width allocated for values. Defaults to 7.
    :param is_force_syntax: Force the use of Syntax rendering for dictionaries/lists.

    Example:

        .. code-block:: python

            print_kv(key="Name", value="John Doe", symbol="👤")
            # Output:
            # 👤 Name   :   John Doe   str[bright_black](8)[/bright_black]

            print_kv(key="Age", value=30, symbol="🔢", padding=3)
            # Output:
            # 🔢 Age : 30   int[bright_black](2)[/bright_black]

    """
    table = create_kv_table(padding=padding, key_ratio=key_ratio, value_ratio=value_ratio)
    if value:
        value_info = f"{type(value).__name__}[bright_black]({converter.get_value_size(value)})[/bright_black]"
    else:
        value_info = ""

    if is_force_syntax and isinstance(value, (dict, list)):
        pretty_value = Syntax(
            json.dumps(value, indent=4), "json", theme="material", line_numbers=False, word_wrap=True, padding=1
        )
    else:
        pretty_value = get_pretty_value(value, is_force_syntax)
    table.add_row(f"{symbol} {key}", f"[grey69] {separator} [/grey69]", pretty_value, value_info)

    pawn.console.print(table)


def print_grid(data: dict = None, title="", symbol="░", separator=":", padding=0, key_ratio=1, value_ratio=7,
               key_prefix="", key_postfix="", value_prefix="", value_postfix="", is_value_type=True):
    """
    Print a grid layout with a title and optional padding and edge padding.

    :param data: The data to display in the grid. Default is None.
    :param title: The title of the grid. Default is an empty string.
    :param symbol: The symbol used for the grid. Default is '░'.  or 🔘★⭐️ ■ ▓  ▒ ░
    :param separator: The separator between the key and the value. Defaults to a colon.
    :param padding: The padding around each cell. Default is 0.
    :param key_ratio: The ratio of the table width allocated for keys. Defaults to 1.
    :param value_ratio: The ratio of the table width allocated for values. Defaults to 7.

    :param key_prefix: A prefix to add to each key. Default is an empty string.
    :param key_postfix: A postfix to add to each key. Default is an empty string.
    :param value_prefix: A prefix to add to each value. Default is an empty string.
    :param value_postfix: A postfix to add to each value. Default is an empty string.
    :param is_value_type: Flag to indicate if value type should be displayed.


    Example:

        .. code-block:: python

            data = {"Item 1": 123, "Item 2": 456}
            print_grid(data, title="Inventory", symbol="■", padding=1, pad_edge=False)

            # Output will display a grid with the title "Inventory", using '■' as the symbol,
            # 1 padding around each cell, and no padding on the edge.

            print_grid(data, title="Inventory", symbol="■", padding=1, key_prefix="[", key_postfix="]", value_prefix="(", value_postfix=")")

    """
    table = create_kv_table(padding=padding, key_ratio=key_ratio, value_ratio=value_ratio)
    pawn.console.rule(f" ✨✨{title}✨✨", style="white")
    if not isinstance(data, dict):
        pawn.console.log(f"'{data}' is not dict")
        return

    for key, value in data.items():
        if is_value_type:
            value_info = f"{type(value).__name__}[bright_black]({converter.get_value_size(value)})[/bright_black]"
        else:
            value_info = ""
        table.add_row(
            f"{symbol} {key_prefix}{key}{key_postfix}",
            f"[grey69] {separator} [/grey69]",
            f"{value_prefix}{get_pretty_value(value)}{value_postfix}",
            value_info
        )
    pawn.console.print(table)
    pawn.console.rule("", style="white")


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


def get_color_by_threshold(value, limit=100, unit="", thresholds=None, return_tuple=False):
    """
    Determine the color based on the value and thresholds.

    :param value: The value to be evaluated.
    :param limit: The limit to compare the value against. Default is 100.
    :param unit: The unit to append to the value. Default is an empty string.
    :param thresholds: A dictionary defining the thresholds and their corresponding colors.
                       The keys are the threshold values (as a fraction of the limit) and the values are the colors.
                       Example: {0.9: "red", 0.8: "orange1", 0.7: "yellow"}
                       Default is {0.9: "red", 0.8: "orange1", 0.7: "yellow", 0.0: "white"}.
    :param return_tuple: If True, returns a tuple (color, formatted_value). Default is False.
    :return: If return_tuple is False, returns a formatted string in rich text format.
             If return_tuple is True, returns a tuple (color, formatted_value).
    """
    if thresholds is None:
        thresholds = {0.9: "red", 0.8: "orange1", 0.7: "yellow", 0.0: "white"}

    percent = value / limit if limit != 0 else 0

    color = "green"
    for threshold, threshold_color in sorted(thresholds.items(), reverse=True):
        if percent >= threshold:
            color = threshold_color
            break

    formatted_value = f"{value}{unit}"

    if return_tuple:
        return color, formatted_value
    else:
        return f"[{color}]{formatted_value}[/{color}]"
