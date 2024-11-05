from pawnlib.config.globalconfig import pawnlib_config, pawn, Null
from pawnlib.typing.constants import const
from rich.console import Console
import logging
import re

try:
    from typing import Literal, Union
except ImportError:
    from typing_extensions import Literal, Union


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
        # level_name = logging.getLevelName(self.log_level)  # 'INFO'

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

    # ConsoleLoggerAdapter.instances.append(self)  # Track instance
    # def _get_log_level(self):
    #     """Determine log level based on verbosity."""
    #     return logging.DEBUG if self.verbose > 1 else logging.INFO if self.verbose == 1 else logging.WARNING

    # @classmethod
    # def set_global_verbose(cls, new_verbose):
    #     """Set global verbosity for all instances."""
    #     cls.global_verbose = new_verbose
    #     for instance in cls.instances:
    #         instance.verbose = new_verbose
    #         instance.logger.setLevel(instance._get_log_level())
        # pawn.console.log(f"Global verbose updated to {new_verbose}")

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
        VALID_RICH_TAGS = {
            'red', 'bold', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black',
            'italic', 'underline', 'blink', 'reverse', 'strike', 'dim',
            'blink2', 'conceal', 'crossed_out', 'default', 'frame', 'framed',
            'overline', 'encircle', 'shadow', 'outline', 'hidden', 'standout',
            'superscript', 'subscript', 'link', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            # Add more valid tags as needed
        }

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

    def _log(self, message: str, level: str = "info", stacklevel=None):
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
            getattr(self.logger, level, self.logger.info)(message, stacklevel=stack_offset)
        elif isinstance(self.logger, Console):
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

    # Public methods for common logging levels
    def critical(self, message: str, stacklevel=None):
        self._log(message, "critical", stacklevel=stacklevel)

    def error(self, message: str, stacklevel=None):
        self._log(message, "error", stacklevel=stacklevel)

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

def setup_logger(logger=None, name: str = "", verbose: Union[bool, int] = False):
    """
    Setup or reuse a logger.

    This function will reuse an existing logger if provided, otherwise it will create a new one.

    :param logger: Existing logger to reuse. If None, a new logger will be created inside ConsoleLoggerAdapter.
    :param name: Name of the logger.
    :param verbose: Verbosity level.
    :return: A ConsoleLoggerAdapter instance.
    """

    # log_level = const.VERBOSE_LEVELS.get(verbose, logging.DEBUG)
    if isinstance(logger, ConsoleLoggerAdapter):
        # if isinstance(logger.logger, logging.Logger):
            # logger.logger.setLevel(log_level)
        return logger  # Reuse the existing ConsoleLoggerAdapter if already provided.
    elif isinstance(logger, logging.Logger):
        # logger.setLevel(log_level)
        return logger
    return ConsoleLoggerAdapter(logger, name, verbose)


# def setup_logger(logger=None, name: str = "", verbose: Union[bool, int] = False):
#     """
#     Setup or reuse a logger and update its level based on verbosity.
#     """
#     if isinstance(logger, ConsoleLoggerAdapter):
#         logger.verbose = verbose
#         return logger  # Reuse the existing ConsoleLoggerAdapter if already provided.
#
#     adapter = ConsoleLoggerAdapter(logger, name, verbose)
#     # adapter.logger.setLevel(adapter._get_log_level())
#     return adapter


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

