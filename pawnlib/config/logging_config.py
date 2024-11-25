import sys
import logging
import os
from logging.handlers import TimedRotatingFileHandler
import re
from pawnlib.config.globalconfig import pawnlib_config, pawn, Null
from pawnlib.typing.constants import const
from rich.console import Console
from rich.traceback import Traceback
from datetime import datetime

try:
    from typing import Literal, Union
except ImportError:
    from typing_extensions import Literal, Union

LOG_LEVEL_SHORT = {
    "DEBUG": "DBG",
    "INFO": "INF",
    "WARNING": "WRN",
    "ERROR": "ERR",
    "CRITICAL": "CRT",
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
        simple_format (bool): Whether to use a simplified log format.
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
    def __init__(self, verbose=0, stdout=True, log_level_short=False, simple_format=False, exc_info=False, console=None):
        """
        Initialize the ConsoleLoggerHandler with customizable options.

        :param verbose: Verbosity level (0 for WARNING, 1 for INFO, 2 for DEBUG).
                        Default is 0.
        :type verbose: int
        :param stdout: Whether to output logs to standard output. Default is True.
        :type stdout: bool
        :param log_level_short: Whether to use short log level names. Default is False.
        :type log_level_short: bool
        :param simple_format: Whether to use a simplified log format. Default is False.
        :type simple_format: bool
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
            2: logging.DEBUG
        }.get(self.verbose, logging.DEBUG)

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
                "critical": "[bold magenta]CRIT[/bold magenta]",
                "error": "[bold red]ERROR[/bold red]",
                "warning": "[bold orange3]WARN[/bold orange3]",
                "info": "[bold green]INFO[/bold green]",
                "debug": "[bold yellow]DEBUG[/bold yellow]",
            }


            if self.simple_format:
                record_name = record.name
                record_name = record_name.split(".")[-1]
                message = f"<{record_name}> {message}"
            else:
                message = f"<{record.name}> {message}"

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

        # if isinstance(logger, ConsoleLoggerAdapter):
        #     raise ValueError("Cannot wrap a ConsoleLoggerAdapter inside another ConsoleLoggerAdapter")
        # self.logger = logger

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
        return const.VERBOSE_LEVELS.get(self.verbose_int, logging.DEBUG)

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
            return text.replace('[', r'\[').replace(']', r'\]')

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

    def __init__(self, fmt=None, datefmt=None, log_level_short=False, simple_format=False):
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
    :param simple_format: Whether to use a simplified format for the log record.
    :type simple_format: bool, optional
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

    def __init__(self, fmt=None, datefmt=None, log_level_short=False, simple_format=False, precision=4):
        """
        Initialize the formatter with optional precision for fractional seconds.

        :param fmt: The format string for the log message.
        :type fmt: str, optional
        :param datefmt: The format string for the date/time in the log message.
        :type datefmt: str, optional
        :param log_level_short: Whether to use short names for log levels (e.g., "E" for "ERROR").
        :type log_level_short: bool, optional
        :param simple_format: Whether to use a simplified format for the log record.
        :type simple_format: bool, optional
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


def setup_app_logger(
        log_type: str = 'console',
        verbose: int = 1,
        log_path: str = "./logs",
        app_name: str = "default",
        log_format: str = None,
        date_format: str = None,
        log_level: Union[int, str, None] = None,
        log_level_short: bool = True,
        simple_format: bool = False,
        exc_info: bool = False,
        rotate_time: str = 'midnight',  # Log rotation time (e.g., 'midnight', 'H', etc.)
        rotate_interval: int = 1,      # Rotation interval (e.g., 1 day, 1 hour)
        backup_count: int = 7,          # Number of backup files to keep
        clear_existing_handlers: bool = False,
):
    """
    Configures the application logger with specified settings.

    This function sets up logging for the application, allowing output to the console, files,
    or both. It supports features such as log level customization, log rotation, and detailed
    formatting with fractional seconds.

    :param log_type: The type of logging output ('console', 'file', or 'both').
    :type log_type: str
    :param verbose: Verbosity level (0=WARNING, 1=INFO, 2=DEBUG). Ignored if `log_level` is specified.
    :type verbose: int
    :param log_path: Directory path for log files.
    :type log_path: str
    :param app_name: Name of the application (used in log file naming).
    :type app_name: str
    :param log_format: Custom format string for log messages.
    :type log_format: str
    :param date_format: Custom date format string.
    :type date_format: str
    :param log_level: Explicit log level (e.g., 'DEBUG', 'INFO'). Overrides `verbose`.
    :type log_level: Union[int, str, None]
    :param log_level_short: Whether to use short names for log levels.
    :type log_level_short: bool
    :param simple_format: Whether to use a simplified format for the logs.
    :type simple_format: bool
    :param exc_info: Whether to include exception information in the logs.
    :type exc_info: bool
    :param rotate_time: Time interval for rotating logs (e.g., 'midnight', 'H').
    :type rotate_time: str
    :param rotate_interval: Number of intervals between rotations.
    :type rotate_interval: int
    :param backup_count: Number of backup files to retain.
    :type backup_count: int
    :param clear_existing_handlers: Whether to clear existing handlers before adding new ones.
    :type clear_existing_handlers: bool

    Example:

        .. code-block:: python

            # Set up a console logger with DEBUG level
            setup_app_logger(
                log_type='console',
                verbose=2,
                app_name='my_app',
                log_level='DEBUG'
            )

            # Set up a file logger with INFO level and daily rotation
            setup_app_logger(
                log_type='file',
                verbose=1,
                log_path='./logs',
                app_name='my_app',
                rotate_time='midnight',
                rotate_interval=1,
                backup_count=10
            )

            import logging

            logger = logging.getLogger()
            logger.info("This is an info message.")
            logger.debug("This is a debug message.")

            # or

            logger = logging.getLogger(__name__)
            logger.info("Start [bold red]Important[/bold red] process")

    """

    if log_type in ('file', 'both'):
        if not os.path.isdir(log_path):
            os.makedirs(log_path)

    if isinstance(log_level, str):
        log_level = log_level.upper()
        if log_level in logging._nameToLevel:
            effective_log_level = logging._nameToLevel[log_level]
        else:
            raise ValueError(f"Invalid `log_level` string provided: {log_level}")
    elif isinstance(log_level, int):
        effective_log_level = log_level
    elif log_level is None:
        effective_log_level = const.VERBOSE_LEVELS.get(verbose, logging.DEBUG)
    else:
        raise ValueError("`log_level` must be of type int or str.")

    root_logger = logging.getLogger()
    root_logger.setLevel(effective_log_level)

    if not log_format:
        log_format = '[%(asctime)s] %(levelname)s::%(filename)s/%(funcName)s(%(lineno)d) %(message)s'

    if clear_existing_handlers:
        root_logger.handlers.clear()

    if log_type in ('console', 'both') and not any(isinstance(h, ConsoleLoggerHandler) for h in root_logger.handlers):
        console_handler = ConsoleLoggerHandler(
            verbose=verbose,
            stdout=True,
            log_level_short=log_level_short,
            simple_format=simple_format,
            exc_info=exc_info
        )
        console_formatter = CleanAndDetailTimeFormatter(
            datefmt=date_format,
            log_level_short=log_level_short,
            simple_format=simple_format,
            precision=3,
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    if log_type in ('file', 'both') and not any(isinstance(h, TimedRotatingFileHandler) for h in root_logger.handlers):
        file_formatter = CleanAndDetailTimeFormatter(
            fmt=log_format,
            datefmt=date_format,
            log_level_short=log_level_short,
            simple_format=simple_format,
            precision=3,
        )
        log_filename = os.path.join(log_path, f"{app_name}.log")
        file_handler = TimedRotatingFileHandler(
            filename=log_filename,
            when=rotate_time,
            interval=rotate_interval,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    if not root_logger.handlers:
        raise ValueError("No handlers were added to the root logger. Please check your `log_type` parameter.")

    return root_logger


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


class LoggerMixin:
    def get_logger(self):
        """
        Returns a logger instance with a name in the format 'module_name.ClassName'.
        """
        return logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")

