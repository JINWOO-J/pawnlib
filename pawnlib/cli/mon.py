#!/usr/bin/env python3
import os
import asyncio
import argparse

from aiohttp import ClientSession
from dotenv import load_dotenv, find_dotenv
from pawnlib.config import pawn, setup_logger
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.resource.monitor import SSHMonitor
from pawnlib.resource.server import get_interface_ips
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter, get_service_specific_arguments
from typing import List, Dict, Optional, Type, Any
from pawnlib.typing import (
    hex_to_number,
    shorten_text,
    str2bool,
    is_valid_token_address,
    sys_exit,
    is_valid_url,

)
from pawnlib.output import print_var, get_script_path, is_file, get_parent_path
from pawnlib.utils.http import AsyncGoloopWebsocket, NetworkInfo
from pawnlib.docker.compose import DockerComposeBuilder
from InquirerPy import inquirer
from rich.prompt import Prompt
from pawnlib.resource import SSHLogPathResolver
from pawnlib.utils.notify import send_slack
from pawnlib.exceptions.notifier import notify_exception
import traceback
from pawnlib.input import get_default_arguments

IS_DOCKER = str2bool(os.environ.get("IS_DOCKER"))

__description__ = "SSH and Wallet Monitoring Tool"
__epilog__ = (
    "\nUsage examples:\n\n"
    "1. Start monitoring SSH log files:\n"
    "     `pawns mon ssh -f /var/log/secure /var/log/auth.log`\n\n"
    "2. Start the wallet client:\n"
    "     `pawns mon wallet --url https://example.com -vvv`\n\n"
    "Note:\n"
    "  You can monitor multiple log files by providing multiple `-f` arguments.\n"
)


class ComposeDefaultSettings:
    BASE_DIR = "/pawnlib"
    LOG_FILE = "/pawnlib/logs"
    VERBOSE = 1
    LOG_TYPE = "file"
    # DEFAULT_BASE_DIR = "."
    # DEFAULT_LOG_FILE = ""
    PRIORITY = "env"


def get_parser():
    parser = CustomArgumentParser(
        description='Command Line Interface for SSH and Wallet Monitoring',
        formatter_class=ColoredHelpFormatter,
        epilog=__epilog__
    )
    parser = get_arguments(parser)
    return parser


def add_common_arguments(parser):
    """Add common arguments to both SSH and Wallet parsers."""
    parser.add_argument(
        '--log-type',
        choices=['console', 'file'],
        default='console',
        help='Choose logger type: console or file (default: console)'
    )
    parser.add_argument(
        '--log-file',
        help='Log file path if using file logger (required if --log-type=file)',
        default=None
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='count',
        default=1,
        help='Increase verbosity level. Use -v, -vv, -vvv, etc.'
    )
    parser.add_argument(
        '--slack-webhook-url',
        help='Slack webhook URL',
        default=None
    )
    parser.add_argument(
        '--send-slack',
        type=str2bool,
        help='Enable sending messages to Slack',
        default=True
    )

    parser.add_argument(
        '--priority',
        choices=['env', 'args'],
        default='args',
        help='Specify whether to prioritize environment variables ("env") or command-line arguments ("args"). Default is "args".'
    )

    return parser


