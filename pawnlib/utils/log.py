#!/usr/bin/env python3
import os
import logging
import sys
from logging import handlers
import traceback
import datetime
from pawnlib.config.globalconfig import pawnlib_config, pawn, Null
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text
from typing import Callable
import re
import inspect

try:
    from typing import Literal, Union
except ImportError:
    from typing_extensions import Literal, Union


class CustomLog:
    """CustomLog

    :param name: logger name

    Example:

        .. code-block:: python

            from pawnlib.utils.log import CustomLog

            file_name = './time_log.txt'
            logger = CustomLog("custom_log")
            logger.set_level('DEBUG')
            logger.stream_handler("INFO")
            logger.time_rotate_handler(filename=file_name,
                                       when="M",
                                       interval=2,
                                       backup_count=3,
                                       level="INFO"
                                       )
            idx = 1
            logger.log.debug(logger.log_formatter(f'debug {idx}'))
            logger.log.info(logger.log_formatter(f'info {idx}'))
            logger.log.warning(logger.log_formatter(f'warning {idx}'))
            logger.log.error(logger.log_formatter(f'error {idx}'))
            logger.log.critical(logger.log_formatter(f'critical {idx}'))

    """

    def __init__(self, name):
        self.log = logging.getLogger(name)
        self.log.propagate = True
        # self.formatter = logging.Formatter("%(levelname).1s|%(asctime)s.%(msecs)06d|-|%(name)s|%(message)s", "%Y%m%d-%H:%M:%S")
        # self.formatter = logging.Formatter(f"%(levelname).1s|%(asctime)s.%(msecs)06d|-|%(name)s|%(filename)s:%(lineno)d %(funcName)-15s| %(message)s", "%Y%m%d-%H:%M:%S")
        self.formatter = logging.Formatter(
            f"%(levelname).1s|%(asctime)s.%(msecs)06d|-|%(name)s|%(filename)s:%(lineno)d| %(message)s",
            "%Y%m%d-%H:%M:%S"
        )
        self.levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }

    def set_level(self, level):
        self.log.setLevel(self.levels[level])

    def log_formatter(self, msg):
        """

        :param msg:
        :return:
        """
        log_str = f"{msg}"
        return log_str

    def stream_handler(self, level):
        """
        :param level:

        Note:
            level

            * "DEBUG" : logging.DEBUG ,
            * "INFO" : logging.INFO ,
            * "WARNING" : logging.WARNING ,
            * "ERROR" : logging.ERROR ,
            * "CRITICAL" : logging.CRITICAL ,
        :return:
        """
        _stream_handler = logging.StreamHandler()
        _stream_handler.setLevel(self.levels[level])
        _stream_handler.setFormatter(self.formatter)
        self.log.addHandler(_stream_handler)
        return self.log

    def file_handler(self, file_name, mode):
        """

        :param file_name: ~.txt / ~.log
        :param mode: "w" / "a"
        :return:
        """
        _file_handler = logging.FileHandler(file_name, mode=mode)
        _file_handler.setLevel(logging.DEBUG)
        _file_handler.setFormatter(self.formatter)
        self.log.addHandler(_file_handler)
        return self.log

    def file_rotating_handler(self, file_name, mode, level, backup_count, log_max_size):
        """

        :param file_name: file의 이름 , ~.txt / ~.log
        :param mode: "w" / "a"
        :param backup_count: backup할 파일 개수
        :param log_max_size: 한 파일당 용량 최대
        :param level:

        > "DEBUG" : logging.DEBUG ,
        > "INFO" : logging.INFO ,
        > "WARNING" : logging.WARNING ,
        > "ERROR" : logging.ERROR ,
        > "CRITICAL" : logging.CRITICAL ,
        :return:
        """

        _file_handler = logging.handlers.RotatingFileHandler(
            filename=file_name,
            maxBytes=log_max_size,
            backupCount=backup_count,
            mode=mode)
        _file_handler.setLevel(self.levels[level])
        _file_handler.setFormatter(self.formatter)
        self.log.addHandler(_file_handler)
        return self.log

    def time_rotate_handler(self,
                            filename='./log.txt',
                            when="M",
                            level="DEBUG",
                            backup_count=4,
                            atTime=datetime.time(0, 0, 0),
                            interval=1):
        """
        :param level:
        :param filename:
        :param when: 저장 주기
        :param interval: 저장 주기에서 어떤 간격으로 저장할지
        :param backup_count: 5
        :param atTime: datetime.time(0, 0, 0)
        :return:
        """
        _file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=filename,
            when=when,  # W0
            backupCount=backup_count,
            interval=interval,
            atTime=atTime)
        _file_handler.setLevel(self.levels[level])
        _file_handler.setFormatter(self.formatter)
        self.log.addHandler(_file_handler)
        return self.log


