import inspect
import logging
import os
from logging.handlers import TimedRotatingFileHandler
import re
from pawnlib.config.globalconfig import pawnlib_config, pawn, Null
from pawnlib.typing.constants import const
from rich.console import Console
from rich.traceback import Traceback
from datetime import datetime
from contextlib import contextmanager

try:
    from typing import Literal, Union, Optional, Dict, List, Tuple
except ImportError:
    from typing_extensions import Literal, Union, Optional, Dict, List, Tuple

TRACE = 5
NO_LOG = logging.CRITICAL + 1
logging.addLevelName(TRACE, "TRACE")
logging.addLevelName(NO_LOG, "NO_LOG")

def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)

logging.Logger.trace = trace


def verbose_to_log_level(
        verbose: int,
        log_levels: Optional[Dict[int, int]] = None,
        clamp: bool = True
) -> int:
    """
    Convert a numeric verbose value to a corresponding logging level.

    By default:
    - verbose < 0 => CRITICAL+1 (즉, 어떤 로그도 표시되지 않음)
    - verbose=0 => WARNING
    - verbose=1 => INFO
    - verbose=2 => DEBUG
    - verbose>=3 => TRACE (기본 정의된 커스텀 레벨, 5)

    If `log_levels` is provided, it must be a dict mapping verbose -> logging level.
    If `clamp=True`, out-of-range verbose values are clamped to min/max keys in `log_levels`.

    :param verbose: Verbosity level (정수)
    :type verbose: int
    :param log_levels: (선택) 사용자 정의 맵핑 { verbose_value: logging_level }
    :type log_levels: dict or None
    :param clamp: True이면, verbose가 log_levels 범위를 벗어날 때 최소/최대 값에 맞춤
    :type clamp: bool
    :return: 로그 레벨 (ex: logging.DEBUG = 10)
    :rtype: int
    :raises ValueError: log_levels가 유효하지 않을 때
    """
    if log_levels is None:
        # 기본 맵핑 (negative => CRITICAL+1, 0=>WARNING, 1=>INFO, 2=>DEBUG, 3=>TRACE, ...)
        # 음수 키를 포함한 예시
        log_levels = {
            -1: logging.CRITICAL + 1,  # 어떤 로그도 찍히지 않게 하는 수준
            0: logging.WARNING,
            1: logging.INFO,
            2: logging.DEBUG,
            3: TRACE,
        }

    if not log_levels or not isinstance(log_levels, dict):
        raise ValueError("log_levels must be a non-empty dictionary.")

    # 모든 key를 정렬해서 min/max를 구함
    sorted_keys = sorted(log_levels.keys())
    min_key, max_key = sorted_keys[0], sorted_keys[-1]

    # clamp=True면, verbose가 min_key보다 작으면 min_key로, max_key보다 크면 max_key로
    if clamp:
        if verbose < min_key:
            verbose = min_key
        elif verbose > max_key:
            verbose = max_key

    # 만약 clamp=False라면, 범위 밖인 verbose에 대한 처리 로직(디폴트값?)을 직접 정의하거나,
    # 여기서 ValueError를 던질 수도 있음. 아래는 예시로 min_key, max_key로 clamp.
    else:
        if not (min_key <= verbose <= max_key):
            raise ValueError(f"Verbose out of range [{min_key}, {max_key}]: {verbose}")

    # 최종적으로 log_levels에서 매핑된 값을 얻어옴
    # 혹시 verbose가 정확히 매핑되지 않았다면, 바로 이전/이후 key로 매핑하는 등의 추가 로직 가능
    # 여기서는 단순히 dict.get() 사용
    if verbose in log_levels:
        return log_levels[verbose]
    else:
        # 만약 clamp 됐는데 exact key 매핑이 없으면, 가장 근접한 key를 찾는 로직을 추가해도 됨
        # 여기서는 안전하게 min_key로 fallback
        return log_levels[min_key]


def verbose_to_log_level(
        verbose: int,
        log_levels: Optional[Dict[int, int]] = None,
        clamp: bool = True
) -> int:
    """
    Convert a numeric verbose value to a corresponding logging level.

    기본 맵핑 (예시):
      0 -> CRITICAL+1  (아무 로그도 출력되지 않게)
      1 -> WARNING
      2 -> INFO
      3 -> DEBUG
      4 -> TRACE
    그 이상(>4)일 때도 4와 같은 취급 (clamp=True일 때)

    :param verbose: Verbosity level (정수)
    :param log_levels: 사용자 지정 맵핑 {verbose: logging_level}
                       None이면 아래 default 사용.
    :param clamp: 범위를 벗어난 verbose 값이 들어오면 min/max로 clamp할지 여부
    :return: 대응되는 파이썬 로깅 레벨 수치
    """
    if log_levels is None:
        # "0이면 로그를 전혀 남기지 않는다." → CRITICAL+1
        # log_levels = {
        #     0: NO_LOG,  # effectively no logs
        #     1: logging.WARNING,
        #     2: logging.INFO,
        #     3: logging.DEBUG,
        #     4: TRACE,                # 커스텀 TRACE level
        # }

        log_levels = {
            -1: NO_LOG,
            0: logging.WARNING,
            1: logging.INFO,
            2: logging.DEBUG,
            3: TRACE,
        }

    if not log_levels or not isinstance(log_levels, dict):
        raise ValueError("log_levels must be a non-empty dictionary.")

    sorted_keys = sorted(log_levels.keys())
    min_key, max_key = sorted_keys[0], sorted_keys[-1]

    # clamp=True → 범위 밖 verbose는 min_key, max_key로 보정
    if clamp:
        if verbose < min_key:
            verbose = min_key
        elif verbose > max_key:
            verbose = max_key
    else:
        # clamp=False → 범위 벗어나면 예외 발생
        if not (min_key <= verbose <= max_key):
            raise ValueError(f"Verbose out of range [{min_key}, {max_key}]: {verbose}")

    return log_levels.get(verbose, logging.CRITICAL + 1)  # fallback


LOG_LEVEL_SHORT = {
    "DEBUG": "DBG",
    "INFO": "INF",
    "WARNING": "WRN",
    "ERROR": "ERR",
    "CRITICAL": "CRT",
    "TRACE": "TRA",
}

VALID_RICH_TAGS = {
    'red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'white', 'black',
    'bright_red', 'bright_green', 'bright_blue', 'bright_yellow', 'bright_magenta', 'bright_cyan', 'bright_white', 'bright_black',
    'bold', 'italic', 'underline', 'blink', 'reverse', 'strike', 'dim', 'conceal',
    'overline', 'frame', 'encircle', 'box', 'squiggly', 'double_underline',
    'link',
    'success', 'warning', 'danger', 'info', 'critical',
    'markdown', 'code', 'quote', 'bullet', 'number',
    'table', 'panel', 'rule', 'padding', 'align', 'columns', 'rows',
    'superscript', 'subscript',
    'emoji', 'task', 'progress', 'spinner', 'status',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
}

# # Add TRACE log level globally
# TRACE_LEVEL_NUM = 5  # TRACE is lower than DEBUG
# logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
#
# def trace(self, message, *args, **kwargs):
#     if self.isEnabledFor(TRACE_LEVEL_NUM):
#         self._log(TRACE_LEVEL_NUM, message, args, **kwargs)
#
# logging.Logger.trace = trace
#

class PreciseTimeFormatter(logging.Formatter):
    """
    A custom logging formatter that overrides the `formatTime` method to include
    microseconds up to 4 decimal places in the timestamp.

    Methods:
        formatTime(record, datefmt=None):
            Formats the time of a log record, appending microseconds with 4 decimal places.

    Example:

        .. code-block:: python

            import logging
            from datetime import datetime

            logger = logging.getLogger("example_logger")
            handler = logging.StreamHandler()
            formatter = PreciseTimeFormatter()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            logger.info("This is an info message.")
    """
    def formatTime(self, record, datefmt=None):
        """
        Override formatTime to include microseconds up to 4 decimal places.

        :param record: The log record containing the timestamp.
        :type record: logging.LogRecord
        :param datefmt: Optional date format string.
        :type datefmt: str, optional
        :return: Formatted time string.
        :rtype: str
        """
        ct = self.converter(record.created)
        if datefmt:
            s = datetime.fromtimestamp(record.created).strftime(datefmt)
        else:
            t = datetime.fromtimestamp(record.created)
            s = t.strftime("%Y-%m-%d %H:%M:%S")
            # Append milliseconds with 4 decimal places
            s += f".{t.microsecond / 1000000:.4f}"[1:]
        return s