def get_arguments(parser=None):
    if not parser:
        parser = CustomArgumentParser()

    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    ssh_parser = subparsers.add_parser('ssh', help='Monitor SSH logs')
    ssh_parser.add_argument(
        '-f', '--file',
        metavar='ssh_log_file',
        help='SSH log file(s) to monitor',
        nargs='+',
        default=[SSHLogPathResolver().get_path()]
    )
    ssh_parser.add_argument(
        '-b', '--base-dir',
        metavar='base_dir',
        help='Base directory for the application',
        default="."
    )
    add_common_arguments(ssh_parser)

    wallet_parser = subparsers.add_parser('wallet', help='Run the Async Goloop Websocket Client')
    wallet_parser.add_argument(
        '--url', '--endpoint-url',
        metavar="endpoint_url",
        dest='endpoint_url',
        help='Endpoint URL',
    )

    wallet_parser.add_argument(
        '--ignore-data-types',
        help='Comma-separated list of data types to ignore',
        default='base'
    )
    wallet_parser.add_argument(
        '--check-tx-result-enabled',
        type=str2bool,
        help='Enable checking transaction results',
        default=True
    )
    wallet_parser.add_argument(
        '--address-filter',
        help='Comma-separated list of addresses to filter',
        default=None
    )
    wallet_parser.add_argument(
        '--max-transaction-attempts',
        type=int,
        help='Maximum transaction attempts',
        default=10
    )
    wallet_parser.add_argument(
        '--max-retries',
        type=int,
        default=10,
        help='Maximum number of retries for WebSocket connection attempts. Must be a positive integer. Default is 10.',
        choices=range(1, 101),  # Allow values between 1 and 100 for better control
        metavar='[1-100]'  # Display valid range in help output
    )
    wallet_parser.add_argument(
        '--blockheight',
        type=int,
        default=None,
        help='Specify the block height to start from (default: None).'
    )
    wallet_parser.add_argument('-n', '--network-name', type=str,  help='network name', default="")
    add_common_arguments(wallet_parser)

    compose_parser = subparsers.add_parser('compose', help='Generate docker-compose.yml file')
    compose_parser.add_argument('-d', '--directory', type=str,  help='Path to the directory to upload or download')
    compose_parser.add_argument('-f', '--compose-file', type=str,  help='docker-compose file name', default="docker-compose.yml")
    add_common_arguments(compose_parser)

    return parser


def load_environment_settings(args) -> dict:
    """
    Load environment settings from command-line arguments or environment variables,
    prioritizing args if provided, otherwise using environment variables.
    """
    def get_setting(
            attr_name: str,
            env_var: str,
            default: Optional[Any] = None,
            value_type: Type = str,
            is_list: bool = False
    ) -> Any:
        """Helper function to get setting value from args or env."""

        # Check if the argument was provided via the command line
        value = getattr(args, attr_name, None)

        # If priority is 'args' and the argument is explicitly provided (including 0), use it
        if args.priority == 'args' and value is not None and value != 0:
            pawn.console.debug(f"Using command-line argument for '{attr_name}': {value}")
            return value

        # Check the environment variable if command-line argument is not provided or default
        env_value = os.environ.get(env_var, None)

        if env_value is not None:
            if is_list:
                pawn.console.debug(f"Using environment variable for '{attr_name}': {env_value}")
                return [item.strip() for item in env_value.split(",") if item.strip()]
            elif value_type == bool:
                pawn.console.debug(f"Using environment variable for '{attr_name}': {env_value}")
                return str2bool(env_value)
            elif value_type == int:
                try:
                    env_value_int = int(env_value)
                    pawn.console.debug(f"Using environment variable for '{attr_name}': {env_value_int}")
                    return env_value_int
                except ValueError:
                    pawn.console.debug(f"[WARN] Invalid int value for environment variable '{env_var}', using default: {default}")
                    return default
            else:
                pawn.console.debug(f"Using environment variable for '{attr_name}': {env_value}")
                return env_value

        # If neither is provided, use the default value
        pawn.console.debug(f"Using default value for '{attr_name}': {default}")
        return default

    settings: dict = {
        'endpoint_url': get_setting('endpoint_url', 'ENDPOINT_URL', default="", value_type=str),
        'ignore_data_types': get_setting('ignore_data_types', 'IGNORE_DATA_TYPES', default=['base'], is_list=True),
        'check_tx_result_enabled': get_setting('check_tx_result_enabled', 'CHECK_TX_RESULT_ENABLED', default=True, value_type=bool),
        'address_filter': get_setting('address_filter', 'ADDRESS_FILTER', default=[], is_list=True),
        'log_type': get_setting('log_type', 'LOG_TYPE', default='console', value_type=str),
        'file': get_setting('file', 'FILE', default=None, is_list=True),
        'slack_webhook_url': get_setting('slack_webhook_url', 'SLACK_WEBHOOK_URL', default=None, value_type=str),
        'send_slack': get_setting('send_slack', 'SEND_SLACK', default=True, value_type=bool),
        'max_transaction_attempts': get_setting('max_transaction_attempts', 'MAX_TRANSACTION_ATTEMPTS', default=10, value_type=int),
        'verbose': get_setting('verbose', 'VERBOSE', default=1, value_type=int),
        'network_name': get_setting('network_name', 'NETWORK_NAME', default="", value_type=str),
    }

    return settings


