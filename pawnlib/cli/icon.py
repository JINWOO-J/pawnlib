#!/usr/bin/env python3
import os
import sys
import asyncio

from pawnlib.config import pawn, setup_logger, setup_app_logger as _setup_app_logger, create_app_logger
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter, get_service_specific_arguments
from typing import List, Dict, Optional, Type, Any, Callable
from pawnlib.config.settings_config import SettingDefinition, load_environment_settings, BaseSettingsConfig, AppConfig
from pawnlib.utils.notify import send_slack, send_slack_async
import traceback
from dataclasses import dataclass
from pawnlib.typing import shorten_text, random_token_address,  str2bool
from pawnlib.output import print_var
from pawnlib.typing.check import is_float, is_int, sys_exit
from pawnlib.config import pawnlib_config as pawn, setup_logger, ConsoleLoggerAdapter, getPawnLogger, pconf
from pawnlib.typing.constants import const
from pawnlib.utils.http import IconRpcHelper, json_rpc, icx_signer, NetworkInfo
from pawnlib.utils.redis_helper import RedisHelper
from redis import exceptions as redis_exceptions
from pawnlib.typing.converter import hex_to_number, HexConverter
from pawnlib.models.response import HexValue, HexTintValue, HexValueParser
from rich.tree import Tree
from rich.text import Text
from rich.prompt import Confirm

from pawnlib.config.logging_config import LoggerMixin, LoggerMixinVerbose, LoggerFactory, change_propagate_setting
from pawnlib.utils.log import print_logger_configurations

IS_DOCKER = str2bool(os.environ.get("IS_DOCKER"))
ALLOWED_TASKS = ['balance', 'iscore', 'stake', 'bond', 'delegate']

kwargs = {
    "address": "hx3825a923db7174c64b7ca81fcb88dbe22e1003fb",
    "value": "0x1e94ec5124186572e"
}

__description__ = "ICON Tool"
__epilog__ = (
    "\nUsage examples:\n\n"
    "1. Interactively claim I-Score:\n"
    "     `pawns icon claim`\n\n"
    "2. Start monitoring ICON assets:\n"
    "     `pawns icon monitor --task-list balance iscore`\n\n"
    "3. Send the minimum fee to the asset wallet:\n"
    "     `pawns icon send_fee`\n\n"
    "4. Send all available assets to the safety wallet:\n"
    "     `pawns icon send_all`\n\n"
    "5. Stake all available ICX:\n"
    "     `pawns icon stake_all`\n\n"
    "6. Delegate all available ICX:\n"
    "     `pawns icon delegate_all`\n\n"
    "7. Fetch the current status of all assets:\n"
    "     `pawns icon status`\n\n"
    "8. Send assets to the safety wallet:\n"
    "     `pawns icon send_to_safety_wallet`\n\n"
    "Note:\n"
    "  Use `--help` with any command to get detailed options, e.g., `pawns icon monitor --help`.\n"
)

def get_parser():
    parser = CustomArgumentParser(
        description='Command Line Interface for ICON Maximizer',
        formatter_class=ColoredHelpFormatter,
        epilog=__epilog__,
        add_help=False
    )
    parser = get_arguments(parser)
    return parser


def add_common_arguments(parser):
    """Add common arguments to parsers."""
    parser.add_argument('--log-type', choices=['console', 'file', 'both'], default='console', help='Choose logger type: console or file (default: console)')
    parser.add_argument('--log-file', help='Log file path if using file logger (required if --log-type=file)', default=None)
    parser.add_argument('-v', '--verbose', action='count', default=1, help='Increase verbosity level. Use -v, -vv, -vvv, etc.')
    parser.add_argument('--slack-webhook-url', help='Slack webhook URL', default=None)
    parser.add_argument('--send-slack',type=str2bool,help='Enable sending messages to Slack',default=True)
    parser.add_argument('-f', '--force',action='count',help='Force mode',default=0)

    parser.add_argument('--priority', choices=['env', 'args'], default='env' if IS_DOCKER else 'args',
        help='Specify whether to prioritize environment variables ("env") or command-line arguments ("args"). Default is "args".'
    )
    parser.add_argument( '-b', '--base-dir', metavar='base_dir', help='Base directory for the application', default=".")

    parser.add_argument( '-fee', '--minimum-fee', type=float, default=0, help='')
    parser.add_argument('-mb', '--minimum-balance', type=float, default=0, help='')
    parser.add_argument('--dry-run', action='count', default=0)

    parser.add_argument('--task-list', nargs='+', help=f'Perform the following tasks: {", ".join(ALLOWED_TASKS)}', default=[])

    return parser