class AppLogger:
    """
    A logger class for managing application logging.

    This logger supports logging to both a file and stdout with customizable formats,
    levels, and handlers. It can also handle exceptions and apply filters to log messages.

    :param app_name: The name of the application, which will be used as the log file name.
    :param log_level: The logging level (default is "INFO"). Options include:
                      "DEBUG", "INFO", "WARN", "ERROR".
    :param log_path: The directory path where log files will be stored (default is "./logs").
    :param stdout: If True, enables logging to stdout (default is False).
    :param markup: If True, enables markup formatting for stdout logging (default is False).
    :param stdout_level: The logging level for stdout (default is "INFO").
                         Options include "DEBUG", "INFO", "WARN", "ERROR", "NOTSET".
    :param stdout_log_formatter: Custom formatter for stdout logging (default is None).
    :param log_format: Custom format for log messages (default is a predefined format).
                       Example: "[%(asctime)s] %(levelname)s - %(message)s".
    :param use_hook_exception: If True, sets a hook to log uncaught exceptions (default is True).
    :param exception_handler: A custom function to handle exceptions (default is None).
    :param debug: If True, enables debug mode for additional logging information (default is False).

    Example Usage:

        from pawnlib.utils import log

        app_logger, error_logger = log.AppLogger().get_logger()
        app_logger.info("This is an info message.")
        error_logger.error("This is an error message.")

        # Advanced usage with configuration
        from pawnlib.config.globalconfig import pawnlib_config as pawn

        app_logger, error_logger = log.AppLogger(
            app_name="app",
            log_path="./logs",
            stdout=True,
            markup=True,
            log_level="DEBUG"
        ).set_global()

        pawn.app_logger.info("This is an info message.")
        pawn.error_logger.error("This is an error message.")

        # Expected Output:
        # [2022-07-25 18:52:44,415] INFO::app_logging_test.py/main(38) This is an info message.
        # [2022-07-25 18:52:44,416] ERROR::app_logging_test.py/main(39) This is an error message.

    Attributes:
        logger: The main application logger instance.
        error_logger: The error logger instance for capturing error messages.

    Methods:
        get_logger(): Returns the main and error logger instances.
        set_global(): Sets the logger instances globally in the pawnlib configuration.

    Note:
        Ensure that the specified log path exists or can be created by the application.
    """

    _logger = None

    def __init__(self,
                 app_name: str = "default",
                 log_level: Literal["INFO", "WARN", "DEBUG"] = "INFO",
                 log_path: str = "./logs",
                 markup: bool = True,
                 stdout: bool = False,
                 stdout_level: Literal["INFO", "WARN", "DEBUG", "NOTSET"] = "INFO",
                 stdout_log_formatter: Callable = "%H:%M:%S,%f",
                 log_format: str = None,
                 std_log_format: str = None,
                 debug: bool = False,
                 use_hook_exception: bool = True,
                 use_clean_text_filter: bool = False,
                 exception_handler: Callable = "",
                 **kwargs
                 ):
        self.app_name = app_name
        self.log_path = log_path
        self.debug = debug
        self.stdout = stdout
        self.stdout_level = stdout_level
        self.stdout_log_formatter = stdout_log_formatter
        self.markup = markup
        self.log_level = log_level
        self.use_hook_exception = use_hook_exception
        self.kwargs = kwargs

        if self.use_hook_exception:
            if exception_handler:
                sys.excepthook = exception_handler
            else:
                sys.excepthook = self.handle_exception
        self.use_clean_text_filter = use_clean_text_filter

        if log_format:
            self.log_format = log_format
        else:
            # self.log_format = "[%(asctime)s] %(name)s::" "%(filename)s/%(funcName)s(%(lineno)d) %(message)s"
            self.log_format = "[%(asctime)s] %(levelname)s::" "%(filename)s/%(funcName)s(%(lineno)d) %(message)s"

        if std_log_format:
            self.std_log_format = std_log_format
        else:
            self.std_log_format = f"<%(name)s> %(message)s"
        self.log_formatter = logging.Formatter(self.log_format)
        self._logger = self.set_logger(self.log_level)
        self._error_logger = self.set_logger("ERROR")

        if not self.stdout:
            self._logger.propagate = False
            self._error_logger.propagate = False

    def get_realpath(self):
        path = os.path.dirname(os.path.abspath(__file__))
        parent_path = os.path.abspath(os.path.join(path, ".."))
        return parent_path

    def set_logger(self, log_type="INFO"):
        # log_path = f"{self.get_realpath()}/logs"
        # print(f"log_path={self.log_path}")
        if not os.path.isdir(self.log_path):
            os.mkdir(self.log_path)

        # _logger = logging.getLogger(f"PAWN_LOGGER_{log_type}")
        if log_type == "ERROR":
            _logger = logging.getLogger(f"pawn.error_logger")
        else:
            _logger = logging.getLogger(f"pawn.app_logger")

        stack = traceback.extract_stack()
        _logger.setLevel(getattr(logging, log_type))

        if log_type == "ERROR":
            filename = f"{self.app_name}.{str(log_type).lower()}.log"
        else:
            filename = f"{self.app_name}.log"

        logfile_filename = "%s/%s" % (self.log_path, filename)

        file_handler = self.time_rotate_handler(
            filename=logfile_filename,
            when='midnight',
            interval=1,
            encoding='utf-8',
            backup_count=10
        )
        file_handler.suffix = '%Y%m%d'
        file_handler.setFormatter(self.log_formatter)

        if self.use_clean_text_filter:
            file_handler.addFilter(CleanTextFilter())

        _logger.addHandler(file_handler)

        if self.stdout:
            if self.stdout_log_formatter:
                log_time_formatter = lambda dt: Text.from_markup(f"[{dt.strftime(self.stdout_log_formatter)[:-3]}]")
            else:
                log_time_formatter = None
            # if self.stdout_log_formatter:
            #
            # else:
            #     log_time_formatter = lambda dt: Text.from_markup(f"[{dt.strftime('%H:%M:%S,%f')[:-3]}]")
            logging.basicConfig(
                # level=self.stdout_level, format="%(message)s", datefmt="[%Y-%m-%d %H:%M:%S.%f]", handlers=[RichHandler(rich_tracebacks=True)]
                level=self.stdout_level,
                # format=f"[STDOUT] %(message)s",
                format=self.std_log_format,
                handlers=[
                    TightLevelRichHandler(
                        rich_tracebacks=True,
                        log_time_format=log_time_formatter,
                        markup=self.markup,
                        **self.kwargs
                    )
                ]
            )
        # else:
        #     # logging.getLogger().handlers = []
        #     root_logger = logging.getLogger()
        #     for handler in root_logger.handlers:
        #         root_logger.removeHandler(handler)

        # _logger.addHandler(self.add_stream_handler(level=log_type))
        return _logger

    def add_stream_handler(self, level):
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        stream_handler.setFormatter(self.log_formatter)
        return stream_handler

    def time_rotate_handler(self,
                            filename='./log.txt',
                            when="M",
                            backup_count=4,
                            atTime=datetime.time(0, 0, 0),
                            interval=1,
                            encoding="utf-8"
                            ):
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=filename,
            when=when,  # W0
            backupCount=backup_count,
            interval=interval,
            atTime=atTime,
            encoding=encoding
        )
        return file_handler

    def get_logger(self):
        """
        Get the logger

        :return:
        """
        return self._logger, self._error_logger

    def set_global(self):
        """
        Add global config in pawnlib

        :return:
        """
        pawnlib_config.set(
            PAWN_APP_LOGGER=self._logger,
            PAWN_ERROR_LOGGER=self._error_logger,
        )

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        if self.use_hook_exception and self._error_logger:
            self._error_logger.error("Unexpected exception", exc_info=(exc_type, exc_value, exc_traceback))


