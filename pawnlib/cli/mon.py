#!/usr/bin/env python3
import os
import asyncio

from aiohttp import ClientSession
import aiofiles
import json
from dotenv import load_dotenv, find_dotenv
from pawnlib.config import pawn, pconf, setup_logger, setup_app_logger as _setup_app_logger, create_app_logger
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.resource.monitor import SSHMonitor
from pawnlib.resource.server import get_interface_ips
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter, get_service_specific_arguments
from typing import List, Dict, Optional, Type, Any
from pawnlib.typing import (
    str2bool,
    sys_exit,
    is_valid_url,
    shorten_text,
    HexConverter,
    todaydate
)
from pawnlib.output import print_var, get_script_path, is_file, get_parent_path
from pawnlib.utils.http import AsyncGoloopWebsocket, NetworkInfo, AsyncIconRpcHelper
from pawnlib.docker.compose import DockerComposeBuilder
from InquirerPy import inquirer
from rich.prompt import Prompt
from pawnlib.resource import SSHLogPathResolver
from pawnlib.utils.notify import send_slack, send_slack_notification, SlackNotifier
from pawnlib.exceptions.notifier import notify_exception
import traceback
from pawnlib.input import get_default_arguments
import logging


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
    PRIORITY = "env"


def parse_address_list(address_string):
    """Comma-separated string to list, removing whitespace."""
    if address_string == "no":
        return []
    return [address.strip() for address in address_string.split(',')]


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
        choices=['console', 'file', 'both'],
        default='console',
        help='Choose logger type: console or file (default: console)'
    )
    parser.add_argument(
        '--log-file',
        help='Log file path if using file logger (required if --log-file=file)',
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
        default='env' if IS_DOCKER else 'args',
        help='Specify whether to prioritize environment variables ("env") or command-line arguments ("args"). Default is "args".'
    )

    parser.add_argument(
        '-b', '--base-dir',
        metavar='base_dir',
        help='Base directory for the application',
        default="."
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
        type=parse_address_list,
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

    wallet_parser.add_argument(
        '--bps-interval', '-i',
        type=int,
        help='Set the interval (in seconds) for calculating Blocks Per Second (BPS) and Transactions Per Second (TPS). '
             'Use a value greater than 0 to enable calculations. Set to 0 to disable BPS/TPS calculations.',
        default=0,
    )

    wallet_parser.add_argument(
        '--skip-until', '-su',
        type=int,
        help='Specify a block height up to which all blocks should be skipped. '
             'Any block with a height less than or equal to this value will be ignored. '
             'Set to 0 to disable block skipping.',
        default=0,
    )

    wallet_parser.add_argument('-n', '--network-name', type=str,  help='network name', default="")
    add_common_arguments(wallet_parser)

    wallet_multi_parser = subparsers.add_parser('wallet-multi', help='Run the Async Goloop Websocket Client')
    wallet_multi_parser.add_argument(
        '--url', '--endpoint-url',
        metavar="endpoint_url",
        dest='endpoint_url',
        help='Endpoint URL',
    )

    wallet_multi_parser.add_argument(
        '--address-filter',
        help='Comma-separated list of addresses to filter',
        type=parse_address_list,
        default=None
    )

    wallet_multi_parser.add_argument(
        '--check-interval',
        type=int,
        help='Monitoring interval in seconds',
        default=10
    )

    wallet_multi_parser.add_argument(
        '--ignore-decimal',
        action='store_true',
        help='Ignore decimal when monitor to wallet ',
        default=False
    )

    add_common_arguments(wallet_multi_parser)

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
                pawn.console.debug(f"<is_list> Using environment variable for '{attr_name}': {env_value}")
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
        'bps_interval': get_setting('bps_interval', 'BPS_INTERVAL', default=0, value_type=int),
        'skip_until': get_setting('skip_until', 'SKIP_UNTIL', default=0, value_type=int),
        'base_dir': get_setting('base_dir', 'BASE_DIR', default="./", value_type=str),
        # 'state_cache_file': os.environ.get('STATE_CACHE_FILE', args.state_cache_file),
        'check_interval': get_setting('check_interval', 'CHECK_INTERVAL', default=10, value_type=int),
        'ignore_decimal': get_setting('ignore_decimal', 'IGNORE_DECIMAL', default=False, value_type=bool),
    }
    return settings


