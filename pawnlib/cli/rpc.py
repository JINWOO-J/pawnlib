#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.output.color_print import *
from pawnlib.output import write_yaml, is_file, open_yaml_file, print_json
from pawnlib.config import pawnlib_config as pawn, pconf
from pawnlib.typing import sys_exit, is_valid_url, json_rpc, is_json, get_value_size, get_size
from pawnlib.utils import IconRpcHelper, IconRpcTemplates, NetworkInfo, icx_signer, CallHttp

from InquirerPy import prompt
from pawnlib.utils import disable_ssl_warnings
from pawnlib.input import PromptWithArgument, PrivateKeyValidator, StringCompareValidator, PrivateKeyOrJsonValidator

disable_ssl_warnings()

NONE_STRING = "__NOT_DEFINED_VALUE__"
__description__ = "This tool uses JSON remote procedure calls, or RPCs, commonly used on the ICON blockchain."

__epilog__ = (
    "This utility offers a comprehensive suite for interacting with the ICON blockchain, leveraging JSON-RPC for efficient communication.\n\n"
    "Usage examples:\n"
    "  1. Query network information:\n\n"
    "     - Fetches block information by height.\n\n"
    "     `pawns rpc --url <RPC_ENDPOINT> --method icx_getBlockByHeight --params '{\"height\":\"0x1\"}'`\n"

    "  2. Send ICX transaction:\n\n"
    "     - Sends an ICX transaction to the network.\n\n"
    "     `pawns rpc --url <RPC_ENDPOINT> --method icx_sendTransaction --params <TRANSACTION_PARAMETERS>`\n"

    "  3. Configure network settings:\n\n"
    "     - Sets the network configuration for subsequent operations.\n\n"
    "     `pawns rpc --platform icon --network mainnet`\n"
    
    "  4. Configure custom network settings:\n\n"
    "      -  If you want to edit network information, create config.yaml with a parameter called config and then change it.\n\n"
    "     `pawns rpc config` \n\n"
    "For detailed command usage and options, refer to the help documentation by running 'pawns rpc --help'."
)


PLATFORM_LIST = ["icon", "havah"]