class PawnConsoleHandler(logging.Handler):
    """
    A custom logging handler that sends formatted log messages to `pawn.console`
    with appropriate styling based on the log level.

    Methods:
        emit(record):
            Processes and sends the log record to `pawn.console`.

    Example:

        .. code-block:: python

            import logging

            logger = logging.getLogger("example_logger")
            handler = PawnConsoleHandler()
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            logger.debug("Debug message.")
            logger.info("Info message.")
            logger.warning("Warning message.")
            logger.error("Error message.")
            logger.critical("Critical message.")
    """
    def emit(self, record):
        """
        Emit a log record by formatting it and sending it to `pawn.console`.

        :param record: The log record to be emitted.
        :type record: logging.LogRecord
        """
        try:
            # Format the record using the handler's formatter
            msg = self.format(record)

            # Send the message to pawn.console with appropriate styling
            if record.levelno >= logging.CRITICAL:
                pawn.console.log(f"[bold red]CRITICAL[/bold red]: {msg}")
            elif record.levelno >= logging.ERROR:
                pawn.console.log(f"[red]ERROR[/red]: {msg}")
            elif record.levelno >= logging.WARNING:
                pawn.console.log(f"[yellow]WARNING[/yellow]: {msg}")
            elif record.levelno >= logging.INFO:
                pawn.console.log(f"[cyan]INFO[/cyan]: {msg}")
            elif record.levelno >= logging.DEBUG:
                pawn.console.debug(f"[green]DEBUG[/green]: {msg}")
            else:
                pawn.console.log(msg)
        except Exception:
            self.handleError(record)


class ConsoleLoggerHandler(logging.Handler):
    """
    A custom logging handler for enhanced console output with verbosity, formatting, and exception handling options.

    Attributes:
        verbose (int): Verbosity level (0 for WARNING, 1 for INFO, 2 for DEBUG).
        stdout (bool): Whether to output logs to standard output.
        console (object): The console object used for output (default is `pawn.console`).
        log_level_short (bool): Whether to use short log level names.
        simple_format (str): Formatting level ("none", "minimal", "detailed", "advanced", "custom").
        exc_info (bool): Whether to include exception information in logs.

    Methods:
        emit(record):
            Processes and sends the log record to `pawn.console`.

    Example:

        .. code-block:: python

            import logging

            logger = logging.getLogger("example_logger")

            # Initialize handler with verbosity level and other options
            handler = ConsoleLoggerHandler(verbose=2, stdout=True, log_level_short=True)

            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)

            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            try:
                1 / 0
            except ZeroDivisionError as e:
                logger.error("An error occurred!", exc_info=True)

            logger.debug("Debugging details.")
    """
    def __init__(self, verbose=0, stdout=True, log_level_short=False, simple_format="minimal", exc_info=False, console=None):
        """
        Initialize the ConsoleLoggerHandler with customizable options.

        :param verbose: Verbosity level (0 for WARNING, 1 for INFO, 2 for DEBUG).
                        Default is 0.
        :type verbose: int
        :param stdout: Whether to output logs to standard output. Default is True.
        :type stdout: bool
        :param log_level_short: Whether to use short log level names. Default is False.
        :type log_level_short: bool
        :param simple_format: Formatting code level ("none", "minimal", "detailed", "advanced", "custom"). Default is minimal.
        :type simple_format: str
        :param exc_info: Whether to include exception information in logs. Default is False.
        :type exc_info: bool
        :param console: The console object used for output. Default is `pawn.console`.
                        If None, it defaults to `pawn.console`.
        :type console: object, optional
        """
        super().__init__()
        self.verbose = verbose
        self.stdout = stdout
        self.console = console or pawn.console
        self.log_level = self._get_log_level()
        self.log_level_short = log_level_short
        self.simple_format = simple_format
        self.exc_info = exc_info

    def _get_log_level(self):
        """
        Determine the appropriate log level based on verbosity.

        :return: The corresponding log level.
                 WARNING for verbosity 0,
                 INFO for verbosity 1,
                 DEBUG for verbosity 2 or higher.
                 Defaults to DEBUG if verbosity is unrecognized.
        :rtype: int
        """
        return {
            0: logging.WARNING,
            1: logging.INFO,
            2: logging.DEBUG,
            3: TRACE
        }.get(self.verbose, logging.DEBUG)

    def _get_code_info(self, record):
        """
        Generate code information based on the selected simple_format.

        :param record: The log record.
        :return: Formatted code info string.
        """
        if self.simple_format == "none":
            return ""
        elif self.simple_format == "minimal":
            return f"<{record.name.split('.')[-1]}> "
        elif self.simple_format == "detailed":
            return f"<{record.name.split('.')[-1]}:{record.lineno}> "
        elif self.simple_format == "advanced":
            file_name = os.path.basename(record.pathname) if record.name == "root" else record.name
            # return f"<{file_name}:{record.lineno} [dim]{record.funcName}()[/dim]> "
            return f"<{file_name}[dim]{record.funcName}({record.lineno})[/dim]> "
        elif self.simple_format == "custom" and callable(self.simple_format):
            return self.simple_format(record)  # Expect a custom function
        else:
            return ""  # Default for unsupported formats

    def emit(self, record):
        """
        Emit a log record by formatting it and sending it to `pawn.console`.

        :param record: The log record to be emitted.
        :type record: logging.LogRecord
        """
        try:
            message = self.format(record)
            message = escape_non_tag_brackets(message)
            level = record.levelname.lower()

            if self.log_level_short:
                _level = LOG_LEVEL_SHORT.get(record.levelname.upper(), record.levelname)
            else:
                _level = level

            level_tags = {
                "CRT": "[bold magenta]CRT[/bold magenta]",
                "ERR": "[bold red]ERR[/bold red]",
                "WRN": "[bold orange3]WRN[/bold orange3]",
                "INF": "[bold green]INF[/bold green]",
                "DBG": "[bold yellow]DBG[/bold yellow]",
                "TRA": "[bold cyan]TRA[/bold cyan]",

                "critical": "[bold magenta]CRIT[/bold magenta]",
                "error": "[bold red]ERROR[/bold red]",
                "warning": "[bold orange3]WARN[/bold orange3]",
                "info": "[bold green]INFO[/bold green]",
                "debug": "[bold yellow]DEBUG[/bold yellow]",

                "trace": "[bold cyan]trace[/bold cyan]",
            }
            code_info = self._get_code_info(record)
            if code_info:
                message = f"{code_info:<16}{message}"

            tag = level_tags.get(_level, "[green]INFO[/green]")
            if level == "error":
                if record.exc_info or self.exc_info:
                    exception_traceback = Traceback.from_exception(*record.exc_info) if record.exc_info else None
                    if exception_traceback:
                        self.console.print(exception_traceback)
                    else:
                        self.console.log(f"{tag} {message}")
                else:
                    self.console.log(f"{tag} {message}")
            elif level == "debug" and pawn.get('PAWN_DEBUG'):
                self.console.debug(message)
            elif level == "trace":
                self.console.log(f"{tag} {message}")
            else:
                self.console.log(f"{tag} {message}")
        except Exception:
            self.handleError(record)