# def setup_app_logger(log_type: str = 'console', verbose: int = 0, app_name: str = ""):
#     """Sets up the logger based on the selected type (console or file)."""
#     log_time_format = '%Y-%m-%d %H:%M:%S.%f'
#
#     if log_type == 'file':
#         stdout_value =str2bool( not IS_DOCKER and (verbose > 1))
#         # pawn.console.log(f"stdout_value={stdout_value}")
#         pawn.set(
#             PAWN_LOGGER=dict(
#                 log_level="INFO",
#                 stdout_level="INFO",
#                 # stdout=verbose > 1,
#                 stdout=stdout_value,
#                 log_format="[%(asctime)s] %(levelname)s::" "%(filename)s/%(funcName)s(%(lineno)d) %(message)s",
#                 std_log_format="%(message)s",
#                 use_hook_exception=True,
#                 use_clean_text_filter=True,
#             ),
#             PAWN_TIME_FORMAT=log_time_format,
#             PAWN_CONSOLE=dict(
#                 redirect=True,
#                 record=True
#             ),
#             app_name=app_name,
#             data={}
#         )
#         pawn.console.log(pawn.to_dict())
#         _logger = pawn.app_logger
#     else:
#         _logger = pawn.console  # Use pawn's built-in console logger
#
#     return setup_logger(_logger, f"Monitoring {app_name}", verbose)


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


class WalletStateTracker:
    def __init__(self, persist_file: str = None):
        self._cache = {}
        self.persist_file = persist_file or "/tmp/state_cache_file.json"
        self.lock = asyncio.Lock()  # 비동기 안전성 추가
        pawn.console.debug(f"state_cache_file = {self.persist_file}")

    def get(self, address: str) -> dict:
        """주소별 캐시 데이터 반환"""
        return self._cache.get(address, {})

    async def update(self, address: str, new_data: dict) -> bool:
        """변경 감지 및 업데이트 수행"""
        async with self.lock:
            prev_data = self.get(address)
            if prev_data != new_data:
                self._cache[address] = new_data
                if self.persist_file:
                    await self._save_to_file()
                return True
            return False

    async def _save_to_file(self):
        """파일 기반 상태 지속화"""
        async with aiofiles.open(self.persist_file, 'w') as f:
            await f.write(json.dumps(self._cache))

    @classmethod
    async def load_from_file(cls, filename: str) -> 'WalletStateTracker':
        """파일에서 상태 복구"""
        instance = cls(persist_file=filename)
        if os.path.exists(filename):
            async with aiofiles.open(filename, 'r') as f:
                contents = await f.read()
                instance._cache = json.loads(contents)
        return instance

    def track_changes(self, old: dict, new: dict) -> dict:
        """변경 필드 식별 로직 분리"""
        return {
            k: {"old": old[k], "new": new[k]}
            for k in new if old.get(k) != new.get(k)
        }


async def worker(rpc, address: str) -> dict:
    """지갑 전체 데이터 반환"""
    async with rpc.semaphore:
        return {
            "balance": await rpc.get_balance(address, return_as_hex=False),
            "stake": await rpc.get_stake(address, return_key="result.stake"),
            "bond": await rpc.get_bond(address, return_key="result.totalBonded"),
            "delegation": await rpc.get_delegation(address, return_key="result.totalDelegated"),
            "reward": await rpc.get_iscore(address, return_key="result.estimatedICX"),
            "last_updated": todaydate('ms')
        }


def deep_filter_ignored(data: Any, ignore_keys: List[str]) -> Any:
    """중첩 구조에서 특정 키 재귀적으로 제거 (검색 결과 [3] 확장)"""
    if isinstance(data, dict):
        return {
            k: deep_filter_ignored(v, ignore_keys)
            for k, v in data.items()
            if k not in ignore_keys
        }
    elif isinstance(data, list):
        return [deep_filter_ignored(item, ignore_keys) for item in data]
    return data


