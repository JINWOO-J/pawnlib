#!/usr/bin/env python3
import os
import logging
import sys
from logging import handlers
import traceback
import datetime
from pawnlib.config.globalconfig import pawnlib_config
from rich.logging import RichHandler
from typing import Callable

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


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

    AppLogger

    :param app_name: application name(=file name)
    :param log_level: log level
    :param log_path: log file path
    :param stdout: Enable stdout, Adding Hook for another library logging.
    :param markup: Enable markup for stdout logging.
    :param stdout_level: stdout log level
    :param stdout_log_formatter: stdout log formatter (function)
    :param log_format: log format / [%(asctime)s] %(name)s::" "%(filename)s/%(funcName)s(%(lineno)d) %(message)s
    :param use_hook_exception: Select whether to log exception errors.
    :param exception_handler: Exception handling function
    :param debug:

    Example:

        .. code-block:: python

            from pawnlib.utils import log

            app_logger, error_logger = log.AppLogger().get_logger()
            app_logger.info("This is a info message")
            error_logger.error("This is a info message")


    Example2:

        .. code-block:: python

            from pawnlib.config.globalconfig import pawnlib_config as pawn

            app_logger, error_logger = log.AppLogger(
                app_name="app",
                log_path="./logs",
                stdout=True
            ).set_global()

            pawn.app_logger.info("This is a info message")
            pawn.error_logger.error("This is a error message")

            # >>>
            [2022-07-25 18:52:44,415] INFO::app_logging_test.py/main(38) This is a info message
            [2022-07-25 18:52:44,416] ERROR::app_logging_test.py/main(39) This is a info message


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
                 debug: bool = False,
                 use_hook_exception: bool = True,
                 exception_handler: Callable = "",
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

        if self.use_hook_exception:
            if exception_handler:
                sys.excepthook = exception_handler
            else:
                sys.excepthook = self.handle_exception

        if log_format:
            self.log_format = log_format
        else:
            self.log_format = "[%(asctime)s] %(name)s::" "%(filename)s/%(funcName)s(%(lineno)d) %(message)s"

        self.log_formatter = logging.Formatter(self.log_format)

        self._logger = self.set_logger(self.log_level)
        self._error_logger = self.set_logger("ERROR")

    def get_realpath(self):
        path = os.path.dirname(os.path.abspath(__file__))
        parent_path = os.path.abspath(os.path.join(path, ".."))
        return parent_path

    def set_logger(self, log_type="INFO"):
        # log_path = f"{self.get_realpath()}/logs"
        # print(f"log_path={self.log_path}")
        if not os.path.isdir(self.log_path):
            os.mkdir(self.log_path)

        _logger = logging.getLogger(log_type)
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
        _logger.addHandler(file_handler)

        if self.stdout:
            from rich.text import Text
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
                format="%(message)s",
                handlers=[
                    RichHandler(
                        rich_tracebacks=True,
                        log_time_format=log_time_formatter,
                        markup=self.markup
                        # log_time_format=lambda dt: f"[{dt.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]}]",
                        # log_time_format=lambda dt:Text.from_markup(f"[red]{dt.ctime()}")
                    )
                ]
            )
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
