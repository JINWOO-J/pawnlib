import re
import json
import sys
from pawnlib.config.globalconfig import pawnlib_config as pawn, global_verbose, pconf, SimpleNamespace
from pawnlib import output
from pawnlib.resource import net
from pawnlib.typing.converter import append_suffix, append_prefix, hex_to_number, FlatDict, FlatterDict, flatten, const
from pawnlib.typing.constants import const
from pawnlib.typing.generator import json_rpc, random_token_address
from pawnlib.typing import check, converter, list_depth

try:
    from pawnlib.utils import icx_signer
except ImportError:
    pass

from typing import Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from enum import Enum, auto
import copy
import operator as _operator
import time

from dataclasses import dataclass, InitVar, field

import requests

ALLOWS_HTTP_METHOD = ["get", "post", "patch", "delete"]
ALLOW_OPERATOR = ["!=", "==", ">=", "<=", ">", "<", "include", "exclude"]


class _ResponseWithElapsed(requests.models.Response):
    success = False

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return f"<Response [{self.status_code}], {self.elapsed}ms, succ={self.success}>"

    def __str__(self):
        return f"<Response [{self.status_code}], {self.elapsed}ms, succ={self.success}>"

    def as_dict(self):

        if not self.__dict__.get('result'):
            try:
                self.__dict__['result'] = self.__dict__['_content'].decode('utf-8')
            except:
                pass

        if self.__dict__.get('result') and isinstance(self.__dict__.get('result'), dict):
            self.__dict__['json'] = self.__dict__['result']
            self.__dict__['text'] = json.dumps(self.__dict__['result'])

        else:
            try:
                self.__dict__['json'] = json.loads(self.__dict__['result'])
            except:
                self.__dict__['json'] = {}
        return self.__dict__


requests.models.Response.__str__ = _ResponseWithElapsed.__str__
requests.models.Response.__repr__ = _ResponseWithElapsed.__repr__
requests.models.Response.as_dict = _ResponseWithElapsed.as_dict


class HttpResponse:
    def __init__(self, status_code=999, response=None, error=None, elapsed=None, success=False):
        self.status_code = status_code
        self.response = response
        self.error = error
        self.elapsed = elapsed
        self.success = success
        if self.response and self.response.json:
            self.json = self.response.json
        else:
            self.json = {}

        if self.error:
            self.ok = False
        else:
            self.ok = True

    def __str__(self):
        return f"<HttpResponse> status_code={self.status_code}, response={self.response}, error={self.error}"

    def __repr__(self):
        return f"<HttpResponse> {self.status_code}, {self.response}, {self.error}"

    def as_dict(self):
        return self.__dict__


class StrEnum(str, Enum):
    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class AllowsHttpMethod(StrEnum):
    get = auto()
    post = auto()
    patch = auto()
    delete = auto()


class AllowsKey(StrEnum):
    status_code = auto()
    headers = auto()
    raw = auto()
    url = auto()
    reason = auto()
    http_version = auto()
    r_headers = auto()
    result = auto()
    elapsed = auto()