def format_balance_change(
        old_val: Any,
        new_val: Any,
        ignore_decimal: bool = False
) -> str:
    """
    - ignore_decimal=True 이면,
      소숫점 이하를 아예 무시(정수 변환).
    - ignore_decimal=False 이면,
      소숫점 4자리까지 반올림하되, 실질적으로 정수면 정수 형태로.
    """
    try:
        # 입력 값이 숫자인지 확인
        if not isinstance(old_val, (int, float)) or not isinstance(new_val, (int, float)):
            raise ValueError(f"Invalid input types: old_val={old_val}, new_val={new_val}")

        if ignore_decimal:
            old_val_proc = int(old_val)
            new_val_proc = int(new_val)
        else:
            old_val_proc = float(old_val)
            new_val_proc = float(new_val)

        change = new_val_proc - old_val_proc
        abs_change = abs(change)

        if old_val_proc == 0:
            pct_change = float('inf') if new_val_proc != 0 else 0.0
        else:
            pct_change = (change / old_val_proc) * 100

        if ignore_decimal:
            new_val_fmt = f"{new_val_proc:,} ICX"
            change_fmt = f"{abs_change:+,} ICX"
        else:
            new_val_rounded = round(new_val_proc, 4)
            change_rounded = round(change, 4)
            abs_change_rounded = abs(change_rounded)

            if new_val_rounded.is_integer():
                new_val_fmt = f"{int(new_val_rounded):,} ICX"  # 정수
            else:
                new_val_fmt = f"{new_val_rounded:,.4f} ICX"    # 소숫점 4자리

            if change_rounded.is_integer():
                change_fmt = f"{change_rounded:+,} ICX"
            else:
                change_fmt = f"{change_rounded:+,.5f} ICX"

        if pct_change == float('inf'):
            pct_fmt = "(new balance)"
        elif abs(pct_change) >= 1000:
            pct_fmt = f"{pct_change:+.5e}%"
        else:
            pct_fmt = f"{pct_change:+.5f}%"

        direction = "▲" if change > 0 else "▽" if change < 0 else ""
        return f"{new_val_fmt} {direction} ({change_fmt}, {pct_fmt})"

    except Exception as e:
        return f"Error formatting: {old_val}→{new_val} ({str(e)})"


def format_changes(changed_fields: dict) -> str:
    """변경 사항을 여러 줄 문자열로 포매팅"""
    lines = []
    for field, values in changed_fields.items():
        old_val = values.get('old')
        new_val = values.get('new')
        change_str = format_balance_change(old_val, new_val)
        lines.append(f"• {field}: {change_str}")
    return "\n".join(lines)


async def detect_changes(
        tracker: WalletStateTracker,
        address: str,
        current_data: dict,
        logger,
        ignore_keys: Optional[List[str]] = None,
        ignore_decimal_changes: bool = False,
        is_send_slack: bool = False,
) -> bool:
    ignore_keys = ignore_keys or []
    filtered_current = deep_filter_ignored(current_data, ignore_keys)
    prev_data = tracker.get(address)
    changed = await tracker.update(address, filtered_current)

    if not prev_data:
        logger.info(f"⨀ Initial state for {address}:\n{json.dumps(filtered_current, indent=2)}")
        return True

    filtered_prev = deep_filter_ignored(prev_data, ignore_keys)

    if filtered_prev != filtered_current:
        changed_fields = {}
        for key in set(prev_data.keys()).union(current_data.keys()):
            if key in ignore_keys:
                continue

            old_val = prev_data.get(key)
            new_val = current_data.get(key)

            # 숫자 값이 아닌 경우를 처리
            if not isinstance(old_val, (int, float)) or not isinstance(new_val, (int, float)):
                logger.warning(f"Skipping non-numeric change for {key}: old_val={old_val}, new_val={new_val}")
                continue

            if (
                    ignore_decimal_changes
                    and isinstance(old_val, (int, float))
                    and isinstance(new_val, (int, float))
            ):
                if int(old_val) == int(new_val):
                    continue

            if old_val != new_val:
                changed_fields[key] = {"old": old_val, "new": new_val}

        
        short_address =  f"💰{shorten_text(address, width=12, placeholder='..', truncate_side='middle')}"
        address_with_link = f"<https://tracker.icon.community/address/{address}|{short_address}>"
        if changed_fields:
            logger.info(f"⨀ State changed for {short_address}:\n{format_changes(changed_fields)}")
            if is_send_slack:                                
                await pconf().slack.send_async(
                    title=f"State changed for {address_with_link}",
                    message=format_changes(changed_fields),                    
                    msg_level="info",
                    status="changed",                    
                    footer="Wallet State Tracker"                    
                )

        return True
    return False


async def run_continuous_monitoring(rpc, addresses: list, tracker: WalletStateTracker, interval: int,
                                    logger, ignore_decimal_changes: bool=False, is_send_slack: bool=False):
    while True:
        tasks = [asyncio.create_task(worker(rpc, addr)) for addr in addresses]
        results = await asyncio.gather(*tasks)

        for addr, data in zip(addresses, results):
            await detect_changes(tracker, addr, data, logger,
                                 ignore_keys=['last_updated', 'unstakes'],
                                 ignore_decimal_changes=ignore_decimal_changes,
                                 is_send_slack=is_send_slack
                                 )

        await asyncio.sleep(interval)