def setup_app_logger(log_type: str = 'console', verbose: int = 0, app_name: str = ""):
    """Sets up the logger based on the selected type (console or file)."""
    log_time_format = '%Y-%m-%d %H:%M:%S.%f'

    if log_type == 'file':
        stdout_value =str2bool( not IS_DOCKER and (verbose > 1))
        # pawn.console.log(f"stdout_value={stdout_value}")
        pawn.set(
            PAWN_LOGGER=dict(
                log_level="INFO",
                stdout_level="INFO",
                # stdout=verbose > 1,
                stdout=stdout_value,
                log_format="[%(asctime)s] %(levelname)s::" "%(filename)s/%(funcName)s(%(lineno)d) %(message)s",
                std_log_format="%(message)s",
                use_hook_exception=True,
                use_clean_text_filter=True,
            ),
            PAWN_TIME_FORMAT=log_time_format,
            PAWN_CONSOLE=dict(
                redirect=True,
                record=True
            ),
            app_name=app_name,
            data={}
        )
        pawn.console.log(pawn.to_dict())
        _logger = pawn.app_logger
    else:
        _logger = pawn.console  # Use pawn's built-in console logger


    return setup_logger(_logger, f"Monitoring {app_name}", verbose)

def merge_environment_settings(args):
    """
    Merge environment settings with command-line arguments based on the selected priority.
    """
    dotenv_path = f"{pawn.get_path()}/.env"
    if not is_file(dotenv_path):
        pawn.console.log(".env file not found")
    else:
        pawn.console.log(f".env file found at '{dotenv_path}'")
        load_dotenv(dotenv_path=dotenv_path)

    parser = get_parser()
    default_args = get_default_arguments(parser)
    env_settings = load_environment_settings(args)
    args_dict = vars(args)
    # settings = env_settings.copy()  # Start with environment settings
    _settings = {}

    # Determine which to prioritize: env or args
    if args.priority == 'env':
        for key, value in args_dict.items():
            # pawn.console.log(f"{key} = {value}")
            if env_settings.get(key) is None:
                _value = value
            else:
                _value = env_settings.get(key, value)

            # _settings[key] = env_settings.get(key, value)
            _settings[key] = _value
    else:
        # Command-line arguments take priority
        for key, args_value in args_dict.items():
            default_value = default_args.get(key)
            env_value = env_settings.get(key, args_value)

            if args_value != default_value:
                _value = args_value
            else:
                _value = env_value
            # pawn.console.log(f"{key}, args_value={args_value}, env_value={env_value}, default={default_value}")
            _settings[key] = _value
    return _settings


def run_monitor_ssh(args, logger):
    settings = merge_environment_settings(args)
    print_var(settings)

    ssh_monitor = SSHMonitor(
        log_file_path=settings.get('file'),
        slack_webhook_url=settings.get('slack_webhook_url'),
        alert_interval=60,
        verbose=settings.get('verbose', 1),
        # verbose=0,
        logger=logger,
        # stdout=True
    )

    async def run_async_monitor():
        await ssh_monitor.monitor_ssh()

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(run_async_monitor())
        loop.run_forever()
    except RuntimeError:
        asyncio.run(run_async_monitor())

