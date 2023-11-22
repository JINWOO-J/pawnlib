#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.output.color_print import *
from pawnlib.output import write_yaml, is_file, open_yaml_file
from pawnlib.config import pawnlib_config as pawn, pconf
from pawnlib.utils import IconRpcHelper, IconRpcTemplates, NetworkInfo, icx_signer

from InquirerPy import prompt
from pawnlib.utils import disable_ssl_warnings
from pawnlib.input import PromptWithArgument, PrivateKeyValidator, StringCompareValidator, PrivateKeyOrJsonValidator

disable_ssl_warnings()
NONE_STRING = "__NOT_DEFINED_VALUE__"
PLATFORM_LIST = ["icon", "havah"]


def get_parser():
    parser = argparse.ArgumentParser(description='RPC')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument(
        'command',
        help='account, icx_sendTransaction, icx_sendTransaction_v3, get_transactionResult, icx_getBalance, icx_getTotalSupply',
        nargs='?'
    )
    parser.add_argument('--url', metavar='url', help='endpoint url default: None', default=None)
    parser.add_argument('--from', metavar='address', dest='from', help='from address. default: None', default=None)
    parser.add_argument('--to', metavar='address', dest="to", help='to address. default: None', default=None)
    parser.add_argument('--address', metavar='address', help=f'icx address. default: None', default=None)
    parser.add_argument('--txhash', metavar='txhash', help='txhash')
    parser.add_argument('--value', metavar='amount', type=float, help=f'icx amount to transfer. unit: icx. ex) 1.0. default:0.001',
                        default=0.001)
    parser.add_argument('--fee', metavar='amount', type=float,
                        help='transfer fee. default: 0.01', default=0.001)
    parser.add_argument('--pk', metavar='private_key',
                        help=f'hexa string. default: None', default=None)
    parser.add_argument('--debug', action='store_true', help=f'debug mode. True/False')
    parser.add_argument('-n', '--number', metavar='number', type=int, help=f'try number. default: None', default=None)

    parser.add_argument('--nid', metavar='nid', type=str, help=f'network id default: None', default=None)

    parser.add_argument('-c', '--config', metavar='config', help='config name')

    parser.add_argument('-k', '--keystore', metavar='keystore', help='keystore file name')
    parser.add_argument('-p', '--password', metavar='password', help='keystore file password')

    parser.add_argument('-t', '--timeout', metavar='timeout', type=float, help=f'timeout')
    parser.add_argument('-w', '--worker', metavar='worker', type=int, help=f'worker')

    # parser.add_argument('-i', '--increase', metavar='increase_count', type=int, help=f'increase count number')
    # parser.add_argument('--increase-count', metavar='increase_count', type=int, help=f'increase count number', default=1)
    # parser.add_argument('-r', '--rnd_icx', metavar='rnd_icx', help=f'rnd_icx', default="no")

    parser.add_argument('-m', '--method', metavar='method', help='method for JSON-RPC', default="")
    parser.add_argument('--platform', type=lambda s : s.lower(), metavar='platform', help='platform name of network name',
                        # choices=PLATFORM_LIST,
                        # default="havah"
                        )

    parser.add_argument('--network', metavar='network_name', help='network name', default="")
    parser.add_argument('--fill-each-prompt',  action='store_true', help='fill each prompt', default=False)
    parser.add_argument('--base-dir', metavar='base_dir', help='base directory', default=os.getcwd())
    # parser.add_argument('--load-type', metavar='network_name', help='network name', default="")

    return parser


def get_methods(answers):
    icon_tpl = IconRpcTemplates()
    return icon_tpl.get_methods(answers['category'])


def get_required(answers):
    icon_tpl = IconRpcTemplates(category=answers['category'], method=answers['method'])
    pawn.console.log(f"get_required => {icon_tpl.get_required_params()}, {answers['category']}, {answers['method']}")

    return icon_tpl.get_required_params()


def fetch_environments_to_args():
    args = pconf().data.args
    env_map = {
        "PLATFORM": "platform",
        "SERVICE": "network",
    }
    for env_key, args_key in env_map.items():
        env_value = os.getenv(env_key, NONE_STRING)
        if env_value != NONE_STRING and \
                getattr(args, args_key, NONE_STRING) != NONE_STRING:
            pawn.console.log(f"[yellow]Defined from environment variable, {env_key}={env_value}, (args.{args_key})")
            setattr(args, args_key, env_value)


def print_banner():
    banner = generate_banner(
        app_name="RPC",
        author=f"jinwoo \n\n - Platform    : {str(pconf().data.args.platform).upper()}",
        description="JSON-RPC request",
        font="graffiti",
        version=_version
    )
    print(banner)


# def initialize_arguments():
#     parser = get_parser()
#     args, unknown = parser.parse_known_args()
#     args.subparser_name = "rpc"
#     pawn.set(
#         PAWN_DEBUG=args.debug,
#         data=dict(
#             args=args
#         )
#     )
#     print_banner()
#     fetch_environments_to_args()
#     pawn.console.log(args)
#
#
#     if args.platform not in PLATFORM_LIST:
#         raise ValueError(f'not supported platform, allowed = {PLATFORM_LIST}')
#
#     return args