@dataclass
class NetworkInfo:
    network_name: InitVar[str] = "mainnet"
    platform: InitVar[str] = "icon"
    force: InitVar[bool] = False
    network_api: str = ""
    planet_api: str = ""
    nid: str = ""
    network: str = ""
    endpoint: str = ""
    symbol: str = ""
    valid_network: bool = False

    def __post_init__(self, network_name="", platform="icon", force=False):

        self._platform_info = {
            "icon": {
                "symbol": "ICX",
                "network_info": {
                    "mainnet": {
                        "network_api": "https://ctz.solidwallet.io",
                        "nid": "0x1"
                    },
                    "lisbon": {
                        "network_api": "https://lisbon.net.solidwallet.io",
                        "nid": "0x2"
                    },
                    "cdnet": {
                        "network_api": "http://20.20.1.122:9000",
                        "nid": "0x53"
                    },
                }
            },
            "havah": {
                "symbol": "HVH",
                "network_info": {
                    "mainnet": {
                        "planet_api": "https://planet.havah.io",
                        "network_api": "https://ctz.havah.io",
                        "nid": "0x100"  # 256
                    },
                    "vega": {
                        "planet_api": "https://planet.vega.havah.io",
                        "network_api": "https://ctz.vega.havah.io",
                        "nid": "0x101"  # 257
                    },
                    "deneb": {
                        "planet_api": "https://planet.dev.havah.io",
                        "network_api": "https://ctz.dev.havah.io",
                        "nid": "0x110"  # 272
                    },
                    "svm_havah": {
                        "network_api": "http://20.20.1.153:9900",
                        "nid": "0x8361",
                    },
                }
            }
        }
        self.network_name = network_name
        self.platform = platform
        self.network_info = {}
        self.static_values = ["nid", "network_api", "endpoint"]
        if not force:
            self._initialize()

    def is_set_static_values(self):
        for static_value in self.static_values:
            if getattr(self, static_value, None):
                return True

    def _get_network_info(self, network_name="", platform=""):
        if network_name:
            self.network_name = network_name
        if platform:
            self.platform = platform

        self.network_name = self.network_name.lower()
        self.platform = self.platform.lower()

        if not self._platform_info.get(self.platform):
            raise ValueError(f"Allowed platform - values {list(self._platform_info.keys())}")

        if not self.is_set_static_values():
            _network_info = self._platform_info[self.platform].get('network_info')
            if isinstance(_network_info, dict) and not _network_info.get(self.network_name):
                raise ValueError(f"Allowed network_name in '{self.platform}' - values {list(_network_info.keys())}")
            self.network_info = self._platform_info[self.platform]['network_info'].get(self.network_name)

        else:
            _network_info = {}

        self.symbol = self._platform_info[self.platform].get('symbol')

        if self.network_info:
            self.valid_network = True
            self.network_info['symbol'] = self.symbol
            self.network_info['network_name'] = self.network_name
            self.network_info['platform'] = self.platform

    def _initialize(self, network_name="", platform=""):
        self._get_network_info(network_name, platform)
        if self.network_info:
            this_data = self.network_info

            if this_data.get("network", None) is None:
                setattr(self, "network", self.network_name)
            for key, value in this_data.items():
                object.__setattr__(self, key, this_data.get(key))

    def set_network(self, network_name=None, platform="icon"):
        if network_name:
            self._initialize(network_name=network_name, platform=platform)

    def list(self) -> list:
        return list(self.network_info.keys())

    def get_platform_list(self) -> list:
        return list(self._platform_info.keys())

    def get_network_list(self, platform="") -> list:
        if platform:
            self.platform = platform

        if self._platform_info.get(self.platform):
            return list(self._platform_info[self.platform]['network_info'].keys())

    def tuple(self) -> tuple:
        return tuple(self.network_info.keys())

    def to_dict(self, network_name=None):
        if self.network_info:
            return self.network_info

        return self.network_info

    def _parse_network_info_string(self):
        if self.network_info and isinstance(self.network_info, dict):
            network_info_str = f"network_info={self.network_info}"
        else:
            self_dict = copy.deepcopy(self.__dict__)
            del self_dict['_platform_info']
            network_info_str = self_dict
        return network_info_str

    def __repr__(self):
        return f"<{self.platform.upper()} {self.__class__.__name__}> {self._parse_network_info_string()}"

    def __str__(self):
        return f"<{self.platform.upper()} {self.__class__.__name__}> {self._parse_network_info_string()}"


class IconRpcTemplates:
    requires_sign_method = ['icx_sendTransaction', 'icx_sendTransaction(SCORE)', 'icx_call']
    templates = {
        "main_api": {
            # "icx_getTotalSupply": json_rpc("icx_getTotalSupply"),
            "icx_getTotalSupply": {},
            "icx_getLastBlock": {},
            "icx_getBalance": {"params": {"address": ""}},
            "icx_getTransactionResult": {"params": {"txHash": ""}},
            "icx_getTransactionByHash": {"params": {"txHash": ""}},
            "icx_getBlockByHeight": {"params": {"height": ""}},
            "icx_getBlockByHash": {"params": {"hash": ""}},
            "icx_getScoreApi": {"params": {"address": ""}},
            "icx_call": {"params": ""},
            "icx_sendTransaction": {
                "params": {
                    "from": "",
                    "to": "",
                    "nid": "",
                    "stepLimit": "",
                    "value": "",
                    "version": "0x3",
                    "nonce": "0x23",
                }
            },
            "icx_sendTransaction(SCORE)": {"method": "icx_sendTransaction"}
        },
        "IISS": {
            "setStake": dict(
                method="icx_sendTransaction",
                params={
                    "method": "setStake",
                    "params": {
                        "value": ""
                    }
                }
            ),
        }
    }

    def __init__(self, category=None, method=None):
        self.return_rpc = {}
        self._category = category
        self._method = method
        self._params = {}
        self.get_rpc()

    def get_category(self):
        return list(self.templates.keys())

    def get_methods(self, category=None):
        methods = []
        for _category in self.get_category():
            if _category == category:
                return self.templates.get(_category).keys()
            methods += self.templates.get(_category).keys()
        return methods

    def create_rpc(self, params={}, method=None):

        pass

    def is_required_sign(self):
        if self._method in self.requires_sign_method:
            return True
        return False

    def load_template(self):
        if self._category:
            _template = self.templates.get(self._category)
        else:
            _template = {}
            for item in self.templates.values():
                _template.update(item)
        return _template

    def get_rpc(self, category=None, method=None):
        if category:
            self._category = category
        if method:
            self._method = method

        # if self._category:
        #     _template = self.templates.get(self._category)
        # else:
        #     _template = self.templates.values()
        _template = self.load_template()

        if self._method:
            if _template:
                _arguments = _template.get(method, {})
                if not isinstance(_arguments, dict):
                    raise ValueError(f"[Template Error] Syntax Error -> category={self._category}, method={self._method}")

                if not self._method:
                    raise ValueError(f"[Template Error] Required method ->  category={self._category}, method={self._method}")
                self._method = _arguments.get('method', self._method)
                self._params = _arguments.get('params', {})
                self.return_rpc = json_rpc(method=self._method, params=self._params)

                # pawn.console.log(f"-- return_rpc {self.return_rpc}")

                return self.return_rpc
        return {}

    def get_required_params(self):
        return self._params