@dataclass
class SettingsConfig(BaseSettingsConfig):
    endpoint_url: SettingDefinition = SettingDefinition('ENDPOINT_URL', default='', value_type=str)
    ignore_data_types: SettingDefinition = SettingDefinition('IGNORE_DATA_TYPES', default=['base'], value_type=str, is_list=True)
    check_tx_result_enabled: SettingDefinition = SettingDefinition('CHECK_TX_RESULT_ENABLED', default=True, value_type=bool)
    address_filter: SettingDefinition = SettingDefinition('ADDRESS_FILTER', default=[], value_type=str, is_list=True)
    log_type: SettingDefinition = SettingDefinition('LOG_TYPE', default='console', value_type=str)
    file: SettingDefinition = SettingDefinition('FILE', default=None, value_type=str, is_list=True)
    slack_webhook_url: SettingDefinition = SettingDefinition('SLACK_WEBHOOK_URL', default=None, value_type=str)
    send_slack: SettingDefinition = SettingDefinition('SEND_SLACK', default=True, value_type=bool)
    max_transaction_attempts: SettingDefinition = SettingDefinition('MAX_TRANSACTION_ATTEMPTS', default=10, value_type=int)
    verbose: SettingDefinition = SettingDefinition('VERBOSE', default=1, value_type=int)
    network_name: SettingDefinition = SettingDefinition('NETWORK_NAME', default='', value_type=str)
    bps_interval: SettingDefinition = SettingDefinition('BPS_INTERVAL', default=0, value_type=int)
    skip_until: SettingDefinition = SettingDefinition('SKIP_UNTIL', default=0, value_type=int)
    base_dir: SettingDefinition = SettingDefinition('BASE_DIR', default='./', value_type=str)
    check_interval: SettingDefinition = SettingDefinition('CHECK_INTERVAL', default=10, value_type=int)
    ignore_decimal: SettingDefinition = SettingDefinition('IGNORE_DECIMAL', default=False, value_type=bool)

    fee_wallet_pk: SettingDefinition = SettingDefinition('FEE_WALLET_PK', default="", value_type=str)
    asset_wallet_pk: SettingDefinition = SettingDefinition('ASSET_WALLET_PK', default="", value_type=str)
    safety_wallet_address: SettingDefinition = SettingDefinition('SAFETY_WALLET_ADDRESS', default="", value_type=str)

    minimum_fee: SettingDefinition = SettingDefinition('MINIMUM_FEE', default=0.1, value_type=float)
    minimum_balance: SettingDefinition = SettingDefinition('MINIMUM_BALANCE', default=1, value_type=float)

    dry_run: SettingDefinition = SettingDefinition('DRY_RUN', default=0, value_type=int)
    force: SettingDefinition = SettingDefinition('FORCE', default=0, value_type=int)
    task_list: SettingDefinition = SettingDefinition('TASK_LIST', default=[], value_type=str, is_list=True)


def get_arguments(parser=None):
    # if not parser:
    #     parser = CustomArgumentParser()
    if not parser:
        parser = CustomArgumentParser(
            description='Command Line Interface for ICON Maximizer',
            formatter_class=ColoredHelpFormatter,
            epilog=__epilog__,
            add_help=True,
        )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    common_parser = CustomArgumentParser(add_help=False)
    add_common_arguments(common_parser)
    subparsers.add_parser("claim",  help="Interactively claim I-Score",  parents=[common_parser], add_help=True)
    subparsers.add_parser("monitor", help="Start monitoring system", parents=[common_parser], add_help=True)
    subparsers.add_parser("send_fee", help="Transferring fee available assets", parents=[common_parser], add_help=True)
    subparsers.add_parser("send_all",  help="Transferring all available assets", parents=[common_parser], add_help=True)
    subparsers.add_parser("stake_all", help="Staking all available assets", parents=[common_parser], add_help=True)
    subparsers.add_parser("delegate_all", help="Delegate all available assets", parents=[common_parser], add_help=True)
    subparsers.add_parser("status",  help="Fetch the current status of all assets including availability and performance metrics.", parents=[common_parser], add_help=True)
    subparsers.add_parser("send_to_safety_wallet", help="", parents=[common_parser], add_help=True)

    return parser


