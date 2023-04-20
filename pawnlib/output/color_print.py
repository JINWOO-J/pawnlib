#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
import getpass
import traceback
import inspect
from pawnlib.typing import converter, date_utils, list_to_oneline_string, const, is_include_list
from pawnlib.config import pawnlib_config as pawn, global_verbose
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import Terminal256Formatter
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
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


                                           RichTable
        ┏━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
        ┃ idx ┃ address                                    ┃ value                    ┃
        ┡━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
        │ 0   │ 1x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08 │ 399999999999999966445568 │
        ├─────┼────────────────────────────────────────────┼──────────────────────────┤
        │ 1   │ 2x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08 │ 399999999999999966445568 │
        ├─────┼────────────────────────────────────────────┼──────────────────────────┤
        │ 2   │ 3x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08 │ 399999999999999966445568 │
        └─────┴────────────────────────────────────────────┴──────────────────────────┘

        PrintRichTable(title="RichTable", data=data, columns=["address"])

                                      RichTable
        ┏━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
        ┃ idx ┃ address                                    ┃
        ┡━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
        │ 0   │ 1x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08 │
        ├─────┼────────────────────────────────────────────┤
        │ 1   │ 2x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08 │
        ├─────┼────────────────────────────────────────────┤
        │ 2   │ 3x038bd14d5ce28a4ac713c21e89f0e6ca5f107f08 │
        └─────┴────────────────────────────────────────────┘

    """

    def __init__(
                self,
                title: str = "",
                data: Union[dict, list] = None,
                columns: list = None,
                remove_columns: list = None,
                with_idx: bool = True,
                call_value_func = str,
                call_desc_func = None,
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

        self._initialize_table()
        self._set_table_data()
        self._print_table()

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
        pawn.console.debug(f"Drawing vertical table")
        if self.with_idx:
            self.table.add_column("idx")
        self.table.add_column("key", justify="left")
        self.table.add_column("value", justify="right")

        if self.call_desc_func and callable(self.call_desc_func):
            self.table.add_column("description", justify="right")

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
                        value = self.call_value_func(item.get(column))
                    row_dict[column] = value
                    line_row.append(value)
                self.rows.append(line_row)
            self.row_count += 1

        for col in self.columns:
            self.table.add_column(col)

    def _extract_columns(self):
        # if self.table_data and len(self.columns) == 0 and isinstance(self.table_data[0], dict):
        if self.table_data and len(self.columns) == 0:
            self.columns = list(self.table_data[0].keys())
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

        if self.table.columns:
            pawn.console.print(self.table)
        else:
            pawn.console.print(f"{self.title} \n  [i]No data ... [/i]")


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


def dump(obj, nested_level=0, output=sys.stdout, hex_to_int=False, debug=True, _is_list=False, _last_key=None):
    """
    Print a variable for debugging.

    :param obj:
    :param nested_level:
    :param output:
    :param hex_to_int:
    :param debug:
    :param _is_list:
    :param _last_key:
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
                dump(v, nested_level + 1, output, hex_to_int, debug, _last_key=k)
            else:
                if debug:
                    v = f"{get_colorful_object(v)} {bcolors.HEADER} {str(type(v)):>20}{bcolors.ENDC}{bcolors.DARK_GREY} len={len(str(v))}{bcolors.ENDC}"
                print(bcolors.OKGREEN + '%s%s:' % (def_spacing + (nested_level + 1) * spacing, k) + bcolors.WARNING + ' %s ' % v + bcolors.ENDC,
                      file=output)
        print('%s}' % (def_spacing + nested_level * spacing), file=output)
    elif type(obj) == list:
        print('%s[' % (def_spacing + (nested_level) * spacing), file=output)
        for v in obj:
            if hasattr(v, '__iter__'):
                dump(v, nested_level + 1, output, hex_to_int, debug, _is_list=True)
            else:
                print(bcolors.WARNING + '%s%s' % (def_spacing + (nested_level + 1) * spacing, get_colorful_object(v)) + bcolors.ENDC, file=output)
        print('%s]' % (def_spacing + (nested_level) * spacing), file=output)
    else:
        if debug:
            converted_hex = ""

            if hex_to_int and converter.is_hex(obj) and not is_include_list(target=_last_key, include_list=ignore_keys, ignore_case=False) :
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


def print_json(obj, **kwargs):
    """
    converted to JSON and print

    :param obj:
    :param kwargs:
    :return:
    """
    if isinstance(obj, dict) or isinstance(obj, list):
        print(json.dumps(obj, **kwargs))
    else:
        print(obj)


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
    return json.dumps(data,  indent=indent)


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

def syntax_highlight(data, name="json", indent=4, style="material", oneline_list=True, line_indent=''):
    """
    Syntax highlighting function

    :param data:
    :param name:
    :param indent:
    :param style:
    :param oneline_list:
    :param line_indent:
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
        data = dict_clean(data)
        code_data = json_compact_dumps(dict(data), indent=indent, monkey_patch=oneline_list)
    elif data:
        code_data = data
    else:
        code_data = ""

    if line_indent:
        code_data = textwrap.indent(code_data, line_indent)

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


def retrieve_name(var):
    callers_local_vars = inspect.currentframe().f_back.f_locals.items()
    return [var_name for var_name, var_val in callers_local_vars if var_val is var]


def retrieve_name_ex(var):
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
    result = {}
    for key, value in data.items():
        if isinstance(value, CaseInsensitiveDict):
            value = dict(value)
        elif value is None:
            value = ''
        result[key] = value
    return result


def print_var(data=None, title='', **kwargs):
    if kwargs.get('line_indent', '__NOT_DEFINED__') == "__NOT_DEFINED__":
        kwargs['line_indent'] = '      '
    if kwargs.get('data', '__NOT_DEFINED__') != "__NOT_DEFINED__":
        del kwargs['data']

    var_name = ""
    try:
        import executing
        call_frame = sys._getframe(1)
        source = executing.Source.for_frame(call_frame)
        ex = source.executing(call_frame)
        func_ast = ex.node
        for ast in func_ast.args:
            var_name = ast.id
    except:
        var_name = ""

    pawn.console.log(f"🎁 [yellow bold]{title}[/yellow bold][blue bold]{var_name}[/blue bold] "
                     f"\t[italic] ({type(data).__name__}), len={len(data)}", _stack_offset=2)
    print(syntax_highlight(data, **kwargs))


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
        self.args = "{0}<{1.__name__}>{2} ({3} line {4}): \n {5}".format(bcolors.FAIL, type(self), bcolors.ENDC, filename, line_no, msg),
        raise Exception(self)