class IconRpcHelper:
    def __init__(self, url="", wallet=None, network_info: NetworkInfo = None, raise_on_failure=False):
        self.wallet = wallet
        self.governance_address = None
        self.request_payload = None
        self.response = None
        self.network_info = network_info
        self.raise_on_failure = raise_on_failure

        if not url and self.network_info:
            url = self.network_info.network_api

        self.url = append_suffix(url, "/api/v3")
        self.debug_url = append_suffix(url, "/api/v3d")
        self.signed_tx = {}
        self._parent_method = ""
        self._can_be_signed = False
        self.on_error = False
        self.initialize()

    def initialize(self):
        # self._set_governance_address()
        pass

    def _set_governance_address(self, method=None):
        if self.network_info and not self.governance_address:
            if self.network_info.platform == "havah":
                if method and method.startswith("get"):
                    self.governance_address = const.CHAIN_SCORE_ADDRESS
                else:
                    self.governance_address = const.GOVERNANCE_ADDRESS
            else:
                self.governance_address = f"cx{'0' * 39}1"

    def _decorator_enforce_kwargs(func):
        def from_kwargs(self, *args, **kwargs):
            func_name = func.__name__
            pawn.console.debug(f"Start '{func_name}' function")
            ret = func(self, *args, **kwargs)
            return ret

        return from_kwargs

    @staticmethod
    def _convert_str_to_dict(payload):
        if isinstance(payload, str):
            try:
                payload_dict = json.loads(payload)
            except:
                return payload
            return payload_dict

        return payload

    def _convert_valid_url_format(self, url=None):
        if url:
            self.url = url
        if self.url:
            self.url = append_http(append_api_v3(self.url))
        else:
            raise ValueError('Invalid url: %s' % self.url)

    def _convert_valid_payload_format(self, payload=None, method=None, params=None):
        if payload:
            _request_payload = self._convert_str_to_dict(payload)
        else:
            _request_payload = json_rpc(method=method, params=params)

        return _request_payload

    def rpc_call(self,
                 url=None,
                 method=None,
                 params: dict = {},
                 payload: dict = {},
                 print_error=False,
                 raise_on_failure=False,
                 store_request_payload=True
                 ) -> dict:
        if url:
            _url = url
        else:
            _url = self.url

        if raise_on_failure:
            _raise_on_failure = raise_on_failure
        else:
            _raise_on_failure = self.raise_on_failure

        _url = append_http(append_api_v3(_url))
        _request_payload = self._convert_valid_payload_format(payload=payload, method=method, params=params)

        if store_request_payload:
            self.request_payload = copy.deepcopy(_request_payload)

        # self.response = jequest(
        #     url=_url,
        #     payload=_request_payload,
        #     method="post"
        # )
        self.response = CallHttp(
            url=_url,
            method="post",
            timeout=1000,
            payload=_request_payload,
            raise_on_failure=_raise_on_failure,
        ).run().response.as_dict()
        # pawn.console.log(self.response)
        # self.response = CallHttp(
        #     url=_url,
        #     method="post",
        #     timeout=1000,
        #     payload=_request_payload,
        #     raise_on_failure=_raise_on_failure,
        # ).run()

        # pawn.console.log(self.response.response)
        # pawn.console.log(self.response.response.as_dict())
        # exit()

        if print_error and self.response.get('status_code') != 200:
            if self.response.get('json') and self.response['json'].get('error'):
                pawn.console.log(f"[red][ERROR] status_code={self.response['status_code']}, error={self.response['json']['error']}")
                pawn.console.log(f"[red][ERROR][/red] payload={_request_payload}")
            elif self.response.get('status_code') == 999:
                pawn.console.log(f"[red][ERROR][/red] {self.response.get('error')}")
                # self.exit_on_failure(f"[red][ERROR][/red] {self.response.get('error')}")
            else:
                pawn.console.log(f"[red][ERROR][/red] status_code={self.response.get('status_code')}, text={self.response.get('text')}")
        return self.response.get('json')

    def print_response(self, hex_to_int=False):
        if self.response.get('status_code') != 200:
            style = "red"
        else:
            style = "rule.line"
        pawn.console.rule(f"<Response {self.response.get('status_code')}>", align='right', style=style, characters="═")
        if self.response.get('json'):
            output.dump(self.response.get('json'), hex_to_int=hex_to_int)
        else:
            print(output.syntax_highlight(self.response.get('text'), name='html'))

    def print_request(self):
        pawn.console.print("")
        pawn.console.rule(f"<Request> {self.url}", align='left')
        pawn.console.print("")
        print(output.syntax_highlight(self.request_payload, line_indent='   '))

    def make_params(self, method=None, params={}):
        json_rpc(
            method=method,
            params=params
        )

    def _is_signable_governance_method(self, method):
        if self.network_info.platform == "havah" and method:
            required_sign_methods = ['set', 'register']
            for required_sign_method in required_sign_methods:
                if method.startswith(required_sign_method):
                    pawn.console.debug(f"{method}, It will be signed with the following. required_sign_methods={required_sign_methods}")
                    return True
        return False

    def _make_governance_payload(self, method, params):

        if self._can_be_signed is None:
            self._can_be_signed = self._is_signable_governance_method(method)
            # pawn.console.log(f"[red] can_be_signed = {self._can_be_signed}")

        if self._can_be_signed:
            parent_method = "icx_sendTransaction"
        else:
            parent_method = "icx_call"
        _request_payload = self._convert_valid_payload_format(
            method=parent_method,
            params={
                "to": self.governance_address,
                "dataType": "call",
                "data": {
                    "method": method,
                    "params": params
                }
            },
        )
        return _request_payload

    def governance_call(self, url=None, method=None, params={}, governance_address=None, sign=None, store_request_payload=True):
        if governance_address:
            self.governance_address = governance_address
        else:
            self._set_governance_address(method=method)

        self._can_be_signed = sign
        _request_payload = self._make_governance_payload(method, params)

        if self._can_be_signed:
            _request_payload['params']['value'] = "0x0"
            self.sign_tx(payload=_request_payload)
            response = self.sign_send()
            return response
        else:
            response = self.rpc_call(
                url=url,
                payload=_request_payload,
                print_error=True,
                store_request_payload=store_request_payload,
            )
            return response.get('result', {})

    def get_step_price(self, ):
        response = self.governance_call(method="getStepPrice", governance_address=const.CHAIN_SCORE_ADDRESS, sign=False, store_request_payload=False)
        return response

    def _get_step_costs(self, url=None):
        response = self.governance_call(method="getStepCosts", governance_address=const.CHAIN_SCORE_ADDRESS, sign=False, store_request_payload=False)
        return response

    def get_step_cost(self, step_kind="apiCall"):
        return self._get_step_costs().get(step_kind)

    def get_estimate_step(self, url=None, tx=None):
        if url:
            _url = url
        else:
            _url = self.debug_url

        if isinstance(tx, dict):
            tx['method'] = "debug_estimateStep"
            res = self.rpc_call(
                url=_url,
                payload=tx,
                store_request_payload=False,
                print_error=True
            )
            res_json = res
            if res_json.get('error'):
                pawn.console.debug(f"[red] An error occurred while running debug_estimateStep, {res_json['error'].get('message')}")
                sys.exit(-1)
            return res.get('result')

        else:
            raise ValueError(f"TX is not dict. tx => {tx}")

    def get_step_limit(self, url=None, tx=None, step_kind="apiCall"):
        if tx:
            _tx = tx
        else:
            _tx = copy.deepcopy(self.request_payload)
        unnecessary_keys = ["stepLimit", "signature"]
        for key in unnecessary_keys:
            if _tx['params'].get(key, '__NOT_DEFINED__') != "__NOT_DEFINED__":
                pawn.console.debug(f"Remove the unnecessary '{key}' in payload")
                del _tx['params'][key]

        estimate_step = self.get_estimate_step(tx=_tx)
        step_cost = self.get_step_cost(step_kind)
        step_price = self.get_step_price()
        if estimate_step and step_cost:
            step_limit = hex(hex_to_number(estimate_step) + hex_to_number(step_cost))
            icx_fee = hex_to_number(estimate_step) * hex_to_number(step_price) / const.TINT
            pawn.console.debug(f"fee = {icx_fee} => estimate[i]({hex_to_number(estimate_step, debug=True)})[/i] * "
                               f"step_price[i]({hex_to_number(step_price, debug=True)})[/i]")

            pawn.console.debug(f"step_limit => {hex_to_number(step_limit, debug=True)}")
            return step_limit
        else:
            pawn.console.log("[red]An error occurred while running get_step_limit")

    def get_balance(self, url=None, address=None, is_comma=False):
        if address:
            response = self.rpc_call(
                url=url,
                method="icx_getBalance",
                params={"address": address}
            )
            return hex_to_number(response.get('result'), is_comma=is_comma)

    def get_tx(self, url=None, tx_hash=None, return_key=None):
        response = self.rpc_call(
            url=url,
            method="icx_getTransactionResult",
            params={"txHash": tx_hash}
        )
        if isinstance(response, dict):
            if return_key:
                return response.get(return_key)
            return response
        return response.get('text')

    def get_tx_wait(self, url=None, tx_hash=None):
        if not tx_hash and self.response.get('json') and self.response['json'].get('result'):
            tx_hash = self.response['json']['result']

        pawn.console.log(f"Check a transaction by {tx_hash}")
        with pawn.console.status(f"[magenta] Wait for transaction to be generated.") as status:
            count = 0
            while True:
                resp = self.get_tx(url=url, tx_hash=tx_hash)
                exit_loop = False
                prefix_text = f"[bold cyan][Wait TX][{count}][/bold cyan] "
                if resp.get('error'):
                    exit_msg = ""
                    if "InvalidParams" in resp['error'].get('message'):
                        exit_loop = True
                        exit_msg = f"[red][FAIL][/red]"
                    text = f"{prefix_text}{exit_msg}[white] {resp['error']['message']}"

                elif resp.get('result'):
                    if resp['result'].get('logsBloom'):
                        resp['result']['logsBloom'] = int(resp['result']['logsBloom'], 16)

                    exit_loop = True
                    text = f"{prefix_text}[OK] {json.dumps(resp['result'])}"
                else:
                    text = resp
                status.update(
                    status=f"[bold red]{text}",
                    spinner_style="yellow",
                )
                if exit_loop:
                    pawn.console.log(f"[bold green][white] {text}")
                    break
                count += 1
                time.sleep(1)
        return resp

    def auto_fill_parameter(self):
        if isinstance(self.request_payload, dict) and self.request_payload.get('params'):
            self.request_payload['params']['from'] = self.wallet.get('address')

            if not self.request_payload['params'].get('nonce'):
                self.request_payload['params']['nonce'] = "0x1"

            if not self.request_payload['params'].get('version'):
                self.request_payload['params']['version'] = "0x3"

            if not self.request_payload['params'].get('timestamp'):
                self.request_payload['params']['timestamp'] = hex(icx_signer.get_timestamp_us())

            if self.network_info.nid and not self.request_payload['params'].get('nid'):
                self.request_payload['params']['nid'] = self.network_info.nid

            if not self.request_payload['params'].get('stepLimit'):
                self.request_payload['params']['stepLimit'] = self.get_step_limit()
        else:
            pawn.console.log(f"[red]Invalid payload - {self.request_payload}")

    def sign_tx(self, wallet=None, payload=None):
        self.request_payload = {}
        self.signed_tx = {}
        if wallet:
            self.wallet = wallet

        self.request_payload = self._convert_valid_payload_format(payload=payload)
        # if not isinstance(payload, dict):
        #     try:
        #         payload = json.loads(payload)
        #     except Exception as e:
        #         raise ValueError(f"Invalid payload - {e}, payload={payload}")

        private_key = self.wallet.get('private_key')
        address = self.wallet.get('address')
        self.auto_fill_parameter()

        singer = icx_signer.IcxSigner(data=private_key)
        self.signed_tx = singer.sign_tx(self.request_payload)

        if address != singer.get_hx_address():
            raise ValueError(f'Invalid address {address} != {singer.get_hx_address()}')

        return self.signed_tx

    def sign_send(self):
        if self.signed_tx:
            response = self.rpc_call(payload=self.signed_tx)
            if isinstance(response, dict) and response.get('result'):
                resp = self.get_tx_wait(tx_hash=response['result'])
                return resp

    @staticmethod
    def _check_tx_result(result):
        if result:
            # print(result)
            response_json = result
            if response_json.get("error"):
                return False
            else:
                if response_json.get('result'):
                    return True
                return response_json