class ConsoleLoggerAdapter:
    # global_verbose = 0  # Class-level verbosity to control all instances
    # instances = []  # Keep track of all instances
    _global_registry = {}  # Global registry to track all adapters by name

    def __init__(
            self,
            logger: Union[logging.Logger, Console, Null, None] = None,
            logger_name: str = "",
            verbose: Union[bool, int] = False,
            stdout: bool = False
    ):
        """
        Wrapper class to unify logging methods for logging.Logger and rich.Console.

        :param logger: The logger object (logging.Logger, rich.Console, or Null)
        :param logger_name: Name of the logger
        :param verbose: Verbosity level (bool or int).
                        If False: WARNING level (default)
                        If True: INFO level
                        If 1: INFO level
                        If 2: DEBUG level
        """
        # Determine log level based on verbose parameter using constants
        if isinstance(verbose, bool):
            self.verbose_int = int(verbose)
        elif isinstance(verbose, int):
            self.verbose_int = verbose
        else:
            self.verbose_int = 0  # Default to 0 if invalid type

        self.logger_name = logger_name

        # Cap the verbose level to the max defined level
        max_verbose_level = max(const.VERBOSE_LEVELS.keys())

        if self.verbose_int > max_verbose_level:
            self.verbose_int = max_verbose_level

        self.log_level = const.VERBOSE_LEVELS.get(self.verbose_int, logging.DEBUG)
        self.verbose = self.verbose_int

        self.stdout = stdout

        if isinstance(logger, ConsoleLoggerAdapter):
            self.logger = logger.logger
        else:
            self.logger = logger

        if self.logger is None:
            self.logger = self._create_default_logger(self.logger_name)
        elif isinstance(self.logger, Null):
            self.logger = pawn.console
            pawn.console.log("[red][ERROR][/red] Logger instance is Null. Using default logger.")

        if isinstance(self.logger, logging.Logger):
            self.logger.setLevel(self.log_level)

            if not self.stdout:
                self.logger.propagate = False

        ConsoleLoggerAdapter._global_registry[logger_name] = self

    def _get_log_level(self):
        """
        Determine log level based on verbosity.
        """
        # return logging.DEBUG if self.verbose > 1 else logging.INFO if self.verbose == 1 else logging.WARNING
        return const.VERBOSE_LEVELS.get(self.verbose_int, TRACE)

    @classmethod
    def get_adapter_logger(cls, name: str) -> "ConsoleLoggerAdapter":
        """
        Retrieve an adapter by name or create a new one if it does not exist.
        """
        if name in cls._global_registry:
            return cls._global_registry[name]
        else:
            # Create a new adapter if it doesn't exist
            new_adapter = ConsoleLoggerAdapter(logger_name=name)
            cls._global_registry[name] = new_adapter
            return new_adapter

    @classmethod
    def set_global_verbose(cls, new_verbose: int):
        """
        Update the verbosity level of all registered adapters.
        """
        pawn.console.log(cls._global_registry)
        for adapter in cls._global_registry.values():
            adapter.verbose = new_verbose
            adapter.verbose_int = new_verbose
            adapter.log_level = adapter._get_log_level()
            if isinstance(adapter.logger, logging.Logger):
                adapter.logger.setLevel(adapter._get_log_level())
        print(f"Global verbosity set to {new_verbose}")

    def _create_default_logger(self, logger_name="") -> logging.Logger:
        """
        Create a default logger if none is provided.
        """
        logger = logging.getLogger(logger_name)
        # if not self.stdout:
        logger.propagate = False
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s <%(name)s> %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(self.log_level)

        return logger

    def _escape_non_tag_brackets(self, message: str) -> str:
        """
        Escape non-rich-tag '[' in the message without altering rich tags.

        :param message: The log message.
        :return: The message with non-rich-tag '[' escaped.
        """
        result = ''
        i = 0
        length = len(message)

        while i < length:
            if message[i] == '[':
                # Possible start of a tag
                tag_match = re.match(r'\[/?([a-zA-Z0-9 _-]+)\]', message[i:])
                if tag_match:
                    tag_content = tag_match.group(1)
                    # Check if all parts of the tag are valid
                    tag_parts = tag_content.split()
                    if all(part in VALID_RICH_TAGS for part in tag_parts):
                        # It's a valid rich tag, copy it as is
                        tag_text = tag_match.group(0)
                        result += tag_text
                        i += len(tag_text)
                    else:
                        # Not a valid rich tag, escape the '['
                        result += r'\['
                        i += 1
                else:
                    # Not a tag, escape the '['
                    result += r'\['
                    i += 1
            else:
                result += message[i]
                i += 1

        return result

    def _should_log(self, level_name: str) -> bool:
        """
        Check if a message should be logged based on the current logging level.
        """
        level_value = getattr(logging, level_name.upper(), logging.INFO)
        return level_value >= self.log_level

    def _log(self, message: str, level: str = "info", stacklevel=None, exc_info: bool = False):
        """
        Internal method to handle logging for both Logger and Console.
        """
        if not isinstance(message, str):
            message = str(message)

        level = level.lower()
        if not self._should_log(level):
            return

        if stacklevel is None:
            stack_offset = self._get_stack_offset()
        else:
            stack_offset = stacklevel

        if isinstance(self.logger, logging.Logger):
            # getattr(self.logger, level, self.logger.info)(message, stacklevel=stack_offset)
            if exc_info:
                self.logger.error(message, exc_info=True, stacklevel=stacklevel or 3)
            else:
                getattr(self.logger, level, self.logger.info)(message, stacklevel=stacklevel or 3)

        elif isinstance(self.logger, Console):
            if exc_info:
                self.logger.log(f"[red] {message}[/red]")
                self.logger.print_exception()
            else:
                message = self._escape_non_tag_brackets(message)  # Escape brackets in the message

                level_tags = {
                    "critical": "[bold red]CRIT[/bold red]",
                    "error": "[red]ERROR[/red]",
                    "warning": "[yellow]WARN[/yellow]",
                    "info": "[cyan]INFO[/cyan]",
                    "debug": "[green]DEBUG[/green]",
                }

                tag = level_tags.get(level, "[cyan]INFO[/cyan]")
                if level == "debug" and pawn.get('PAWN_DEBUG'):
                    self.logger.debug(message, _stack_offset=4)
                else:
                    self.logger.log(f" {tag}<{stack_offset}> {message}", _stack_offset=stack_offset)
        else:
            pass  # Do nothing if logger type is unknown

    def _get_stack_offset(self) -> int:
        # Return the appropriate stack offset
        return 3

    def exception(self, message: str, stacklevel=None, exc_info=True):
        """
        Log an exception with the error level and include the traceback.
        """
        self._log(message, level="error", exc_info=exc_info, stacklevel=stacklevel)

    # Public methods for common logging levels
    def critical(self, message: str, stacklevel=None):
        self._log(message, "critical", stacklevel=stacklevel)

    def error(self, message: str, stacklevel=None, exc_info=False):
        self._log(message, "error", stacklevel=stacklevel, exc_info=exc_info)

    def warn(self, message: str, stacklevel=None):
        self._log(message, "warning", stacklevel=stacklevel)

    def warning(self, message: str, stacklevel=None):
        self._log(message, "warning", stacklevel=stacklevel)

    def info(self, message: str, stacklevel=None):
        self._log(message, "info", stacklevel=stacklevel)

    def debug(self, message: str, stacklevel=None):
        self._log(message, "debug", stacklevel=stacklevel)

    def __repr__(self):
        """
        Return a string representation of the ConsoleLoggerAdapter showing the type of logger used and log level.
        """
        logger_type = self._get_logger_type(self.logger)
        log_level_name = logging.getLevelName(self.log_level)
        return f"<ConsoleLoggerAdapter '{self.logger_name}', logger_type={logger_type}, verbose={self.verbose_int}, log_level={log_level_name}>"

    def _get_logger_type(self, logger):
        """
        Helper method to recursively determine the type of the logger.
        """
        if isinstance(logger, ConsoleLoggerAdapter):
            return self._get_logger_type(logger.logger)
        elif isinstance(logger, logging.Logger):
            return "Logger"
        elif isinstance(logger, Console):
            return "Console"
        elif isinstance(logger, Null):
            return "Null"
        else:
            return type(logger).__name__


def escape_non_tag_brackets(message: str) -> str:
    """
    Escape '[' and ']' that are not part of a valid Rich tag.

    :param message: The log message.
    :return: The message with non-tag brackets escaped.
    """
    def replace_bracket(match):
        text = match.group(0)
        if re.match(r'\[/?([a-zA-Z0-9 _-]+)\]', text):
            return text  # Valid tag
        else:
            # return text.replace('[', r'\[').replace(']', r'\]')
            return text.replace('[', r'\[')

    return re.sub(r'\[.*?\]', replace_bracket, message)


class BaseFormatter(logging.Formatter):
    """
    A custom logging formatter that provides additional flexibility for log formatting.

    This formatter allows customization of log level display, simple formatting, and
    time formatting. It also cleans the log message by removing rich tags.

    :param fmt: The format string for the log message.
    :type fmt: str, optional
    :param datefmt: The format string for the date/time in the log message.
    :type datefmt: str, optional
    :param log_level_short: Whether to use short names for log levels (e.g., "E" for "ERROR").
    :type log_level_short: bool, optional
    :param simple_format: Whether to use a simplified format for the log record.
    :type simple_format: bool, optional

    Methods:
        - formatTime(record, datefmt=None): Formats the timestamp of the log record.
        - format(record): Cleans and reformats the log record message.

    Example:

        .. code-block:: python

            import logging

            # Define a custom formatter
            formatter = BaseFormatter(
                fmt="%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                log_level_short=True
            )

            # Create a logger and handler
            logger = logging.getLogger("example_logger")
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            # Log messages
            logger.info("This is an info message.")
            logger.error("This is an error message with <rich> tags.")
    """

    def __init__(self, fmt=None, datefmt=None, log_level_short=False, simple_format="minimal"):
        super().__init__(fmt, datefmt)
        self.log_level_short = log_level_short
        self.simple_format = simple_format

    def formatTime(self, record, datefmt=None):
        """
        Format the timestamp of a log record.

        If a custom `datefmt` is provided, it will be used to format the time.
        Otherwise, it defaults to "YYYY-MM-DD HH:MM:SS".

        :param record: The log record containing the timestamp.
        :type record: logging.LogRecord
        :param datefmt: Optional custom format string for the timestamp.
        :type datefmt: str, optional
        :return: The formatted timestamp as a string.
        :rtype: str
        """
        ct = self.converter(record.created)
        if datefmt:
            return datetime.fromtimestamp(record.created).strftime(datefmt)
        else:
            t = datetime.fromtimestamp(record.created)
            return t.strftime("%Y-%m-%d %H:%M:%S")

    def format(self, record):
        """
        Clean and reformat the log record message.

        This method cleans the original message by removing rich tags and optionally
        modifies other attributes of the log record based on initialization parameters.

        :param record: The original log record to be formatted.
        :type record: logging.LogRecord
        :return: The formatted log message as a string.
        :rtype: str
        """
        try:
            original_message = record.getMessage()
            clean_message = remove_rich_tags(original_message)

            record_copy = logging.makeLogRecord(record.__dict__)
            record_copy.msg = clean_message
            record_copy.args = ()

            if self.log_level_short:
                record_copy.levelname = LOG_LEVEL_SHORT.get(record.levelname.upper(), record.levelname)

            return super().format(record_copy)
        except Exception as e:
            return f"Logging error: {e}"


class CleanFormatter(BaseFormatter):
    """
    A subclass of `BaseFormatter` with no additional functionality.

    This class inherits all features from `BaseFormatter` without any modifications,
    making it suitable for cases where no further customization is required.

    Example:

        .. code-block:: python

            import logging

            # Define a clean formatter
            formatter = CleanFormatter(
                fmt="%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

            # Create a logger and handler
            logger = logging.getLogger("clean_logger")
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

            # Log messages
            logger.info("This is a clean info message.")
    """
    pass