def fill_sign_params_from_args(payload: dict):
    args = pconf().data.args
    args_list = ["to", "stepLimit", "nid", "value", "nonce"]

    payload.setdefault('params', {})

    for args_key in args_list:
        value = getattr(args, args_key, None)
        if value is not None:
            if args_key == "value":
                value = hex(int(value * 10 ** 18))
            pawn.console.debug(f"[yellow]Defined from parameters variable, {args_key}={value}, (args.{args_key})")
            payload['params'][args_key] = value
    return payload


def network_info_to_args(network_info):
    print(network_info)


class RpcCommand:
    def __init__(self):
        self.args = None
        self.network_info = None
        self.icon_tpl = IconRpcTemplates()
        self._payload = {}
        self.icon_rpc = None

        self.config_file = "config.yaml"
        self.config_data = {}

    def initialize_arguments(self):
        parser = get_parser()
        args, unknown = parser.parse_known_args()
        args.subparser_name = "rpc"
        pawn.set(
            PAWN_DEBUG=args.debug,
            data=dict(
                args=args
            )
        )
        print_banner()
        fetch_environments_to_args()
        pawn.console.log(args)
        self.load_config_file()
        self.args = pconf().data.args

        self.network_info = NetworkInfo(force=True)
        self.network_info.update_platform_info(self.config_data)

    def set_network_info(self):
        PromptWithArgument(
            message="Select Platform ?",
            choices=self.network_info.get_platform_list(),
            type="list",
            argument="platform",
        ).prompt()

        PromptWithArgument(
            message="Select Network ?",
            choices=self.network_info.get_network_list(platform=self.args.platform),
            type="list",
            argument="network",
            default="vega"
        ).prompt()

        self.network_info.set_network(platform=self.args.platform, network_name=self.args.network)
        pawn.console.log(self.network_info)

    def generate_tx_payload(self):
        self.icon_rpc = IconRpcHelper(network_info=self.network_info)
        pawn.console.log("Fetching Governance SCORE API")
        _governance_score_api  = self.icon_rpc.get_governance_api()
        self.icon_tpl.update_template(_governance_score_api)

        category = None
        if not self.args.method:
            category = PromptWithArgument(
                message="Select a category to use in JSON-RPC.",
                choices=self.icon_tpl.get_category(),
                long_instruction="\nUse the up/down keys to select",
                max_height="40%",
                default="",
                argument="",
                # args=pconf().data.args
            ).select()

        PromptWithArgument(
            message=">> Select a method to use in JSON-RPC.",
            choices=self.icon_tpl.get_methods(category=category),
            long_instruction="\nUse the up/down keys to select",
            type="list",
            max_height="40%",
            default="",
            argument="method",
            # args=pconf().data.args
        ).fuzzy()

        self._payload = self.icon_tpl.get_rpc(category=category, method=self.args.method)
        required_params = self.icon_tpl.get_required_params()

        if required_params and self.args.fill_each_prompt:
            _questions = []
            for k, v in required_params.items():
                _questions.append({'type': 'input', 'name': k.lower(), 'message': f'What\'s "{k}" parameter?'})
                # from 주소면 wallet 디렉토리를 읽어서 리스트를 보여준다.
            self._payload['params'] = prompt(_questions)

        if self.icon_tpl.is_required_sign() or self._payload.get('method') == "icx_sendTransaction":
            self.icon_rpc.wallet = icx_signer.WalletCli().load()
            self._payload['params']['from'] = self.icon_rpc.wallet.get('address')
            self.print_balance()
            self.prepare_signature()

        self._payload = PromptWithArgument(
            type="input",
            message="Edit transaction: ",
            default="\n"+json.dumps(self._payload, indent=4),
            long_instruction="\nedit the transaction",
        ).prompt()

        if self.icon_tpl.is_required_sign():
            self._payload = self.icon_rpc.sign_tx(payload=self._payload)
        self.icon_rpc.rpc_call(url=self.args.url, payload=self._payload)
        self.icon_rpc.print_request()
        self.icon_rpc.print_response(hex_to_int=True)

        if self.icon_tpl.is_required_sign():
            self.icon_rpc.get_tx_wait()

    def print_balance(self):
        address = self.icon_rpc.wallet.get('address')
        balance = self.icon_rpc.get_balance(address=address)
        pawn.console.log(f"address={address}, balance={balance} {self.network_info.symbol}")

    def prepare_signature(self):
        self._payload = fill_sign_params_from_args(self._payload)

        if self.network_info.nid:
            self._payload['params']['nid'] = self.network_info.nid

    def write_config_file(self):

        from pawnlib.output.file import check_file_overwrite
        if check_file_overwrite(filename=self.config_file):
            pawn.console.log("Write configuration config.yaml")
            network_info = NetworkInfo(force=True).get_platform_info()
            write_yaml(self.config_file, data=network_info)

    def load_config_file(self):
        if is_file(self.config_file):
            self.config_data = open_yaml_file(self.config_file)
            pawn.console.log(f"Loaded configuration from '{self.config_file}' len={len(self.config_data)}")
            pawn.console.log(self.config_data)

    def run(self):
        self.initialize_arguments()
        if self.args.command == "config":
            self.write_config_file()
            return

        self.set_network_info()
        self.generate_tx_payload()


def main():
    cli = RpcCommand()
    cli.run()


if __name__ == '__main__':
    print("*"* 100)
    main()