class MonitoringManager(LoggerMixinVerbose):
    initialized = False
    def __init__(self, rpc_method: Callable, name: str, pk: str, wallet, icon_rpc_helper, hook: Callable = None, params: dict = {}, logger=None, verbose=1):
        self.rpc_method = rpc_method
        self.name = name
        self.pk = pk
        self.wallet = wallet
        self.icon_rpc_helper = icon_rpc_helper
        self.hook = hook
        self.params = params
        # self.logger = ConsoleLoggerAdapter(logger, "MonitoringManager", verbose > 0)
        # self.logger = setup_logger(logger, "MonitoringManager", verbose)
        # self.logger = self.get_logger()
        self.init_logger(logger=logger, verbose=verbose)

        if not MonitoringManager.initialized:  # 클래스 변수 사용
            self.logger.info(f"Initializing monitoring system {self.logger}")
            MonitoringManager.initialized = True  # 클래스 변수 업데이트

        self.address = self.icon_rpc_helper.get_wallet_address(self.pk)
        self.previous_value = None
        self.redis_helper = RedisHelper()


    def _find_value_difference(self, old_value, new_value):
        # Case 1: If both values are dicts, compare key-by-key
        if isinstance(old_value, dict) and isinstance(new_value, dict):
            differences = {key: (old_value.get(key), new_value.get(key)) for key in new_value if old_value.get(key) != new_value.get(key)}
            return differences if differences else None

        # Case 2: If both values are lists, compare element by element
        elif isinstance(old_value, list) and isinstance(new_value, list):
            differences = [(i, (old, new)) for i, (old, new) in enumerate(zip(old_value, new_value)) if old != new]
            # Also handle if the lists have different lengths
            if len(old_value) != len(new_value):
                differences.append(('length_mismatch', (len(old_value), len(new_value))))
            return differences if differences else None

        # Case 3: For all other data types (strings, int, float, etc.)
        else:
            if old_value != new_value:
                return {'old_value': old_value, 'new_value': new_value}

        # If no differences found
        return None

    async def run_monitoring(self):
        """Run the monitoring loop to check for changes in wallet metrics."""
        while True:
            try:
                current_value = self.rpc_method(address=self.address, return_as_hex=True, **self.params)
                redis_key = f"monitoring_wallet:{self.address}:{self.name}"
                previous_value = self.redis_helper.get(redis_key, as_json=True)
                _shorten_address = shorten_text(self.address, width=15, placeholder="..", shorten_middle=True)
                HexValue.set_default_max_unit("G")
                HexValue.set_default_symbol("ICX")
                HexValue.set_default_format_type("readable_number")

                previous_value_hex = HexValueParser(previous_value)
                current_value_hex = HexValueParser(current_value)

                if isinstance(previous_value_hex, HexValue) and isinstance(current_value_hex, HexValue):
                    difference_value = current_value_hex - previous_value_hex
                else:
                    difference_value = None

                # self.logger.debug(f"[{self.name}][{_shorten_address}] {self.name:>15}: {previous_value_hex.readable_number} == {current_value_hex.readable_number}")
                self.logger.debug(f"[{self.name}][{_shorten_address}] {self.name:>15}: {previous_value_hex} == {current_value_hex}, difference: {difference_value}")
                # self.logger.debug(f"[{self.name}][{_shorten_address}] {self.name:>15}: {previous_value} == {current_value}")

                if previous_value != current_value:
                    differences = self._find_value_difference(previous_value, current_value)
                    if differences:
                        self.logger.info(f"[{self.name}][{_shorten_address}] Value changed: {differences}")
                        self.redis_helper.set(redis_key, current_value, as_json=True)
                        if self.hook:
                            await self._trigger_hooks(current_value, previous_value)
                await asyncio.sleep(5)

            except ConnectionError as e:
                self.logger.error(f"Network error during monitoring: {e}. Retrying in 10 seconds.")
                await asyncio.sleep(10)
            except ValueError as e:
                self.logger.error(f"Invalid parameter error: {e}. Check configuration.")
                await asyncio.sleep(5)
            except redis_exceptions.ConnectionError as e:
                self.logger.error(f"Redis connection error: {e}. Ensure Redis is running.")
                await asyncio.sleep(10)
            except Exception as e:
                self.logger.error(f"Unexpected error during monitoring: {e}")
                await asyncio.sleep(10)

    async def _trigger_hooks(self, current_value, previous_value):
        if isinstance(self.hook, list):
            for _hook in self.hook:
                await _hook(name=self.name, address=self.address, current_value=current_value, previous_value=previous_value)
        else:
            await self.hook(name=self.name, address=self.address, current_value=current_value, previous_value=previous_value)