class CleanAndDetailTimeFormatter(BaseFormatter):
    """
    A custom logging formatter that extends `BaseFormatter` to include detailed time formatting
    with fractional seconds precision.

    This formatter allows customization of log level display, simple formatting, and time formatting,
    with the added ability to specify the number of decimal places for fractional seconds.

    :param fmt: The format string for the log message.
    :type fmt: str, optional
    :param datefmt: The format string for the date/time in the log message.
    :type datefmt: str, optional
    :param log_level_short: Whether to use short names for log levels (e.g., "E" for "ERROR").
    :type log_level_short: bool, optional
    :param simple_format: Formatting code level ("none", "minimal", "detailed", "advanced", "custom"). Default is minimal.
    :type simple_format: str
    :param precision: The number of decimal places for fractional seconds in the timestamp.
                      Defaults to 4.
    :type precision: int, optional

    Methods:
        - formatTime(record, datefmt=None): Formats the timestamp of the log record with fractional seconds.

    Example:

        .. code-block:: python

            import logging

            # Define a custom formatter with fractional second precision
            formatter = CleanAndDetailTimeFormatter(
                fmt="%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                precision=6
            )

            # Create a logger and handler
            logger = logging.getLogger("detailed_logger")
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)

            # Log messages
            logger.info("This is an info message.")
            logger.error("This is an error message with detailed time.")
    """

    def __init__(self, fmt=None, datefmt=None, log_level_short=False, simple_format="minimal", precision=4):
        """
        Initialize the formatter with optional precision for fractional seconds.

        :param fmt: The format string for the log message.
        :type fmt: str, optional
        :param datefmt: The format string for the date/time in the log message.
        :type datefmt: str, optional
        :param log_level_short: Whether to use short names for log levels (e.g., "E" for "ERROR").
        :type log_level_short: bool, optional
        :param simple_format: Formatting code level ("none", "minimal", "detailed", "advanced", "custom"). Default is minimal.
        :type simple_format: str
        :param precision: The number of decimal places for fractional seconds in the timestamp.
                          Defaults to 4.
        :type precision: int, optional
        """
        super().__init__(fmt, datefmt, log_level_short, simple_format)
        self.precision = precision

    def formatTime(self, record, datefmt=None):
        """
        Format the timestamp of a log record with fractional seconds.

        If a custom `datefmt` is provided, it will be used to format the time. Otherwise,
        it defaults to "YYYY-MM-DD HH:MM:SS" with fractional seconds formatted to the specified precision.

        :param record: The log record containing the timestamp.
        :type record: logging.LogRecord
        :param datefmt: Optional custom format string for the timestamp.
        :type datefmt: str, optional
        :return: The formatted timestamp as a string.
        :rtype: str
        """
        ct = self.converter(record.created)
        if datefmt:
            s = datetime.fromtimestamp(record.created).strftime(datefmt)
        else:
            t = datetime.fromtimestamp(record.created)
            s = t.strftime("%Y-%m-%d %H:%M:%S")
            fractional_seconds = f"{t.microsecond / 1_000_000:.{self.precision}f}"[1:]
            # s += fractional_seconds
            s += fractional_seconds.replace(".", ",")  # Replace decimal point with a comma
        return s


def remove_rich_tags(message: str) -> str:
    """
    Removes valid Rich tags from the given message while leaving invalid tags intact.

    This function scans the input message for Rich-style tags (e.g., `[tag]` or `[/tag]`),
    validates them against a predefined list of valid tags, and removes only the valid ones.
    Invalid tags are preserved in the output.

    :param message: The input string containing Rich-style tags.
    :type message: str
    :return: The message with valid Rich tags removed.
    :rtype: str

    Example:

        .. code-block:: python

            # Example usage
            message = "This is a [bold]bold[/bold] and [invalid]invalid[/invalid] tag example."
            clean_message = remove_rich_tags(message)
            print(clean_message)
            # Output: "This is a bold and [invalid]invalid[/invalid] tag example."
    """
    tag_re = re.compile(r'\[/?([a-zA-Z0-9 _-]+)\]')

    def is_valid_tag(tag_content: str) -> bool:
        """
        Checks if the given tag content is valid based on predefined valid tags.

        :param tag_content: The content of the tag to validate.
        :type tag_content: str
        :return: True if the tag is valid, False otherwise.
        :rtype: bool
        """
        tag_parts = tag_content.strip().split()
        return all(part in VALID_RICH_TAGS for part in tag_parts)

    result = ''
    pos = 0
    while pos < len(message):
        match = tag_re.match(message, pos)
        if match:
            tag_content = match.group(1)
            if is_valid_tag(tag_content):
                pos = match.end()  # Skip valid tags
            else:
                result += match.group(0)  # Keep invalid tags
                pos = match.end()
        else:
            result += message[pos]
            pos += 1
    return result


