import re
import json
import sys
import socket
import ssl
from functools import partial
from datetime import datetime
from pawnlib.config.globalconfig import pawnlib_config as pawn, global_verbose, pconf, SimpleNamespace, Null
from pawnlib.output import (
    NoTraceBackException,
    dump, syntax_highlight, kvPrint, debug_logging,
    PrintRichTable, get_debug_here_info,
    print_json)
from pawnlib.resource import net
from pawnlib.typing import date_utils
from pawnlib.typing.converter import append_suffix, append_prefix, hex_to_number, FlatDict, FlatterDict, flatten, const, shorten_text
from pawnlib.typing.constants import const
from pawnlib.typing.generator import json_rpc, random_token_address, generate_json_rpc
from pawnlib.typing.check import keys_exists, is_int, is_float, list_depth, is_valid_token_address, sys_exit, is_hex, is_valid_tx_hash
from pawnlib.utils.operate_handler import WaitStateLoop
from pawnlib.output import pretty_json, align_text, get_file_extension, is_directory, is_file
from pawnlib.utils.in_memory_zip import gen_deploy_data_content
from websocket import create_connection, WebSocket, enableTrace
try:
    from pawnlib.utils import icx_signer
except ImportError:
    pass

from typing import Any, Dict, Iterator, Tuple, Union, Callable, Type
from collections import OrderedDict

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
from rich.prompt import Prompt, Confirm


ALLOWS_HTTP_METHOD = ["get", "post", "patch", "delete", "head", "put", "connect", "options", "trace", "patch"]
ALLOW_OPERATOR = ["!=", "==", ">=", "<=", ">", "<", "include", "exclude"]


class _ResponseWithElapsed(requests.models.Response):
    success = False
    error = None

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
requests.models.Response.error = _ResponseWithElapsed.error
requests.models.Response.success = _ResponseWithElapsed.success
requests.models.Response.as_dict = _ResponseWithElapsed.as_dict


