import logging
import os
import configparser
import sys
from uuid import uuid4
from pathlib import Path
from typing import Optional, Callable
from collections import namedtuple
from collections.abc import Mapping
import pawnlib.config.configure
from pawnlib.__version__ import __title__, __version__
from pawnlib.config.__fix_import import Null
from pawnlib.config.console import Console
from collections import OrderedDict
from rich.traceback import install as rich_traceback_install
import copy
from types import SimpleNamespace
from functools import partial
from rich import inspect as rich_inspect
import collections
import re


class NestedNamespace(SimpleNamespace):
    @staticmethod
    def _______map_____entry(entry):
        if isinstance(entry, dict):
            return NestedNamespace(**entry)

        return entry

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for key, val in kwargs.items():
            if type(val) == dict:
                setattr(self, key, NestedNamespace(**val))
            elif type(val) == list:
                setattr(self, key, list(map(self._______map_____entry, val)))

    def _keys(self) -> list:
        return list(self.__dict__.keys())

    def _values(self) -> list:
        return list(self.__dict__.values())

    def as_dict(self) -> dict:
        return self._namespace_to_dict(self.__dict__)

    def _namespace_to_dict(self, _dict):
        dict2 = {}
        for k in _dict.keys():
            if isinstance(_dict[k], dict) or isinstance(_dict[k], NestedNamespace):
                dict2[k] = self._namespace_to_dict(_dict[k]._asdict())
            else:
                dict2[k] = _dict[k]
        return dict2

    def _asdict(self) -> dict:
        return self.__dict__

    # def __repr__(self):
    #     'Return a nicely formatted representation string'
    #     field_names = tuple(self.as_dict().keys())
    #     field_values = tuple(self.as_dict().values())
    #     indent = "\n    "
    #     # indent = ""
    #     repr_fmt = '(' + ', '.join(f'{indent}{name}=%r' for name in field_names) + f'{indent})'
    #     return self.__class__.__name__ + repr_fmt % field_values

    def __repr__(self, indent=4):
        result = self.__class__.__name__ + '('
        items_len = len(self.__dict__)
        _first = 0
        _indent_space = ''

        for k, v in self.__dict__.items():
            if _first == 0 and items_len > 0:
                result += "\n"
                _first = 1
            if k.startswith('__'):
                continue
            if isinstance(v, NestedNamespace):
                value_str = v.__repr__(indent + 4)
            else:
                value_str = str(v)

            if k and value_str:
                if _first:
                    _indent_space = ' ' * indent
                result += _indent_space + k + '=' + value_str + ",\n"
        result += ' ' * (len(_indent_space) - 4) + f')'
        return result


def nestednamedtuple(dict_items: dict, ignore_keys: list = []) -> namedtuple:
    """
    Converts dictionary to a nested namedtuple recursively.


    :param: dictionary: Dictionary to convert into a nested namedtuple.

    :example:

        .. code-block:: python

            from pawnlib.config.globalconfig import nestednamedtuple
            nt = nestednamedtuple({"hello": {"ola": "mundo"}})
            print(nt) # >>> namedtupled(hello=namedtupled(ola='mundo'))

    """
    dictionary = copy.copy(dict_items)
    if isinstance(dictionary, Mapping) and not isinstance(dictionary, fdict):
        # for ignore_type in ["configparser.SectionProxy", "configparser.ConfigParser"]:
        for ignore_type in ["configparser.ConfigParser"]:
            if ignore_type in str(type(dictionary)):
                for key, value in list(dictionary.items()):
                    dictionary[key] = value
                return dictionary

        for key, value in list(dictionary.items()):
            # if  key in ignore_keys:
            #     dictionary[key] = value
            # else:
            dictionary[key] = nestednamedtuple(value)

        return namedtuple("namedtupled", dictionary)(**dictionary)
    elif isinstance(dictionary, list):
        return [nestednamedtuple(item) for item in dictionary]

    return dictionary


class fdict(dict):
    """

    Forced dictionary. Prevents dictionary from becoming a nested namedtuple.

    :example:

        .. code-block:: python

            from pawnlib.config.globalconfig import nestednamedtuple, fdict
            d = {"hello": "world"}
            nt = nestednamedtuple({"forced": fdict(d), "notforced": d})
            print(nt.notforced)    # >>> namedtupled(hello='world')
            print(nt.forced)       # >>> {'hello': 'world'}
    """
    pass


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


