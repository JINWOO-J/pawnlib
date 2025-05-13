from typing import Optional, Callable, Type, Any, Dict, TypeVar, Generic
from pawnlib.config import pawn, NestedNamespace
from pawnlib.utils.http import NetworkInfo
from dataclasses import dataclass, field
from pawnlib.output import print_var
import os
from dotenv import load_dotenv, find_dotenv



def str2bool(value: str) -> bool:
    return value.lower() in ("yes", "true", "t", "1")


class SettingDefinition:
    def __init__(
            self,
            env_var: str,
            default: Optional[Any] = None,
            value_type: Type = str,
            is_list: bool = False,
            custom_converter: Optional[Callable[[str], Any]] = None
    ):
        self.env_var = env_var
        self.default = default
        self.value_type = value_type
        self.is_list = is_list
        self.custom_converter = custom_converter

    def get_value(self, args, attr_name: str) -> Any:
        """설정 값을 가져오는 메서드"""
        # 명령줄 인수 우선 확인
        value = getattr(args, attr_name, None)
        if args.priority == 'args' and value is not None and value != 0:
            pawn.console.debug(f"Using command-line argument for '{attr_name}': {value}")
            return value

        # 환경 변수 확인
        env_value = os.environ.get(self.env_var, None)
        if env_value is not None:
            try:
                if self.is_list:
                    pawn.console.debug(f"<is_list> Using environment variable for '{attr_name}': {env_value}")
                    return [item.strip() for item in env_value.split(",") if item.strip()]
                elif self.custom_converter:
                    pawn.console.debug(f"Using custom converter for '{attr_name}': {env_value}")
                    return self.custom_converter(env_value)
                elif self.value_type == bool:
                    pawn.console.debug(f"Using environment variable for '{attr_name}': {env_value}")
                    return str2bool(env_value)
                elif self.value_type == int:
                    env_value_int = int(env_value)
                    pawn.console.debug(f"Using environment variable for '{attr_name}': {env_value_int}")
                    return env_value_int
                else:
                    pawn.console.debug(f"Using environment variable for '{attr_name}': {env_value}")
                    return env_value
            except (ValueError, TypeError) as e:
                pawn.console.debug(f"[WARN] Invalid value for '{self.env_var}' (type: {self.value_type.__name__}), using default: {self.default}. Error: {e}")
                return self.default

        # 기본값 반환
        pawn.console.debug(f"Using default value for '{attr_name}': {self.default}")
        return self.default


@dataclass
class BaseSettingsConfig:
    def get_definitions(self) -> Dict[str, SettingDefinition]:
        """모든 설정 정의를 딕셔너리로 반환"""
        return {key: value for key, value in self.__dict__.items() if isinstance(value, SettingDefinition)}

    def add_definition(self, name: str, definition: SettingDefinition):
        """새로운 설정 정의 추가"""
        setattr(self, name, definition)

T = TypeVar('T', bound=BaseSettingsConfig)

def load_environment_settings(args, settings_config: Type[T] = BaseSettingsConfig) -> Dict[str, Any]:
    """
    Load environment settings from command-line arguments or environment variables,
    prioritizing args if provided, otherwise using environment variables.

    Args:
        args: Command-line arguments object
        settings_config: BaseSettingsConfig instance (or its subclass) containing setting definitions
    """
    load_dotenv()
    settings: Dict[str, Any] = {}

    # 정의된 설정 로드
    for attr_name, definition in settings_config().get_definitions().items():
        settings[attr_name] = definition.get_value(args, attr_name)

    # 동적으로 추가된 args 속성 반영
    for attr_name in dir(args):
        if (attr_name not in settings_config().get_definitions() and
                not attr_name.startswith('_') and
                attr_name != 'priority'):
            settings[attr_name] = getattr(args, attr_name)

    return settings


class AppConfig(NestedNamespace):
    """
    A configuration class accessible in a namespace style.
    The settings are provided as a dictionary and converted to NestedNamespace for use.

    Attributes:
        network: Network information (based on NetworkInfo, converted to NestedNamespace)
        extras: Additional settings or metadata (converted to NestedNamespace)
    """
    def __init__(
            self,
            network_info: NetworkInfo = None,
            extras: Optional[Dict[str, Any]] = None,
            **settings
    ):

        if not isinstance(settings, dict):
            raise ValueError(f"settings must be a dict. Received type: {type(settings)}")

    # Check if settings is a dictionary and convert it to NestedNamespace
        # if settings and not isinstance(settings, dict):
        #     raise ValueError(f"settings must be a dict. Received type: {type(settings)}")

        # Initialize with NestedNamespace for settings, network, and extras
        super().__init__(
            network_info=network_info,
            extras=NestedNamespace(**(extras or {})),
            **settings
        )

    def __repr__(self):
        return f"AppConfig({self.__dict__})"