class CleanTextFilter(logging.Filter):
    def filter(self, record):
        # Remove ASCII and tags from the message before logging
        record.msg = _remove_ascii_and_tags(record.msg)
        return True


def _remove_ascii_and_tags(text: str = "", case_sensitive: Literal["lower", "upper", "both"] = "lower"):
    text = _remove_ascii_color_codes(text)
    text = _remove_tags(text, case_sensitive=case_sensitive)
    return text

def _remove_ascii_color_codes(text):
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


def _remove_tags(text,
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

class TightLevelRichHandler(RichHandler):
    def get_level_text(self, record) -> Text:
        """Get the level name from the record.

        Args:
            record (LogRecord): LogRecord instance.

        Returns:
            Text: A tuple of the style and level name.
        """
        display_level_count = 3
        level_name = record.levelname

        short_level_name = record.levelname[0:display_level_count]

        level_text = Text.styled(
            short_level_name.ljust(display_level_count), f"logging.level.{level_name.lower()}"
        )
        return level_text


def print_logger_configurations(min_level="DEBUG"):
    from rich.console import Console
    from rich.table import Table
    from pawnlib.typing.constants import const

    if not min_level:
        raise ValueError(f"Required minimum log level, allows values - {const.get_level_keys()}")

    console = Console()
    table = Table(title=f"Logger Configurations , min_level={min_level}({const.get_level(min_level)})")

    # Add table columns
    table.add_column("Logger Name", style="cyan", overflow="fold")
    table.add_column("Effective Level", style="magenta")
    table.add_column("Propagate", style="red")
    table.add_column("Handlers Count", style="orange1")
    table.add_column("Handler ID", style="dim")
    table.add_column("Handler Type", style="green")
    table.add_column("Stream Dest.", style="yellow")
    table.add_column("Handler Level", style="purple")
    table.add_column("Formatter", style="blue")
    table.add_column("Filters", style="purple")

    for logger_name, logger in logging.root.manager.loggerDict.items():
        if logger_name == '':
            continue

        # Skip placeholder loggers
        if isinstance(logger, logging.PlaceHolder):
            console.print(f"[red]Logger Name: {logger_name} is a PlaceHolder and not initialized.[/red]")
            continue

        effective_level = logging.getLevelName(logger.getEffectiveLevel())
        propagate = str(logger.propagate)
        handlers_count = str(len(logger.handlers))

        if logger.getEffectiveLevel() >= const.get_level(min_level):

            if logger.handlers:
                for handler in logger.handlers:
                    handler_id = hex(id(handler))
                    handler_type = type(handler).__name__
                    handler_level = logging.getLevelName(handler.level)
                    formatter = handler.formatter._fmt if handler.formatter else "No formatter configured"
                    filters = ', '.join([str(f) for f in handler.filters]) if handler.filters else "No filters"

                    # Get stream destination for StreamHandlers
                    stream_dest = (
                        handler.stream.name if hasattr(handler, "stream") else "N/A"
                    )

                    # Add row with all info
                    table.add_row(
                        logger_name, effective_level, propagate, handlers_count,
                        handler_id, handler_type, stream_dest, handler_level,
                        formatter, filters
                    )
            else:
                table.add_row(logger_name, effective_level, propagate, handlers_count, "No handlers configured", "", "", "", "", "")

    console.print(table)

def list_all_loggers():
    return list(logging.root.manager.loggerDict.keys())