class AppOrEnabledFilter(logging.Filter):
    """
    A logging filter that allows log records to pass if their logger name
    starts with a specified application name or exactly matches a logger name
    in an explicit enabled list.
    """
    def __init__(self, app_prefixes: List[str], enabled_list: list = None, name: str = ''):
        """
        Initializes the filter.

        :param app_prefixes: A list of application name prefixes. Loggers whose names exactly match any of these prefixes or start with any of these prefixes followed by a dot (e.g., 'myapp' or 'myapp.module') will be allowed.
        :type app_prefixes: List[str]
        :param enabled_list: An optional list of specific logger names that should always be enabled, regardless of the `app_prefixes`.
        :type enabled_list: list, optional
        :param name: The name of the filter. This is passed to the parent logging.Filter class.
        :type name: str, optional

        Example:

            .. code-block:: python

                filter1 = AppOrEnabledFilter(app_prefixes=['my_app'], enabled_list=['httpx'])
                filter2 = AppOrEnabledFilter(app_prefixes=['my_app', 'another_app'])
        """
        super().__init__(name)
        self.app_prefixes_dot = tuple(f"{prefix}." for prefix in app_prefixes)
        self.app_names = tuple(app_prefixes)
        self.enabled_list = set(enabled_list or [])

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determines whether the given log record should be output.

        The record passes if:
        - The record's logger name is exactly one of `self.app_names` (e.g., 'oci_tools'), OR
        - The record's logger name starts with one of `self.app_prefixes_dot` (e.g., 'oci_tools.sub'), OR
        - The record's logger name is found in `self.enabled_list` (e.g., 'httpx' if 'httpx' is in `enabled_list`).

        :param record: The log record to evaluate.
        :type record: logging.LogRecord
        :returns: True if the record should be processed, False otherwise.
        :rtype: bool

        Example:

            .. code-block:: python

                # Assuming filter initialized with app_prefixes=['my_app'], enabled_list=['external_lib']
                record1 = logging.LogRecord(name='my_app', level=logging.INFO, pathname='', lineno=0, msg='Test', args=(), exc_info=None)
                filter.filter(record1)
                # >> True

                record2 = logging.LogRecord(name='my_app.sub_module', level=logging.INFO, pathname='', lineno=0, msg='Test', args=(), exc_info=None)
                filter.filter(record2)
                # >> True

                record3 = logging.LogRecord(name='external_lib', level=logging.INFO, pathname='', lineno=0, msg='Test', args=(), exc_info=None)
                filter.filter(record3)
                # >> True

                record4 = logging.LogRecord(name='another_lib', level=logging.INFO, pathname='', lineno=0, msg='Test', args=(), exc_info=None)
                filter.filter(record4)
                # >> False

                # Assuming filter initialized with app_prefixes=['appA', 'appB']
                record5 = logging.LogRecord(name='appB', level=logging.INFO, pathname='', lineno=0, msg='Test', args=(), exc_info=None)
                filter.filter(record5)
                # >> True

                record6 = logging.LogRecord(name='appB.component', level=logging.INFO, pathname='', lineno=0, msg='Test', args=(), exc_info=None)
                filter.filter(record6)
                # >> True
        """
        if record.name in self.app_names or record.name.startswith(self.app_prefixes_dot):
            return True
        if self.enabled_list and record.name in self.enabled_list:
            return True
        return False


def setup_app_logger(
    app_name: Union[str, List[str]],
    log_type: str = 'console',
    verbose: int = 1,
    log_path: str = "./logs",
    log_format: str = None,
    date_format: str = None,
    log_level: Union[int, str, None] = None,
    clear_existing_handlers: bool = True,
    configure_root: bool = False,
    propagate: bool = False,
    enabled_third_party_loggers: Optional[List[str]] = None,
    log_all_third_party: bool = False,
    log_level_short: bool = True,
    simple_format: Union[str, bool] = "detailed",
    exc_info: bool = False,
    rotate_time: str = 'midnight',
    rotate_interval: int = 1,
    backup_count: int = 7,
    handle_propagate: bool = False,
    propagate_scope: str = 'all'
):
    """
    Configures and sets up a Python logger for an application, addressing filtering
    and duplicate output issues while maintaining backward compatibility.
    The function operates in two modes based on the `configure_root` parameter.

    :param app_name: The name(s) of the application. Can be a single string or a list of strings. Used for naming the logger(s) and the log file. If a list, the first item is used for the log file name.
    :type app_name: Union[str, List[str]]
    :param log_type: Specifies where logs should be output. Can be 'console', 'file', or 'both'. Defaults to 'console'.
    :type log_type: str
    :param verbose: Verbosity level, an integer from 0 to 5. Higher values mean more detailed logs. This is translated to a logging level if `log_level` is not explicitly set. Defaults to 1.
    :type verbose: int
    :param log_path: The directory where log files will be stored if `log_type` includes 'file'. Defaults to "./logs".
    :type log_path: str
    :param log_format: The format string for log messages. If None, a default format is used.
    :type log_format: str, optional
    :param date_format: The format string for the date/time in log messages. If None, a default is used.
    :type date_format: str, optional
    :param log_level: The logging level to set (e.g., logging.INFO, 'DEBUG'). Overrides `verbose` if provided.
    :type log_level: Union[int, str, None]
    :param clear_existing_handlers: If True, clears all existing handlers from the logger before adding new ones. This primarily applies when `configure_root` is False. Defaults to True.
    :type clear_existing_handlers: bool
    :param configure_root: If True, configures the root logger. This enables a centralized logging approach with filtering. If False, configures a named logger (based on `app_name`). Defaults to False.
    :type configure_root: bool
    :param propagate: Whether messages from the `app_name` logger will be passed to ancestor loggers. Only applies when `configure_root` is False. Defaults to False.
    :type propagate: bool
    :param enabled_third_party_loggers: A list of names of specific third-party loggers that should always be enabled, even if `log_all_third_party` is False. Applies when `configure_root` is True.
    :type enabled_third_party_loggers: Optional[List[str]]
    :param log_all_third_party: If True, all log messages from any logger (including third-party) will be processed by the handlers. If False and `configure_root` is True, only logs from `app_name` (or `app_prefixes`) and specified `enabled_third_party_loggers` will pass through the filter. Defaults to False.
    :type log_all_third_party: bool
    :param log_level_short: If True, uses a short form for log levels in the console output (e.g., 'D' for DEBUG).
    :type log_level_short: bool
    :param simple_format: Controls the detail level of the default format for console. Can be "detailed", True (for a simpler format), or False (for the most basic format).
    :type simple_format: Union[str, bool]
    :param exc_info: If True, exception information is added to log records. This is passed to the ConsoleLoggerHandler.
    :type exc_info: bool
    :param rotate_time: When to rotate log files. Options like 'midnight', 'H' (hourly), 'M' (minutes). Only applies if `log_type` includes 'file'.
    :type rotate_time: str
    :param rotate_interval: The interval for log file rotation (e.g., 1 for daily rotation if `rotate_time` is 'midnight'). Only applies if `log_type` includes 'file'.
    :type rotate_interval: int
    :param backup_count: The number of old log files to keep. Only applies if `log_type` includes 'file'.
    :type backup_count: int
    :param handle_propagate: If True, automatically adjusts propagation settings for other loggers based on `propagate_scope` to prevent duplicate output.
    :type handle_propagate: bool
    :param propagate_scope: Defines the scope for `handle_propagate`. Can be 'all' or other specific scopes relevant to pawnlib.
    :type propagate_scope: str
    :returns: The configured logger instance, typically for the first `app_name` in the list if `app_name` is a list, or the single `app_name` string.
    :rtype: logging.Logger

    Example:

        .. code-block:: python

            import logging
            import os
            # Assuming pawnlib.utils.log module is available or its components are imported
            # from pawnlib.utils.log import setup_app_logger, verbose_to_log_level, ConsoleLoggerHandler, CleanAndDetailTimeFormatter, AppOrEnabledFilter, change_propagate_setting
            # from logging.handlers import TimedRotatingFileHandler

            # Example 1: Basic console logger for a single app name
            logger1 = setup_app_logger(app_name="my_application", log_type="console", verbose=3)
            logger1.info("This is an informational message from my_application.")
            logging.getLogger("another_module").debug("This message will not show by default if configure_root is False.")

            # Example 2: File logger with rotation for a specific app
            logger2 = setup_app_logger(
                app_name="file_app",
                log_type="file",
                log_path="./my_logs",
                log_level="WARNING",
                rotate_time='D', # Daily rotation
                backup_count=5
            )
            logger2.warning("This warning goes to a file.")
            logger2.info("This info message will not appear due to WARNING level.")

            # Example 3: Centralized root logger with multiple app prefixes and third-party filtering
            # Logs for 'main_app', 'sub_component', and 'httpx' will be processed
            root_logger = setup_app_logger(
                app_name=["main_app", "sub_component"],
                log_type="console",
                configure_root=True,
                log_level="DEBUG", # Root logger gets DEBUG, effective level for 'main_app' and 'sub_component' is DEBUG
                enabled_third_party_loggers=['httpx', 'sqlalchemy']
            )
            logging.getLogger("main_app").info("Main app message.")
            logging.getLogger("sub_component.core").debug("Sub component debug message.")
            logging.getLogger("httpx").info("HTTPX library message.")
            logging.getLogger("requests").warning("Requests library message (should be filtered out).")
            logging.getLogger("sqlalchemy.engine").info("SQLAlchemy engine message.")


            # Example 4: Centralized root logger logging ALL messages
            all_logs_logger = setup_app_logger(
                app_name="catch_all_app",
                log_type="console",
                configure_root=True,
                log_level="INFO",
                log_all_third_party=True
            )
            logging.getLogger("catch_all_app").info("My app's info.")
            logging.getLogger("any_library_name").debug("Debug from any library, will show because log_all_third_party is True and root is DEBUG.")
    """
    if log_level is not None:
        effective_log_level = log_level.upper() if isinstance(log_level, str) else log_level
    else:
        effective_log_level = verbose_to_log_level(verbose)

    app_prefixes = [app_name] if isinstance(app_name, str) else app_name

    target_logger = logging.getLogger() if configure_root else logging.getLogger(app_prefixes[0])

    if configure_root:
        target_logger.handlers.clear()
        target_logger.setLevel(logging.DEBUG)
        for prefix in app_prefixes:
            logging.getLogger(prefix).setLevel(effective_log_level)
    else:
        target_logger.propagate = propagate
        if clear_existing_handlers:
            target_logger.handlers.clear()
        if propagate:

            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                is_console_conflict = (log_type in ('console', 'both') and isinstance(handler, logging.StreamHandler))
                is_file_conflict = (log_type in ('file', 'both') and isinstance(handler, logging.FileHandler))
                if is_console_conflict or is_file_conflict:
                    root_logger.removeHandler(handler)
        target_logger.setLevel(effective_log_level)

    if log_type in ('console', 'both'):
        if not any(isinstance(h, ConsoleLoggerHandler) for h in target_logger.handlers):
            console_handler = ConsoleLoggerHandler(
                verbose=verbose, stdout=True, log_level_short=log_level_short,
                simple_format=simple_format, exc_info=exc_info
            )
            console_formatter = CleanAndDetailTimeFormatter( # fmt 인자 없이 호출
                datefmt=date_format, log_level_short=log_level_short,
                simple_format=simple_format, precision=3,
            )
            console_handler.setFormatter(console_formatter)
            target_logger.addHandler(console_handler)

    if log_type in ('file', 'both'):
        if not any(isinstance(h, TimedRotatingFileHandler) for h in target_logger.handlers):
            if not log_format: # 파일 포맷 기본값 설정
                log_format = '[%(asctime)s] %(levelname)s - %(name)s:%(lineno)d - %(message)s'
            file_formatter = CleanAndDetailTimeFormatter( # fmt 인자를 포함하여 호출
                fmt=log_format, datefmt=date_format, log_level_short=log_level_short,
                simple_format=simple_format, precision=3,
            )
            os.makedirs(log_path, exist_ok=True)
            log_filename = os.path.join(log_path, f"{app_prefixes[0]}.log")
            file_handler = TimedRotatingFileHandler(
                filename=log_filename, when=rotate_time, interval=rotate_interval,
                backupCount=backup_count, encoding='utf-8'
            )
            file_handler.setFormatter(file_formatter)
            target_logger.addHandler(file_handler)

    if configure_root and not log_all_third_party:
        app_filter = AppOrEnabledFilter(app_prefixes, enabled_third_party_loggers)
        for handler in target_logger.handlers:
            # 모든 핸들러에 필터를 동일하게 적용
            handler.addFilter(app_filter)

    if handle_propagate:
        change_propagate_setting(
            propagate=propagate, propagate_scope=propagate_scope,
            log_level=effective_log_level
        )

    return logging.getLogger(app_prefixes[0])


def setup_logger(logger=None, name: str = "", verbose: Union[bool, int] = False):
    """
    Setup or reuse a logger.

    This function will reuse an existing logger if provided, otherwise it will create a new one.

    :param logger: Existing logger to reuse. If None, a new logger will be created inside ConsoleLoggerAdapter.
    :param name: Name of the logger.
    :param verbose: Verbosity level.
    :return: A ConsoleLoggerAdapter instance.
    """

    if isinstance(logger, ConsoleLoggerAdapter):
        return logger  # Reuse the existing ConsoleLoggerAdapter if already provided.
    elif isinstance(logger, logging.Logger):
        return logger
    return ConsoleLoggerAdapter(logger, name, verbose)


def getPawnLogger(name=None, verbose=0):
    """
    Return a logger with the specified name, creating it if necessary.
    It will reuse an existing logger if it exists.
    """
    if name in ConsoleLoggerAdapter._global_registry:
        return ConsoleLoggerAdapter._global_registry[name]

    # Create new adapter and register it
    new_logger = ConsoleLoggerAdapter(logger_name=name, verbose=verbose)
    ConsoleLoggerAdapter._global_registry[name] = new_logger
    return new_logger


def add_logger(cls):
    """
    Decorator to add a logger attribute to a class.
    """
    class Wrapped(cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
    return Wrapped


def get_logger(name=None, level=logging.INFO):
    """
    Returns a logger instance.
    If `name` is not provided, it defaults to the caller's module name.
    """

    if name is None:
        frame = inspect.currentframe().f_back
        name = frame.f_globals["__name__"]

    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    logger.setLevel(level)
    return logger


class LoggerMixin:
    # def get_logger(self):
    #     """
    #     Returns a logger instance with a name in the format 'module_name.ClassName'.
    #     """
    #     return logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")

    def get_logger(self):
        """
        Returns a logger instance with a name in the format 'module_name.ClassName'.
        """
        logger_name = f"{self.__module__}.{self.__class__.__name__}"
        logger = logging.getLogger(logger_name)
        if not logger.handlers:
            logger.addHandler(logging.NullHandler())
        return logger

