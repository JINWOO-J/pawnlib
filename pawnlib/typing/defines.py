from pawnlib.config import pawn, pconf
# from os.path import exists as os_path_exists, expanduser as os_path_expanduser
from glob import glob
from dotenv import load_dotenv

import os


class _AttributeHolder(object):
    """Abstract base class that provides __repr__.

    The __repr__ method returns a string in the format::
        ClassName(attr=name, attr=name, ...)
    The attributes are determined either by a class-level attribute,
    '_kwarg_names', or by inspecting the instance __dict__.
    """

    def __repr__(self):
        type_name = type(self).__name__
        arg_strings = []
        star_args = {}
        for arg in self._get_args():
            arg_strings.append(repr(arg))
        for name, value in self._get_kwargs():
            if name.isidentifier():
                arg_strings.append('%s=%r' % (name, value))
            else:
                star_args[name] = value
        if star_args:
            arg_strings.append('**%s' % repr(star_args))
        return '%s(%s)' % (type_name, ', '.join(arg_strings))

    def _get_kwargs(self):
        return sorted(self.__dict__.items())

    def _get_args(self):
        return []

    def _set_args(self, key, value):
        self.__dict__[key] = value

    def _update(self, **kwargs):
        self.__dict__.update(kwargs)


class Namespace(_AttributeHolder):
    """Simple object for storing attributes.

    Implements equality by attribute names and values, and provides a simple
    string representation.

    Example:

        .. code-block:: python

            from pawnlib.typing import defines

            namespace = defines.Namespace(s=2323, sdsd="Sdsd")
            namespace.s
            # >> 2323
            namespace.sdsd
            # >> 'Sdsd'
    """

    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])

    def __eq__(self, other):
        if not isinstance(other, Namespace):
            return NotImplemented
        return vars(self) == vars(other)

    def __contains__(self, key):
        return key in self.__dict__


def set_namespace_default_value(namespace=None, key='', default=""):
    """
    Set a default value when a key in a namespace has no value

    :param namespace:
    :param key:
    :param default:
    :return:

    Example:

        .. code-block:: python

            from pawnlib.config import pawn, pconf
            from pawnlib.typing import set_namespace_default_value

            pawn.set(
            data={"aaaa": "bbbb"}
            )
            pawn.console.log(pconf())
            undefined_key = set_namespace_default_value(
                namespace=pconf().data,
                key="cccc",
                default="ddddd"
            )
            pawn.console.log(undefined_key)

    """
    if key and hasattr(namespace, key):
        return getattr(namespace, key)
    return default


def fill_required_data_arguments(required={}):
    """
     Fill the required data arguments.

     :param required: A dictionary of required arguments.
     :type required: dict
     :return: The filled arguments.
     :rtype: argparse.Namespace

     Example:

         .. code-block:: python

             required = {"arg1": "value1", "arg2": "value2"}
             args = fill_required_data_arguments(required)
             # args.arg1 == "value1"
             # args.arg2 == "value2"

     """
    none_string = "__NOT_DEFINED_VALUE__"
    if getattr(pconf(), "data", None) and getattr(pconf().data, "args", None):
        args = pconf().data.args
        for req_key, req_value in required.items():
            args_value = getattr(args, req_key, none_string)
            if args_value == none_string:
                # pawn.console.debug(f"Define the data args -> {req_key}, {req_value}")
                setattr(args, req_key, req_value)
    else:
        # pawn.console.debug(f"New definition: {required}")
        args = Namespace(**required)
    return args


def load_env_with_defaults(defaults=None, required_keys=None, force_reload=False, verbose=False, dotenv_path=None):
    """
    Load environment variables from a .env file with additional features like defaults, required keys,
    reload options, and custom logging.

    :param defaults: A dictionary of default values for environment variables if they are not found in the .env file.
                     Values can be static (e.g., 'default_key') or functions for dynamic defaults (e.g., lambda: 'default').
    :type defaults: dict
    :param required_keys: A list of environment variables that are required. If any of these are missing after loading,
                          a warning or error message will be displayed.
    :type required_keys: list
    :param force_reload: If True, overwrites existing environment variables with values from the .env file.
    :type force_reload: bool
    :param verbose: If True, enables detailed logging for each loaded variable and missing required keys.
    :type verbose: bool
    :param dotenv_path: Optional path to the .env file. Defaults to the ".env" file in the current directory.
    :type dotenv_path: str

    Example usage:

        1. Basic loading of environment variables from .env file:

            >>> load_env_with_defaults()

        2. Loading with default values for missing environment variables:

            >>> defaults = {
            ...     'DATABASE_URL': 'sqlite:///default.db',
            ...     'API_KEY': 'default_key'
            ... }
            >>> load_env_with_defaults(defaults=defaults)

        3. Loading required environment variables and checking for missing keys:

            >>> required_keys = ['DATABASE_URL', 'API_KEY']
            >>> load_env_with_defaults(required_keys=required_keys)

        4. Forcing reload of .env variables even if they are already set in the environment:

            >>> load_env_with_defaults(force_reload=True)

        5. Enabling verbose logging to see detailed load progress:

            >>> load_env_with_defaults(verbose=True)

        6. Specifying a custom .env file path:

            >>> load_env_with_defaults(dotenv_path='/custom/path/.env')

        7. Combining multiple options:

            >>> load_env_with_defaults(defaults=defaults, required_keys=required_keys, force_reload=True, verbose=True, dotenv_path='/custom/path/.env')

    Notes:
        - `defaults`: Use this to specify fallback values for environment variables not found in the .env file. You can provide static values or dynamic values as functions.
        - `required_keys`: If any keys in this list are missing after loading, they will be logged (if `verbose=True`) or raise an exception if required.
        - `force_reload`: Overwrites existing environment variables with .env file values if set to True.
        - `verbose`: Outputs detailed logs for each environment variable loaded, including defaults and any missing required keys.
        - `dotenv_path`: Allows specifying a custom .env file location, defaulting to the .env file in the current directory if not provided.
    """

    dotenv_path = dotenv_path or f"{pawn.get_path()}/.env"

    if not _is_file(dotenv_path):
        verbose and pawn.console.log(".env file not found")
    else:
        verbose and pawn.console.log(f".env file found at '{dotenv_path}'")
        load_dotenv(dotenv_path=dotenv_path, override=force_reload)

        # Logging and applying defaults if provided
        if defaults:
            for key, value in defaults.items():
                if os.getenv(key) is None:
                    os.environ[key] = value
                    verbose and pawn.console.log(f"{key} not found in .env. Using default: {value}")
                else:
                    verbose and pawn.console.log(f"{key} loaded from .env: {os.getenv(key)}")
        else:
            for key, value in os.environ.items():
                verbose and pawn.console.log(f"Loaded {key}: {value}")

    if required_keys:
        missing_keys = [key for key in required_keys if key not in os.environ]
        if missing_keys:
            warning_msg = f"Missing required environment variables: {', '.join(missing_keys)}"
            pawn.console.log(warning_msg)
            raise EnvironmentError(warning_msg)

    # Confirm completion
    verbose and pawn.console.log("Environment variables loaded successfully.")


def _is_file(filename: str) -> bool:
    """
    Check if the file exists.

    :param filename: (str) Name of the file to check.
    :return: (bool) True if the file exists, False otherwise.

    Example:

        .. code-block:: python

            is_file('example.txt')
            # >> True
    """
    if not filename:
        return False

    if "*" in filename:
        if len(glob(filename)) > 0:
            return True
        else:
            return False
    else:
        return os.path.exists(os.path.expanduser(filename))