def get_parser():
    parser = argparse.ArgumentParser(description='RPC')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument(
        'command',
        help='Edit network information by creating a config.yaml file.',
        nargs='?',
        choices=["config", ""]
    )
    parser.add_argument('--url', metavar='url', help='endpoint url default: None', default=None)
    parser.add_argument('--from', metavar='address', dest='from', help='from address. default: None', default=None)
    parser.add_argument('--to', metavar='address', dest="to", help='to address. default: None', default=None)
    parser.add_argument('--address', metavar='address', help=f'icx address. default: None', default=None)
    parser.add_argument('--txhash', metavar='txhash', help='txhash')
    parser.add_argument('--value', metavar='amount', type=float, help=f'icx amount to transfer. unit: icx. ex) 1.0. default:0.001',
                        default=0.001)
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
    parser.add_argument('--params', metavar='params',  help='params for JSON-RPC', default={})
    parser.add_argument('-x', '--http-method', metavar='method', help='method for HTTP', default="post")
    parser.add_argument('--platform', type=lambda s : s.lower(), metavar='platform', help='platform name of network name',
                        # choices=PLATFORM_LIST,
                        # default="havah"
                        )
    parser.add_argument('--src',  metavar='source', help='Source path of SCORE', default="")
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
            if not payload['params'].get(args_key):
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
        self.is_supported_platform = False

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
        self.args = pconf().data.args

    def load_network_config(self):
        self.load_config_file()
        self.network_info = NetworkInfo(force=True)
        self.network_info.update_platform_info(self.config_data)

    def load_config_file(self):
        if is_file(self.config_file):
            self.config_data = open_yaml_file(self.config_file)

            pawn.console.log(f"Loaded configuration from '{self.config_file}' len={get_value_size(self.config_data)}, size={get_size(self.config_file)}")
            pawn.console.debug(self.config_data)

    def set_network_info(self):
        pawn.console.log(self.network_info)

        platform_list = self.network_info.get_platform_list() + ["etc"]
        PromptWithArgument(
            message="Select Platform ?",
            choices=platform_list,
            type="list",
            argument="platform",
        ).prompt()

        network_list = self.network_info.get_network_list(platform=self.args.platform)
        if network_list:
            PromptWithArgument(
                message="Select Network ?",
                choices=network_list,
                type="list",
                argument="network",
                default="vega"
            ).prompt()
            self.network_info.set_network(platform=self.args.platform, network_name=self.args.network)
            self.is_supported_platform = True
        pawn.console.log(self.network_info)

    def generate_tx_payload(self):
        self.icon_rpc = IconRpcHelper(network_info=self.network_info)
        pawn.console.log("Fetching Governance SCORE API")
        _governance_score_api = self.icon_rpc.get_governance_api()
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

        if self.icon_tpl.get_params_hint():
            pawn.console.log(f"Type Hints for '{self.args.method}'")
            print_json(self.icon_tpl.get_params_hint())

        required_params = self.icon_tpl.get_required_params()

        if required_params and self.args.fill_each_prompt:
            _questions = []
            for k, v in required_params.items():
                _questions.append({'type': 'input', 'name': k.lower(), 'message': f'What\'s "{k}" parameter?'})
                # from 주소면 wallet 디렉토리를 읽어서 리스트를 보여준다.
            self._payload['params'] = prompt(_questions)

        self.load_wallet_and_prepare_for_sign()

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

    def load_wallet_and_prepare_for_sign(self):
        if self.icon_tpl.is_required_sign() or self._payload.get('method') == "icx_sendTransaction":
            self.icon_rpc.wallet = icx_signer.WalletCli().load()
            self._payload['params']['from'] = self.icon_rpc.wallet.get('address')
            self.print_balance()
            self.prepare_signature()

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

    def call_raw_rpc(self):
        try:

            valid_url = is_valid_url(self.args.url)
            pawn.console.log(f"{self.args.url}, is_valid_url => {valid_url}")

            # if not valid_url:
            #     sys_exit(f"Required valid url -> {self.args.url}")

            if not isinstance(self.args.params, (str, dict)) or not is_json(self.args.params) and not isinstance(self.args.params, dict):
                sys_exit(f"Invalid params -> {self.args.params}")

            if not self._payload:
                json_params = json.loads(self.args.params) if is_json(self.args.params) else self.args.params
                self._payload = json_rpc(method=self.args.method, params=json_params)

            call_http = CallHttp(
                url=self.args.url,
                method=self.args.http_method,
                payload=self._payload,
                headers={"Content-Type": "application/json"}
            )
            res = call_http.run()
            pawn.console.log(call_http.response, f"payload={json.dumps(self._payload)}")
            dump(res.response.json, hex_to_int=True)
        except Exception as e:
            pawn.console.log(f"An error occurred: {e}")
            sys_exit(f"An error occurred: {e}")

    def deploy_score(self):
        pawn.console.log(self.args)
        self.icon_rpc = IconRpcHelper(network_info=self.network_info)

        if not is_json(self.args.params):
            sys_exit(f"Required invalid params-> {self.args.params}")

        if not self.args.src:
            sys_exit(f"Required Source path of SCORE -> {self.args.src}")

        self.args.params = json.loads(self.args.params)

        _params = PromptWithArgument(
            type="input",
            message="Edit Params: ",
            default="\n"+json.dumps(self.args.params, indent=4),
            long_instruction="\nedit the transaction",
        ).prompt()

        if self.args.to:
            pawn.console.log(f"Update to '{self.args.to}'")

        self._payload = self.icon_rpc.create_deploy_payload(
            # src="examples/icon_rpc_test/SCORE/hello-world/build/libs/hello-world-0.1.0-optimized.jar",
            src=self.args.src,
            params=json.loads(_params),
            governance_address=self.args.to
        )
        self.load_wallet_and_prepare_for_sign()
        del self.icon_rpc.request_payload['params']['value']
        pawn.console.rule("2. Calculate Fee")
        pawn.console.log(f"Fee = {self.icon_rpc.get_fee( symbol=True)}")

        pawn.console.rule("3. Sign the Transaction")
        signed_payload = self.icon_rpc.sign_tx(payload=self._payload)
        print_json(signed_payload)

        pawn.console.rule("4. Send the Transaction")
        self.icon_rpc.rpc_call(payload=signed_payload)
        self.icon_rpc.print_response()

        pawn.console.rule("5. Wait the Transaction")
        self.icon_rpc.get_tx_wait()
        self.icon_rpc.print_response()

    def create_json_rpc_request_from_dot_command(self):

        # pawn.console.log(self.icon_tpl.get_methods())
        # exit()
        parts = self.args.method.split('.')

        if len(parts) > 2:
            method = parts[0]
            param_type = parts[1]
            param_value = parts[2]
            pawn.console.log(parts, method, param_type, param_value)
            self._payload = json_rpc(method=method, params={param_type: param_value})
            pawn.console.debug(f"auto payload={self._payload}")

    def run(self):
        self.initialize_arguments()
        if self.args.command == "config":
            self.write_config_file()
            return

        self.load_network_config()

        if not self.args.url:
            self.set_network_info()

        if self.is_supported_platform:
            if self.args.method == "deploy":
                pawn.console.log("Deploy SCORE")
                self.deploy_score()
            else:
                self.generate_tx_payload()
        else:
            pawn.console.log(f"Unsupported platform={self.args.platform}, network_name={self.args.network}")
            self.create_json_rpc_request_from_dot_command()
            self.call_raw_rpc()


def main():
    cli = RpcCommand()
    cli.run()

main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)


if __name__ == '__main__':
    print("*"* 100)
    main()