class MonitoringSystem:
    def __init__(self, icon_rpc_helper: IconRpcHelper, pks: List[str], monitor_tasks: List[Callable], params: dict = {}, logger=None, verbose=0):
        self.icon_rpc_helper = icon_rpc_helper
        self.pks = pks
        self.monitor_tasks = monitor_tasks
        self.monitors = []

        for pk in self.pks:
            self.icon_rpc_helper.initialize_wallet(pk)
            wallet = self.icon_rpc_helper.get_wallet_address

            for task in self.monitor_tasks:
                self.monitors.append(MonitoringManager(
                    task.get('rpc_method'),
                    task.get('name'),
                    pk,
                    wallet,
                    self.icon_rpc_helper,
                    # hook=self.monitoring_hooks.get(method['name']),
                    hook=task.get('event_hooks'),
                    params=params,
                    logger=logger,
                    verbose=verbose
                ))

    async def run_all(self):
        sem = asyncio.Semaphore(10)
        async def bounded_monitor(monitor):
            async with sem:
                await monitor.run_monitoring()
        await asyncio.gather(*(bounded_monitor(m) for m in self.monitors))


class IconTools:
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = config.logger

        self.logger.info("Initializing Icon Tools")

        self.network_info = config.network_info

        self.fee_wallet_pk =  config.fee_wallet_pk
        self.fee_wallet =  icx_signer.load_wallet_key(self.fee_wallet_pk)

        self.asset_wallet_pk =  config.asset_wallet_pk
        self.asset_wallet =  icx_signer.load_wallet_key(self.asset_wallet_pk)

        self.asset_address =  icx_signer.load_wallet_key(self.asset_wallet_pk).get('address')
        self.safety_wallet_address =  config.safety_wallet_address

        self.minimum_fee = config.minimum_fee
        self.minimum_balance = config.minimum_balance
        self.rpc_helper = IconRpcHelper(
            network_info=self.network_info,
            wallet=self.asset_wallet_pk,
            raise_on_failure=False,
            use_hex_value=True,
            # verbose=config.verbose,
            # logger=config.logger
        )

        self.dry_run = config.dry_run

    def send_icx(self, from_wallet, to_address, icx=0.01):
        _value = hex(int(icx * const.ICX_IN_LOOP))

        icon_rpc = IconRpcHelper(
            network_info=self.network_info,
            wallet=from_wallet,
            raise_on_failure=True
        )
        balance = icon_rpc.get_balance()
        address = icon_rpc.wallet.get('address')

        if not balance:
            self.logger.info(f"{address}'s not enough balance = {balance}")
            return

        payload = json_rpc(
            method="icx_sendTransaction",
            params={
                "from": icon_rpc.wallet.get('address'),
                "to": to_address,
                "value": hex(int(icx * const.ICX_IN_LOOP))
            }
        )
        icon_rpc.sign_tx(payload=payload)
        result = icon_rpc.sign_send()
        self.logger.info(f"Transaction sent from {from_wallet} to {to_address}, result: {result}")

    def ensure_minimum_fee(self, force=False):
        balance = self.rpc_helper.get_balance()
        if balance < HexTintValue(self.config.minimum_fee) or force:
            self.logger.info(f"💸 Sending the minimum fee of {self.config.minimum_fee} ICX")
            try:
                self.send_icx(
                    from_wallet=self.config.fee_wallet_pk,
                    to_address=self.rpc_helper.get_wallet_address(),
                    icx=self.config.minimum_fee,
                )
            except Exception as e:
                self.logger.error(f"Failed to send ICX: {e}")

        else:
            self.logger.info(f"Enough Fee, balance={balance}")

    def claim_iscore_interactive(self):
        iscore = self.rpc_helper.get_iscore()
        self.logger.info(f"💰 Claimable I-Score: {iscore} ICX available for claiming.")
        if Confirm.ask("Do you want to claim the I-Score now?"):
            self.logger.info("🔄 Proceeding with the claim process...")
            result = self.rpc_helper.claim_iscore(is_wait=True)
            self.logger.info(result)
            balance = self.rpc_helper.get_balance()
            if Confirm.ask(f"Do you want to send to '{self.config.safety_wallet_address}' with {balance} ICX"):
                self.rpc_helper.send_all_icx(to_address=self.config.safety_wallet_address, min_balance=0)

    def send_fee_and_send_assets(self):
        self.ensure_minimum_fee()
        asset_iscore = self.rpc_helper.get_iscore()
        self.logger.info(f"💸 Claim the {asset_iscore} ICX")
        self.rpc_helper.claim_iscore(is_wait=True)
        self.logger.info(f"🚨 Transferring all available assets ({self.minimum_fee} ICX) from the asset address `{self.asset_address}` "
                         f"to the safety wallet: `{self.config.safety_wallet_address}`, left_balance={self.config.minimum_balance}")
        self.rpc_helper.send_all_icx(self.config.safety_wallet_address, self.config.minimum_balance)

    def send_fee_and_stake_all(self):
        self.ensure_minimum_fee()
        self.rpc_helper.stake_all_icx(min_balance=self.minimum_balance, margin_steps=300, dry_run=self.dry_run)

    def send_fee_and_delegate_all(self):
        self.ensure_minimum_fee()
        self.rpc_helper.delegate_all_icx()

    def fetch_status(self):
        pawn.console.rule("fetch status")
        self.display_balance_info(wallet_name="ASSET_WALLET",  address=self.asset_wallet.get('address'))
        self.display_balance_info(wallet_name="FEE_WALLET", address=self.fee_wallet.get('address'))
        self.display_balance_info(wallet_name="SAFETY_WALLET", address=self.safety_wallet_address)

    def display_balance_info(self, wallet_name="",  address=""):
        # rpc_helper = IconRpcHelper(network_info=self.network_info, wallet=private_key, raise_on_failure=False, use_hex_value=True)
        rpc_helper = self.rpc_helper

        balance_icx = rpc_helper.get_balance(address=address)
        if address:
            wallet_address = address
        else:
            wallet_address = rpc_helper.get_wallet_address()

        print("\n")
        staked = rpc_helper.get_stake(address=address)
        bond_info = rpc_helper.get_bond(address=address, return_key="result")

        total_bond = bond_info.get('totalBonded')
        bond_voting_power = bond_info.get('votingPower')
        unbonds = bond_info.get('unbonds')

        delegation_info = rpc_helper.get_delegation(address=address, return_key="result")
        total_delegated = delegation_info.get('totalDelegated')
        voting_power = delegation_info.get('votingPower')

        available_voting = staked - (total_delegated + total_bond)
        iscore = rpc_helper.get_iscore(address=address)

        root = Tree(Text(f"{wallet_name} Wallet ({wallet_address})", style="bold cyan"))
        root.add(f"[bold yellow]Balance:[/bold yellow] {balance_icx.output()}")

        # Stake Information
        root.add(f"[bold yellow]Staked:[/bold yellow] {staked.output()}")
        root.add(f"[bold yellow]I-Score:[/bold yellow] {iscore.output()}")
        root.add(f"[bold yellow]Available Voting:[/bold yellow] {available_voting.output()}")

        delegations_section = root.add("[bold yellow]Delegations[/bold yellow]")
        delegations_section.add(f"Total Delegated: {total_delegated.output()}")
        delegations_section.add(f"Voting Power: {voting_power.output()}")

        for index, delegation in enumerate(delegation_info.get('delegations')):
            delegation_address = delegation.get('address')
            delegation_value_icx = delegation.get('value')
            delegations_section.add(f"[{index}] Address: {delegation_address}")
            delegations_section.add(f"[{index}] Value: {delegation_value_icx.output()}")

        # Bonds Section
        bonds_section = root.add("[bold yellow]Bonds[/bold yellow]")
        bonds_section.add(f"[bold yellow]Total:[/bold yellow] {total_bond.output()}")
        bonds_section.add(f"[bold yellow]voting_power:[/bold yellow] {bond_voting_power.output()}")
        bonds_section.add(f"[bold yellow]unbonds:[/bold yellow] {unbonds}")

        bond_list = bond_info.get('bonds')
        for index, bond in enumerate(bond_list):
            bond_address = bond.get('address')
            bond_value_icx = bond.get('value').output()
            bonds_section.add(f"[{index}] Address: {bond_address}")
            bonds_section.add(f"[{index}] Value: {bond_value_icx}")
        pawn.console.print(root)

    def start_monitoring(self):

        network_info = self.config.network_info
        asset_wallet_pk = self.config.asset_wallet_pk
        fee_wallet_pk = self.config.fee_wallet_pk
        safety_wallet_address =  self.config.safety_wallet_address

        icon_rpc_helper = IconRpcHelper(network_info=network_info, wallet=self.asset_wallet, raise_on_failure=False)
        pks = [asset_wallet_pk]
        monitor_tasks = [
            { 'name': 'balance', 'rpc_method': icon_rpc_helper.get_balance, 'event_hooks': [self.print_changed_hook, self.slack_notification]},
            { 'name': 'iscore', 'rpc_method': icon_rpc_helper.get_iscore, 'event_hooks': [self.claim_iscore_and_send_to_safety_wallet, self.slack_notification]},
            { 'name': 'stake', 'rpc_method': icon_rpc_helper.get_stake, 'event_hooks': [self.print_changed_hook, self.slack_notification]},
            { 'name': 'bond', 'rpc_method': icon_rpc_helper.get_bond, 'event_hooks': [self.print_changed_hook, self.slack_notification]},
            { 'name': 'delegate', 'rpc_method': icon_rpc_helper.get_delegation, 'event_hooks': [self.print_changed_hook, self.slack_notification]},


            # {'rpc_method': icon_rpc_helper.get_stake, 'name': 'stake'},
            # {'rpc_method': icon_rpc_helper.get_bond, 'name': 'bond'},
            # {'rpc_method': icon_rpc_helper.get_delegation, 'name': 'delegation'}
        ]

        if hasattr(self.config, 'task_list'):
            task_names = self.config.task_list

            if not all(task in ALLOWED_TASKS for task in task_names):
                self.logger.error(f"Invalid task name: {task_names}, allowed tasks: {ALLOWED_TASKS}")
                sys_exit(f"Invalid task name: {task_names}, allowed tasks: {ALLOWED_TASKS}")

            monitor_tasks = [task for task in monitor_tasks if task['name'] in task_names]

        task_names = ", ".join(task.get('name') for task in monitor_tasks)
        self.logger.info(f"Starting monitoring for tasks: {task_names}")


        monitoring_system = MonitoringSystem(
            icon_rpc_helper=icon_rpc_helper, pks=pks, monitor_tasks=monitor_tasks, logger=self.logger, verbose=self.config.verbose,
        )
        # Run all monitors
        asyncio.run(monitoring_system.run_all())

    async def claim_iscore_and_send_to_safety_wallet(self, **kwargs):
        name = kwargs.get('name')
        address = kwargs.get('address')
        current_value = kwargs.get('current_value')
        previous_value = kwargs.get('previous_value')

        if current_value == "0x0":
            return

        self.logger.info(f"Changed I-SCore:  {name}, {address}, {hex_to_number(current_value, debug=True, is_tint=True)}")
        self.ensure_minimum_fee()
        self.rpc_helper.claim_iscore(is_wait=True)
        self.logger.info(f"🚨 Transferring all available assets ({self.minimum_fee} ICX) from the validator `{self.asset_address}` "
                         f"to the safety wallet: `{self.safety_wallet_address}` minimum_balance={self.minimum_balance}")
        self.send_to_safety_wallet(current_value)

    def send_to_safety_wallet(self, result=None, dry_run=False):
        if self.safety_wallet_address:
            self.rpc_helper.send_all_icx(to_address=self.safety_wallet_address, min_balance=self.minimum_balance, dry_run=self.dry_run)
        else:
            self.logger.info(f"SAFETY_WALLET_ADDRESS is not defined. Keep  the {hex_to_number(result, debug=True, is_tint=True)} ICX")

    async def slack_notification(self, **kwargs):
        self.logger.info(f"✨✨✨✨ Slack notification: [{kwargs.get('name')}] Address: {kwargs.get('address')}, Result: {kwargs.get('current_value')  }")

        try:
            await send_slack(
                title=f"Changed {kwargs.get('name')},  Address: {kwargs.get('address')}",
                msg_text=HexConverter(kwargs, convert_type="tint", suffix=" ICX", decimal_places=2).data,
                msg_level="info",
                async_mode=True,
                footer="ICON Tracker"
            )
        except Exception as e:
            self.logger.error(f"Error sending slack notification: {e}")

    async def changed_balance(self, name, address, result):
        print(f"Changed Balanced {name}, {address}, {result}")

    async def print_changed_hook(self, **kwargs ):
        self.logger.info(f"✨✨✨✨ Changed Hook: {kwargs.get('name')}, {kwargs.get('address')}, {kwargs.get('current_value')}, {kwargs.get('previous_value')}")