class JsonRequest:
    def __init__(self):
        """
        TODO: It will be generated the JSON or JSON-RPC request
        """
        pass


def disable_ssl_warnings():
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def append_http(url):
    """

    Add http:// if it doesn't exist in the URL

    :param url:
    :return:
    """

    if "http://" not in url and "https://" not in url:
        url = f"http://{url}"
    return url


def append_ws(url):
    """

    Add ws:// if it doesn't exist in the URL

    :param url:
    :return:
    """
    if "https://" in url:
        url = url.replace("https://", "wss://")
    elif "http://" in url:
        url = url.replace("http://", "ws://")
    elif "ws://" not in url and "wss://" not in url:
        url = f"ws://{url}"
    return url


def append_api_v3(url):
    if "/api/v3" not in url:
        return f"{url}/api/v3"
    return append_http(url)


def remove_http(url):
    """
    Remove the r'https?://' string

    :param url:
    :return:

    """
    return re.sub(r"https?://", '', url)


def get_operator_truth(inp, relate, cut):
    ops = {
        '>': _operator.gt,
        '<': _operator.lt,
        '>=': _operator.ge,
        '<=': _operator.le,
        '==': _operator.eq,
        '!=': _operator.ne,
        'include': lambda y, x: x in y,
        'exclude': lambda y, x: x not in y
    }
    return ops[relate](inp, cut)


