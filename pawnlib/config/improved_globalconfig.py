"""
Improved Global Configuration System for Pawnlib

This module provides a modern, type-safe, and thread-safe configuration management system
that addresses the limitations of the original globalconfig.py.

Key improvements:
- Type safety with Pydantic schemas
- Thread-safe operations
- Clear initialization phases
- Context-based configuration isolation
- Better error handling and validation
- Simplified architecture
"""

import logging
import os
import json
import threading
from pathlib import Path
from typing import (
    Dict, Any, Optional, Type, TypeVar, List, Callable,
    Union, ContextManager, Protocol, runtime_checkable
)
from enum import Enum
from dataclasses import dataclass, field
from contextlib import contextmanager
from abc import ABC, abstractmethod
from uuid import uuid4
import copy

try:
    from pydantic import BaseModel, Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # Fallback for when pydantic is not available
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def dict(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

from pawnlib.__version__ import __title__, __version__
from pawnlib.config.__fix_import import Null
from pawnlib.config.console import Console

# Type variables
T = TypeVar('T')
ConfigType = TypeVar('ConfigType', bound=BaseModel)


class ConfigState(Enum):
    """Configuration lifecycle states"""
    UNINITIALIZED = "uninitialized"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


@runtime_checkable
class ConfigSource(Protocol):
    """Protocol for configuration sources"""

    def load(self) -> Dict[str, Any]:
        """Load configuration data from source"""
        ...

    def save(self, config: Dict[str, Any]) -> None:
        """Save configuration data to source"""
        ...


class EnvironmentConfigSource:
    """Environment variables configuration source"""

    def __init__(self, prefix: str = "PAWN", type_converters: Optional[Dict] = None):
        self.prefix = prefix.upper()
        self._type_converters = type_converters or {
            'bool': self._str_to_bool,
            'int': int,
            'float': float,
            'str': str,
            'list': self._str_to_list,
            'dict': self._str_to_dict
        }

    def load(self) -> Dict[str, Any]:
        """Load environment variables with prefix"""
        config = {}
        prefix_len = len(self.prefix) + 1

        for key, value in os.environ.items():
            if key.startswith(f"{self.prefix}_"):
                config_key = key[prefix_len:].lower()
                config[config_key] = self._auto_convert(value)

        return config

    def save(self, config: Dict[str, Any]) -> None:
        """Save configuration to environment (for current process only)"""
        for key, value in config.items():
            env_key = f"{self.prefix}_{key.upper()}"
            os.environ[env_key] = str(value)

    def _auto_convert(self, value: str) -> Any:
        """Automatically convert string values to appropriate types"""
        # Try boolean first
        if value.lower() in ('true', 'false', 'yes', 'no', '1', '0'):
            return self._str_to_bool(value)

        # Try integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Try JSON (for lists/dicts)
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass

        # Return as string
        return value

    @staticmethod
    def _str_to_bool(value: str) -> bool:
        """Convert string to boolean"""
        return value.lower() in ('true', '1', 'yes', 'on')

    @staticmethod
    def _str_to_list(value: str) -> List[str]:
        """Convert comma-separated string to list"""
        return [item.strip() for item in value.split(',') if item.strip()]

    @staticmethod
    def _str_to_dict(value: str) -> Dict[str, Any]:
        """Convert JSON string to dictionary"""
        return json.loads(value)


class FileConfigSource:
    """File-based configuration source"""

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)

    def load(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if not self.file_path.exists():
            return {}

        try:
            if self.file_path.suffix.lower() == '.json':
                return self._load_json()
            elif self.file_path.suffix.lower() in ('.ini', '.cfg'):
                return self._load_ini()
            else:
                logging.warning(f"Unsupported config file format: {self.file_path.suffix}")
                return {}
        except Exception as e:
            logging.error(f"Failed to load config file {self.file_path}: {e}")
            return {}

    def save(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            if self.file_path.suffix.lower() == '.json':
                self._save_json(config)
            elif self.file_path.suffix.lower() in ('.ini', '.cfg'):
                self._save_ini(config)
            else:
                logging.warning(f"Unsupported config file format for saving: {self.file_path.suffix}")
        except Exception as e:
            logging.error(f"Failed to save config file {self.file_path}: {e}")

    def _load_json(self) -> Dict[str, Any]:
        """Load JSON configuration file"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_json(self, config: Dict[str, Any]) -> None:
        """Save JSON configuration file"""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _load_ini(self) -> Dict[str, Any]:
        """Load INI configuration file"""
        import configparser
        parser = configparser.ConfigParser()
        parser.read(self.file_path)

        config = {}
        for section_name in parser.sections():
            section = {}
            for key, value in parser.items(section_name):
                section[key] = value
            config[section_name] = section

        return config

    def _save_ini(self, config: Dict[str, Any]) -> None:
        """Save INI configuration file"""
        import configparser
        parser = configparser.ConfigParser()

        for section_name, section_data in config.items():
            if isinstance(section_data, dict):
                parser.add_section(section_name)
                for key, value in section_data.items():
                    parser.set(section_name, key, str(value))

        with open(self.file_path, 'w', encoding='utf-8') as f:
            parser.write(f)


# Configuration Schema Definition
if PYDANTIC_AVAILABLE:
    class PawnlibConfigSchema(BaseModel):
        """Type-safe configuration schema with validation"""
        debug: bool = Field(default=False, description="Enable debug mode")
        timeout: int = Field(default=6000, ge=0, description="Global timeout in milliseconds")
        app_name: str = Field(default="pawnlib_app", min_length=1, description="Application name")
        log_level: str = Field(default="INFO", description="Logging level")
        env_prefix: str = Field(default="PAWN", description="Environment variable prefix")
        max_workers: int = Field(default=4, ge=1, le=100, description="Maximum worker threads")
        verbose: int = Field(default=0, ge=0, le=3, description="Verbosity level")
        use_console: bool = Field(default=True, description="Enable console output")
        console_width: Optional[int] = Field(default=None, description="Console width")

        @validator('log_level')
        def validate_log_level(cls, v):
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if v.upper() not in valid_levels:
                raise ValueError(f"log_level must be one of {valid_levels}")
            return v.upper()

        @validator('timeout')
        def validate_timeout(cls, v):
            if v < 0:
                raise ValueError("timeout must be non-negative")
            return v

        class Config:
            extra = "allow"  # Allow additional fields for flexibility
else:
    # Fallback schema when pydantic is not available
    @dataclass
    class PawnlibConfigSchema:
        debug: bool = False
        timeout: int = 6000
        app_name: str = "pawnlib_app"
        log_level: str = "INFO"
        env_prefix: str = "PAWN"
        max_workers: int = 4
        verbose: int = 0
        use_console: bool = True
        console_width: Optional[int] = None


class ThreadSafeConfigManager:
    """Thread-safe configuration manager with validation"""

    def __init__(self, schema_class: Type = PawnlibConfigSchema):
        self._schema_class = schema_class
        self._config = schema_class()
        self._lock = threading.RLock()
        self._sources: List[ConfigSource] = []
        self._change_listeners: List[Callable[[str, Any, Any], None]] = []

    def set(self, key: str, value: Any) -> None:
        """Set a single configuration value"""
        with self._lock:
            old_value = getattr(self._config, key, None)

            # Validate by creating new config instance
            if PYDANTIC_AVAILABLE:
                current_dict = self._config.dict()
                current_dict[key] = value
                validated_config = self._schema_class(**current_dict)
                self._config = validated_config
            else:
                setattr(self._config, key, value)

            # Notify listeners
            self._notify_change(key, old_value, value)

    def update(self, **kwargs) -> None:
        """Update multiple configuration values"""
        with self._lock:
            if PYDANTIC_AVAILABLE:
                current_dict = self._config.dict()
                current_dict.update(kwargs)
                validated_config = self._schema_class(**current_dict)
                self._config = validated_config
            else:
                for key, value in kwargs.items():
                    setattr(self._config, key, value)

            # Notify listeners for each change
            for key, value in kwargs.items():
                self._notify_change(key, None, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        with self._lock:
            if hasattr(self._config, key):
                return getattr(self._config, key)
            elif PYDANTIC_AVAILABLE and hasattr(self._config, '__fields__'):
                # Check if it's an extra field in pydantic
                config_dict = self._config.dict()
                return config_dict.get(key, default)
            else:
                return default

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        with self._lock:
            if PYDANTIC_AVAILABLE:
                return self._config.dict()
            else:
                return {k: v for k, v in self._config.__dict__.items()
                       if not k.startswith('_')}

    def add_source(self, source: ConfigSource) -> None:
        """Add configuration source"""
        with self._lock:
            self._sources.append(source)

    def reload_from_sources(self) -> None:
        """Reload configuration from all sources"""
        with self._lock:
            for source in self._sources:
                try:
                    source_config = source.load()
                    self.update(**source_config)
                except Exception as e:
                    logging.error(f"Failed to load from source {source}: {e}")

    def add_change_listener(self, listener: Callable[[str, Any, Any], None]) -> None:
        """Add configuration change listener"""
        self._change_listeners.append(listener)

    def _notify_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notify all listeners of configuration change"""
        for listener in self._change_listeners:
            try:
                listener(key, old_value, new_value)
            except Exception as e:
                logging.error(f"Error in config change listener: {e}")


class ConfigInitializer:
    """Handles configuration initialization in proper order"""

    def __init__(self, config_manager: ThreadSafeConfigManager):
        self.config_manager = config_manager
        self._state = ConfigState.UNINITIALIZED
        self._initialization_steps: List[Callable] = []
        self._error_handlers: List[Callable[[Exception], None]] = []

    def add_step(self, step: Callable) -> None:
        """Add initialization step"""
        self._initialization_steps.append(step)

    def add_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Add error handler for initialization failures"""
        self._error_handlers.append(handler)

    def initialize(self,
                  env_prefix: str = "PAWN",
                  config_file: Optional[Path] = None,
                  defaults: Optional[Dict[str, Any]] = None) -> None:
        """Initialize configuration in proper order"""
        try:
            self._state = ConfigState.LOADING

            # Step 1: Apply defaults
            if defaults:
                self.config_manager.update(**defaults)

            # Step 2: Load from environment
            env_source = EnvironmentConfigSource(prefix=env_prefix)
            self.config_manager.add_source(env_source)
            env_config = env_source.load()
            if env_config:
                self.config_manager.update(**env_config)

            # Step 3: Load from config file
            if config_file:
                file_source = FileConfigSource(config_file)
                self.config_manager.add_source(file_source)
                file_config = file_source.load()
                if file_config:
                    self.config_manager.update(**file_config)

            # Step 4: Execute custom initialization steps
            for step in self._initialization_steps:
                step(self.config_manager)

            self._state = ConfigState.READY

        except Exception as e:
            self._state = ConfigState.ERROR
            for handler in self._error_handlers:
                try:
                    handler(e)
                except Exception as handler_error:
                    logging.error(f"Error in initialization error handler: {handler_error}")
            raise

    @property
    def state(self) -> ConfigState:
        return self._state

    def is_ready(self) -> bool:
        return self._state == ConfigState.READY


class ConfigContextManager:
    """Context manager for configuration isolation in testing"""

    def __init__(self, base_manager: ThreadSafeConfigManager):
        self._base_manager = base_manager
        self._config_stack: List[Dict[str, Any]] = []

    @contextmanager
    def temporary_config(self, **overrides) -> ContextManager[ThreadSafeConfigManager]:
        """Temporarily override configuration"""
        # Save current state
        current_config = self._base_manager.to_dict()
        self._config_stack.append(current_config.copy())

        try:
            # Apply overrides
            self._base_manager.update(**overrides)
            yield self._base_manager
        finally:
            # Restore previous state
            if self._config_stack:
                previous_config = self._config_stack.pop()
                # Reset to previous config
                self._base_manager._config = self._base_manager._schema_class(**previous_config)


class ConfigSectionMap:
    """Configuration section mapper compatible with legacy ConfigSectionMap"""

    def __init__(self):
        import configparser
        self.parser = configparser.ConfigParser(interpolation=None)
        self.parser.optionxform = str  # Preserve case sensitivity

    def read(self, filename):
        """Read configuration file"""
        try:
            self.parser.read(filename)
            return True
        except Exception as e:
            print(f"Error reading config file {filename}: {e}")
            return False

    def as_dict(self, section=None):
        """Convert to dictionary format compatible with legacy"""
        try:
            # Get all sections data
            d = {}

            # Add DEFAULT section if it exists
            if self.parser.defaults():
                d["DEFAULT"] = dict(self.parser.defaults())

            # Add all other sections
            for section_name in self.parser.sections():
                d[section_name] = {}
                for key, value in self.parser.items(section_name):
                    # Skip items that are in DEFAULT section to avoid duplication
                    if key not in self.parser.defaults():
                        d[section_name][key] = value
                    else:
                        # Include DEFAULT items in each section for legacy compatibility
                        d[section_name][key] = value

            if section:
                return d.get(section, {})
            return d

        except Exception as e:
            print(f"Error converting config to dict: {e}")
            return {}

    def items(self):
        """Get all sections as items"""
        try:
            return self.as_dict().items()
        except Exception:
            return []

    def __getitem__(self, key):
        """Get section by key"""
        try:
            if self.parser.has_section(key):
                return dict(self.parser.items(key))
            return {}
        except Exception:
            return {}

    def __contains__(self, key):
        """Check if section exists"""
        return self.parser.has_section(key)

    def keys(self):
        """Get all section names"""
        sections = list(self.parser.sections())
        if self.parser.defaults():
            sections.insert(0, "DEFAULT")
        return sections



# Enhanced NestedNamespace for backward compatibility - 레거시 호환성 개선
class NestedNamespace:
    """Enhanced nested namespace with dot notation access - 레거시 호환성 개선"""

    def __init__(self, data: Optional[Dict[str, Any]] = None, **kwargs):
        if data is None:
            data = {}

        # kwargs와 data를 합침
        combined_data = {**data, **kwargs}

        # 직접 __dict__에 설정하여 레거시 방식과 동일하게 동작
        for key, value in combined_data.items():
            if isinstance(value, dict):
                setattr(self, key, NestedNamespace(value))
            elif isinstance(value, list):
                # 리스트 내부의 dict도 NestedNamespace로 변환
                mapped_list = []
                for item in value:
                    if isinstance(item, dict):
                        mapped_list.append(NestedNamespace(item))
                    else:
                        mapped_list.append(item)
                setattr(self, key, mapped_list)
            else:
                setattr(self, key, value)

    def __getattr__(self, key: str) -> Any:
        """Get attribute with fallback to None"""
        if key.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")
        return None

    def __setattr__(self, key: str, value: Any) -> None:
        """Set attribute, converting dicts to NestedNamespace"""
        if isinstance(value, dict) and not isinstance(value, NestedNamespace):
            value = NestedNamespace(value)
        elif isinstance(value, list):
            # 리스트 내부의 dict도 NestedNamespace로 변환
            mapped_list = []
            for item in value:
                if isinstance(item, dict):
                    mapped_list.append(NestedNamespace(item))
                else:
                    mapped_list.append(item)
            value = mapped_list
        super().__setattr__(key, value)

    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access"""
        return getattr(self, key, None)

    def __setitem__(self, key: str, value: Any) -> None:
        """Dictionary-style assignment"""
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get value with default"""
        return getattr(self, key, default)

    def update(self, **kwargs) -> None:
        """Update namespace"""
        for key, value in kwargs.items():
            setattr(self, key, value)

    def keys(self):
        """Get all keys"""
        return [k for k in self.__dict__.keys() if not k.startswith('_')]

    def values(self):
        """Get all values"""
        return [v for k, v in self.__dict__.items() if not k.startswith('_')]

    def items(self):
        """Get all items"""
        return [(k, v) for k, v in self.__dict__.items() if not k.startswith('_')]

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary recursively"""
        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary recursively"""
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, NestedNamespace):
                    result[key] = value.to_dict()
                elif isinstance(value, list):
                    mapped_list = []
                    for item in value:
                        if isinstance(item, NestedNamespace):
                            mapped_list.append(item.to_dict())
                        else:
                            mapped_list.append(item)
                    result[key] = mapped_list
                else:
                    result[key] = value
        return result

    def get_nested(self, keys: list):
        """
        Retrieve a nested value from the namespace using a list of keys.

        Example:
            >>> ns = NestedNamespace({'level1': {'level2': {'level3': 'value'}}})
            >>> ns.get_nested(['level1', 'level2', 'level3'])
            'value'
        """
        result = self
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key, None)
            else:
                result = getattr(result, key, None)
            if result is None:
                return None
        return result

    def __repr__(self, indent=4):
        """String representation with proper indentation - 레거시 호환"""
        result = self.__class__.__name__ + '('
        items_len = len([k for k in self.__dict__.keys() if not k.startswith('_')])
        _first = 0
        _indent_space = ''

        for k, v in self.__dict__.items():
            if k.startswith('_'):
                continue

            if _first == 0 and items_len > 0:
                result += "\n"
                _first = 1

            if isinstance(v, NestedNamespace):
                value_str = v.__repr__(indent + 4)
            else:
                value_str = repr(v)

            if k and value_str:
                if _first:
                    _indent_space = ' ' * indent
                result += _indent_space + k + '=' + value_str + ",\n"

        # 마지막 줄바꿈 제거하고 닫는 괄호 추가
        if result.endswith(',\n'):
            result = result[:-2] + '\n'

        result += ' ' * (len(_indent_space) - 4) + ')'
        return result

    def __str__(self) -> str:
        """String representation"""
        return self.__repr__()

    def __bool__(self) -> bool:
        """Boolean representation"""
        return len([k for k in self.__dict__.keys() if not k.startswith('_')]) > 0

    def _asdict(self) -> Dict[str, Any]:
        """Internal dictionary representation for compatibility"""
        return self.__dict__


class ImprovedPawnlibConfig:
    """
    Improved Pawnlib Configuration Manager

    This class provides a modern, thread-safe, and type-safe configuration
    management system for Pawnlib applications with full backward compatibility.
    """

    def __init__(self,
                 app_name: str = "pawnlib_app",
                 env_prefix: str = "PAWN",
                 config_file: Optional[Union[str, Path]] = None,
                 debug: bool = False,
                 schema_class: Type = PawnlibConfigSchema):

        # Core components
        self._manager = ThreadSafeConfigManager(schema_class)
        self._initializer = ConfigInitializer(self._manager)
        self._context_manager = ConfigContextManager(self._manager)

        # Configuration state
        self._app_name = app_name
        self._env_prefix = env_prefix
        self._config_file = Path(config_file) if config_file else None
        self._debug = debug

        # Legacy compatibility attributes
        self.version = f"{__title__}/{__version__}"
        self.version_number = __version__
        self.app_logger = Null()
        self.error_logger = Null()
        self.console = Null()
        self.data = NestedNamespace()

        # Legacy state tracking
        self._loaded = {
            "console": False,
            "on_ready": False
        }

        # Initialize with defaults
        defaults = {
            'app_name': app_name,
            'env_prefix': env_prefix,
            'debug': debug,
            'version': self.version,
            'version_number': self.version_number
        }

        try:
            self._initializer.initialize(
                env_prefix=env_prefix,
                config_file=self._config_file,
                defaults=defaults
            )

            # Mark as ready
            self._loaded['on_ready'] = True

            # Initialize console if needed

            if self.get('use_console', True):
                self._init_console()

            # Load config file in legacy style
            self._load_config_file_legacy_style()

        except Exception as e:
            logging.error(f"Failed to initialize PawnlibConfig: {e}")
            # Continue with defaults only

    def _init_console(self) -> None:
        """Initialize console for output"""
        try:
            import sys
            from pawnlib.config.console import Console

            is_interactive = hasattr(sys, 'ps1') or sys.stdin.isatty()
            self.console = Console(redirect=not is_interactive)
            self._loaded['console'] = True
        except Exception as e:
            logging.warning(f"Failed to initialize console: {e}")
            self.console = Null()

    def _load_config_file_legacy_style(self):
        """Load config file in legacy style for backward compatibility"""
        if not self._loaded.get('on_ready', False):
            return

        config_file = self.get('PAWN_CONFIG_FILE', 'config.ini')

        if isinstance(config_file, str):
            config_file = Path(config_file)
        elif not isinstance(config_file, Path):
            config_file = Path('config.ini')

        try:
            if config_file.exists() and config_file.is_file():
                config = ConfigSectionMap()
                success = config.read(str(config_file))

                if not success:
                    self.update(PAWN_CONFIG={})
                    return

                config_dict = config.as_dict()

                # Process each section and try to parse JSON values
                processed_dict = {}
                for section, config_item in config_dict.items():
                    processed_dict[section] = {}

                    for key, value in config_item.items():
                        # Try to parse value as JSON
                        try:
                            parsed_value = json.loads(value)
                            processed_dict[section][key] = parsed_value
                        except (json.JSONDecodeError, TypeError):
                            # If it's not JSON, just keep the original value
                            processed_dict[section][key] = value

                # Set PAWN_CONFIG in both improved and legacy format
                self.update(PAWN_CONFIG=processed_dict)

                # Check for duplicate keys (legacy behavior)
                self._check_duplicate_keys(config)

            else:
                self.update(PAWN_CONFIG={})
                if hasattr(self.console, 'debug'):
                    self.console.debug(f"[bold red] cannot found config_file - {config_file}")

        except Exception as e:
            if hasattr(self.console, 'log'):
                self.console.log(f"[bold red]Error occurred while loading config.ini - {e}")
            else:
                logging.error(f"Error occurred while loading config.ini - {e}")

            # Set empty config on error
            self.update(PAWN_CONFIG={})




    def _check_duplicate_keys(self, config):
        """Check for duplicate keys in config (legacy behavior)"""
        try:
            for config_category, config_value in config.items():
                section_dict = config[config_category]
                lower_keys = [key.lower() for key in section_dict.keys()]
                duplicate_keys = self._list_duplicates(lower_keys)

                for conf_key, conf_value in section_dict.items():
                    if conf_key.lower() in duplicate_keys:
                        if hasattr(self.console, 'log'):
                            self.console.log(f"[yellow][WARN] Similar keys exist in config.ini - [{config_category}] {conf_key}={conf_value}")
        except Exception as e:
            logging.warning(f"Error checking duplicate keys: {e}")

    def _list_duplicates(self, seq):
        """Find duplicate items in sequence (legacy helper)"""
        seen = set()
        seen_add = seen.add
        seen_twice = set(x for x in seq if x in seen or seen_add(x))
        return list(seen_twice)

    def get_path(self, path_input):
        """Get path object (legacy compatibility)"""
        if isinstance(path_input, (str, Path)):
            return Path(path_input)
        return Path('.')

    # Core configuration methods
    def set(self, **kwargs) -> None:
        """Set configuration values"""
        if kwargs:
            self._manager.update(**kwargs)

            # Check if config file path changed and reload
            if 'PAWN_CONFIG_FILE' in kwargs:
                self._load_config_file_legacy_style()

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._manager.get(key, default)

    def update(self, **kwargs) -> None:
        """Update configuration values"""
        self._manager.update(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return self._manager.to_dict()

    def conf(self) -> NestedNamespace:
        """Legacy method for getting configuration as namespace object"""
        config_dict = self.to_dict()
        return NestedNamespace(config_dict)

    def as_namespace(self) -> NestedNamespace:
        """Get configuration as nested namespace for dot notation access"""
        return self.conf()

    # Advanced operations
    def increase(self, **kwargs) -> Dict[str, Any]:
        """Increase numeric values"""
        results = {}
        for key, increment in kwargs.items():
            current = self.get(key, 0)
            if isinstance(current, (int, float)) and isinstance(increment, (int, float)):
                new_value = current + increment
                self.set(**{key: new_value})
                results[key] = new_value
            else:
                logging.warning(f"Cannot increase non-numeric value: {key}")
        return results


    def decrease(self, **kwargs) -> Dict[str, Any]:
        """Decrease numeric values"""
        results = {}
        for key, decrement in kwargs.items():
            current = self.get(key, 0)
            if isinstance(current, (int, float)) and isinstance(decrement, (int, float)):
                new_value = current - decrement
                self.set(**{key: new_value})
                results[key] = new_value
            else:
                logging.warning(f"Cannot decrease non-numeric value: {key}")
        return results

    def append_list(self, **kwargs) -> None:
        """Append values to list configurations"""
        for key, value in kwargs.items():
            current = self.get(key, [])
            if isinstance(current, list):
                current.append(value)
                self.set(**{key: current})
            else:
                self.set(**{key: [value]})

    def remove_list(self, **kwargs) -> None:
        """Remove values from list configurations"""
        for key, value in kwargs.items():
            current = self.get(key, [])
            if isinstance(current, list) and value in current:
                current.remove(value)
                self.set(**{key: current})

    # Context management
    def temporary_config(self, **overrides) -> ContextManager['ImprovedPawnlibConfig']:
        """Create temporary configuration context"""
        return self._context_manager.temporary_config(**overrides)

    # Status and inspection
    def is_ready(self) -> bool:
        """Check if configuration is ready"""
        return self._initializer.is_ready()

    def get_state(self) -> ConfigState:
        """Get current configuration state"""
        return self._initializer.state

    def inspect(self) -> None:
        """Inspect current configuration"""
        try:
            from rich import inspect as rich_inspect
            rich_inspect(self.to_dict())
        except ImportError:
            import pprint
            pprint.pprint(self.to_dict())

    def reload(self) -> None:
        """Reload configuration from all sources"""
        self._manager.reload_from_sources()
        self._load_config_file_legacy_style()

    # Legacy compatibility methods
    def make_config(self, **kwargs) -> None:
        """Legacy method for setting configuration"""
        self.update(**kwargs)

    def __str__(self) -> str:
        return f"ImprovedPawnlibConfig(app_name='{self._app_name}', state={self.get_state().value})"

    def __repr__(self) -> str:
        return self.__str__()



# Legacy compatibility wrapper

class LegacyCompatibilityWrapper:
    """Wrapper for backward compatibility with existing code - 레거시 완전 호환"""

    def __init__(self, improved_config: ImprovedPawnlibConfig):
        self._config = improved_config
        self._legacy_data = {}
        self._initialize_legacy_compatibility()

    def _initialize_legacy_compatibility(self):
        """Initialize legacy compatibility settings"""
        # 레거시 환경변수들을 로드
        legacy_env_vars = {}
        for key, value in os.environ.items():
            if key.startswith('PAWN_'):
                legacy_env_vars[key] = self._convert_legacy_value(value)

        # 레거시 설정 구조 생성
        self._legacy_data.update(legacy_env_vars)

        # 기본 레거시 설정들
        default_legacy_config = {
            'PAWN_VERBOSE': 0,
            'PAWN_INI': False,
            'PAWN_CONFIG_FILE': 'config.ini',
            'PAWN_DEBUG': False,
            'PAWN_TIMEOUT': 6000,
            'PAWN_LOGGER': {},
            'PAWN_VERSION': f"{__title__}/{__version__}",
            'PAWN_USE_GLOBAL_NS': False,
            'PAWN_CONSOLE': {'log_path': False},
            'PAWN_LINE': False,
            'PAWN_PATH': os.getcwd(),
            'PAWN_TIME_FORMAT': '%H:%M:%S.%f',
            'PAWN_SSL_CHECK': True,
            'PAWN_CONFIG': {}
        }

        # 기본값 설정 (이미 있는 값은 덮어쓰지 않음)
        for key, value in default_legacy_config.items():
            if key not in self._legacy_data:
                self._legacy_data[key] = value

        # improved config에서 값들을 가져와서 레거시 형태로 변환
        improved_dict = self._config.to_dict()
        for key, value in improved_dict.items():
            legacy_key = f"PAWN_{key.upper()}"
            self._legacy_data[legacy_key] = value

    def _convert_legacy_value(self, value: str) -> Any:
        """Convert string environment variable to appropriate type"""
        # Boolean 변환
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'

        # 숫자 변환
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # JSON 변환 시도
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            pass

        return value

    def __getattr__(self, name: str) -> Any:
        # conf() 메서드는 특별 처리
        if name == 'conf':
            return self.conf
        # 다른 속성들은 improved config에 위임
        return getattr(self._config, name)

    def set(self, **kwargs) -> Any:
        """Legacy set method - 레거시와 개선된 양쪽에 설정"""
        # 개선된 설정에 저장할 kwargs
        improved_kwargs = {}

        for key, value in kwargs.items():
            # PAWN_ 프리픽스가 있으면 레거시 데이터에 저장
            if key.startswith('PAWN_'):
                self._legacy_data[key] = value
                # PAWN_ 제거한 키로도 개선된 설정에 저장 (특정 키들은 제외)
                if key not in ['PAWN_CONFIG']:  # PAWN_CONFIG는 레거시 전용
                    clean_key = key[5:].lower()
                    improved_kwargs[clean_key] = value
            else:
                # 일반 키는 바로 저장하고 PAWN_ 버전도 생성
                improved_kwargs[key] = value
                legacy_key = f"PAWN_{key.upper()}"
                self._legacy_data[legacy_key] = value

        # improved config에 저장 (PAWN_CONFIG 제외)
        if improved_kwargs:
            self._config.update(**improved_kwargs)  # set 대신 update 사용

        # PAWN_CONFIG_FILE이 변경되면 config 파일 재로드
        if 'PAWN_CONFIG_FILE' in kwargs:
            self._config._load_config_file_legacy_style()

        return self


    def get(self, key: str, default: Any = None) -> Any:
        """Legacy get method"""
        # PAWN_ 프리픽스가 있으면 레거시 데이터에서 찾기
        if key.startswith('PAWN_'):
            return self._legacy_data.get(key, default)
        else:
            # 일반 키는 개선된 설정에서 찾기
            return self._config.get(key, default)

    def conf(self) -> NestedNamespace:
        """Legacy conf method - returns NestedNamespace with legacy structure"""
        # 개선된 설정에서 최신 값들을 가져와서 레거시 데이터 업데이트
        improved_dict = self._config.to_dict()
        for key, value in improved_dict.items():
            legacy_key = f"PAWN_{key.upper()}"
            self._legacy_data[legacy_key] = value

        # 특별히 PAWN_CONFIG는 직접 확인
        pawn_config = self._config.get('PAWN_CONFIG')
        if pawn_config is not None:
            self._legacy_data['PAWN_CONFIG'] = pawn_config

        # 레거시 구조를 NestedNamespace로 변환
        return NestedNamespace(self._legacy_data)


    def to_dict(self) -> Dict[str, Any]:
        """Legacy to_dict method"""
        # 최신 데이터로 업데이트
        improved_dict = self._config.to_dict()
        for key, value in improved_dict.items():
            legacy_key = f"PAWN_{key.upper()}"
            self._legacy_data[legacy_key] = value

        return self._legacy_data.copy()

    def make_config(self, **kwargs) -> None:
        """Legacy make_config method"""
        self.set(**kwargs)

    # 다른 레거시 메서드들...
    def increase(self, **kwargs) -> Dict[str, Any]:
        results = {}
        for key, increment in kwargs.items():
            current = self.get(key, 0)
            if isinstance(current, (int, float)) and isinstance(increment, (int, float)):
                new_value = current + increment
                self.set(**{key: new_value})
                results[key] = new_value
        return results

    def decrease(self, **kwargs) -> Dict[str, Any]:
        results = {}
        for key, decrement in kwargs.items():
            current = self.get(key, 0)
            if isinstance(current, (int, float)) and isinstance(decrement, (int, float)):
                new_value = current - decrement
                self.set(**{key: new_value})
                results[key] = new_value
        return results

    def append_list(self, **kwargs) -> None:
        for key, value in kwargs.items():
            current = self.get(key, [])
            if isinstance(current, list):
                current.append(value)
                self.set(**{key: current})
            else:
                self.set(**{key: [value]})

    def remove_list(self, **kwargs) -> None:
        for key, value in kwargs.items():
            current = self.get(key, [])
            if isinstance(current, list) and value in current:
                current.remove(value)
                self.set(**{key: current})


# Factory functions
def create_improved_config(
    app_name: str = "pawnlib_app",
    env_prefix: str = "PAWN",
    config_file: Optional[Union[str, Path]] = None,
    debug: bool = False,
    schema_class: Type = PawnlibConfigSchema
) -> ImprovedPawnlibConfig:
    """Factory function to create improved configuration manager"""
    return ImprovedPawnlibConfig(
        app_name=app_name,
        env_prefix=env_prefix,
        config_file=config_file,
        debug=debug,
        schema_class=schema_class
    )


_default_improved_config = create_improved_config()
improved_pawnlib_config = LegacyCompatibilityWrapper(_default_improved_config)

# Aliases for convenience - 레거시와 동일한 방식
pawn_improved = improved_pawnlib_config
pconf_improved = improved_pawnlib_config.conf

# Export commonly used classes and functions
__all__ = [
    'ImprovedPawnlibConfig',
    'ThreadSafeConfigManager',
    'ConfigState',
    'PawnlibConfigSchema',
    'EnvironmentConfigSource',
    'FileConfigSource',
    'ConfigContextManager',
    'NestedNamespace',
    'create_improved_config',
    'improved_pawnlib_config',
    'pawn_improved',
    'pconf_improved',
    'LegacyCompatibilityWrapper',
    'ConfigSectionMap'
]