class HttpResponse:
    def __init__(self, status_code=999, response=None, error=None, elapsed=None, success=False):
        self.status_code = status_code
        self.response = response
        self.error = error
        self.elapsed = elapsed
        self.success = success
        self.text = None

        if getattr(response, "text", None):
            self.response = response.text

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
    network_name: str = "mainnet"
    platform: str = "icon"
    force: bool = False
    network_api: str = ""
    planet_api: str = ""
    nid: str = ""
    network: str = ""
    endpoint: str = ""
    symbol: str = ""
    valid_network: bool = False

    def __post_init__(self):

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
                    "techteam": {
                        "network_api": "https://techteam.net.solidwallet.io",
                        "nid": "0xa"
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
        # self.network_name = network_name
        # self.platform = platform
        self.network_info = {}
        self.static_values = ["nid", "network_api", "endpoint"]
        if not self.force:
            self._initialize()

    def is_set_static_values(self):
        # missing_static_values = [static_value for static_value in self.static_values if not getattr(self, static_value, None)]
        # if missing_static_values:
        #     pawn.console.debug(f"[red]Missing static values: {missing_static_values}")
        return any(getattr(self, static_value, None) for static_value in self.static_values)

    def _get_network_info(self, network_name="", platform=""):
        if network_name:
            self.network_name = network_name
        if platform:
            self.platform = platform
        self.network_name = self.network_name.lower()
        self.platform = self.platform.lower()

        if self.network_name == "veganet":
            self.network_name = "vega"

        elif self.network_name == "denebnet":
            self.network_name = "deneb"

        if not self._platform_info.get(self.platform):
            raise ValueError(f"Allowed platform - values {list(self._platform_info.keys())}")
        if not self.is_set_static_values():
            _network_info = self._platform_info[self.platform].get('network_info')
            if isinstance(_network_info, dict) and not _network_info.get(self.network_name):
                raise ValueError(f"Allowed network_name in '{self.platform}' - values {list(_network_info.keys())}")
            self.network_info = self._platform_info[self.platform]['network_info'].get(self.network_name)

        self.symbol = self._platform_info[self.platform].get('symbol')

        if self.network_info:
            self.valid_network = True
            self.network_info['symbol'] = self.symbol
            self.network_info['network_name'] = self.network_name
            self.network_info['platform'] = self.platform
        else:
            self.network_info = self._extract_network_info()

        if not self.network_info.get('endpoint') and self.network_info.get('network_api'):
            self.network_info['endpoint'] = append_suffix(self.network_info['network_api'], "/api/v3")

    def _initialize(self, network_name="", platform=""):
        self._get_network_info(network_name, platform)
        if self.network_info and self.valid_network:
            self._set_attributes()

    def _set_attributes(self):
        this_data = self.network_info

        if this_data.get("network", None) is None:
            setattr(self, "network", self.network_name)
        for key, value in this_data.items():
            object.__setattr__(self, key, this_data.get(key))

    def set_network(self, network_name=None, platform="icon"):
        if network_name and platform:
            self._initialize_static_values()
            self._initialize(network_name=network_name, platform=platform)

    def _initialize_static_values(self):
        for static_value in self.static_values:
            setattr(self, static_value, None)

    def list(self) -> list:
        return list(self.network_info.keys())

    def get_platform_list(self) -> list:
        return list(self._platform_info.keys())

    def get_platform_info(self) -> dict:
        return self._platform_info

    def update_platform_info(self, data={}) -> dict:
        self._platform_info.update(data)
        return self._platform_info

    def add_network(self, platform, network_name, network_api, nid):
        if platform in self._platform_info:
            self._platform_info[platform]["network_info"][network_name.lower()] = {
                "network_api": network_api,
                "nid": nid
            }

    def get_network_list(self, platform="") -> list:
        if platform:
            self.platform = platform

        if self._platform_info.get(self.platform):
            return list(self._platform_info[self.platform]['network_info'].keys())

    def tuple(self) -> tuple:
        return tuple(self.network_info.keys())

    def to_dict(self):
        if self.network_info:
            return self.network_info
        return self.network_info

    def _extract_network_info(self):
        _static_network_info = {
            key: value for key, value in copy.deepcopy(self.__dict__).items()
            if key and value and key not in ['_platform_info', 'static_values', 'network_info']
        }
        return _static_network_info

    def _parse_network_info_string(self):
        return self.network_info if self.network_info else self._extract_network_info()

    def __repr__(self):
        return f"<{self.platform.upper()} {self.__class__.__name__}> network_info={self._parse_network_info_string()}"

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
            "icx_getScoreStatus": {"params": {"address": ""}},
            "debug_getTrace": {"params": {"txHash": ""}},
            "debug_estimateStep": {"params": {}},
            "icx_getNetworkInfo": {},
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

    def update_template(self, new_template):
        self.templates.update(**new_template)

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

        _template = self.load_template()
        if self._method and _template:
            _arguments = _template.get(method, {})
            if not isinstance(_arguments, dict):
                raise ValueError(f"[Template Error] Syntax Error -> category={self._category}, method={self._method}")

            if not self._method:
                raise ValueError(f"[Template Error] Required method ->  category={self._category}, method={self._method}")

            if _arguments.get('method'):
                self.return_rpc = json_rpc(**_arguments)
            else:
                self._method = _arguments.get('method', self._method)
                self._params = _arguments.get('params', {})
                self.return_rpc = json_rpc(method=self._method, params=self._params)

            # pawn.console.log(f"-- return_rpc {self.return_rpc}")

            return self.return_rpc
        return {}

    def get_required_params(self):
        return self._params


class IconRpcHelper:
    def __init__(self, url="", wallet=None, network_info: NetworkInfo = None, raise_on_failure=True, debug=False, required_sign_methods=None):
        self.wallet = wallet
        self.governance_address = None
        self.request_payload = None
        self.response = None
        self.network_info = network_info
        self.raise_on_failure = raise_on_failure
        self.debug = debug
        if required_sign_methods and isinstance(required_sign_methods, list):
            self.required_sign_methods = required_sign_methods
        else:
            self.required_sign_methods = ['set', 'register', "unregister", "claim", "vote", "apply", "remove", "cancel", "acceptScore", "reject"]

        if not url and self.network_info:
            url = self.network_info.network_api

        self.url = append_suffix(url, "/api/v3")
        self.debug_url = append_suffix(url, "/api/v3d")
        self.signed_tx = {}
        self._parent_method = ""
        self._can_be_signed = None
        self.on_error = False
        self.initialize()
        self._use_global_reqeust_payload = False
        self.global_reqeust_payload = {}
        self.score_api = {}

        self.default = {
            "stepLimit": hex(2500000)
        }

    def initialize(self):
        # self._set_governance_address()
        if self.network_info:
            pawn.console.debug(self.network_info)
        else:
            pawn.console.debug("Not found network_info")

        self.initialize_wallet()

    def initialize_wallet(self):
        if self.wallet and not isinstance(self.wallet, dict):
            pawn.console.debug("Loading wallet from icx_signer.load_wallet_key()")
            self.wallet = icx_signer.load_wallet_key(self.wallet)

    def _set_governance_address(self, method=None):
        if self.network_info and not self.governance_address:
            if self.network_info.platform == "havah":
                if method and method.startswith("get"):
                    self.governance_address = const.CHAIN_SCORE_ADDRESS
            else:
                self.governance_address = const.GOVERNANCE_ADDRESS

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
                 timeout=5000,
                 params: dict = {},
                 payload: dict = {},
                 print_error=False,
                 reset_error=True,
                 raise_on_failure=False,
                 store_request_payload=True,
                 http_method: Literal["get", "post", "patch", "delete"] = 'post',
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

        if reset_error:
            self.on_error = False

        if store_request_payload:
            self.request_payload = copy.deepcopy(_request_payload)

        self.response = CallHttp(
            url=_url,
            method=http_method,
            timeout=timeout,
            payload=_request_payload,
            raise_on_failure=_raise_on_failure,
        ).run().response.as_dict()

        if self.response.get('status_code') != 200:
            self.on_error = True
            self.print_error_message(print_error)

        return self.response.get('json')

    def print_error_message(self, print_error=True):
        if print_error:
            if self.response.get('json') and self.response['json'].get('error'):
                pawn.console.log(f"[red][ERROR][/red] payload={self.request_payload}")
                pawn.console.log(f"[red][ERROR] status_code={self.response['status_code']}, error={self.response['json']['error']}")
            elif self.response.get('status_code') == 999:
                pawn.console.log(f"[red][ERROR][/red] {self.response.get('error')}")
                # self.exit_on_failure(f"[red][ERROR][/red] {self.response.get('error')}")
            else:
                pawn.console.log(f"[red][ERROR][/red] status_code={self.response.get('status_code')}, text={self.response.get('text')}")

    def print_response(self, hex_to_int=False):
        if self.response.get('status_code') != 200:
            style = "red"
        else:
            style = "rule.line"
        pawn.console.rule(f"<Response {self.response.get('status_code')}>", align='right', style=style, characters="═")
        if self.response.get('json'):
            dump(self.response.get('json'), hex_to_int=hex_to_int)
        else:
            print(syntax_highlight(self.response.get('text'), name='html'))

    def print_request(self):
        pawn.console.print("")
        pawn.console.rule(f"<Request> {self.url}", align='left')
        pawn.console.print("")
        print(syntax_highlight(self.request_payload, line_indent='   '))

    def make_params(self, method=None, params={}):
        json_rpc(
            method=method,
            params=params
        )

    def _is_signable_governance_method(self, method):
        # if self.network_info.platform == "havah" or self.network_info.platform == "icon" and method:
        if method:
            for required_sign_method in self.required_sign_methods:
                if method.startswith(required_sign_method):
                    pawn.console.debug(f"{method}, It will be signed with the following. required_sign_methods={self.required_sign_methods}")
                    return True
        return False

    def create_governance_payload(self, method, params):

        if self._can_be_signed is None:
            self._can_be_signed = self._is_signable_governance_method(method)

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

    def governance_call(self, url=None, method=None, params={}, governance_address=None,
                        sign=None, store_request_payload=True, is_wait=True, value="0x0", step_limit=None):
        if governance_address:
            self.governance_address = governance_address
        else:
            self._set_governance_address(method=method)

        if sign is not None:
            self._can_be_signed = sign
        pawn.console.debug(f"Does the method require a signature? _can_be_signed={self._can_be_signed}")
        _request_payload = self.create_governance_payload(method, params)

        if self._can_be_signed:
            # if _request_payload['params'].get('value', None):
            _request_payload['params']['value'] = value
            self.sign_tx(payload=_request_payload, step_limit=step_limit)
            response = self.sign_send(is_wait=is_wait)
            return response
        else:
            response = self.rpc_call(
                url=url,
                payload=_request_payload,
                print_error=True,
                store_request_payload=store_request_payload,
            )
            return response.get('result', {})

    def create_deploy_payload(self, src="", params={}, governance_address=None):
        self.governance_address = governance_address if governance_address else const.CHAIN_SCORE_ADDRESS
        file_extension_mapping = {
            "jar": "java"
        }
        _file_extension = get_file_extension(src) if is_file(src) else None
        _file_type = file_extension_mapping.get(_file_extension, "python")

        if not _file_extension:
            self.exit_on_failure(f"Invalid SCORE source - '{src}'", force_exit=True)
            return

        _content = gen_deploy_data_content(src)
        _request_payload = self._convert_valid_payload_format(
            method="icx_sendTransaction",
            params={
                "to": self.governance_address,
                "dataType": "deploy",
                "data": {
                    "contentType": f"application/{_file_type}",
                    "content": f'0x{_content.hex()}',
                    "params": params,
                },
            },
        )
        self.global_reqeust_payload = _request_payload
        return _request_payload

    def deploy_score(self, src="", params={}, step_limit=None, governance_address=None, is_wait=True, is_confirm_send=False):
        payload = self.create_deploy_payload(src, params, governance_address)
        self.sign_tx(payload=payload, step_limit=step_limit)

        if is_confirm_send:
            print_json(self.signed_tx)
            is_send = Confirm.ask("Do you want to send the [bold red]deploy[/bold red] transaction?", default=False)
        else:
            is_send = True

        if is_send:
            response = self.sign_send(is_wait=is_wait)
            return response

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

        _tx = copy.deepcopy(tx)
        _tx = self.auto_fill_parameter(_tx)

        if isinstance(_tx, dict):
            _tx['method'] = "debug_estimateStep"
            res = self.rpc_call(
                url=_url,
                payload=_tx,
                store_request_payload=False,
                print_error=True
            )
            res_json = res
            if res_json.get('error'):
                # pawn.console.debug(f"[red] An error occurred while running debug_estimateStep, {res_json['error'].get('message')}")
                # sys.exit(-1)
                self.exit_on_failure(f"An error occurred while running debug_estimateStep, {res_json['error'].get('message')}")

            return res.get('result')

        else:
            self.exit_on_failure(f"TX is not dict. tx => {_tx}")

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
        _guess_step_kind = self._guess_step_kind(tx=_tx)
        pawn.console.debug(f"guess step_kind = {_guess_step_kind}")
        step_cost = self.get_step_cost(_guess_step_kind)
        step_price = self.get_step_price()

        if estimate_step and step_cost:
            step_limit = hex(hex_to_number(estimate_step) + hex_to_number(step_cost))
            icx_fee = hex_to_number(estimate_step) * hex_to_number(step_price) / const.TINT
            pawn.console.debug(f"fee = {icx_fee} => estimate[i]({hex_to_number(estimate_step, debug=True)})[/i] * "
                               f"step_price[i]({hex_to_number(step_price, debug=True)})[/i]")

            pawn.console.debug(f"step_limit => {hex_to_number(step_limit, debug=True)}")
            return step_limit
        else:
            _default_step_limit = self.default.get("stepLimit")
            pawn.console.log(f"[red][FAIL][/red] An error occurred while running get_step_limit(). set default : {_default_step_limit}")
            return _default_step_limit

    @staticmethod
    def _guess_step_kind(tx=None):
        step_kind_dict = {
            "dataType": {
                "deploy": "contractCreate",
                "call": "apiCall"
            }
        }
        _default_step_kind = "get"
        if not isinstance(tx, dict):
            return _default_step_kind

        for payload_key, value in step_kind_dict.items():
            if keys_exists(tx, "params", payload_key):
                _data_type = tx['params'][payload_key]
                return step_kind_dict[payload_key].get(_data_type, _default_step_kind)
        return _default_step_kind

    def get_fee(self, tx=None, symbol=False):
        _tx = self.parse_tx_var(tx)
        if keys_exists(_tx, "params", "stepLimit"):
            del _tx['params']['stepLimit']
        estimate_step = self.get_estimate_step(tx=_tx)
        step_kind = self._guess_step_kind(tx)
        pawn.console.debug(f"_guess_step_kind = {step_kind}")
        step_cost = self.get_step_cost(step_kind)
        step_price = self.get_step_price()
        step_limit = hex(hex_to_number(estimate_step) + hex_to_number(step_cost))

        fee = hex_to_number(estimate_step) * hex_to_number(step_price) / const.TINT
        pawn.console.debug(f"[red] fee = (estimate_step + step_cost) * step_price = {fee}")
        pawn.console.debug(f"[red] fee = ({estimate_step} + {step_cost}) * {step_price} = {fee}")

        if symbol:
            fee = f"{fee} {self.network_info.symbol}"

        return fee

    def get_score_api(self, address="", url=None):
        if not is_valid_token_address(address, prefix="cx"):
            return self.exit_on_failure(f"Invalid token address - {address}")

        response = self.rpc_call(
            url=url,
            method="icx_getScoreApi",
            params={"address": address},
            store_request_payload=False,
        )

        error = self.response.get('error')
        if error:
            self.exit_on_failure(error)
            return 0

        return response.get('result')

    @staticmethod
    def name_to_params(list_data):
        return {data.get('name'): "" for data in list_data}

    def _convert_score_api_to_params(self, data=[], address=""):
        result = {}
        for _input in data:
            if _input.get('type') != "function":
                continue

            method = "icx_call" if _input.get('readonly') == "0x1" else "icx_sendTransaction"
            score_method = _input.get('name')

            result[score_method] = dict(
                method=method,
                params=dict(
                    dataType="call",
                    to=address,
                    data=dict(
                        method=score_method,
                        params=self.name_to_params(_input.get('inputs'))
                    )
                )
            )

            if method == "icx_sendTransaction":
                result[score_method]['params']['value'] = "0x0"
            # pawn.console.log(f"{_input.get('type')} {score_method} , {_input.get('inputs')}, {_input.get('readonly')}")
        return result

    def get_governance_api(self, url=None):
        self.score_api = {}
        for address in [const.GOVERNANCE_ADDRESS, const.CHAIN_SCORE_ADDRESS]:
            _api_result = self.get_score_api(address=address, url=url)
            if _api_result:
                self.score_api[address] = self._convert_score_api_to_params(_api_result, address=address)

        return self.score_api

    def get_balance(self, url=None, address=None, is_comma=False):
        if not address and self.wallet:
            address = self.wallet.get('address')

        if is_valid_token_address(address):
            response = self.rpc_call(
                url=url,
                method="icx_getBalance",
                params={"address": address},
                store_request_payload=False,
            )
            _balance = response.get('result')
            if self.response.get('error'):
                self.exit_on_failure(self.response.get('error'))
                return 0
            return hex_to_number(_balance, is_comma=is_comma, is_tint=True)
        else:
            return self.exit_on_failure(f"Invalid token address - {address}")

    def get_tx(self,  tx_hash=None, url=None,  return_key=None):
        if not tx_hash:
            tx_hash = self._get_tx_hash
        if not is_valid_tx_hash(tx_hash):
            self.exit_on_failure(f"Invalid tx_hash - {tx_hash}")

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

    def get_tx_wait(self,  tx_hash=None, url=None,  is_compact=True):
        tx_hash = self._get_tx_hash(tx_hash)
        if not tx_hash:
            return
        self.on_error = False
        count = 0
        with pawn.console.status("[magenta] Wait for transaction to be generated.") as status:
            while True:
                resp = self._check_transaction(url, tx_hash)
                if resp.get('error'):
                    text, exit_loop = self._handle_error_response(resp, count, tx_hash)
                elif resp.get('result'):
                    text, exit_loop = self._handle_success_response(resp, count, tx_hash)
                else:
                    text = resp
                status.update(
                    status=text,
                    spinner_style="yellow",
                )
                if exit_loop:
                    self._print_final_result(text, is_compact, resp)
                    break
                count += 1
                time.sleep(1)
            if self.on_error and tx_hash:
                self.get_debug_trace(tx_hash, reset_error=False)
        return resp

    def _get_tx_hash(self, tx_hash):
        if not tx_hash and isinstance(self.response, dict):
            if keys_exists(self.response, 'json', 'result', 'txHash'):
                tx_hash = self.response['json']['result']['txHash']
            elif keys_exists(self.response, 'json', 'result'):
                tx_hash = self.response['json']['result']
        if not tx_hash:
            pawn.console.log(f"[red] Not found tx_hash='{tx_hash}'")
        return tx_hash

    def _check_transaction(self, url, tx_hash):
        return self.get_tx(url=url, tx_hash=tx_hash)

    def _handle_error_response(self, resp, count, tx_hash):
        exit_loop = False
        exit_msg = ""
        prefix_text = f"[cyan][Wait TX][{count}][/cyan] Check a transaction by [i cyan]{tx_hash}[/i cyan] "
        _error_message = resp['error'].get('message')
        exit_error_messages = ["InvalidParams", "NotFound: E1005:not found tx id"]

        if any(error_message in _error_message for error_message in exit_error_messages):
            exit_loop = True
            exit_msg = "[red][FAIL][/red]"
            self.on_error = True
        text = f"{prefix_text}{exit_msg}[white] '{_error_message}'"
        return text, exit_loop

    def _handle_success_response(self, resp, count, tx_hash):
        if resp['result'].get('logsBloom'):
            resp['result']['logsBloom'] = int(resp['result']['logsBloom'], 16)
        if resp['result'].get('failure'):
            _resp_status = "[red][FAIL][/red]"
            self.on_error = True
        else:
            _resp_status = "[green][OK][/green]"
            self.on_error = False
        exit_loop = True
        prefix_text = f"[cyan][Wait TX][{count}][/cyan] Check a transaction by [i cyan]{tx_hash}[/i cyan] "
        text = align_text(prefix_text, _resp_status, ".")
        return text, exit_loop

    def _print_final_result(self, text, is_compact, resp):
        final_result = f"[bold green][white]{text}"
        if is_compact:
            final_result = shorten_text(final_result, width=205)
        pawn.console.tprint(final_result)
        if self.debug or pawn.get('PAWN_DEBUG'):
            print_json(resp['result'])

    def get_debug_trace(self, tx_hash, print_table=True, reset_error=True):
        response = self.rpc_call(
            url=self.debug_url,
            method="debug_getTrace",
            params={"txHash": tx_hash},
            store_request_payload=False,
            reset_error=reset_error,
        )
        if isinstance(response, dict) and keys_exists(response, "result", "logs") and print_table:
            PrintRichTable(f"debug_getTrace={tx_hash}", data=response['result']['logs'])
        else:
            pawn.console.log(response)
        return response

    def parse_tx_var(self, tx=None):
        if tx:
            _tx = copy.deepcopy(tx)
            self._use_global_reqeust_payload = False
        else:
            _tx = self.request_payload
            self._use_global_reqeust_payload = True
            # pawn.console.debug(f"[red]_use_global_reqeust_payload={self._use_global_reqeust_payload}")
        return _tx

    def _force_fill_from_address(self, tx=None):
        _tx = self.parse_tx_var(tx)
        if not isinstance(_tx, dict):
            pawn.console.debug(f"tx is not dict, tx={tx}, _tx={_tx}, request_payload = {self.request_payload}")
            exit()

        if self.wallet and self.wallet.get('address'):
            _tx['params']['from'] = self.wallet.get('address')
        else:
            self.exit_on_failure(exception="Not found 'from address'. Not defined wallet")
        return _tx

    def auto_fill_parameter(self, tx=None, is_force_from_addr=False):
        _tx = self.parse_tx_var(tx)
        if isinstance(_tx, dict) and _tx.get('params'):
            if not _tx['params'].get('from') or is_force_from_addr:
                self._force_fill_from_address()
            if not _tx['params'].get('nonce'):
                _tx['params']['nonce'] = "0x1"

            if not _tx['params'].get('version'):
                _tx['params']['version'] = "0x3"

            if not _tx['params'].get('timestamp'):
                _tx['params']['timestamp'] = hex(icx_signer.get_timestamp_us())

            if not _tx['params'].get('nid') and self.network_info and self.network_info.nid:
                _tx['params']['nid'] = self.network_info.nid
        else:
            self.exit_on_failure(f"Invalid payload => {_tx}")

        if self._use_global_reqeust_payload:
            self.request_payload = _tx
        return _tx

    def auto_fill_step_limit(self, tx=None, step_limit=None):
        _tx = self.parse_tx_var(tx)
        if isinstance(_tx, dict) and _tx.get('params'):
            if step_limit:
                if not is_hex(step_limit):
                    pawn.console.debug(f"Converting step limit to hex {step_limit}=>{hex(int(step_limit))}")
                    step_limit = hex(int(step_limit))

                _tx['params']['stepLimit'] = step_limit
            elif not _tx['params'].get('stepLimit'):
                _tx['params']['stepLimit'] = self.get_step_limit()
        else:
            self.exit_on_failure(f"Invalid payload => {_tx}")

    def sign_tx(self, wallet=None, payload=None, check_balance=True, step_limit=None):
        self.request_payload = {}
        self.signed_tx = {}
        if wallet:
            self.wallet = wallet

        if not self.wallet or not isinstance(self.wallet, dict):
            self.exit_on_failure(f"[red] Not defined wallet => {self.wallet}")

        if not payload and self.global_reqeust_payload:
            pawn.console.debug("Use global_reqeust_payload")
            payload = self.global_reqeust_payload

        self.request_payload = self._convert_valid_payload_format(payload=payload)
        private_key = self.wallet.get('private_key')
        address = self.wallet.get('address')

        if check_balance:
            _balance = self.get_balance()
            if self.network_info:
                symbol = self.network_info.symbol
            else:
                symbol = ""
            pawn.console.log(f"<{address}>'s Balance = {_balance} {symbol}")

            if not _balance or _balance == 0:
                return self.exit_on_failure(f"<{address}> Out of Balance = {_balance} {symbol}")
        self.auto_fill_parameter(is_force_from_addr=True)
        self.auto_fill_step_limit(step_limit=step_limit)

        singer = icx_signer.IcxSigner(data=private_key)
        self.signed_tx = singer.sign_tx(self.request_payload)

        if address != singer.get_hx_address():
            self.exit_on_failure(f'Invalid address {address} != {singer.get_hx_address()}')

        self.global_reqeust_payload = {}
        return self.signed_tx

    def exit_on_failure(self, exception, force_exit=False):
        self.on_error = True
        if self.raise_on_failure:
            raise NoTraceBackException(exception)
        else:
            pawn.console.log(f"[red][FAIL][/red] Stopped {get_debug_here_info().get('function_name')}(), {exception}")
            if force_exit:
                sys_exit()
        return exception

    def sign_send(self, is_wait=True, is_compact=False):
        if self.signed_tx:
            response = self.rpc_call(payload=self.signed_tx, print_error=True)
            if not is_wait:
                return response

            if isinstance(response, dict) and response.get('result'):
                resp = self.get_tx_wait(tx_hash=response['result'], is_compact=is_compact)
                return resp
        else:
            self.exit_on_failure(f"Required signed transaction")

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
                pawn.console.debug(f"get_operator_truth(target={self.target}, {self.operator}, expected={self.expected}) = {self.result}")
            except:
                self.result = False

    def _set_string_valid_type(self, ):
        _debug_message = ""
        for var_name in ["target", "expected"]:
            _attr_value_in_class = getattr(self, var_name, "__NOT_NONE__")
            if _attr_value_in_class != "__NOT_NONE__":
                if isinstance(_attr_value_in_class, str):
                    if is_int(_attr_value_in_class):
                        setattr(self, var_name, int(_attr_value_in_class))
                    elif is_float(_attr_value_in_class):
                        setattr(self, var_name, float(_attr_value_in_class))

                _modified_value = getattr(self, var_name)
                _debug_message += f"{var_name} = {_modified_value} ({type(_modified_value)}) , "

        # pawn.console.debug(_debug_message)

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
    SHORTEN_MESSAGE_DICT = {
        requests.exceptions.Timeout: {
            "message": "Timeout Error",
            "params_message": "timeout={}"
        },
        requests.exceptions.HTTPError: "HTTP Error",
        requests.exceptions.ConnectionError: "DNS lookup Error",
        requests.exceptions.RequestException: "OOps: Something Else",
    }

    def __init__(self,
                 url=None,
                 method: Literal["get", "post", "patch", "delete"] = "get",
                 # method: Literal[AllowsHttpMethod.get] = "get",
                 # method: AllowsHttpMethod = AllowsHttpMethod.get,
                 # method: Literal[tuple(method for method in AllowsHttpMethod)],
                 payload={},
                 timeout=3000,
                 ignore_ssl: bool = False,
                 verbose: int = 0,
                 success_criteria: Union[dict, list, str, None] = "__DEFAULT__",
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

        _default_criteria = [AllowsKey.status_code, "<=", 399]
        if success_criteria == '__DEFAULT__':
            self.success_criteria = _default_criteria
        elif success_criteria:
            self.success_criteria = success_criteria
        else:
            self.success_criteria = None

        self.success_operator = success_operator
        self.success_syntax = success_syntax
        self.kwargs = kwargs
        self.raise_on_failure = raise_on_failure
        self._DEFAULT_UA = f"CallHttp Agent/{pawn.get('PAWN_VERSION')}"
        self.on_error = False
        # self.response = requests.models.Response()
        self.response = HttpResponse()
        self.flat_response = None

        self.success = None
        self._success_results = []
        self._success_criteria = None
        self.timing = 0
        # self.run()

    def _shorten_exception_message_handler(self, exception):
        default_msg = f"(url={self.url} method={self.method.upper()}"
        for req_exception, values in self.SHORTEN_MESSAGE_DICT.items():
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
            raise NoTraceBackException(exception)
        else:
            pawn.console.debug(f"[red][FAIL][/red] {exception}")
            # self.response.status_code = 999
            # self.response.success = False
            # self.response.error = self._shorten_exception_message_handler(exception)
            # print(self.timing)
            return self.response

    def run(self):
        self._prepare()
        start = time.perf_counter()
        self.fetch_response()
        end = time.perf_counter()
        self.timing = int((end - start) * 1000)
        self._parse_response()
        self.fetch_criteria()
        self.response.success = self.is_success()

        if not self.is_success() and getattr(self.response, 'reason', ''):
            self.response.error = f"{self.response.status_code} {self.response.reason}"

        return self

    def _prepare(self):
        self.url = append_http(self.url)

    def get_response(self) -> HttpResponse:
        return self.response

    def fetch_response(self):
        (json_response, data, http_version, r_headers, error) = ({}, {}, None, None, None)
        if self.method not in ("get", "post", "patch", "delete"):
            pawn.error_logger.error(f"unsupported method='{self.method}', url='{self.url}' ") if pawn.error_logger else False
            return self.exit_on_failure(f"Unsupported method={self.method}, url={self.url}")
        try:
            try:
                _payload_string = json.dumps(self.payload)
            except Exception as e:
                _payload_string = self.payload
            pawn.console.debug(f"[TRY] url={self.url}, method={self.method.upper()}, kwargs={self.kwargs}")
            if pawn.get("PAWN_DEBUG"):
                print_json(_payload_string)

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
            if self.timing:
                _elapsed = self.timing
            else:
                _elapsed = 0
        self.response.elapsed = _elapsed

        if getattr(self.response, 'raw', None):
            self.response.http_version = self.response.raw.version
        else:
            self.response.http_version = ""
        if self.response and not self.on_error:
            try:
                self.response.result = self.response.json()
            except:
                self.response.result = self.response.text

    def fetch_criteria(self,
                       success_criteria: Union[dict, list] = None,
                       success_operator: Literal["and", "or"] = "and",
                       ):
        _response_dict = self.response.as_dict()

        if success_criteria:
            self.success_criteria = success_criteria
        if success_operator:
            self.success_operator = success_operator

        if not self.success_criteria:
            pawn.console.debug("passing success_criteria")
        else:
            if self.success_syntax == "string" or self.success_syntax == "auto":
                _check_syntax = self._check_criteria_syntax()
                if _check_syntax:
                    pawn.console.debug(f"[blue]Try to convert[/blue] {type(self.success_criteria)}, _check_criteria_syntax={_check_syntax}")
                    self._recursive_convert_criteria()

            depth = list_depth(self.success_criteria)
            if depth == 1:
                self.success_criteria = [self.success_criteria]

            for criteria in self.success_criteria:
                # pawn.console.debug(f"Compare Criteria => {type(criteria)} {criteria}")
                if isinstance(criteria, list):
                    _criteria = copy.deepcopy(criteria)
                    _criteria.append(_response_dict)
                    self._success_results.append(SuccessResponse(*_criteria))
                elif isinstance(criteria, dict):
                    criteria['target'] = _response_dict
                    self._success_results.append(SuccessResponse(**criteria))
            # pawn.console.debug(self._success_results)

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


class CheckSSL:

    def __init__(self, host=None, timeout: float = 5.0, port: int = 443, raw_data=False):
        self._host = host
        self._timeout = timeout
        self._port = port
        self.ssl_info = None
        self._now = datetime.now()
        self._raw_data = raw_data
        self.ssl_dateformat = r'%b %d %H:%M:%S %Y %Z'
        self.get_ssl()
        self.ssl_result = {}

    def get_ssl(self):
        context = ssl.create_default_context()
        context.check_hostname = False

        conn = context.wrap_socket(
            socket.socket(socket.AF_INET),
            server_hostname=self._host,
        )
        conn.settimeout(self._timeout)
        conn.connect((self._host, self._port))
        conn.do_handshake()
        self.ssl_info = conn.getpeercert()
        self._parse_ssl_info()
        conn.close()
        return self.ssl_info

    def _parse_ssl_info(self):
        expire_date = self.ssl_expiry_datetime()
        diff = expire_date - datetime.now()
        self._calculated_date = {
            "expire_date": expire_date.strftime("%Y-%m-%d"),
            "left_days": diff.days
        }
        self.ssl_info.update(self._calculated_date)
        if not self._raw_data:
            _tmp_ssl_info = {}
            _to_dict_keys = ["subject", "issuer"]
            _to_list_keys = ["subjectAltName"]

            for key, value in self.ssl_info.items():
                if key in _to_dict_keys:
                    self.ssl_info[key] = self._tuple_to_dict(value)
                elif key in _to_list_keys:
                    print(f"key={key}, value={value}")
                    self.ssl_info[key] = self._tuple_to_list(value)

    @staticmethod
    def _tuple_to_dict(_tuple=None):
        _tmp_dict = {}
        if isinstance(_tuple, tuple):
            for _data in _tuple:
                _tmp_dict.update(_data)
        return _tmp_dict

    @staticmethod
    def _tuple_to_list(_tuple=None):
        _tmp_dict = {}
        if isinstance(_tuple, tuple):
            for _data in _tuple:
                _key = _data[0]
                _domain = _data[1]
                pawn.console.log(f"[red] _tuple_to_list ={_key}, {_domain}")
                if not _tmp_dict.get(_key):
                    _tmp_dict[_key] = []
                _tmp_dict[_key].append(_domain)
        return _tmp_dict

    def ssl_expiry_datetime(self) -> datetime:
        return datetime.strptime(self.ssl_info['notAfter'], self.ssl_dateformat)

    def analyze_ssl(self):
        api_url = 'https://api.ssllabs.com/api/v3/'
        _do_function = partial(jequest, f"{api_url}/analyze?host={self._host}")
        WaitStateLoop(
            loop_function=_do_function,
            exit_function=self._check_ssl_result,
        ).run()

    def _check_ssl_result(self, result):
        if result.get('json') and result['json'].get('status') == "READY":
            self.ssl_result = result['json']
            pawn.console.log(self.ssl_result)
            return True


class CallWebsocket:

    def __init__(
            self,
            connect_url,
            verbose=0,
            timeout=10,
            send_callback: Callable[..., Any] = None,
            recv_callback: Callable[..., Any] = None,
            use_status_console: bool = False,
    ):
        self.connect_url = connect_url
        self.verbose = verbose
        self.timeout = timeout
        self.send_callback = send_callback
        self.recv_callback = recv_callback

        self.ws_url = append_ws(connect_url)
        self.http_url = append_http(connect_url)
        self.status_console = Null()
        self._use_status_console = use_status_console

        self._ws = None

        if self.verbose > 3:
            enableTrace(True)

    def connect_websocket(self, api_url=""):
        self._ws = create_connection(f"{self.ws_url}/{api_url}", timeout=self.timeout, sslopt={"cert_reqs": ssl.CERT_NONE})
        self._ws.settimeout(self.timeout)

    def run(self, api_url="api/v3/icon_dex/block", status_console=False):
        self.connect_websocket(api_url)
        if self._use_status_console or status_console:
            with pawn.console.status("Call WebSocket") as self.status_console:
                self.send_recv_callback()
        else:
            self.send_recv_callback()

    def send_recv_callback(self):
        if callable(self.send_callback):
            self._ws.send(self.send_callback())

        while True:
            response = self._ws.recv()
            if callable(self.recv_callback):
                self.recv_callback(response)


class GoloopWebsocket(CallWebsocket):

    def __init__(self,
                 connect_url,
                 verbose=0,
                 timeout=10,
                 blockheight=0,
                 sec_thresholds=4,
                 monitoring_target=None,
                 ignore_ssl=True,
                 ):

        self.connect_url = connect_url
        self.verbose = verbose
        self.timeout = timeout
        self.blockheight = blockheight
        self.sec_thresholds = sec_thresholds
        self.monitoring_target = monitoring_target
        if self.monitoring_target is None:
            self.monitoring_target = ["block"]

        self.compare_diff_time = {}
        self.delay_cnt = {}

        self.block_timestamp_prev = 0
        self.block_timestamp = None
        self.tx_count = 0
        self.tx_timestamp = 0
        self.tx_timestamp_dt = None

        self.blockheight_now = 0

        if ignore_ssl:
            disable_ssl_warnings()

        if self.verbose > 0:
            use_status_console = True
        else:
            use_status_console = False

        super().__init__(
            connect_url=self.connect_url,
            verbose=self.verbose,
            timeout=self.timeout,
            send_callback=self.request_blockheight_callback,
            recv_callback=self.parse_blockheight,
            use_status_console=use_status_console
        )

    def request_blockheight_callback(self):
        if self.blockheight == 0:
            self.blockheight = self.get_last_blockheight()
        pawn.console.log(f"Call request_blockheight_callback - blockheight: {self.blockheight:,}")
        send_data = {
            "height": hex(self.blockheight)
        }
        return json.dumps(send_data)

    def parse_blockheight(self, response=None):
        response_json = json.loads(response)
        self.compare_diff_time = {}

        if response_json and response_json.get('hash'):
            hash_result = self.get_block_hash(response_json.get('hash'))
            self.blockheight_now = hash_result.get("height")
            pawn.set(LAST_EXECUTE_POINT=self.blockheight_now)
            self.block_timestamp = hash_result.get("time_stamp")

            _message = f"[bold][📦 {self.blockheight_now:,}][/bold] 📅 {date_utils.timestamp_to_string(self.block_timestamp)}, tx_hash: {hash_result.get('block_hash')}"
            pawn.console.debug(_message)
            self.status_console.update(_message)

            if self.block_timestamp_prev != 0:
                self.compare_diff_time['block'] = abs(self.block_timestamp_prev - self.block_timestamp)

            tx_list = hash_result.get('confirmed_transaction_list')
            self.tx_count = len(tx_list)

            for tx in tx_list:
                self.tx_timestamp = int(tx.get("timestamp", "0x0"), 0)  # 16진수, timestamp가 string이여야한다.
                if self.tx_timestamp:
                    self.compare_diff_time['tx'] = abs(self.block_timestamp - self.tx_timestamp)

                for target in self.monitoring_target:
                    diff_time = self.compare_diff_time.get(target, 0) / 1_000_000
                    if diff_time != 0 and abs(diff_time) > self.sec_thresholds:
                        pawn.console.log(f"[{target.upper():^5}] {self.output_format(key_string=target, diff_time=diff_time, is_string=True)}")
                        if self.verbose > 2:
                            dump(hash_result['confirmed_transaction_list'])
            self.block_timestamp_prev = self.block_timestamp

        else:
            pawn.console.log(response_json)

    def output_format(self, key_string="", diff_time=0, is_string=False):
        self.delay_cnt[key_string] = self.delay_cnt.get(key_string, 0) + 1

        blockheight_date = date_utils.timestamp_to_string(self.block_timestamp)
        if key_string == "block":
            diff_message = f"BH_time(now): {blockheight_date}, " \
                           f"BH_time(prev): {date_utils.timestamp_to_string(self.block_timestamp_prev)}"
        else:
            diff_message = f"BH_time: {blockheight_date}, TX_time: {date_utils.timestamp_to_string(self.tx_timestamp)}"

        result = (f"<{self.delay_cnt[key_string]}> [{key_string} Delay][{date_utils.second_to_dayhhmm(diff_time)}] ",
                  f"BH: {self.blockheight_now}, "
                  # f"diff: {date_utils.second_to_dayhhmm(diff_time)}, "
                  f"TX_CNT:{self.tx_count}, {diff_message}")
        if is_string:
            return "".join(result)
        return result

    def get_last_blockheight(self):
        res = jequest(method="post", url=f"{self.http_url}/api/v3", data=generate_json_rpc(method="icx_getLastBlock"))
        pawn.console.log(res['json'].get('result'))
        if res['json'].get('result'):
            return res['json']['result'].get('height')

    def get_block_hash(self, hash):
        res = jequest(
            method="post",
            url=f"{self.http_url}/api/v3",
            data=generate_json_rpc(method="icx_getBlockByHash", params={"hash": hash})
        )
        if res.get('json'):
            return res['json'].get('result')
        else:
            pawn.console.log(f"[red] {res}")


def gen_rpc_params(method=None, params=None):
    default_rpc = {
        "jsonrpc": "2.0",
        "id": 1234,
        "method": method,
    }

    if params:
        default_rpc['params'] = params
    return default_rpc


def getBlockByHash(nodeHost, hash):
    url = append_http(f"{nodeHost}/api/v3")
    data = gen_rpc_params(method="icx_getBlockByHash", params={"hash": hash})
    response = requests.post(url=url, data=json.dumps(data), timeout=10, verify=False)
    return response.json()


def getTransactionByHash(nodeHost, hash):
    url = append_http(f"{nodeHost}/api/v3")
    data = gen_rpc_params(method="icx_getTransactionByHash", params={"txHash": hash})
    response = requests.post(url=url, data=json.dumps(data), timeout=10, verify=False)
    return response.json()


def getLastBlock(nodeHost):
    url = append_http(f"{nodeHost}/api/v3")
    data = gen_rpc_params(method="icx_getLastBlock")
    response = requests.post(url=url, data=json.dumps(data), timeout=10, verify=False)

    if response.status_code == 200:
        json_res = response.json()
        if json_res.get("result"):
            return json_res["result"]["height"]
    else:
        print(response)
        sys.exit()
    return 0


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
            kvPrint("Http Error:", errh)
        pawn.error_logger.error(f"Http Error:{errh}") if pawn.error_logger else False

    except requests.exceptions.ConnectionError as errc:
        error = errc
        if ("[Errno 11001] getaddrinfo failed" in str(errc) or  # Windows
                "[Errno -2] Name or service not known" in str(errc) or  # Linux
                "[Errno 8] nodename nor servname " in str(errc)):  # OS X
            errc = "DNSLookupError"
        if global_verbose > 0:
            kvPrint("Error Connecting:", errc, "FAIL")
        pawn.error_logger.error(f"Error Connecting:{errc}, {url}") if pawn.error_logger else False

    except requests.exceptions.Timeout as errt:
        error = errt
        if global_verbose > 0:
            kvPrint("Timeout Error:", errt, "FAIL")
        pawn.error_logger.error(f"Timeout Connecting:{errt}, {url}") if pawn.error_logger else False

    except requests.exceptions.RequestException as err:
        error = err
        if global_verbose > 0:
            kvPrint("OOps: Something Else", err, "FAIL")
        pawn.error_logger.error(f"OOps: Something Else:{err}, {url}") if pawn.error_logger else False

    # cprint(f"----> {url}, {method}, {payload} , {response.status_code}", "green")

    try:
        response_code = response.status_code
    except:
        response_code = 999

    json_payload = json.dumps(payload)
    if global_verbose > 1:
        debug_logging(f"{url}, {method}, {json_payload} , {response_code}")

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