def guess_key(find_key, data):
    guessed_result = []
    if isinstance(data, dict):
        for k, v in data.keys():
            if find_key in k:
                guessed_result.append(k)
    elif isinstance(data, list):
        for k in data:
            if find_key in k:
                guessed_result.append(k)
    return guessed_result


class SuccessCriteria:
    def __init__(
            self,
            target: str = "",
            operator: Literal["!=", "==", ">=", "<=", ">", "<", "include", "exclude"] = "",
            expected: Union[str, int, float] = "",
            # operator: Literal[tuple(ALLOW_OPERATOR)] = ""
    ):
        if target:
            self.target = target
        self.operator = operator
        self.expected = expected
        self.result = False

        if (self.expected or self.expected == 0) and self.target and self.operator:
            try:
                self._set_string_valid_type()
                self.result = get_operator_truth(self.target, self.operator, self.expected)
            except:
                self.result = False

    def _set_string_valid_type(self, ):
        _debug_message = ""
        for var_name in ["target", "expected"]:
            _attr_value_in_class = getattr(self, var_name, "__NOT_NONE__")
            if _attr_value_in_class != "__NOT_NONE__":
                if isinstance(_attr_value_in_class, str):
                    if check.is_int(_attr_value_in_class):
                        setattr(self, var_name, int(_attr_value_in_class))
                    elif check.is_float(_attr_value_in_class):
                        setattr(self, var_name, float(_attr_value_in_class))

                _modified_value = getattr(self, var_name)
                _debug_message += f"{var_name} = {_modified_value} ({type(_modified_value)}) , "

        pawn.console.debug(_debug_message)

    def __str__(self):
        return "<SuccessCriteria %s>" % self.__dict__

    def __repr__(self):
        return "<SuccessCriteria %s>" % self.__dict__

    def to_dict(self):
        return self.__dict__