def main():
    banner = generate_banner(
        app_name="ICON Tools",
        author="jinwoo",
        description="ICON utils",
        font="graffiti",
        version=_version
    )

    pawn.set(PAWN_LINE=False)

    parser = get_parser()
    args, unknown = parser.parse_known_args()
    print(banner)

    args_index = 2 if len(sys.argv) > 1 and sys.argv[1] == 'icon' else 1

    if len(sys.argv) <= args_index:
        parser.print_help()
        sys_exit("No command specified", 0)

    args = parser.parse_args(sys.argv[args_index:])
    pawn.console.log(f"args = {args}")

    settings = load_environment_settings(args, SettingsConfig)
    network_info = NetworkInfo(network_name="custom-network", network_api=settings.get('endpoint_url'))
    logger = create_app_logger(
        log_type=settings.get('log_type'),  app_name="icon_tools",
        propagate=False, verbose=settings.get('verbose')
    )

    # change_propagate_setting(propagate=True, log_level=5, pawnlib_level=5)
    if settings.get('verbose') > 2:
        LoggerFactory.set_global_log_level(verbose=settings.get('verbose'))

    config = AppConfig(network_info=network_info, logger=logger, **settings)

    logger.info("start")
    print_var(config)
    logger.info(f"endpoint={network_info.endpoint}, nid={network_info.nid}")

    icon_tools = IconTools(config)
    commands = {
        "claim": icon_tools.claim_iscore_interactive,
        "send_fee": lambda : icon_tools.ensure_minimum_fee(config.force > 0),
        "send_all": icon_tools.send_fee_and_send_assets,
        "stake_all": icon_tools.send_fee_and_stake_all,
        "delegate_all": icon_tools.send_fee_and_delegate_all,

        "monitor": icon_tools. start_monitoring,
        "status": icon_tools.fetch_status,
        "send_to_safety_wallet": icon_tools.send_to_safety_wallet,
    }

    try:
        if args.command in commands:
            commands[args.command]()
        else:
            logger.info(f"{args.command} not found")
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


if __name__ == '__main__':
    main()
