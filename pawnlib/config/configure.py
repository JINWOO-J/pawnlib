import os
from pathlib import Path
from typing import Optional
import json
import logging


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


@singleton
class Configure:
    def __init__(self, file_name="../config.ini", path=None, section=None):

        self.file_name = file_name
        if path:
            self.path = path
        else:
            self.path = os.path.dirname(os.path.abspath(__file__))
        self.full_path = os.path.join(self.path, self.file_name)
        self.section = section
        self.name = "default"

    def _get_config(self, ):
        self.config.optionxform = str  # change to uppercase
        self.config.read(self.full_path)
        return self._converter(self.config._sections)


class Config:
    CONFIG_DEFAULT_FILE = 'configure.json'

    def __init__(self, config_path: Optional[Path] = None, logger=None):
        super().__init__()
        self._current_path: Optional[Path] = None
        self._config_path = config_path or self.get_path(self.CONFIG_DEFAULT_FILE)
        self._config = {}
        self._logger = logger
        self._log_options = None
        self._load_config_file(self._config_path, check_exist=False)
        # self._set_common_default()
        self._load_config_env()
        # self._update_log_options()

    def load_config(self, config_path: Path):
        """Load User configuration file.
        :param config_path: The str path created with pathlib.Path is recommended.
        """
        self._load_config_file(config_path=config_path)
        self._update_log_options()

    def __setattr__(self, key, value):
        if key in ['_current_path', '_config_path', '_config', '_logger', '_log_options']:
            self.__dict__[key] = value
        else:
            self._config[key] = value

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__getattribute__(name)
        return self[name]

    def __setitem__(self, key, item):
        self._config[key] = item
        # self._update_log_options()

    def __getitem__(self, key):
        return self._config[key]

    def _set_common_default(self):
        if 'debug' not in self._config:
            self._logger.debug("config['debug'] is not configured. So default(False) is used.")
            self._config['debug'] = False
        if 'log_level' not in self._config:
            self._logger.debug("config['log_level'] is not configured. So default(logging.WARNING) is used.")
            self._config['log_level'] = logging.getLevelName(logging.WARNING)
        if 'log_format' not in self._config:
            self._logger.debug("config['log_format'] is not in configured. So default is used.")
            self._config['log_format'] = \
                "%(asctime)s,%(msecs)03d %(process)d %(thread)d %(levelname)s %(filename)s(%(lineno)d) %(message)s"

    def _load_config_file(self, config_path: Path, check_exist=True):
        if not check_exist and not config_path.is_file():
            return

        with open(config_path, 'r') as config_file:
            self._config.update(json.load(config_file))
            self._current_path = config_path.parent

    def _load_config_env(self):
        for config_name in self._config:
            env_value = os.getenv(config_name) or os.getenv(str.upper(config_name))
            if env_value is not None:
                if isinstance(self[config_name], (bool, int, float)):
                    env_value = eval(env_value)
                self[config_name] = env_value

    def write_config(self, config_path: Optional[Path] = None, encoding: str = 'utf-8'):
        """You can set config values in code, and save it as a file.

        :param config_path: Path or CONFIG_DEFAULT_FILE.
        :param encoding: file encoding.

        :return:

        """
        write_path = config_path or self._config_path
        with open(write_path, 'w', encoding=encoding) as config_file:
            json.dump(self._config, config_file, indent=4, sort_keys=True)

    def get_path(self, path: str) -> Path:
        """Get Path from the directory where the configure.json file is.
        :param path: file_name or path
        :return:
        """
        root_path = self._current_path or Path(os.path.join(os.getcwd()))
        return root_path.joinpath(path)


if __name__ == '__main__':
    CFG = Configure()