class SuccessResponse(SuccessCriteria):
    def __init__(
            self,
            target_key: str = "",
            operator: Literal["!=", "==", ">=", "<=", ">", "<", "include", "exclude"] = "",
            expected: Union[str, int, float] = "",
            target: dict = {},
    ):
        # if not target or not operator or not expected or target_key:
        #     raise ValueError(f"target: {target}, operator: {operator}, expected: {expected}, target_key: {target_key} ")

        if not isinstance(target, dict):
            pawn.console.log(f"[red]<Error>[/red] '{target}' is not dict")
            self.result = False
            raise ValueError(f"target is not dict - '{target}'")

        self.target_key = target_key
        self.target = FlatDict(target)

        _selected_flatten_target = self.target.get(self.target_key)
        super().__init__(target=_selected_flatten_target, operator=operator, expected=expected)

        if not _selected_flatten_target:
            pawn.console.debug(f"[red]<Error>[/red] '{self.target_key}' is not attribute in {list(self.target.keys())}")
            pawn.console.debug(
                f"[red]<Error>[/red] '{self.target_key}' not found. \n Did you mean {guess_key(self.target_key, self.target.keys())} ?")
            self.result = False


class CallHttp:
    def __init__(self,
                 url=None,
                 method: Literal["get", "post", "patch", "delete"] = "get",
                 # method: Literal[AllowsHttpMethod.get] = "get",
                 # method: AllowsHttpMethod = AllowsHttpMethod.get,
                 # method: Literal[tuple(method for method in AllowsHttpMethod)],
                 payload={},
                 timeout=1000,
                 ignore_ssl: bool = False,
                 verbose: int = 0,
                 success_criteria: Union[dict, list, str] = None,
                 success_operator: Literal["and", "or"] = "and",
                 success_syntax: Literal["operator", "string", "auto"] = "auto",
                 raise_on_failure: bool = False,
                 auto_run: bool = True,

                 **kwargs
                 ):

        self.url = url
        self.method = method.lower()
        self.payload = payload
        self.timeout = timeout / 1000
        self.ignore_ssl = ignore_ssl
        self.verbose = verbose
        self.success_criteria = success_criteria
        self.success_operator = success_operator
        self.success_syntax = success_syntax

        self.kwargs = kwargs
        self.raise_on_failure = raise_on_failure
        self._DEFAULT_UA = f"CallHttp Agent/{pawn.get('PAWN_VERSION')}"
        self.on_error = False
        self.response = requests.models.Response()
        self.flat_response = None

        self.success = None
        self._success_results = []
        self._success_criteria = None
        self.timing = 0
        # self.run()

    def _shorten_exception_message_handler(self, exception):
        _shorten_message_dict = {
            requests.exceptions.Timeout: {
                "message": "Timeout Error",
                "params_message": f"timeout={self.timeout}"
            },
            requests.exceptions.HTTPError: "HTTP Error",
            requests.exceptions.ConnectionError: "DNS lookup Error",
            requests.exceptions.RequestException: "OOps: Something Else",
        }
        _shorten_message = _shorten_message_dict.get(exception)
        default_msg = f"(url={self.url}, method={self.method}"

        # connection_pool = exception.__context__.pool
        # hostname = connection_pool.host
        # port = connection_pool.port

        for req_exception, values in _shorten_message_dict.items():
            if isinstance(exception, req_exception):

                if isinstance(values, dict) and values.get('message'):
                    _message = f"<{values.get('message')}>"
                    _params_message = f" {values.get('params_message', '')}"
                else:
                    _message = f"<{values}>"
                    _params_message = ''
                return f"{_message}{default_msg}{_params_message})"

        return f"<Unknown Error>{default_msg})"

    def exit_on_failure(self, exception):
        self.on_error = True
        self.response = HttpResponse(status_code=999, error=self._shorten_exception_message_handler(exception), elapsed=self.timing)
        if self.raise_on_failure:
            raise output.NoTraceBackException(exception)
        else:
            pawn.console.debug(f"[red][FAIL][/red] {exception}")
            # self.response.status_code = 999
            # self.response.success = False
            # self.response.error = self._shorten_exception_message_handler(exception)
            # print(self.timing)
            return self.response

    def run(self) -> HttpResponse:
        self._prepare()
        start = time.perf_counter()
        self.fetch_response()
        end = time.perf_counter()
        self.timing = int((end - start) * 1000)
        self._parse_response()
        self.fetch_criteria()
        self.response.success = self.is_success()

        return self

    def _prepare(self):
        self.url = append_http(self.url)

    def fetch_response(self):
        (json_response, data, http_version, r_headers, error) = ({}, {}, None, None, None)
        if self.method not in ("get", "post", "patch", "delete"):
            pawn.error_logger.error(f"unsupported method='{self.method}', url='{self.url}' ") if pawn.error_logger else False
            # raise ValueError(f"unsupported method={self.method}, url={self.url}")
            return self.exit_on_failure(f"Unsupported method={self.method}, url={self.url}")
        try:
            try:
                _payload_string = json.dumps(self.payload)
            except Exception as e:
                _payload_string = self.payload
            pawn.console.debug(f"[TRY] url={self.url}, method={self.method}, payload={_payload_string}, kwargs={self.kwargs}")
            func = getattr(requests, self.method)
            if self.method == "get":
                self.response = func(self.url, verify=False, timeout=self.timeout, **self.kwargs)
            else:
                self.response = func(self.url, json=self.payload, verify=False, timeout=self.timeout, **self.kwargs)
        except Exception as e:
            return self.exit_on_failure(e)

    def _parse_response(self):
        self.response.timing = self.timing

        try:
            _elapsed = int(self.response.elapsed.total_seconds() * 1000)
        except AttributeError:
            _elapsed = 0

        self.response.elapsed = _elapsed

        if getattr(self.response, 'raw', None):
            self.response.http_version = self.response.raw.version
        else:
            self.response.http_version = ""

        # self.response.headers = self.response.headers

        if self.response and not self.on_error:
            try:
                self.response.result = self.response.json()
            except:
                self.response.result = self.response.text

    def fetch_criteria(self,
                       success_criteria: Union[dict, list] = None,
                       success_operator: Literal["and", "or"] = "and",
                       ):
        # pawn.console.log(self.response)
        _response_dict = self.response.as_dict()

        # output.dump(_response_dict)
        if success_criteria:
            self.success_criteria = success_criteria
        if success_operator:
            self.success_operator = success_operator

        if not self.success_criteria:
            pawn.console.debug("passing success_criteria")
        else:

            # if isinstance(self.success_criteria, str):
            #     pawn.console.log(f"String {type(self.success_criteria)}. '{self.success_criteria}'")
            #     self.success_criteria = self._convert_criteria(self.success_criteria)
            # pawn.console.log(res)

            if self.success_syntax == "string" or self.success_syntax == "auto":
                _check_syntax = self._check_criteria_syntax()
                if _check_syntax:
                    pawn.console.debug(f"[blue]Try to convert[/blue] {type(self.success_criteria)}, _check_criteria_syntax={_check_syntax}")
                    self._recursive_convert_criteria()

            depth = list_depth(self.success_criteria)
            if depth == 1:
                self.success_criteria = [self.success_criteria]

            for criteria in self.success_criteria:
                pawn.console.debug(f"{type(criteria)} {criteria}")
                if isinstance(criteria, list):
                    _criteria = copy.deepcopy(criteria)
                    _criteria.append(_response_dict)
                    self._success_results.append(SuccessResponse(*_criteria))
                elif isinstance(criteria, dict):
                    criteria['target'] = _response_dict
                    self._success_results.append(SuccessResponse(**criteria))
            pawn.console.debug(self._success_results)

    @staticmethod
    def _find_operator(string):
        for operator in ALLOW_OPERATOR:
            if operator in string:
                return True
        return False

    def _check_criteria_syntax(self, criteria=None):
        if not criteria:
            criteria = self.success_criteria

        if isinstance(criteria, str):
            if self._find_operator(criteria):
                return True
            return False

        elif isinstance(criteria, list):
            for ct in criteria:
                return self._check_criteria_syntax(ct)

    def _recursive_convert_criteria(self, string_criteria=None, depth=None):

        if not string_criteria:
            string_criteria = self.success_criteria

        if string_criteria and isinstance(string_criteria, str):
            self.success_criteria = self._convert_criteria(string_criteria)
            return self.success_criteria

        elif isinstance(self.success_criteria, list):
            string_criteria_in_list = []
            for string_criteria in string_criteria:
                converted_criteria = self._recursive_convert_criteria(string_criteria)
                if converted_criteria:
                    string_criteria_in_list.append(converted_criteria)

            if len(string_criteria_in_list) > 0:
                self.success_criteria = string_criteria_in_list

    def _convert_criteria(self, argument):
        for operator in ALLOW_OPERATOR:
            if operator in argument:
                result = argument.split(operator)
                if any(word in result[0] for word in ALLOW_OPERATOR + ['=']):
                    pawn.console.log(f"[red]Invalid operator - '{argument}', {result}")
                    raise ValueError(f"Invalid operator - '{argument}', {result}")
                result.insert(1, operator)
                return result
        return False

    def _convert_list_criteria(self, arguments):
        result = []
        for argument in arguments:
            criteria = self._convert_criteria(argument)
            if criteria:
                result.append(criteria)
        return result

    def is_success(self):
        success_count = 0
        expected_count = len(self._success_results)

        if isinstance(self._success_results, list):
            for _result in self._success_results:
                if _result.result:
                    success_count += 1

        if self.success_operator == "and" and success_count == expected_count:
            return True
        elif self.success_operator == "or" and success_count > 0:
            return True
        return False