def run_wallet_client(args, logger):
    settings = merge_environment_settings(args)
    if not settings['endpoint_url']:
        sys_exit("[ERROR] Endpoint URL is required. Please provide it via '--url' or '--endpoint-url' argument or 'ENDPOINT_URL' environment variable.")

    if not is_valid_url(settings['endpoint_url']):
        sys_exit(f"[ERROR] The provided URL '{settings['endpoint_url']}' is invalid. Please check the format and try again.")

    settings_uppercase = {key.upper(): value for key, value in settings.items()}
    pawn.console.log("[INFO] Settings loaded from environment variables and command-line arguments.")
    pawn.console.log("Effective settings:\n")
    print_var(settings_uppercase)

    if settings.get('network_name'):
        network_info = NetworkInfo(network_name=settings.get('network_name'))
        pawn.console.log(f"Network information retrieved using NetworkInfo: {network_info}")
        if network_info.network_api:
            settings['endpoint_url'] = network_info.network_api
            pawn.console.log(f"Changed endpoint url  to {network_info}")
    else:
        network_info = None
    # Initialize AsyncGoloopWebsocket client
    async def run_client():
        async with ClientSession() as session:
            websocket_client = AsyncGoloopWebsocket(
                url=settings['endpoint_url'],
                verbose=int(settings['verbose']),
                ignore_data_types=settings['ignore_data_types'],
                check_tx_result_enabled=settings['check_tx_result_enabled'],
                address_filter=settings['address_filter'],
                send_slack=settings['send_slack'],
                max_transaction_attempts=int(settings['max_transaction_attempts']),
                slack_webhook_url=settings['slack_webhook_url'],
                logger=logger,
                session=session,
                network_info=network_info,
                max_retries=settings['max_retries']
            )
            await websocket_client.initialize()
            await websocket_client.run_from_blockheight(blockheight=args.blockheight)
    try:
        loop = asyncio.get_running_loop()  # Check if there's already a running loop
        if loop.is_running():
            # If the loop is running, create a new task for the client
            loop.create_task(run_client())
        else:
            # If no loop is running, use asyncio.run to start a new event loop
            asyncio.run(run_client())
    except RuntimeError as e:
        # Handle the case where no loop is running and we need to start a new one
        if str(e) == "no running event loop":
            asyncio.run(run_client())
        else:
            notify_exception(e, logger=logger)
    except Exception as e:
        notify_exception(e, logger=logger)
        raise e


def select_service_name():
    """
    Show a simple menu to select between SSH and Wallet for docker-compose generation.
    """
    options = [
        {"name": "Generate docker-compose.yml for SSH Monitoring", "value": "ssh", "description": "Generate docker-compose.yml for SSH log monitoring"},
        {"name": "Generate docker-compose.yml for Wallet Monitoring", "value": "wallet", "description": "Generate docker-compose.yml for Wallet WebSocket monitoring"},
    ]
    selected_option = inquirer.select(
        message="Select a service to generate docker-compose.yml for:",
        choices=options,
        instruction="Use the arrow keys to navigate and Enter to select.",
    ).execute()
    return selected_option


def prompt_for_env_variables(settings: dict) -> dict:
    """
    Prompt user to input values for settings. Use default values if provided.
    If a value is a list, it will be converted to a comma-separated string.
    Special handling for BASE_DIR and LOG_FILE defaults from ComposeDefaultSettings.

    Args:
        settings (dict): Dictionary containing key-value pairs of settings.

    Returns:
        dict: Dictionary with user-provided or default values.
    """
    env_dict = {}
    settings_uppercase = {key.upper(): value for key, value in settings.items()}
    default_settings = {attr.upper(): getattr(ComposeDefaultSettings, attr)
                        for attr in dir(ComposeDefaultSettings)
                        if not callable(getattr(ComposeDefaultSettings, attr)) and not attr.startswith("__")}
    pawn.console.log(default_settings)
    merged_settings = {**settings_uppercase, **default_settings}
    pawn.console.log(merged_settings)
    for key, default_value in merged_settings.items():
        if isinstance(default_value, list):
            default_value_str = ",".join(str(item) for item in default_value)
        else:
            default_value_str = str(default_value) if default_value is not None else ""
        default_str = f" (default: {default_value_str})" if default_value_str else ""
        user_input = Prompt.ask(f"Enter Environment value for '{key}'{default_str}", default=default_value_str).strip()
        env_dict[key] = user_input

    return env_dict