def run_multi_wallet_monitoring(args, logger):
    settings = merge_environment_settings(args)

    async def _main():
        tracker = await WalletStateTracker.load_from_file(
            os.path.join(settings['base_dir'], "wallet_states.json")
        )

        async with AsyncIconRpcHelper(
                url=settings['endpoint_url'],
                max_concurrency=5,
                logger=logger
        ) as rpc:
            await run_continuous_monitoring(
                rpc=rpc,
                addresses=settings['address_filter'],
                tracker=tracker,
                interval=settings['check_interval'],
                logger=logger,
                ignore_decimal_changes=settings['ignore_decimal'],
                is_send_slack=settings['send_slack'],
            )
    asyncio.run(_main())


def run_wallet_client_with_websocket(args, logger):
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
                verbose=int(settings['verbose']) > 2,
                ignore_data_types=settings['ignore_data_types'],
                check_tx_result_enabled=settings['check_tx_result_enabled'],
                address_filter=settings['address_filter'],
                send_slack=settings['send_slack'],
                max_transaction_attempts=int(settings['max_transaction_attempts']),
                slack_webhook_url=settings['slack_webhook_url'],
                # logger=logger,
                session=session,
                network_info=network_info,
                max_retries=settings['max_retries'],
                bps_interval=settings['bps_interval'],
                skip_until=settings['skip_until'],
                base_dir=settings['base_dir'],

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
        {"name": "Generate docker-compose.yml for Wallet-Multi Monitoring", "value": "wallet-multi", "description": "Generate docker-compose.yml for Wallet-Multi WebSocket monitoring"},
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


# def initialize_logger(settings):
#     """Set up the logger based on the command and its log type."""
#     app_name = f"{settings.get('command')}_watcher"
#     return create_app_logger(
#         app_name=f"{settings.get('command')}_watcher",
#         log_type=settings.get('log_type'),
#         verbose=settings.get('verbose'),
#         propagate=False,
#     )


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

    if IS_DOCKER:
        pawn.console.rule("RUN IN DOCKER")

    print_var(settings)

    if settings.get('command'):
        # logger = initialize_logger(settings)
        logger = create_app_logger(
            app_name=f"{settings.get('command')}_watcher",
            log_type=settings.get('log_type'),
            verbose=settings.get('verbose'),
            propagate=False,
        )
        logger.info(f"Running command: '{settings['command']}'")

    else:
        logger = None

    local_ip_list = get_interface_ips(ignore_interfaces=['lo0', 'lo'], ip_only=True)

    if local_ip_list:
        local_ip_list = ", ".join(local_ip_list)

    
    text = f"The `{args.command.upper()}` service has been successfully launched"
    
    msg_text = {
        # "info": f"The `{args.command.upper()}` service has been successfully launched on the following IP addresses: {local_ip_list}",
        "IP addresses": local_ip_list,
    }    

    if args.command == "wallet" or args.command == "wallet-multi":
        msg_text['URL'] = settings['endpoint_url']

    pawn.set(slack=SlackNotifier())

    if settings.get('send_slack'):
        pconf().slack.send(
            title=f":rocket: {args.command.upper()} Monitoring Service Started",
            text=text,
            message=msg_text,
            status="info",
            msg_level="info",            
            footer=f"{args.command.title()}"

        )
    try:
        if args.command == "ssh":
            pawn.console.log(f"Starting SSH monitoring with files: {args.file}")
            run_monitor_ssh(args, logger)
        elif args.command == "wallet":
            pawn.console.log("Starting Async Goloop Websocket Client")
            run_wallet_client_with_websocket(args, logger)
        elif args.command == "wallet-multi":
            pawn.console.log("Starting Multiwallet monitoring")
            run_multi_wallet_monitoring(args, logger)
        elif args.command == "compose":
            pawn.console.log("Generating docker-compose.yml file")
            run_compose_init(args, logger, parser)
        else:
            parser.print_help()
    except Exception as e:
        tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        pconf().slack.send(
            title="Error Occurred",
            message=f"An error occurred: {str(e)}\n\nTraceback:\n{tb_str}",
            status="critical",
            msg_level="error",
            footer=f"{args.command.title()}"
        )
        raise e

main.__doc__ = (
    f"{__description__}\n{__epilog__}"
)


if __name__ == '__main__':
    main()