def jequest(url, method="get", payload={}, elapsed=False, print_error=False, timeout=None, ipaddr=None, **kwargs) -> dict:
    """
    This functions will be called the http requests.

    :param url:
    :param method:
    :param payload:
    :param elapsed:
    :param print_error:
    :param timeout: Timeout seconds
    :param ipaddr: Change the request IP address in http request
    :param \*\*kwargs: Optional arguments that ``request`` takes.

    :return:
    """
    if ipaddr:
        if url.startswith('http') or url.startswith('http://'):
            domain = re.sub(r'https?://', '', url)
            # net.override_dns(domain, ipaddr)
            # net.override_dns(domain=domain, ipaddr=ipaddr)
            net.OverrideDNS(domain=domain, ipaddr=ipaddr).set()
    else:
        net.OverrideDNS().unset()

    pawnlib_timeout = pawn.to_dict().get('PAWN_TIMEOUT', 10)
    if pawnlib_timeout > 0:
        pawnlib_timeout = pawnlib_timeout / 1000

    timeout = timeout or pawnlib_timeout

    url = append_http(url)
    (json_response, data, http_version, r_headers, error) = ({}, {}, None, None, None)

    response = None
    if method not in ("get", "post", "patch", "delete"):
        # cprint(f"[ERROR] unsupported method={method}, url={url} ", color="red")
        pawn.error_logger.error(f"unsupported method={method}, url={url} ") if pawn.error_logger else False
        return {"error": "unsupported method"}
    try:
        func = getattr(requests, method)
        if method == "get":
            response = func(url, verify=False, timeout=timeout, **kwargs)
        else:
            response = func(url, json=payload, verify=False, timeout=timeout, **kwargs)
        http_version = response.raw.version
        r_headers = response.headers

    except requests.exceptions.HTTPError as errh:
        error = errh
        if global_verbose > 0:
            output.kvPrint("Http Error:", errh)
        pawn.error_logger.error(f"Http Error:{errh}") if pawn.error_logger else False

    except requests.exceptions.ConnectionError as errc:
        error = errc
        if ("[Errno 11001] getaddrinfo failed" in str(errc) or  # Windows
                "[Errno -2] Name or service not known" in str(errc) or  # Linux
                "[Errno 8] nodename nor servname " in str(errc)):  # OS X
            errc = "DNSLookupError"
        if global_verbose > 0:
            output.kvPrint("Error Connecting:", errc, "FAIL")
        pawn.error_logger.error(f"Error Connecting:{errc}, {url}") if pawn.error_logger else False

    except requests.exceptions.Timeout as errt:
        error = errt
        if global_verbose > 0:
            output.kvPrint("Timeout Error:", errt, "FAIL")
        pawn.error_logger.error(f"Timeout Connecting:{errt}, {url}") if pawn.error_logger else False

    except requests.exceptions.RequestException as err:
        error = err
        if global_verbose > 0:
            output.kvPrint("OOps: Something Else", err, "FAIL")
        pawn.error_logger.error(f"OOps: Something Else:{err}, {url}") if pawn.error_logger else False

    # cprint(f"----> {url}, {method}, {payload} , {response.status_code}", "green")

    try:
        response_code = response.status_code
    except:
        response_code = 999

    json_payload = json.dumps(payload)
    if global_verbose > 1:
        output.debug_logging(f"{url}, {method}, {json_payload} , {response_code}")

    if response_code != 999:
        try:
            json_response = response.json()
        except:
            json_response = {}
            data["text"] = response.text
            # debug_logging(f"{url} , response is not json -> '{response.text}'")

        if elapsed:
            data["elapsed"] = int(response.elapsed.total_seconds() * 1000)
            if len(json_response) > 0:
                json_response["elapsed"] = data["elapsed"]

    if response_code > 200 and response_code != 999 and print_error:
        text = response.text
        pawn.error_logger.error(f"status_code: {response_code} , url: {url} , payload: {payload}, response: {text}") if pawn.error_logger else False
    data["status_code"] = response_code
    data["http_version"] = http_version
    data["r_headers"] = r_headers
    data["json"] = json_response
    data["error"] = error
    if print_error:
        if error:
            pawn.error_logger.error(f"{error}") if pawn.error_logger else False

    if isinstance(payload, dict):
        payload = json.dumps(payload)

    pawn.console.debug(f"url={url}, method={method}, payload={payload}, kwargs={kwargs}, error={error}")

    return data


icon_rpc_call = IconRpcHelper().rpc_call