class ConfigSectionMap(configparser.ConfigParser):
    """
    override configparser.ConfigParser

    Example:

        .. code-block:: python

            config = ConfigSectionMap()
            config.read('config.ini')

            config_file = config.as_dict()

    """

    def __init__(self):
        # https://stackoverflow.com/questions/47640354/reading-special-characters-text-from-ini-file-in-python
        super(configparser.ConfigParser, self).__init__(interpolation=None)

    def as_dict(self, section=None):
        d = dict(self._sections)
        if self._defaults:
            d["DEFAULT"] = self._defaults
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop('__name__', None)
        if section:
            return d.get(section)
        return d

    def get_default(self):
        return dict(self._defaults)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# @singleton
class PawnlibConfig(metaclass=Singleton):
    def __init__(self, global_name="pawnlib_global_config", app_logger=Null(), error_logger=Null(), timeout=6000, debug=False):
        """
        This class can share variables using globals().

        :param global_name: Global Variable Name
        :param app_logger: global app logger
        :param error_logger: global error logger
        :param timeout: global timeout

        :example

                .. code :: python

                    # auto attach
                    from pawnlib.config.globalconfig import pawnlib_config as pwn
                    from pawnlib.output.file import get_real_path

                    pwn.set(
                        PAWN_LOGGER=dict(
                            app_name="default_app",
                            log_path=f"{get_script_path(__file__)}/logs",
                            stdout=True,
                            use_hook_exception=False,
                        ),
                        PAWN_DEBUG=True,
                        app_name=APP_NAME,
                        data={} # Global NameSpace
                    )


                .. code :: python

                    # attach logger
                    from pawnlib.config.globalconfig import pawnlib_config as pwn
                    from pawnlib.output.file import get_real_path

                    app_logger, error_logger = log.AppLogger(
                        app_name="default_app",
                        log_path=f"{get_real_path(__file__)}/logs",
                        stdout=True,
                        use_hook_exception=False,
                    ).get_logger()

                    pwn.set(
                        PAWN_APP_LOGGER=app_logger,
                        PAWN_ERROR_LOGGER=error_logger,
                        PAWN_DEBUG=True,
                        app_name=APP_NAME,
                        data={} # Global NameSpace
                    )

        """
        self.global_name = f"{global_name}_{uuid4()}"
        self.app_logger = app_logger
        self.error_logger = error_logger

        self.app_name = ""
        self.timeout = timeout
        self.verbose = 0
        self.debug = debug

        self.version = f"{__title__}/{__version__}"
        self.env_prefix = "PAWN"
        self._environments = {}
        self.data = NestedNamespace()

        self._current_path: Optional[Path] = None

        self._config_file = None
        self._pawn_configs = {}
        self.console = Null()
        self.console_options = None
        self.stdout_log_formatter = None
        self._none_string = "____NONE____"

        self._loaded = {
            "console": False,
            "on_ready": False

        }

        self._do_not_execute_namespace_keys = [f"{self.env_prefix}_LOGGER", f"{self.env_prefix}_CONSOLE"]
        self.log_time_format = None

        globals()[self.global_name] = {}
        self._init_console(force_init=True)

    @staticmethod
    def inspect(*args, **kwargs):
        """
        Inspect function which can produce a report on any Python object, such as class, instance, or builtin.
        :param args:
        :param kwargs:
        :return:
        """
        return rich_inspect(*args, **kwargs)

    def _log_formatter(self, dt):

        if self.log_time_format.endswith('.%f'):
            return dt.strftime(self.log_time_format)[:-3]
        else:
            return dt.strftime(self.log_time_format)

    def _init_console(self, force_init=True):

        _console_options = dict(
            pawn_debug=self.debug,
            redirect=self.debug,  # <-- not supported by rich.console.Console
            record=True,
            soft_wrap=True,
            force_terminal=True,
            # log_time_format="[%Y-%m-%d %H:%M:%S.%f]"
            log_time_format=lambda dt: f"[{dt.strftime('%H:%M:%S,%f')[:-3]}]"
        )
        # print(self.console_options)
        if not self._loaded.get('console'):
            # There are visible problems with InquirerPy.
            _console_options['redirect'] = False

        if self._loaded.get('console') or force_init:
            if self.console_options:
                if self.console_options.get('log_time_format') and not isinstance(self.console_options.get('log_time_format'), Callable):
                    _log_time_format = self.console_options['log_time_format']
                    self.log_time_format = self.console_options['log_time_format']

                    if ".%f" in _log_time_format:
                        self.console_options['log_time_format'] = lambda dt: f"[{dt.strftime(_log_time_format)[:-3]}]"
                    else:
                        self.console_options['log_time_format'] = lambda dt: f"[{dt.strftime(_log_time_format)}]"
                    self.stdout_log_formatter = self.console_options['log_time_format']
                _console_options.update(self.console_options)
            # self.console_options = copy.deepcopy(_console_options)
            self.console = Console(**_console_options)

    def _load_config_file(self, config_path=None):
        if self._loaded['on_ready']:
            config = ConfigSectionMap()
            config.optionxform = str
            _config_filename = self.get_path(self._config_file)
            try:
                if _config_filename.is_file():
                    config.read(_config_filename)
                    self.set(PAWN_CONFIG=config.as_dict())
                else:
                    self.set(PAWN_CONFIG={})
                    self.console.debug(f"[bold red] cannot found config_file - {_config_filename}")
                for config_category, config_value in config.items():
                    lower_keys = [key.lower() for key in config[config_category].keys()]
                    duplicate_keys = _list_duplicates(lower_keys)
                    for conf_key, conf_value in config[config_category].items():
                        if conf_key.lower() in duplicate_keys:
                            self.console.log(f"[yellow]\[WARN] Similar keys exist in config.ini - \[{config_category}] {conf_key}={conf_value}")
            except Exception as e:
                self.console.log(f"[bold red]Error occurred while loading config.ini - {e}")

    def get_path(self, path: str = "") -> Path:
        """Get Path from the directory where the configure.json file is.

        :param path: file_name or path

        :return:

        """
        if self._current_path:
            root_path = Path(self._current_path)
        else:
            root_path = Path(os.path.join(os.getcwd()))
        return root_path.joinpath(path)

    @staticmethod
    def pawnlib_path():
        _dir = os.path.dirname(__file__)
        if "/config" in _dir:
            return _dir.replace("/config", "")
        return _dir

    @staticmethod
    def get_python_version():
        major, minor, micro = sys.version_info[:3]
        return f"Python {major}.{minor}.{micro} {sys.platform}"

    def init_with_env(self, **kwargs):
        """
        Initialize with environmental variables.

        :param kwargs: dict
        :return:
        """
        self.fill_config_from_environment()
        self.set(**kwargs)
        # self._load_config_file()
        self._loaded['on_ready'] = True
        self.console.debug(f"🐍 {self.get_python_version()}, ♙ {__title__.title()}/{__version__}, PATH={self.pawnlib_path()}")
        self._load_config_file()
        return self

    @staticmethod
    def str2bool(v):
        """
        This function is intended to return a boolean value.

        :param v:
        :return:
        """
        true_list = ("yes", "true", "t", "1", "True", "TRUE")
        if type(v) == bool:
            return v
        if type(v) == str:
            return v.lower() in true_list
        return eval(f"{v}") in true_list

    def fill_config_from_environment(self):
        """
        Initialize with environmental variables.

        .. code :: python

            # default environments

            PAWN_INI = False
            PAWN_DEBUG = False
            PAWN_VERBOSE = 0
            PAWN_TIMEOUT = 7000
            PAWN_APP_LOGGER = ""
            PAWN_ERROR_LOGGER = ""
            PAWN_VERSION =
            PAWN_GLOBAL_NAME = pawnlib_global_config_UUID

        :return:
        """
        default_structure = {
            "VERBOSE": {
                "type": int,
                "default": 0,
            },
            "INI": {
                "type": self.str2bool,
                "default": False,
            },
            "CONFIG_FILE": {
                "type": str,
                "default": "config.ini",
            },
            "DEBUG": {
                "type": self.str2bool,
                "default": False,
            },
            "TIMEOUT": {
                "type": int,
                "default": 7000,
            },
            "APP_LOGGER": {
                "type": str,
                "default": ""
            },
            "ERROR_LOGGER": {
                "type": str,
                "default": ""
            },
            "LOGGER": {
                "type": dict,
                "default": {}
            },
            "VERSION": {
                "type": str,
                "default": self.version.title()
            },
            "GLOBAL_NAME": {
                "type": str,
                "default": self.global_name
            },
            "CONSOLE": {
                "type": dict,
                "default": {}
            },
            "LINE": {
              "type": self.str2bool,
              "default": True,
            },
            "PATH": {
                "type": str,
                "default": Path(os.path.join(os.getcwd()))
            },
            "TIME_FORMAT": {
                "type": str,
                "default": "%H:%M:%S.%f"
            },
        }
        mandatory_environments = list(default_structure.keys())

        for environment in mandatory_environments:
            environment_name = f"{self.env_prefix}_{environment}"
            environment_value = os.getenv(environment_name)
            filled_environment_value = ""
            if default_structure.get(environment):
                required_type = default_structure[environment].get("type", None)
                if required_type is None:
                    self.console.log(f"[red]{environment_name} type is None. Required type")
                if environment_value in [None, 0, ""]:
                    filled_environment_value = default_structure[environment].get("default")
                elif required_type:
                    filled_environment_value = required_type(environment_value)
            self._environments[environment_name] = {
                "input": os.getenv(environment_name),
                "value": filled_environment_value,
            }
            self.set(**{environment_name: filled_environment_value})
            if isinstance(self.verbose, int) and self.verbose >= 3:
                self.console.debug(f"{environment_name}={filled_environment_value} (env={environment_value})")

    def make_config(self, dictionary: Optional[dict] = None, **kwargs) -> None:
        """Creates a global configuration that can be accessed anywhere during runtime.
        This function is a useful replacement to passing configuration classes between classes.
        Instead of creating a `Config` object, one may use :func:`make_config` to create a
        global runtime configuration that can be accessed by any module, function, or object.

        :param dictionary: Dictionary to create global configuration with.
        :param kwargs: Arguments to make global configuration with.

        Example:

            .. code-block:: python

                from pawnlib.config.globalconfig import PawnlibConfig
                PawnlibConfig.make_config(hello="world")


        """
        dictionary = dictionary or {}
        globals()[self.global_name] = {**dictionary, **kwargs}

    def get(self, key=None, default=None):
        """
        This method is intended to return a key value

        :param key:
        :param default:
        :return:

        Example:

            .. code-block:: python

                from pawnlib.config.globalconfig import pawnlib_config
                pawnlib_config.set(hello="world")
                pawnlib_config.get("hello")

        """
        if self.global_name in globals():
            return globals()[self.global_name].get(key, default)
        return default

    def set(self, **kwargs):
        """
        This method is intended to store key values.

        :param kwargs:
        :return:

        Example:

            .. code-block:: python

                from pawnlib.config.globalconfig import pawnlib_config
                pawnlib_config.set(hello="world")
                pawnlib_config.get("hello")

        """
        priority_keys = [f"{self.env_prefix}_PATH", f"{self.env_prefix}_TIME_FORMAT", f"{self.env_prefix}_DEBUG", f"{self.env_prefix}_VERBOSE"]
        order_dict = OrderedDict(kwargs)

        def _enforce_set_value(source_key=None, target_key=None, target_dict=None):
            if kwargs.get(source_key):
                if isinstance(target_dict, dict) and not target_dict.get(target_key):
                    target_dict[target_key] = kwargs[source_key]
                    if isinstance(self.verbose, int) and self.verbose >= 3:
                        self.console.debug(f'set => {target_key}={kwargs[source_key]}')

        for priority_key in priority_keys:
            if order_dict.get(priority_key):
                order_dict.move_to_end(key=priority_key, last=False)

        if self.global_name in globals():
            for p_key, p_value in order_dict.items():
                if self._environments.get(p_key, self._none_string) != self._none_string \
                        and self._environments[p_key].get("input"):
                    if self._environments[p_key].get('input') and \
                            self._environments[p_key].get('value') != p_value:
                        self.console.log(f"[yellow][WARN] Environment variables and settings are different. "
                                         f"'{p_key}': {self._environments[p_key]['value']}(ENV) != {p_value}(Config)")
                        p_value = self._environments[p_key]['value']

                if p_key == f"{self.env_prefix}_LOGGER" and p_value:
                    if isinstance(p_value, dict):
                        from pawnlib.utils.log import AppLogger
                        if p_value.get('app_name') is None and kwargs.get('app_name'):
                            p_value['app_name'] = kwargs['app_name']
                            self.app_name = kwargs['app_name']
                        _enforce_set_value(source_key=f'{self.env_prefix}_TIME_FORMAT', target_key='stdout_log_formatter', target_dict=p_value)
                        self.app_logger, self.error_logger = AppLogger(**p_value).get_logger()

                elif p_key == f"{self.env_prefix}_APP_LOGGER" and p_value:
                    self.app_logger = self._check_logger_not_null(p_key, p_value)
                elif p_key == f"{self.env_prefix}_ERROR_LOGGER" and p_value:
                    self.error_logger = self._check_logger_not_null(p_key, p_value)
                elif p_key == f"{self.env_prefix}_DEBUG":
                    self.debug = self.str2bool(p_value)
                    self.console.pawn_debug = self.str2bool(p_value)
                    if self.debug:
                        rich_traceback_install(show_locals=True, width=160)
                        if self.app_logger:
                            set_debug_logger(self.app_logger)
                elif p_key == f"{self.env_prefix}_LINE":
                    _hide_log_path = {"log_path": p_value}
                    if isinstance(self.console_options, dict):
                        self.console_options.update(**_hide_log_path)
                    else:
                        self.console_options = _hide_log_path
                    self._init_console()
                    # self._loaded['console'] = True
                elif p_key == f"{self.env_prefix}_CONSOLE":
                    _enforce_set_value(source_key=f'{self.env_prefix}_TIME_FORMAT', target_key='log_time_format', target_dict=p_value)
                    self.console_options = p_value
                    self._init_console()
                    self._loaded['console'] = True
                elif p_key == f"{self.env_prefix}_TIMEOUT":
                    self.timeout = p_value
                elif p_key == f"{self.env_prefix}_VERBOSE":
                    self.verbose = p_value
                elif p_key == f"{self.env_prefix}_PATH":
                    self._current_path = p_value
                    self._load_config_file()
                elif p_key == f"{self.env_prefix}_CONFIG_FILE":
                    self._config_file = p_value
                    self._load_config_file()

                elif p_key == "data" and p_value != self._none_string:
                    if isinstance(p_value, dict):
                        self.data = NestedNamespace(**p_value)
                    else:
                        self.console.log("[bold red] The data namespace value must be a Dict")
                    # else:
                    #     self.data = NestedNamespace()
                    #     setattr(self, p_key, p_value)
                    #     self.console.log(f"fff => {self.data}")
                    p_value = self.data

                globals()[self.global_name][p_key] = p_value

    def _check_logger_not_null(self, key, value):
        if type(value).__name__ == "Logger":
            return value
        else:
            self.console.debug(f"[red]Invalid Logger [/red] => {key}: {value} ({type(value)})")
            return Null()

    def increase(self, **kwargs):
        """
        Find the key and increment the number.

        :param kwargs:
        :return:

        Example:

            .. code-block:: python

                from pawnlib.config.globalconfig import pawnlib_config

                pawnlib_config.increase(count=1)
                print(pawnlib_config.get("count"))
                # >> 1

                pawnlib_config.increase(count=1)
                print(pawnlib_config.get("count"))

                # >> 2

                pawnlib_config.increase(count=10)
                print(pawnlib_config.get("count"))

                # >> 12


        """
        return self._modify_value(_command="increase", **kwargs) or 0

    def decrease(self, **kwargs):
        """
        Find the key and decrement the number.
        :param kwargs:
        :return:

        Example:

            .. code-block:: python

                from pawnlib.config.globalconfig import pawnlib_config

                pawnlib_config.set(count=100)
                print(pawnlib_config.get("count"))
                # >> 100

                pawnlib_config.decrease(count=1)
                print(pawnlib_config.get("count"))

                # >> 99

                pawnlib_config.decrease(count=10)
                print(pawnlib_config.get("count"))

                # >> 89

        """
        return self._modify_value(_command="decrease", **kwargs) or 0

    def append_list(self, **kwargs):
        """
        Find the key and append the value to list.
        :param kwargs:
        :return:

        Example:

            .. code-block:: python

                from pawnlib.config.globalconfig import pawnlib_config

                pawnlib_config.append_list(results="result1")
                pawnlib_config.append_list(results="result2")

                print(pawnlib_config.get("results"))

                # >> ['result1', 'result2']


        """

        return self._modify_value(_command="append_list", **kwargs) or []

    def remove_list(self, **kwargs):
        """
        Find the key and remove the value to list.
        :param kwargs:
        :return:

        Example:

            .. code-block:: python

                from pawnlib.config.globalconfig import pawnlib_config

                pawnlib_config.set(results=['result1', 'result2'])
                pawnlib_config.remove_list(results="result2")

                print(pawnlib_config.get("results"))

                # >> ['result1']

        """
        return self._modify_value(_command="remove_list", **kwargs) or []

    @staticmethod
    def _modify_value_initialize(_command=None):
        init_values = {
            "increase": 0,
            "decrease": 0,
            "append_list": [],
            "remove_list": [],
        }
        return init_values.get(_command)

    def _modify_value(self, _command=None, **kwargs):
        """
        Find the key and modify the value.
        :param _command:
        :param kwargs:
        :return:
        """
        is_modify = False
        init_value = self._modify_value_initialize(_command=_command)

        for key, value in kwargs.items():
            tmp_result = self.get(key=key, default="___NONE_VALUE___")

            if tmp_result == "___NONE_VALUE___":
                tmp_result = init_value

            if _command == "increase":
                if isinstance(tmp_result, int) or isinstance(tmp_result, float):
                    tmp_result += value
                    is_modify = True
            elif _command == "decrease":
                if isinstance(tmp_result, int) or isinstance(tmp_result, float):
                    tmp_result -= value
                    is_modify = True
            elif _command == "append_list" and isinstance(tmp_result, list):
                tmp_result.append(value)
                is_modify = True
            elif _command == "remove_list" and isinstance(tmp_result, list):
                tmp_result.remove(value)
                is_modify = True
            if is_modify:
                globals()[self.global_name][key] = tmp_result
                return tmp_result
        return init_value

    def __str__(self):
        return f"<{self.version.title()}>[{self.global_name}]\n{self.to_dict()}"

    def conf(self) -> namedtuple:
        """Access global configuration as a :class:`pawnlib.config.globalconfig.PawnlibConfig`.

        Example:

            .. code-block:: python

                from pawnlib.config.globalconfig import pawnlib_config
                print(pawnlib_config.conf().hello) # >>> 'world'

        """
        g = globals()
        if self.global_name in g:
            # return nestednamedtuple(g[self.global_name], ignore_keys=self._do_not_execute_namespace_keys)
            return NestedNamespace(**g[self.global_name])
        else:
            return NestedNamespace({})

    def to_dict(self) -> dict:
        """Access global configuration as a dict.

        Example:

            .. code-block:: python

                from pawnlib.config.globalconfig import pawnlib_config
                print(pawnlib_config.to_dict().get("hello")) # >>> 'world'

        """
        g = globals()
        if self.global_name in g:
            return g[self.global_name]
        else:
            return {}

    # def ns(self):
    #     return self.data
    #
    # def data_to_namespace(self):
    #
    #     g = globals()
    #     if self.global_name in g:
    #         return self.data
    #
    #     return self.data


def _list_duplicates(seq):
    seen = set()
    seen_add = seen.add
    # adds all elements it doesn't know yet to seen and all other to seen_twice
    seen_twice = set(x for x in seq if x in seen or seen_add(x))
    # turn the set into a list (as requested)
    return list(seen_twice)


def set_debug_logger(logger_name=None, propagate=0, get_logger_name='PAWNS', level='DEBUG'):
    if logger_name:
        __logger = logging.getLogger(get_logger_name)
        __logger.propagate = propagate
        __logger.setLevel(level)
        __logger.addHandler(logger_name)


pawnlib_config = PawnlibConfig(global_name="pawnlib_global_config").init_with_env()
pawn = pawnlib_config
pconf = partial(pawn.conf)
global_verbose = pawnlib_config.get('PAWN_VERBOSE', 0)
