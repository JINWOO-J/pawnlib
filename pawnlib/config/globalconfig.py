import os
from typing import Optional, TYPE_CHECKING
from collections import namedtuple
from collections.abc import Mapping
from pawnlib.__version__ import __title__, __version__
from pawnlib.typing.generator import uuid_generator, Null
from pawnlib.config.console import Console


def nestednamedtuple(dictionary: dict) -> namedtuple:
    """
    Converts dictionary to a nested namedtuple recursively.


    :param: dictionary: Dictionary to convert into a nested namedtuple.

    :example:

        .. code-block:: python

            from pawnlib.config.globalconfig import nestednamedtuple
            nt = nestednamedtuple({"hello": {"ola": "mundo"}})
            print(nt) # >>> namedtupled(hello=namedtupled(ola='mundo'))

    """

    if isinstance(dictionary, Mapping) and not isinstance(dictionary, fdict):
        for key, value in list(dictionary.items()):
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


@singleton
class PawnlibConfig:
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
                            log_path=f"{get_real_path(__file__)}/logs",
                            stdout=True,
                            use_hook_exception=False,
                        ),
                        PAWN_DEBUG=True,
                        app_name=APP_NAME,
                        app_data={}
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
                        app_data={}
                    )

        """
        self.global_name = f"{global_name}_{uuid_generator()}"
        self.app_logger = app_logger
        self.error_logger = error_logger

        self.app_name = ""
        self.timeout = timeout
        self.verbose = 0
        self.debug = debug

        self.version = f"{__title__}/{__version__}"
        self.env_prefix = "PAWN"
        self.data = {}
        self.console = Console(
            redirect=True,  # <-- not supported by rich.console.Console
            record=True,
            soft_wrap=True,
            force_terminal=True
        )
        globals()[self.global_name] = {}

    def init_with_env(self, **kwargs):
        """
        Initialize with environmental variables.

        :param kwargs: dict
        :return:
        """
        self.fill_config_from_environment()
        self.set(**kwargs)
        return self

    # def set_config_ini(self):
    #     from configparser import ConfigParser
    #     self.configure = ConfigParser()
    #     self.configure.optionxform = str  # change to uppercase
    #     self.configure.read(self.full_path)

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

            default environments

            PAWN_INI = False
            PAWN_VERBOSE = 0
            PAWN_TIMEOUT = 7000
            PAWN_APP_LOGGER = ""
            PAWN_ERROR_LOGGER = ""
            PAWN_VERSION =
            PAWN_GLOBAL_NAME = pawnlib_global_config_UUID

        :return:
        """
        default_structure = {
            "INI": {
                "type": self.str2bool,
                "default": False,
            },
            "DEBUG": {
                "type": self.str2bool,
                "default": False,
            },
            "VERBOSE": {
                "type": int,
                "default": 0,
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
            }
        }

        mandatory_environments = list(default_structure.keys())
        for environment in mandatory_environments:
            environment_name = f"{self.env_prefix}_{environment}"
            environment_value = os.getenv(environment_name)

            if default_structure.get(environment):
                required_type = default_structure[environment].get("type", None)

                if environment_value is None or environment_value == 0 or environment_value == "":
                    environment_value = default_structure[environment].get("default")

                elif required_type:
                    environment_value = required_type(environment_value)
            self.set(**{environment_name: environment_value})

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

    # def __getitem__(self, key):
    #     print(f"__getitem__" * 10)
    #     # return getattr(self, key)
    #     return globals()[self.global_name].get(key)
    #
    # def __setitem__(self, key, value):
    #     return setattr(self, key, value)

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
        if self.global_name in globals():
            for p_key, p_value in kwargs.items():
                if p_key == "PAWN_LOGGER" and p_value:
                    from pawnlib.utils.log import AppLogger
                    if isinstance(p_value, dict) and p_value.get("app_name", "") == "":
                        if p_value.get('app_name') is None and kwargs.get('app_name'):
                            p_value['app_name'] = kwargs['app_name']
                        self.app_logger, self.error_logger = AppLogger(**p_value).get_logger()

                elif kwargs.get(f"{self.env_prefix}_APP_LOGGER"):
                    self.app_logger = kwargs[f"{self.env_prefix}_APP_LOGGER"]
                elif kwargs.get(f"{self.env_prefix}_ERROR_LOGGER"):
                    self.error_logger = kwargs[f"{self.env_prefix}_ERROR_LOGGER"]
                elif kwargs.get(f"{self.env_prefix}_TIMEOUT"):
                    self.timeout = kwargs[f"{self.env_prefix}_TIMEOUT"]
                elif kwargs.get(f"{self.env_prefix}_VERBOSE"):
                    self.verbose = kwargs[f"{self.env_prefix}_VERBOSE"]
                elif kwargs.get(f"{self.env_prefix}_DEBUG"):
                    self.debug = kwargs[f"{self.env_prefix}_DEBUG"]
                globals()[self.global_name][p_key] = p_value

            if self.debug:
                from rich.traceback import install
                install(show_locals=True)

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
            elif _command == "append_list":
                if isinstance(tmp_result, list):
                    tmp_result.append(value)
                    is_modify = True
            elif _command == "remove_list":
                if isinstance(tmp_result, list):
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
            return nestednamedtuple(g[self.global_name])
        else:
            return nestednamedtuple({})

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

pawnlib_config = PawnlibConfig(global_name="pawnlib_global_config").init_with_env()
global_verbose = pawnlib_config.get('PAWN_VERBOSE', 0)