def run_compose_init(args, logger, parser):
    logger.info("Starting Docker Compose initialization.")
    # settings = merge_environment_settings(args)

    builder = DockerComposeBuilder(compose_file=args.compose_file)
    logger.debug(f"Using compose file: {args.compose_file}")

    service_name = select_service_name()
    logger.info(f"Selected service name: {service_name}")

    service_args = get_service_specific_arguments(parser, service_name)
    logger.debug(f"Service specific arguments for '{service_name}': {service_args}")

    environments = prompt_for_env_variables(service_args)
    logger.debug(f"Prompted environment variables: {environments}")

    image = builder.get_valid_input("Enter the image name", default=f"jinwoo/pawnlib:{_version}")
    logger.info(f"Using image: {image}")

    volumes = builder.get_volumes("./logs:/pawnlib/logs")
    logger.debug(f"Initial volumes: {volumes}")

    if service_name == "ssh" and environments.get('FILE'):
        _file_path = os.path.dirname(environments['FILE'])
        volumes.append(f"{_file_path}:{_file_path}")
        logger.info(f"Adding volume for SSH service: {_file_path}")

    service = {
        "image": image,
        "container_name": f"{service_name}_container",
        "hostname": "${HOSTNAME}",
        "environment": environments,
        "command": f"pawns mon {service_name} --priority env",
        "volumes": volumes,
        "restart": "on-failure:5"
    }

    logger.debug(f"Constructed service configuration: {service}")

    builder.add_service(service_name, service)
    logger.info(f"Added service '{service_name}' to the Docker Compose builder.")

    docker_compose_data = builder.get_docker_compose_data()
    logger.debug("Retrieved Docker Compose data.")

    # builder.create_docker_compose()
    builder.save_docker_compose()
    logger.info("Docker Compose file saved successfully.")


def initialize_logger(settings):
    """Set up the logger based on the command and its log type."""
    app_name = f"{settings.get('command')}_watcher"
    pawn.console.log(app_name)
    return setup_app_logger(log_type=settings.get('log_type'), verbose=settings.get('verbose'), app_name=app_name)


def main():
    banner = generate_banner(
        app_name="Monitoring",
        author="jinwoo",
        description="Monitor SSH logs and run the Async Goloop Websocket Client",
        font="ogre",
        version=f"{_version}, IS_DOCKER={IS_DOCKER}"
    )

    parser = get_parser()
    args = parser.parse_args()

    print(banner)
    pawn.console.log(f"Parsed arguments: {args}")

    settings = merge_environment_settings(args)
    print_var(settings)

    if settings.get('command'):
        logger = initialize_logger(settings)
    else:
        logger = None

    local_ip_list = get_interface_ips(ignore_interfaces=['lo0', 'lo'], ip_only=True)

    if local_ip_list:
        local_ip_list = ", ".join(local_ip_list)

    msg_text = {
            "Info": f"The `{args.command.upper()}` service has been successfully launched on the following IP addresses: {local_ip_list}",
    }

    if args.command == "wallet":
        msg_text['URL'] = settings['endpoint_url']

    if settings.get('send_slack'):
        send_slack(
            title=f":rocket: {args.command.upper()} Monitoring Service Started",
            msg_text=msg_text,
            status="info",
            msg_level="info",
            icon_emoji=":start-button:",
            # async_mode=False
        )
    # # 예외 발생 시 슬랙으로 에러 알림을 전송하는 부분
    # tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    # send_slack(
    #     title=":warning: **Error Occurred**",
    #     msg_text={
    #         "Error Message": f"```{str(e)}```",
    #         "Traceback": f"```{tb_str}```"
    #     },
    #     status="error",
    #     msg_level="error",
    #     icon_emoji=":alert:"
    # )

    try:
        if args.command == "ssh":
            pawn.console.log(f"Starting SSH monitoring with files: {args.file}")
            run_monitor_ssh(args, logger)
        elif args.command == "wallet":
            pawn.console.log("Starting Async Goloop Websocket Client")
            run_wallet_client(args, logger)
        elif args.command == "compose":
            pawn.console.log("Generating docker-compose.yml file")
            run_compose_init(args, logger, parser)
        else:
            parser.print_help()
    except Exception as e:
        tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        send_slack(
            msg_text=f"An error occurred: {str(e)}\n\nTraceback:\n{tb_str}",
            status="error",
            msg_level="error",
            icon_emoji=":alert:"
        )
        raise e

main.__doc__ = (
    f"{__description__}\n{__epilog__}"
)


if __name__ == '__main__':
    main()