def change_log_level(new_level, logger=None):
    """
    Change the log level of the specified logger or the root logger.

    :param new_level: New log level (e.g., 'DEBUG', 'INFO').
    :param logger: Logger instance to modify. If None, modifies the root logger.
    """
    if logger is None:
        logger = logging.getLogger()  # Default to root logger

    if isinstance(new_level, str):
        new_level = new_level.upper()
        if new_level in logging._nameToLevel:
            logger.setLevel(logging._nameToLevel[new_level])
        else:
            raise ValueError(f"Invalid log level: {new_level}")
    elif isinstance(new_level, int):
        logger.setLevel(new_level)
    else:
        raise ValueError("Log level must be a string or integer.")


class LoggerFactory:
    """
    A factory class for creating and managing loggers with console and file output.

    Supports configuration of loggers with console and/or file handlers, customizable log formats,
    and global settings for level and format. Handles propagation and temporary settings via context managers.

    :param _loggers: Dictionary of logger instances, keyed by logger name
    :type _loggers: dict
    :param _global_log_level: Global logging level applied to all loggers if `use_global_level` is True
    :type _global_log_level: int or None
    :param _use_global_level: Flag to enforce global log level across all loggers
    :type _use_global_level: bool
    :param _global_simple_format: Default format style for console output ('detailed' or 'minimal')
    :type _global_simple_format: str
    :param _global_filters: List of filter functions applied to all loggers
    :type _global_filters: list
    :param _global_handler_configs: List of dictionaries containing handler type and configuration
    :type _global_handler_configs: list
    :param _propagate: Whether log messages propagate to parent loggers
    :type _propagate: bool
    :param _propagate_scope: Scope for applying propagation settings ('all' by default)
    :type _propagate_scope: str

    .. code-block:: python

        # Example usage
        import logging
        from  import LoggerFactory

        # Basic logger with both console and file output
        logger = LoggerFactory.create_app_logger(
            log_type='both',
            verbose=2,
            app_name='MyApp',
            log_path='./logs'
        )
        logger.info("Application started")
        logger.debug("Debug message")
        # Console Output:
        # [INF] <MyApp:XX> Application started
        # [DBG] <MyApp:XX> Debug message
        # File Output (./logs/MyApp.log):
        # [2025-03-12 10:00:00,123] INF::main.py/main(XX) Application started
        # [2025-03-12 10:00:00,124] DBG::main.py/main(XX) Debug message

        # Sub-logger with inherited settings
        sub_logger = LoggerFactory.get_logger('MyApp.sub', verbose=2)
        sub_logger.info("Sub logger message")
        # Console Output:
        # [INF] <MyApp.sub:XX> Sub logger message

        # Temporary settings with context manager
        with LoggerFactory.temporary_settings(log_level=1, simple_format='minimal'):
            temp_logger = LoggerFactory.get_logger('MyApp.temp')
            temp_logger.info("Temporary info message")
            temp_logger.debug("This debug won't appear")
        # Console Output:
        # [INF] Temporary info message

        # Adjust logger level
        LoggerFactory.adjust_logger_level('MyApp', verbose=1)
        logger.debug("This debug won't appear after level change")
    """
    _loggers = {}
    _global_log_level = None
    _use_global_level = False
    _global_simple_format = "detailed"
    _global_filters = []
    _global_handler_configs = [{"type": ConsoleLoggerHandler, "kwargs": {"stdout": True, "log_level_short": True}}]
    _propagate = False
    _propagate_scope = 'all'
    _global_logging_enabled = False

    @classmethod
    def enable_global_logging(cls, enabled: bool = True):
        cls._global_logging_enabled = enabled
        # 전역 설정 변경 시 모든 로거 업데이트
        for logger in cls._loggers.values():
            if enabled and not logger.handlers:  # 핸들러가 없으면 추가
                for handler in cls._create_handlers(verbose=0):
                    logger.addHandler(handler)
            elif not enabled:  # 비활성화 시 핸들러 제거
                logger.handlers.clear()
                logger.setLevel(NO_LOG)

    @classmethod
    def create_app_logger(
            cls,
            log_type: str = 'console',
            verbose: int = 1,
            log_path: str = "./logs",
            app_name: str = "default",
            log_format: str = None,
            date_format: str = '%Y-%m-%d %H:%M:%S',
            log_level: Union[int, str, None] = None,
            log_level_short: bool = True,
            simple_format: str = "detailed",
            exc_info: bool = False,
            rotate_time: str = 'midnight',
            rotate_interval: int = 1,
            backup_count: int = 7,
            clear_existing_handlers: bool = True,
            propagate: bool = None
    ) -> logging.Logger:
        """
        Configure and return an application logger.

        :param log_type: Type of logging ('console', 'file', or 'both')
        :type log_type: str
        :param verbose: Verbosity level (0=WARNING, 1=INFO, 2=DEBUG)
        :type verbose: int
        :param log_path: Directory path for log files
        :type log_path: str
        :param app_name: Name of the logger
        :type app_name: str
        :param log_format: Custom log format string (default: detailed timestamp format)
        :type log_format: str, optional
        :param date_format: Date format for log timestamps
        :type date_format: str
        :param log_level: Logging level as int or str (e.g., 'INFO')
        :type log_level: int or str, optional
        :param log_level_short: Use short level names (e.g., INF)
        :type log_level_short: bool
        :param simple_format: Formatting code level ("none", "minimal", "detailed", "advanced", "custom"). Default is minimal.
        :type simple_format: str
        :param exc_info: Include exception info in logs
        :type exc_info: bool
        :param rotate_time: When to rotate logs (e.g., 'midnight')
        :type rotate_time: str
        :param rotate_interval: Interval for log rotation
        :type rotate_interval: int
        :param backup_count: Number of backup log files to keep
        :type backup_count: int
        :param clear_existing_handlers: Clear existing handlers before adding new ones
        :type clear_existing_handlers: bool
        :param propagate: Set propagation behavior (overrides class default if provided)
        :type propagate: bool, optional
        :return: Configured logger instance
        :rtype: logging.Logger
        :raises ValueError: If no handlers are added to the logger

        Example:

            .. code-block:: python

                from pawnlib.config import create_app_logger

                # Set up a console logger with DEBUG level
                logger_console = create_app_logger(
                    log_type='console',
                    verbose=2,
                    app_name='my_app',
                    log_level='DEBUG'
                )

                logger_console.info("Start [bold red]Important[/bold red] process")

                # Set up a file logger with INFO level and daily rotation
                logger = create_app_logger(
                    log_type='file',
                    verbose=1,
                    log_path='./logs',
                    app_name='my_app',
                    rotate_time='midnight',
                    rotate_interval=1,
                    backup_count=10
                )

                logger.info("This is an info message.")
                logger.debug("This is a debug message.")

        """

        if log_type in ('file', 'both'):
            if not os.path.isdir(log_path):
                os.makedirs(log_path)

        # 로깅 레벨 결정
        if isinstance(log_level, str):
            log_level = logging._nameToLevel.get(log_level.upper(), logging.INFO)
        elif log_level is None:
            log_level = verbose_to_log_level(verbose)

        # 로거 생성 및 설정
        logger = logging.getLogger(app_name)
        logger.setLevel(log_level)
        if propagate is not None:
            cls._propagate = propagate

        logger.propagate = cls._propagate
        if clear_existing_handlers:
            logger.handlers.clear()  # 기존 핸들러 제거로 중복 방지

        # 기본 로그 포맷 설정
        if not log_format:
            log_format = '[%(asctime)s,%(msecs)03d] %(levelname)s::%(filename)s/%(funcName)s(%(lineno)d) %(message)s'

        # # simple_format에 따른 콘솔 포맷 설정
        # if simple_format == "detailed":
        #     console_fmt = '[%(levelname)s] <%(name)s:%(lineno)d> %(message)s'
        # elif simple_format == "minimal":
        #     console_fmt = '[%(levelname)s] %(message)s'
        # else:
        #     console_fmt = log_format

        # 포매터 생성
        console_formatter = CleanAndDetailTimeFormatter(datefmt=date_format, log_level_short=log_level_short)
        file_formatter = CleanAndDetailTimeFormatter(fmt=log_format, datefmt=date_format, log_level_short=log_level_short)

        # _global_handler_configs 초기화 및 핸들러 설정
        cls._global_handler_configs = []
        if (verbose >= 0 or cls._global_logging_enabled) and log_type in ('console', 'both'):
            console_handler = ConsoleLoggerHandler(
                verbose=verbose,
                stdout=True,
                log_level_short=log_level_short,
                simple_format=simple_format,
                exc_info=exc_info
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            cls._global_handler_configs.append({
                "type": ConsoleLoggerHandler,
                "kwargs": {
                    "verbose": verbose,
                    "stdout": True,
                    "log_level_short": log_level_short,
                    "simple_format": simple_format,
                    "exc_info": exc_info,
                },
            })

        if (verbose >= 0 or cls._global_logging_enabled) and log_type in ('file', 'both'):
            log_filename = os.path.join(log_path, f"{app_name}.log")
            file_handler = TimedRotatingFileHandler(
                filename=log_filename,
                when=rotate_time,
                interval=rotate_interval,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            cls._global_handler_configs.append({
                "type": TimedRotatingFileHandler,
                "kwargs": {
                    "filename": log_filename,
                    "when": rotate_time,
                    "interval": rotate_interval,
                    "backupCount": backup_count,
                    "encoding": 'utf-8',
                },
                "formatter": file_formatter
            })

        if not logger.handlers and (verbose >= 0 or cls._global_logging_enabled):
            raise ValueError(f"No handlers added for logger '{app_name}' despite enabled logging.")

        cls._loggers[app_name] = logger
        cls._global_simple_format = simple_format
        if cls._use_global_level and cls._global_log_level is not None:
            logger.setLevel(cls._global_log_level)
            for handler in logger.handlers:
                handler.setLevel(cls._global_log_level)

        return logger
        # if log_type in ('console', 'both'):
        #     console_handler = ConsoleLoggerHandler(
        #         verbose=verbose,
        #         stdout=True,
        #         log_level_short=log_level_short,
        #         simple_format=simple_format,
        #         exc_info=exc_info
        #     )
        #     console_handler.setFormatter(console_formatter)
        #     logger.addHandler(console_handler)
        #     cls._global_handler_configs.append({
        #         "type": ConsoleLoggerHandler,
        #         "kwargs": {
        #             "verbose": verbose,
        #             "stdout": True,
        #             "log_level_short": log_level_short,
        #             "simple_format": simple_format,
        #             "exc_info": exc_info,
        #         },
        #         # "formatter": console_formatter  # 포매터 별도 저장
        #     })
        #
        # if log_type in ('file', 'both'):
        #     log_filename = os.path.join(log_path, f"{app_name}.log")
        #     file_handler = TimedRotatingFileHandler(
        #         filename=log_filename,
        #         when=rotate_time,
        #         interval=rotate_interval,
        #         backupCount=backup_count,
        #         encoding='utf-8'
        #     )
        #     file_handler.setFormatter(file_formatter)  # 파일 핸들러에 포매터 설정
        #     logger.addHandler(file_handler)
        #     cls._global_handler_configs.append({
        #         "type": TimedRotatingFileHandler,
        #         "kwargs": {
        #             "filename": log_filename,
        #             "when": rotate_time,
        #             "interval": rotate_interval,
        #             "backupCount": backup_count,
        #             "encoding": 'utf-8',
        #         },
        #         "formatter": file_formatter  # 포매터 별도 저장
        #     })
        #
        # if not logger.handlers:
        #     raise ValueError(f"No handlers added for logger '{app_name}'.")
        #
        # cls._loggers[app_name] = logger
        # cls._global_simple_format = simple_format
        # if cls._use_global_level and cls._global_log_level is not None:
        #     logger.setLevel(cls._global_log_level)
        #     for handler in logger.handlers:
        #         handler.setLevel(cls._global_log_level)
        #
        # return logger

    @classmethod
    def set_global_log_level(cls, verbose=0, use_global: bool = True):
        """
        Set global logging level and enforce it across all loggers.

        :param verbose: Verbosity level (0=WARNING, 1=INFO, 2=DEBUG)
        :type verbose: int
        :param use_global: Enforce global level on all loggers
        :type use_global: bool
        """
        log_level = verbose_to_log_level(verbose)
        cls._global_log_level = log_level
        cls._use_global_level = use_global
        for logger in cls._loggers.values():
            logger.setLevel(log_level)
            for handler in logger.handlers:
                handler.setLevel(log_level)

    @classmethod
    def set_global_simple_format(cls, simple_format: str):
        """
        Set global simple format for console handlers.

        :param simple_format: Format style ('detailed', 'minimal')
        :type simple_format: str
        """
        cls._global_simple_format = simple_format
        for logger in cls._loggers.values():
            for handler in logger.handlers:
                if isinstance(handler, ConsoleLoggerHandler):
                    handler.simple_format = simple_format

    @classmethod
    def add_global_filter(cls, filter_func):
        """
        Add a global filter to all loggers.

        :param filter_func: Filter function to apply to log records
        :type filter_func: callable
        """
        cls._global_filters.append(filter_func)
        for logger in cls._loggers.values():
            for f in cls._global_filters:
                logger.addFilter(f)

    @classmethod
    def add_global_handler(cls, handler_type, **kwargs):
        """
        Add a global handler to all loggers.

        :param handler_type: Type of handler to add (e.g., ConsoleLoggerHandler)
        :type handler_type: type
        :param kwargs: Keyword arguments for handler initialization
        """
        cls._global_handler_configs.append({"type": handler_type, "kwargs": kwargs})
        for logger in cls._loggers.values():
            handler = handler_type(**kwargs)
            logger.addHandler(handler)
            handler.setLevel(cls._global_log_level or logging.WARNING)

    @classmethod
    def clear_unused_loggers(cls):
        """
        Remove unused loggers from the factory.
        """
        active_loggers = {}
        for name, logger in cls._loggers.items():
            if logger.manager.getLogger(name) is logger:
                active_loggers[name] = logger
        cls._loggers = active_loggers

    @classmethod
    def adjust_logger_level(cls, name: str, verbose: int):
        """
        Adjust the logging level for a specific logger.

        :param name: Name of the logger to adjust
        :type name: str
        :param verbose: Verbosity level (0=WARNING, 1=INFO, 2=DEBUG)
        :type verbose: int
        :raises ValueError: If the logger is not found
        """
        logger = cls._loggers.get(name)
        if logger:
            log_level = verbose_to_log_level(verbose)
            logger.setLevel(log_level)
            for handler in logger.handlers:
                handler.setLevel(log_level)
        else:
            raise ValueError(f"Logger '{name}' not found.")

    @classmethod
    def get_global_settings(cls):
        """
        Get current global settings of the factory.

        :return: Dictionary containing global settings
        :rtype: dict
        """
        return {
            "log_level": cls._global_log_level,
            "use_global_level": cls._use_global_level,
            "simple_format": cls._global_simple_format,
            "logger_count": len(cls._loggers),
            "filters": [f.__name__ for f in cls._global_filters],
            "handlers": [config["type"].__name__ for config in cls._global_handler_configs],
            "global_logging_enabled": cls._global_logging_enabled
        }

    @classmethod
    @contextmanager
    def temporary_settings(cls, log_level=None, simple_format=None):
        """
        Temporarily adjust global settings within a context.

        :param log_level: Temporary log level
        :type log_level: int, optional
        :param simple_format: Temporary simple format
        :type simple_format: str, optional
        :yield: Context for temporary settings
        :rtype: None
        """
        original_level = cls._global_log_level
        original_format = cls._global_simple_format
        original_use_global = cls._use_global_level

        if log_level is not None:
            cls.set_global_log_level(verbose_to_log_level(log_level), use_global=True)
        if simple_format is not None:
            cls.set_global_simple_format(simple_format)

        try:
            yield
        finally:
            cls._global_log_level = original_level
            cls._global_simple_format = original_format
            cls._use_global_level = original_use_global
            for logger in cls._loggers.values():
                # logger.setLevel(original_level or logging.WARNING)
                logger.setLevel(original_level or NO_LOG)
                for handler in logger.handlers:
                    handler.setLevel(original_level or NO_LOG)
                    if isinstance(handler, ConsoleLoggerHandler):
                        handler.simple_format = original_format

    @classmethod
    def _create_handlers(cls, verbose=0, simple_format=None):
        """
        Create handlers based on global configurations.

        :param verbose: Verbosity level for handlers
        :type verbose: int
        :param simple_format: Override simple format for console handlers
        :type simple_format: str, optional
        :return: List of configured handlers
        :rtype: list
        """
        handlers = []
        for config in cls._global_handler_configs:
            handler_type = config["type"]
            kwargs = config["kwargs"]
            if handler_type == ConsoleLoggerHandler:
                kwargs = kwargs.copy()
                kwargs.update({
                    "verbose": verbose,
                    "simple_format": cls._global_simple_format if simple_format is None else simple_format
                })
            handler = handler_type(**kwargs)
            if "formatter" in config:
                handler.setFormatter(config["formatter"])  # 저장된 포매터 적용
            for f in cls._global_filters:
                handler.addFilter(f)
            handlers.append(handler)
        return handlers

    # @classmethod
    # def get_logger(cls, name, verbose=0, simple_format=None):
    #     """
    #     Get or create a logger with specified settings.
    #
    #     :param name: Name of the logger
    #     :type name: str
    #     :param verbose: Verbosity level (0=WARNING, 1=INFO, 2=DEBUG)
    #     :type verbose: int
    #     :param simple_format: Override simple format for console handlers
    #     :type simple_format: str, optional
    #     :return: Configured logger instance
    #     :rtype: logging.Logger
    #     """
    #     logger = cls._loggers.get(name)
    #     if not logger:
    #         logger = logging.getLogger(name)
    #         logger.propagate = cls._propagate
    #         # 기존 핸들러가 없으면 새 핸들러 추가
    #         if not logger.handlers and verbose >= 0:
    #             for handler in cls._create_handlers(verbose, simple_format):
    #                 logger.addHandler(handler)
    #         cls._loggers[name] = logger
    #
    #     log_level = cls._global_log_level if cls._use_global_level and cls._global_log_level is not None else verbose_to_log_level(verbose)
    #     if logger.level != log_level:
    #         logger.setLevel(log_level)
    #         for handler in logger.handlers:
    #             handler.setLevel(log_level)
    #
    #     return logger
    @classmethod
    def get_logger(cls, name, verbose=0, simple_format=None):
        logger = cls._loggers.get(name)
        if not logger:
            logger = logging.getLogger(name)
            logger.propagate = cls._propagate
            # 변경: verbose >= 0 또는 전역 설정 활성화 시에만 핸들러 추가
            if not logger.handlers and (verbose >= 0 or cls._global_logging_enabled):
                for handler in cls._create_handlers(verbose, simple_format):
                    logger.addHandler(handler)
            cls._loggers[name] = logger

        log_level = cls._global_log_level if cls._use_global_level and cls._global_log_level is not None else verbose_to_log_level(verbose)
        if logger.level != log_level:
            logger.setLevel(log_level)
            for handler in logger.handlers:
                handler.setLevel(log_level)

        return logger

    # 신규 추가: 특정 로거의 핸들러 제거 메서드
    @classmethod
    def clear_handlers(cls, name: str):
        """특정 로거의 모든 핸들러를 제거하고 로깅 비활성화"""
        logger = cls._loggers.get(name)
        if logger:
            logger.handlers.clear()
            logger.setLevel(NO_LOG)
        else:
            raise ValueError(f"Logger '{name}' not found.")

    # 신규 추가: 모든 로거의 핸들러 제거 메서드
    @classmethod
    def clear_all_handlers(cls):
        """모든 로거의 핸들러를 제거하고 로깅 비활성화"""
        for logger in cls._loggers.values():
            logger.handlers.clear()
            logger.setLevel(NO_LOG)


class LoggerMixinVerbose:
    """
    A mixin class for initializing loggers in classes with customizable verbosity and format.

    Provides a method to set up a logger either by inheriting an existing logger or creating a new one
    using `LoggerFactory`. Ensures the logger is properly configured with handlers, levels, and propagation settings.

    Example:

        .. code-block:: python

            # Example usage
            from pawnlib.config import LoggerMixinVerbose, LoggerFactory

            # Define a class using the mixin
            class MyClass(LoggerMixinVerbose):
                def __init__(self, verbose=1):
                    self.init_logger(verbose=verbose)

            # Basic usage with LoggerFactory
            obj = MyClass(verbose=2)
            obj.logger.info("Class initialized")
            # Output:
            # [INF] <__main__.MyClass:XX> Class initialized

            # Using an existing logger
            parent_logger = LoggerFactory.create_app_logger(log_type='console', verbose=1, app_name='Parent')
            obj_with_parent = MyClass(verbose=0)
            obj_with_parent.init_logger(logger=parent_logger)
            obj_with_parent.logger.info("Using parent logger")
            # Output:
            # [INF] <Parent:XX> Using parent logger
    """
    def init_logger(self, logger: Optional[logging.Logger] = None, verbose: int = 0, simple_format: Optional[str] = None):
        """
        Initialize or update the logger for the class instance.

        :param logger: Existing logger to inherit handlers and level from
        :type logger: logging.Logger, optional
        :param verbose: Verbosity level (0=WARNING, 1=INFO, 2=DEBUG)
        :type verbose: int
        :param simple_format: Override simple format for console handlers ('detailed', 'minimal')
        :type simple_format: str, optional
        """
        log_level = verbose_to_log_level(verbose)

        # if not hasattr(self, 'logger') or self.logger is None:
        #     if logger and isinstance(logger, logging.Logger):
        #         self.logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        #         self.logger.handlers = logger.handlers
        #         self.logger.setLevel(logger.level)
        #         self.logger.propagate = False
        #     elif logger and isinstance(logger, Console):
        #         self.logger = ConsoleLoggerAdapter(logger, "name", verbose)
        #     else:
        #         self.logger = LoggerFactory.get_logger(f"{self.__module__}.{self.__class__.__name__}", verbose, simple_format)

        if not hasattr(self, 'logger') or self.logger is None:
            if logger and isinstance(logger, logging.Logger):
                self.logger = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
                self.logger.handlers = logger.handlers
                self.logger.setLevel(log_level)
                self.logger.propagate = False

            elif logger and isinstance(logger, Console):
                self.logger = ConsoleLoggerAdapter(logger, "name", verbose)
            else:
                self.logger = LoggerFactory.get_logger(
                    name=f"{self.__module__}.{self.__class__.__name__}",
                    verbose=verbose,
                    simple_format=simple_format
                )
        else:
            self.logger.setLevel(log_level)
            self.logger.propagate = False

        if hasattr(self.logger, 'handlers') and self.logger.handlers:
            for handler in self.logger.handlers:
                if handler:
                    handler.setLevel(log_level)



def change_propagate_setting(propagate: bool = True, propagate_scope: str = 'all', log_level: int = None, pawnlib_level: int = None, third_party_level: int = None):
    """
    Change the propagation settings and log levels for all registered loggers.

    Allows modification of propagation behavior and log levels across all loggers, with scoping options
    to target all loggers, only `pawnlib` loggers, or third-party loggers.

    :param propagate: Whether loggers should propagate messages to parent loggers
    :type propagate: bool
    :param propagate_scope: Scope for applying propagation ('all', 'pawnlib', 'third_party')
    :type propagate_scope: str
    :param log_level: Log level to apply when scope is 'all'
    :type log_level: int, optional
    :param pawnlib_level: Log level for `pawnlib` loggers when scope is 'pawnlib' or 'third_party'
    :type pawnlib_level: int, optional
    :param third_party_level: Log level for non-`pawnlib` loggers when scope is 'pawnlib' or 'third_party'
    :type third_party_level: int, optional
    :raises ValueError: If `propagate_scope` is not one of 'all', 'pawnlib', or 'third_party'

    Example:

        .. code-block:: python

            # Example usage
            from pawnlib.config import change_propagate_setting, LoggerFactory

            # Create some loggers
            app_logger = LoggerFactory.create_app_logger(log_type='console', verbose=1, app_name='MyApp')
            pawn_logger = LoggerFactory.get_logger('pawnlib.utils', verbose=2)
            third_logger = LoggerFactory.get_logger('external.lib', verbose=1)

            # Change propagation for all loggers
            change_propagate_setting(propagate=False, propagate_scope='all', log_level=20)
            app_logger.info("No propagation")
            # Output:
            # [INF] <MyApp:XX> No propagation

            # Change propagation for pawnlib loggers only
            change_propagate_setting(propagate=True, propagate_scope='pawnlib', pawnlib_level=10, third_party_level=30)
            pawn_logger.debug("Pawnlib debug with propagation")
            third_logger.debug("Third-party debug suppressed")
            # Output:
            # [DBG] <pawnlib.utils:XX> Pawnlib debug with propagation
    """
    valid_scopes = ['all', 'pawnlib', 'third_party']
    if propagate_scope not in valid_scopes:
        raise ValueError(f"Invalid propagate_scope: {propagate_scope}")

    for logger_name, logger_instance in logging.Logger.manager.loggerDict.items():
        if isinstance(logger_instance, logging.Logger):
            # Propagate 설정
            if propagate_scope == 'all':
                logger_instance.propagate = propagate
                level = log_level
            elif propagate_scope == 'pawnlib':
                logger_instance.propagate = propagate if logger_name.startswith('pawnlib') else not propagate
                level = pawnlib_level if logger_name.startswith('pawnlib') else third_party_level
            elif propagate_scope == 'third_party':
                logger_instance.propagate = propagate if not logger_name.startswith('pawnlib') else not propagate
                level = third_party_level if not logger_name.startswith('pawnlib') else pawnlib_level

            if level is not None:
                logger_instance.setLevel(level)
                if logger_name.startswith('pawnlib'):
                    pawn.console.log(f"logger_name={logger_instance}, level={level}")
                for handler in logger_instance.handlers:
                    handler.setLevel(level)


create_app_logger = LoggerFactory.create_app_logger
# setup_app_logger = LoggerFactory.create_app_logger
