import re
import json
import sys
import socket
import logging
import ssl
import os
from functools import partial
from datetime import datetime
import httpx
from pawnlib.exceptions.notifier import notify_exception

from pawnlib.config.globalconfig import pawnlib_config as pawn, global_verbose, pconf, SimpleNamespace, Null
from pawnlib.config.logging_config import ConsoleLoggerAdapter, setup_logger, LoggerMixin, LoggerMixinVerbose
from pawnlib.output import (
    NoTraceBackException,
    dump, syntax_highlight, kvPrint, debug_logging,
    PrintRichTable, get_debug_here_info, print_syntax,
    print_json,
    pretty_json, align_text, get_file_extension, is_directory, is_file, print_var, print_var2, print_grid
    )
from pawnlib.resource import net
from pawnlib.typing import (
    append_suffix, append_prefix, hex_to_number, FlatDict, Flattener, shorten_text, StackList,
    replace_path_with_suffix, format_text, format_link, list_to_dict_by_key,
    get_shortened_tx_hash, date_utils, HexConverter, json_rpc, random_token_address, generate_json_rpc,
    keys_exists, is_int, is_float, list_depth, is_valid_token_address, sys_exit, is_hex, is_valid_tx_hash, check_key_and_type,
    convert_bytes, const,
)
from pawnlib.utils.operate_handler import WaitStateLoop
from pawnlib.utils.in_memory_zip import gen_deploy_data_content
from websocket import create_connection, WebSocket, enableTrace
from websocket._exceptions import WebSocketConnectionClosedException
from pawnlib.models.response import HexValue, HexTintValue, HexValueParser, HttpResponse, HTTPStatus, ResponseWithElapsed

try:
    from pawnlib.utils import icx_signer
except ImportError:
    pass

from typing import Any, Dict, Iterator, Tuple, Union, Callable, Type, Optional, List, Awaitable, TypeVar
try:
    from typing import Literal  # Python 3.8+
except ImportError:
    from typing_extensions import Literal  # Python 3.7 and below

from enum import Enum, auto
import copy
import operator as _operator
import time
from dataclasses import dataclass, InitVar, field
import requests
from rich.prompt import Prompt, Confirm
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
import asyncio
import aiohttp
from urllib.parse import urlparse
from decimal import Decimal
import atexit
import warnings
from random import uniform
from requests.auth import HTTPBasicAuth
from requests.exceptions import SSLError, RequestException
import dns.resolver
import json


ALLOWS_HTTP_METHOD = const.HTTPMethodConstants.get_http_methods(lowercase=True)
ALLOW_OPERATOR = const.ALLOW_OPERATOR

requests.models.Response.__str__ = ResponseWithElapsed.__str__
requests.models.Response.__repr__ = ResponseWithElapsed.__repr__
requests.models.Response.error = ResponseWithElapsed.error
requests.models.Response.success = ResponseWithElapsed.success
requests.models.Response.as_dict = ResponseWithElapsed.as_dict
requests.models.Response.as_simple_dict = ResponseWithElapsed.as_simple_dict

_ACTIVE_SESSIONS = set()
def _force_close_sessions():
    """Forcefully closes open sessions upon program exit."""
    if not _ACTIVE_SESSIONS:
        return
    
    # Handle quietly instead of printing warning messages
    warnings.filterwarnings("ignore", category=ResourceWarning)
    
    for session in _ACTIVE_SESSIONS:
        if hasattr(session, 'connector') and hasattr(session.connector, '_close'):
            session.connector._close()
    _ACTIVE_SESSIONS.clear()

atexit.register(_force_close_sessions)


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
    response_time= auto()


@dataclass
class NetworkInfo:
    network_name: str = ""
    platform: str = "icon"
    force: bool = False
    network_api: str = ""
    planet_api: str = ""
    nid: str = ""
    network: str = ""
    endpoint: str = ""
    tracker: str = ""
    symbol: str = ""
    valid_network: bool = False

    MANDATORY_KEYS = ["platform", "nid"]
    STATIC_VALUES = ["nid", "network_api", "endpoint"]

    def __post_init__(self):

        self._platform_info = {
            "icon": {
                "symbol": "ICX",
                "network_info": {
                    "mainnet": {
                        "network_api": "https://ctz.solidwallet.io",
                        "nid": "0x1",
                        "tracker": "https://tracker.icon.community",
                    },
                    "lisbon": {
                        "network_api": "https://lisbon.net.solidwallet.io",
                        "nid": "0x2",
                        "tracker": "https://tracker.lisbon.icon.community",
                    },
                    "techteam": {
                        "network_api": "https://techteam.net.solidwallet.io",
                        "nid": "0xa"
                    },
                    "berlin": {
                        "network_api": "https://berlin.net.solidwallet.io",
                        "nid": "0x7",
                        "tracker": "https://tracker.lisbon.icon.community"
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
        self.network_info = {}
        if not self.force:
            self._initialize()

    def is_set_static_values(self):
        return any(getattr(self, static_value, None) for static_value in self.STATIC_VALUES)

    def _get_network_info(self, network_name: str = "", platform: str = ""):
        """
        Retrieves network information based on the network name and platform.

        Args:
            network_name (str): The name of the network (e.g., 'mainnet', 'vega').
            platform (str): The platform name (e.g., 'icon', 'havah').

        Raises:
            ValueError: If the platform or network is invalid and 'force' is not enabled.
        """
        self.network_name = network_name.lower() if network_name else self.network_name.lower()
        self.platform = platform.lower() if platform else self.platform.lower()

        alias_map = {"veganet": "vega", "denebnet": "deneb"}
        self.network_name = alias_map.get(self.network_name, self.network_name)

        platform_info = self._platform_info.get(self.platform)
        if not platform_info:
            if not self.force:
                allowed_platforms = list(self._platform_info.keys())
                raise ValueError(f"Invalid platform '{self.platform}'. Allowed platforms: {allowed_platforms}")
            else:
                self.network_info = {}
                return

        network_info = platform_info.get('network_info', {})
        if not self.is_set_static_values():
            if self.network_name not in network_info:
                if not self.force:
                    allowed_networks = list(network_info.keys())
                    raise ValueError(f"Invalid network '{self.network_name}' for platform '{self.platform}'. "
                                     f"Allowed networks: {allowed_networks}")
            else:
                self.network_info = network_info.get(self.network_name, {})

        self.symbol = platform_info.get('symbol', "")
        if self.network_info:
            self.valid_network = True
            self.network_info.update({
                'symbol': self.symbol,
                'network_name': self.network_name,
                'platform': self.platform,
            })
        else:
            self.network_info = self._extract_network_info()

        if not self.network_info.get('endpoint') and self.network_info.get('network_api'):
            self.network_info['network_api'] = append_http(self.network_info['network_api'])
            self.network_info['endpoint'] = replace_path_with_suffix(self.network_info['network_api'], "/api/v3")

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
            self.reset_static_values()
            self._initialize(network_name=network_name, platform=platform)

    def reset_static_values(self):
        for static_value in self.STATIC_VALUES:
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
        return []

    def tuple(self) -> tuple:
        return tuple(self.network_info.keys())

    def to_dict(self):
        if self.network_info:
            return self.network_info
        return self.network_info

    def find_network_by_platform_and_nid(self, platform: str, nid: str):
        """
        Find network and endpoint information based on platform and nid.

        Args:
            platform (str): The platform name (e.g., 'icon', 'havah').
            nid (str): The network ID in hexadecimal format (e.g., '0x1').

        Returns:
            dict: Network information including endpoint, network_api, and tracker.

        Raises:
            ValueError: If the platform or nid is not found in the platform info.
        """
        platform_info = self._platform_info.get(platform.lower())
        if not platform_info:
            raise ValueError(f"Platform '{platform}' is not found. Available platforms: {list(self._platform_info.keys())}")

        network_info = platform_info.get("network_info", {})
        for network_name, network_details in network_info.items():
            if network_details.get("nid") == nid:
                endpoint = network_details.get("endpoint") or replace_path_with_suffix(
                    append_http(network_details.get("network_api", "")), "/api/v3"
                )
                return {
                    "platform": platform,
                    "network_name": network_name,
                    "nid": nid,
                    "endpoint": endpoint,
                    "network_api": network_details.get("network_api"),
                    "tracker": network_details.get("tracker"),
                }

        raise ValueError(f"NID '{nid}' is not found for platform '{platform}'. Available NIDs: {[info.get('nid') for info in network_info.values()]}")

    def fetch_network_info(self):
        if not self.network_api:
            pawn.console.log("[red]Error:[/red] 'network_api' is not set. Cannot fetch network information.")
            return

        if self.network_api:
            try:
                pawn.console.debug("Try fetching network info")
                api_url = append_http(append_api_v3(self.network_api))
                result = IconRpcHelper().rpc_call(url=api_url, method="icx_getNetworkInfo", return_key="result")

                if not result:
                    pawn.console.log("[red]Error:[/red] Received an empty response from icx_getNetworkInfo API.")
                    return

                for key in self.MANDATORY_KEYS:
                    self.__dict__[key] = result[key]
                platform_info = self._platform_info.get(self.platform, {})
                self.symbol = platform_info.get('symbol', 'Unknown')
                _network_api = append_http(self.network_api)
                self.network_api = _network_api
                self.endpoint = replace_path_with_suffix(_network_api, "/api/v3")
                self.valid_network = True
                pawn.console.debug("Successfully fetched and updated network info.")

            except KeyError as e:
                pawn.console.log(f"[red]KeyError:[/red] Missing key in result: {e}")
            except Exception as e:
                pawn.console.log(f"[red]Exception occurred while fetching network info:[/red] {e}")

    def _extract_network_info(self):
        mandatory_keys = ["platform", "network_api", "nid"]
        if not self.nid:
            self.fetch_network_info()
        _static_network_info = {
            key: value for key, value in copy.deepcopy(self.__dict__).items()
            if (key and value and key not in ['_platform_info', 'static_values', 'network_info']) or key in mandatory_keys
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
        self._params_hint = {}
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

        if isinstance(self.return_rpc, dict) and self.return_rpc.get('method') == "icx_sendTransaction":
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

    def get_rpc(self, category=None, method=None, params=None):
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
                if _arguments.get('params_hint', "__NOT_DEFINED__") != "__NOT_DEFINED__":
                    self._params_hint = _arguments['params_hint']
                    del _arguments['params_hint']

                if params and _arguments.get('params') and _arguments['params'].get('data'):
                    try:
                        _arguments['params']['data']['params'] = json.loads(params)
                    except Exception as e:
                        sys_exit(f"Params error {params} => {e}")


                self.return_rpc = json_rpc(**_arguments)
            else:
                self._method = _arguments.get('method', self._method)
                if params:
                    try:
                        self._params = json.loads(params)
                    except Exception as e:
                        sys_exit(f"Params error {params} => {e}")
                else:
                    self._params = _arguments.get('params', {})
                self.return_rpc = json_rpc(method=self._method, params=self._params)

            return self.return_rpc
        return {}

    def get_required_params(self):
        return self._params

    def get_params_hint(self):
        return self._params_hint


class IconRpcHelper(LoggerMixinVerbose):
    def __init__(self, url="", wallet=None, network_info: NetworkInfo = None, raise_on_failure=True, debug=False,
                 required_sign_methods=None, wait_sleep=1, tx_method="icx_getTransactionResult", logger=None,
                 margin_steps=0, verbose=0, use_hex_value=False, **kwargs):
        self.wallet = wallet
        self.governance_address = None
        self.request_payload = None
        self.response = None
        self.network_info = network_info
        self.raise_on_failure = raise_on_failure
        self.debug = debug
        self.wait_sleep = wait_sleep
        self.tx_method = tx_method

        # self.logger = setup_logger(logger, "IconRpcHelper", verbose)
        # self.logger = self.get_logger()

        # super().__init__()

        self.init_logger(logger=logger, verbose=verbose)

        # print_var(self.logger)

        self.margin_steps = margin_steps
        self.use_hex_value = use_hex_value
        self.kwargs = kwargs

        self.logger.info("Start IconRpcHelper")
        if required_sign_methods and isinstance(required_sign_methods, list):
            self.required_sign_methods = required_sign_methods
        else:
            self.required_sign_methods = ["set", "register", "unregister", "claim", "vote", "apply", "remove", "cancel", "acceptScore", "reject"]

        if not url and self.network_info:
            url = self.network_info.network_api

        self.url = replace_path_with_suffix(url, "/api/v3")
        self.debug_url = replace_path_with_suffix(url, "/api/v3d")
        self.signed_tx = {}
        self._parent_method = ""
        self._can_be_signed = None
        self.on_error = False
        self.initialize()
        self._use_global_request_payload = False
        self.global_request_payload = {}
        self.score_api = {}
        self.elapsed_stack = StackList(max_length=100)
        self.timing_stack = StackList(max_length=100)
        self.start_time = time.time()
        self.end_time = 0

        self.default = {
            "stepLimit": hex(2500000)
        }

    def set_use_hex_value(self, value):
        if isinstance(value, bool):
            self.use_hex_value = value
            # Additional logic can be added here (e.g., logging)
        else:
            raise ValueError("use_hex_value must be a boolean.")

    def test_logger(self):
        self.logger.info("test_logger")

    def initialize(self):
        self._set_governance_address()
        if self.network_info:
            pawn.console.debug(self.network_info)
        else:
            pawn.console.debug("Not found network_info")

        self.initialize_wallet()

    def initialize_wallet(self, wallet=None):
        if wallet:
            self.wallet = wallet

        if self.wallet and not isinstance(self.wallet, dict):
            pawn.console.debug("Loading wallet from icx_signer.load_wallet_key()")
            self.wallet = icx_signer.load_wallet_key(self.wallet)

    def get_wallet_address(self, wallet=None):
        if wallet:
            return icx_signer.load_wallet_key(wallet).get('address')
        return self.wallet.get('address')

    def _set_governance_address(self, method=None):
        if self.network_info and not self.governance_address:
            if self.network_info.platform == "havah" and method and method.startswith("get"):
                self.governance_address = const.CHAIN_SCORE_ADDRESS
            else:
                self.governance_address = const.GOVERNANCE_ADDRESS

        # If governance_address is still not set, default to GOVERNANCE_ADDRESS
        self.governance_address = self.governance_address or const.CHAIN_SCORE_ADDRESS

    def _set_governance_address_with_const(self, method):
        rpc_api_methods = {}
        if self.network_info.platform == "havah":
            rpc_api_methods = const.HAVAH_METHODS
        elif self.network_info.platform == "icon":
            rpc_api_methods = const.ICON_METHODS

        if rpc_api_methods:
            for score_address, score_methods in rpc_api_methods.items():
                if method in score_methods:
                    self.governance_address = score_address

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
                 return_key=None,
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

        # pawn.console.log(self.response.get('elapsed'), self.response.get('timing'))
        self.elapsed_stack.push(self.response.get('elapsed'))
        self.timing_stack.push(self.response.get('timing'))
        return self.handle_response_with_key(self.response.get('json'), return_key=return_key)

    def get_elapsed(self, mode='elapsed'):
        if mode == "elapsed":
            return self.elapsed_stack
        if mode == "timing":
            return self.timing_stack

    def get_total_elapsed(self):
        return int((time.time() - self.start_time) * 1000)

    def print_error_message(self, print_error=True):
        if print_error:
            if self.response.get('json') and self.response['json'].get('error'):
                pawn.console.log(f"[red][ERROR][/red] payload={self.request_payload}")
                pawn.console.log(f"[red][ERROR] status_code={self.response['status_code']}, error={self.response['json']['error']}")
            elif self.response.get('status_code') == 999:
                pawn.console.log(f"[red][ERROR][/red] {self.response.get('error')}")
                # self.exit_on_failure(f"[red][ERROR][/red] {self.response.get('error')}")
            else:
                pawn.console.log(f"[red][ERROR][/red] url={self.response.get('url')}, status_code={self.response.get('status_code')}, text={self.response.get('text')}")

    def print_response(self, hex_to_int=False, message=""):
        if self.response.get('status_code') != 200:
            style = "red"
        else:
            style = "rule.line"
        pawn.console.rule(f"<Response {self.response.get('status_code')}> {message}", align='right', style=style, characters="═")
        if self.response.get('json'):
            dump(self.response.get('json'), hex_to_int=hex_to_int)
        else:
            print(syntax_highlight(self.response.get('text'), name='html'))

    def print_request(self, message=""):
        pawn.console.print("")
        pawn.console.rule(f"<Request> {self.url} {message}", align='left')
        pawn.console.print("")
        print(syntax_highlight(self.request_payload, line_indent='   '))

    def make_params(self, method=None, params={}):
        json_rpc(
            method=method,
            params=params
        )

    def _is_signable_governance_method(self, method: str) -> bool:
        # if self.network_info.platform == "havah" or self.network_info.platform == "icon" and method:
        if method:
            for required_sign_method in self.required_sign_methods:
                if method.startswith(required_sign_method):
                    pawn.console.debug(f"{method}, It will be signed with the following. required_sign_methods={self.required_sign_methods}")
                    return True
        return False

    def create_governance_payload(self, method, params={}):

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

    def governance_call(self, url=None, method=None, params: dict = {}, governance_address=None,
                        sign=None, store_request_payload=True, is_wait=True, value="0x0", step_limit=None, return_key="result"):
        if governance_address:
            self.governance_address = governance_address
        else:
            self._set_governance_address_with_const(method=method)

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
                return_key=return_key
            )
            return response

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
        pawn.console.debug(f"file_extension={_file_extension}, file_type={_file_type}, content_size={len(_content)}")
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
        self.request_payload = _request_payload
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

    def get_step_cost(self, step_kind="input"):
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
                self.exit_on_failure(f"An error occurred while running 'debug_estimateStep', {res_json['error'].get('message')}, URL={_url}, _tx={_tx}")

            return res.get('result')

        else:
            self.exit_on_failure(f"TX is not dict. tx => {_tx}")

    def get_step_limit(self, url=None, tx=None, step_kind=None):
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

        if not step_kind:
            step_kind = self._guess_step_kind(tx=_tx)
            pawn.console.debug(f"guess step_kind = {step_kind}")

        step_cost = self.get_step_cost(step_kind)
        step_price = self.get_step_price()

        if estimate_step and step_cost:
            # step_limit = hex(hex_to_number(estimate_step) + hex_to_number(step_cost))
            step_limit = hex(hex_to_number(estimate_step)+ hex_to_number(self.margin_steps))
            # step_limit = hex(hex_to_number(estimate_step))
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

    def get_fee(self, tx=None, symbol=False, step_kind=None):
        _tx = self.parse_tx_var(tx)
        if keys_exists(_tx, "params", "stepLimit"):
            del _tx['params']['stepLimit']
        if keys_exists(_tx, "params", "signature"):
            del _tx['params']['signature']
        estimate_step = self.get_estimate_step(tx=_tx)
        if not step_kind:
            step_kind = self._guess_step_kind(tx)
            pawn.console.debug(f"_guess_step_kind = {step_kind}")
        step_cost = self.get_step_cost(step_kind)
        step_price = self.get_step_price()
        step_limit = hex(hex_to_number(estimate_step) + hex_to_number(step_cost))
        fee = hex_to_number(estimate_step) * hex_to_number(step_price) / const.TINT

        if symbol:
            fee = f"{fee} {self.network_info.symbol}"
        pawn.console.debug(f"fee = (estimate_step + step_cost) * step_price = {fee}")
        pawn.console.debug(f"fee = ({estimate_step} + {step_cost}) * {step_price} = {fee}")
        pawn.console.debug(f"step_limit = {step_limit}")
        return fee

    def get_score_api(self, address="", url=None) -> list:
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
            return []
        return response.get('result', [])

    @staticmethod
    def name_to_params(list_data):
        return {data.get('name'): "" for data in list_data}

    @staticmethod
    def make_params_hint(list_data):
        if not list_data:
            return {}
        formatted_data = {}
        for data in list_data:
            name = data.get('name')
            data_type = data.get('type', "")
            default = data.get('default', "")
            formatted_data[name] = f"{default}({data_type})"
        return formatted_data

    def _convert_score_api_to_params(self, data=[], address="", return_method_only=False):
        if return_method_only:
            result = []
        else:
            result = {}

        for _input in data:
            if _input.get('type') != "function":
                continue

            method = "icx_call" if _input.get('readonly') == "0x1" else "icx_sendTransaction"
            score_method = _input.get('name')

            if return_method_only:
                result.append(score_method)
            else:
                result[score_method] = dict(
                    method=method,
                    params=dict(
                        dataType="call",
                        to=address,
                        data=dict(
                            method=score_method,
                            params=self.name_to_params(_input.get('inputs'))
                        )
                    ),
                    params_hint=self.make_params_hint(_input.get('inputs'))
                )

                if method == "icx_sendTransaction" and _input.get('payable') != "0x1":
                    result[score_method]['params']['value'] = "0x0"
            # pawn.console.log(f"{_input.get('type')} {score_method} , {_input.get('inputs')}, {_input.get('readonly')}")
        return result

    def get_governance_api(self, url=None, return_method_only=False):
        self.score_api = {}
        for address in [const.GOVERNANCE_ADDRESS, const.CHAIN_SCORE_ADDRESS]:
            _api_result = self.get_score_api(address=address, url=url)
            if _api_result:
                self.score_api[address] = self._convert_score_api_to_params(_api_result, address=address, return_method_only=return_method_only)

        return self.score_api

    def get_balance(self, url=None, address=None, is_comma=False, is_tint=True, return_as_hex=False, return_as_decimal=False, use_hex_value=None):
        """
        Retrieve the balance of the given address.

        :param url: RPC URL.
        :param address: Address to get the balance for.
        :param is_comma: Whether to format the number with commas.
        :param is_tint: Whether to return as TINT.
        :param return_as_hex: Whether to return the balance in its raw hex form.
        :param return_as_decimal: If True, returns the balance as a floating-point number in ICX.
        :param use_hex_value: If True, returns a HexValue object instead of a raw balance.
        :return: Balance in the requested format.
        """
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

            use_hex_value = use_hex_value or self.use_hex_value

            if use_hex_value:
                return HexValueParser(_balance)

            if return_as_hex:
                return _balance

            balance_number = hex_to_number(_balance, is_comma=is_comma, is_tint=is_tint)

            # If as_float is requested, convert the balance to a float in ICX (from wei)
            if return_as_decimal:
                balance_float = Decimal(balance_number)
                return balance_float
            return balance_number
        else:
            return self.exit_on_failure(f"Invalid token address - {address}")

    def analyze_tx_block_time(self, transaction):
        tx_timestamp = int(transaction['timestamp'], 16)
        block_height = transaction['blockHeight']
        block_timestamp = self.get_block(block_height, return_key="result.time_stamp")

        # pawn.console.log(f"diff_time={(tx_timestamp-block_timestamp)/1_000_000}")
        elapsed_time = (tx_timestamp-block_timestamp)/1_000_000

        return {
            # "tx_hash": tx_hash,
            "tx_timestamp": tx_timestamp,
            "block_height": block_height,
            "block_timestamp": block_timestamp,
            "elapsed_time": elapsed_time
        }

    def get_block(self, block_height=None, return_key=None):
        if not block_height:
            self.exit_on_failure("Required block_height for get_block()")

        if is_int(block_height):
            _block_height = hex(block_height)
        elif is_hex(block_height):
            _block_height = block_height

        response = self.rpc_call(
            method="icx_getBlockByHeight",
            params={"height": _block_height}
        )

        if isinstance(response, dict):
            if return_key:
                return FlatDict(response).get(return_key)
            return response
        return response.get('text')

    def get_stake(self, address=None, return_as_hex=False, return_key="result.stake", use_hex_value=None):
        if not address:
            address = self.wallet.get('address')

        return_value = self.governance_call(
            method="getStake",
            params={"address": address},
            return_key=return_key
        )

        use_hex_value = use_hex_value or self.use_hex_value
        if use_hex_value:
            return HexValueParser(return_value)

        if return_as_hex:
            return return_value
        return hex_to_number(return_value, is_tint=True)

    def get_bond(self, address=None, return_as_hex=False, return_key="result.bonds", use_hex_value=None)-> list:
        if not address:
            address = self.wallet.get('address')

        return_value = self.governance_call(
            method="getBond",
            params={"address": address},
            return_key=return_key
        )

        use_hex_value = use_hex_value or self.use_hex_value
        if use_hex_value:
            return HexValueParser(return_value)

        if return_as_hex:
            return return_value
        return hex_to_number(return_value, is_tint=True)

    def get_delegation(self, address=None, return_as_hex=False, return_key="result.delegations", use_hex_value=None):
        if not address:
            address = self.wallet.get('address')

        return_value = self.governance_call(
            method="getDelegation",
            params={"address": address},
            return_key=return_key
        )

        use_hex_value = use_hex_value or self.use_hex_value
        if use_hex_value:
            return HexValueParser(return_value)

        if return_as_hex:
            return return_value
        return hex_to_number(return_value, is_tint=True)

    def get_iscore(self, address=None, return_as_hex=False, return_key="result.estimatedICX", use_hex_value=None):
        if not address:
            address = self.wallet.get('address')

        return_value = self.governance_call(
            method="queryIScore",
            params={"address": address},
            return_key=return_key
        )

        use_hex_value = use_hex_value or self.use_hex_value
        if use_hex_value:
            return HexValueParser(return_value)

        if return_as_hex:
            return return_value
        return hex_to_number(return_value, is_tint=True)

    def claim_iscore(self, url=None, step_limit=None, is_wait=True, return_key="result"):
        _response = self.governance_call(url, method="claimIScore", sign=True, step_limit=step_limit, is_wait=is_wait)
        response = self.handle_response_with_key(response=_response, return_key=return_key)
        return response

    def unjail(self, url=None, step_limit=None, is_wait=True,  return_key="result"):
        _response = self.governance_call(url, method="requestUnjail", sign=True, step_limit=step_limit, is_wait=is_wait)
        response = self.handle_response_with_key(response=_response, return_key=return_key)
        return response

    def handle_response_with_key(self, response=None, return_key=None):
        if response is None:
            response = self.response
        if isinstance(response, dict):
            if return_key and response:
                return FlatDict(response).get(return_key)
            return response
        return response.get('text')

    def get_tx(self,  tx_hash=None, url=None,  return_key=None, use_hex_value=None):
        if not tx_hash:
            tx_hash = self._get_tx_hash(tx_hash)
        if not is_valid_tx_hash(tx_hash):
            self.exit_on_failure(f"Invalid tx_hash - {tx_hash}")

        response = self.rpc_call(
            url=url,
            # method="icx_getTransactionResult",
            method=self.tx_method,
            params={"txHash": tx_hash}
        )

        use_hex_value = use_hex_value or self.use_hex_value
        if use_hex_value:
            return HexValueParser(response)

        if isinstance(response, dict):
            if return_key:
                return response.get(return_key)
            return response
        return response.get('text')

    def get_tx_wait(self,  tx_hash=None, url=None,  is_compact=True, is_block_time=False, max_attempts=None):
        tx_hash = self._get_tx_hash(tx_hash)
        if not tx_hash:
            return
        self.on_error = False

        if pawn.console._live:
            if not getattr(pawn, "console_status", None):
                pawn.console_status = getattr(pawn, "console_status", None)
            resp = self.check_transaction_loop(tx_hash, url, is_compact, pawn.console_status, is_block_time, max_attempts=max_attempts)
        else:
            with pawn.console.status("[magenta] Wait for transaction to be generated.") as status:
                resp = self.check_transaction_loop(tx_hash, url, is_compact, status, is_block_time, max_attempts=max_attempts)

        return resp

    def check_transaction_loop(self, tx_hash=None, url=None,  is_compact=True, status=None, is_block_time=False, max_attempts=None):
        """
        Check the transaction loop until a result is received or max_attempts is reached.

        :param tx_hash: The transaction hash.
        :param url: The URL for the transaction.
        :param is_compact: Whether to display a compact result.
        :param status: Status object for logging progress.
        :param is_block_time: Whether to include block elapsed time in the result.
        :param max_attempts: Maximum number of attempts before exiting the loop (None for unlimited).
        :return: The final response.
        """

        count = 0
        exit_loop = None
        while True:
            resp = self._check_transaction(url, tx_hash)
            if resp.get('error'):
                text, exit_loop = self._handle_error_response(resp, count, tx_hash)
            elif resp.get('result'):
                if is_block_time:
                    block_elapsed_time = f"<{self.analyze_tx_block_time(resp.get('result')).get('elapsed_time'):.2f}s> "
                else:
                    block_elapsed_time = ""

                text, exit_loop = self._handle_success_response(resp, count, tx_hash, prefix_text=block_elapsed_time)
            else:
                text = resp

            wait_callback = self.kwargs.get('wait_callback')

            if wait_callback and callable(wait_callback):
                wait_callback(text)
            elif getattr(status, "update", None):
                status.update(
                    status=text,
                    spinner_style="yellow",
                )

            # Check if max_attempts is reached
            if max_attempts is not None and count >= max_attempts:
                error_message = f"Reached maximum attempts ({max_attempts}) for transaction {get_shortened_tx_hash(tx_hash)}"

                detailed_message = (
                    f"{error_message}.\n"
                    f"Response: {resp}"
                )
                if isinstance(resp, dict) and resp.get('error') and resp['error']['message']:
                    resp['error']['message'] = f"{resp['error']['message']}, Reason: {error_message}"
                    # self.on_error = True
                    text, exit_loop = self._handle_error_response(resp, count, tx_hash)
                    self.exit_on_failure(f"{detailed_message}")
                    # pawn.console.log(f"[green] text={text}, exit={exit_loop} ")
                    # break
                #
                #     return resp
                # return detailed_message

            if exit_loop:
                self._print_final_result(text, is_compact, resp)
                break

            count += 1
            time.sleep(self.wait_sleep)
        if self.on_error and tx_hash:
            self.get_debug_trace(tx_hash, reset_error=False)

        return resp

    def _get_tx_hash(self, tx_hash):
        if not tx_hash and isinstance(self.response, dict):
            pawn.console.debug(f"tx_hash not found. It will be found in the self.response")
            if keys_exists(self.response, 'json', 'result', 'txHash'):
                tx_hash = self.response['json']['result']['txHash']
            elif keys_exists(self.response, 'json', 'result'):
                tx_hash = self.response['json']['result']
        if not tx_hash:
            pawn.console.log(f"[red] Not found tx_hash='{tx_hash}'")

        if  is_valid_tx_hash(tx_hash):
            return tx_hash
        else:
            pawn.console.log(f"[red] Invalid tx_hash value = {tx_hash}")
        return ""

    def _check_transaction(self, url, tx_hash):
        return self.get_tx(url=url, tx_hash=tx_hash)

    def _handle_error_response(self, resp, count, tx_hash):
        exit_loop = False
        exit_msg = ""
        prefix_text = f"[cyan][Wait TX][{count}][/cyan] Check a transaction by [i cyan]{tx_hash}[/i cyan] "
        _error_message = resp['error'].get('message')
        exit_error_messages = ["InvalidParams", "NotFound: E1005:not found tx id", "Reached maximum attempts"]

        if any(error_message in _error_message for error_message in exit_error_messages):
            exit_loop = True
            exit_msg = "[red][FAIL][/red]"
            self.on_error = True
        text = f"{prefix_text}{exit_msg}[white] '{_error_message}'"
        return text, exit_loop

    def _handle_success_response(self, resp, count, tx_hash, prefix_text=""):
        # if resp['result'].get('logsBloom'):
        #     resp['result']['logsBloom'] = int(resp['result']['logsBloom'], 16)
        if resp['result'].get('failure'):
            _resp_status = "[red][FAIL][/red]"
            self.on_error = True
        else:
            _resp_status = "[green][OK][/green]"
            self.on_error = False
        exit_loop = True
        prefix_text = f"[cyan][Wait TX][{count}][/cyan] {prefix_text}Check a transaction by [i cyan]{tx_hash}[/i cyan] "
        text = align_text(prefix_text, _resp_status, ".")
        return text, exit_loop

    def _print_final_result(self, text, is_compact, resp):
        final_result = f"[bold green][white]{text}"
        if is_compact:
            final_result = shorten_text(final_result, width=pawn.console.width, use_tags=True)
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
            PrintRichTable(f"debug_getTrace={tx_hash}", data=response['result']['logs'], no_wrap=True)
        else:
            pawn.console.log(response)
        return response

    def parse_tx_var(self, tx=None):
        if tx:
            _tx = copy.deepcopy(tx)
            self._use_global_request_payload = False
        else:
            if self.request_payload:
                _tx = self.request_payload
            else:
                _tx = self.global_request_payload
            self._use_global_request_payload = True
            # pawn.console.debug(f"[red]_use_global_request_payload={self._use_global_request_payload}")
        return _tx

    def _force_fill_from_address(self):
        if self.wallet and self.wallet.get('address'):
            return self.wallet.get('address')
        else:
            self.exit_on_failure(exception="Not found 'from address'. Not defined wallet")

    def auto_fill_parameter(self, tx=None, is_force_from_addr=False):
        _tx = self.parse_tx_var(tx)
        if isinstance(_tx, dict) and _tx.get('params'):
            if not _tx['params'].get('from') or is_force_from_addr:
                _tx['params']['from'] = self._force_fill_from_address()
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

        if self._use_global_request_payload:
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

        if not payload and self.global_request_payload:
            pawn.console.debug("Use global_request_payload")
            payload = self.global_request_payload

        self.request_payload = self._convert_valid_payload_format(payload=payload)
        private_key = self.wallet.get('private_key')
        address = self.wallet.get('address')
        #
        # if self.request_payload.get('params') and  not keys_exists(self.request_payload, "params", "value"):
        #     self.request_payload['params']['value'] = "0x0"

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

        self.global_request_payload = {}
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

    def sign_send(self, is_wait=True, is_compact=False, is_block_time=False, max_attempts=None):
        if self.signed_tx:
            response = self.rpc_call(payload=self.signed_tx, print_error=True)
            if not is_wait:
                return response

            if isinstance(response, dict) and response.get('result'):
                resp = self.get_tx_wait(tx_hash=response['result'], is_compact=is_compact, is_block_time=is_block_time, max_attempts=max_attempts)
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

    def preview_transaction_fee(self, payload, margin_steps=0, return_in_loop=False, use_decimal=False, use_hex_value=False):
        """
        Estimate the transaction fee for a given payload.

        :param payload: The transaction payload for which the fee is to be estimated.
        :type payload: dict
        :param margin_steps: Additional steps to add to the estimated step limit (default: 0).
        :type margin_steps: int
        :param return_in_loop: If True, returns the transaction fee in LOOP (smallest unit). Defaults to False (ICX).
        :type return_in_loop: bool
        :param use_decimal: If True, use Decimal for calculations to maintain precision. Defaults to False.
        :type use_decimal: bool
        :return: Estimated transaction fee in ICX (or LOOP if return_in_loop is True).
        :param use_hex_value: If True, returns a HexValue object instead of a raw balance.

        :rtype: Union[float, Decimal, int]
        :raises ValueError: If the payload is not properly formatted.

        Example usage:

            .. code-block:: python

                from pawnlib.uitils.http import IconRpcHelper

                # Initialize the helper
                icon_rpc_helper = IconRpcHelper(wallet="your_wallet_private_key")

                # Prepare transaction payload
                payload = {
                    "from": "hx123...",
                    "to": "hx456...",
                    "value": "0x1bc16d674ec80000",  # Example value in LOOP (1 ICX)
                    "stepLimit": "0xf4240"
                }

                # Preview the transaction fee in ICX
                estimated_fee = icon_rpc_helper.preview_transaction_fee(payload, margin_steps=500, use_decimal=True)
                print(f"Estimated Transaction Fee: {estimated_fee} ICX")
        """
        if not isinstance(payload, dict):
            raise ValueError("The payload must be a dictionary containing the transaction details.")

        # Estimate the step requirements
        estimated_steps_hex = self.get_estimate_step(tx=payload)
        estimated_steps = int(estimated_steps_hex, 16)

        # Add margin to estimated steps
        calculated_step_limit = estimated_steps + margin_steps

        # Fetch step price
        step_price_hex = self.get_step_price()
        step_price = int(step_price_hex, 16)

        # Calculate the transaction fee in LOOP
        transaction_fee_loop = calculated_step_limit * step_price

        # If return_in_loop is True, return fee in LOOP (smallest unit)
        if return_in_loop:
            return transaction_fee_loop

        # Otherwise, convert LOOP to ICX
        if use_hex_value:
            return HexValue(transaction_fee_loop)
        elif use_decimal:
            # Convert LOOP to ICX using Decimal
            transaction_fee_icx = Decimal(transaction_fee_loop) / Decimal('1e18')
        else:
            # Convert LOOP to ICX using float
            transaction_fee_icx = transaction_fee_loop / 1e18

        self.logger.info(f"Estimated Transaction Fee: {transaction_fee_icx} ICX ({transaction_fee_loop} LOOP)")
        return transaction_fee_icx


    def send_all_icx_with_decimal(self, to_address, fee=None, step_limit=None, min_balance=0, margin_steps=1000):
        """
        Transfer all available ICX from the wallet to the specified address, accounting for transaction fees.

        :param to_address: The recipient address where the ICX will be sent.
        :type to_address: str
        :param fee: Optional. The transaction fee in ICX. If not provided, it will be automatically calculated.
        :type fee: float or None
        :param step_limit: Optional. Custom step limit for the transaction. If not provided, it will be calculated.
        :type step_limit: int or None
        :param min_balance: Optional. The minimum balance to keep in the wallet after the transfer. Defaults to 0 ICX.
        :type min_balance: float
        :param margin_steps: The additional margin to apply to the estimated step limit. Defaults to 1000.
        :type margin_steps: int
        :return: None. Sends all available ICX except for the transaction fee and minimum balance.
        :rtype: None
        :raises ValueError: If the calculated transfer amount is less than or equal to zero.
        :raises Exception: If the transaction fails.

        Example usage:

            .. code-block:: python

                from pawnlib.utils.http import IconRpcHelper

                # Initialize the helper with the sender's wallet
                icon_rpc_helper = IconRpcHelper(wallet="your_wallet_private_key")

                # Transfer all ICX to the safety wallet
                icon_rpc_helper.send_all_icx(
                    to_address="hx8095412a43d07ed9869e55501c044849586ed671",
                    fee=0.00125,  # Optional fee
                    step_limit=100000,  # Optional step limit
                    min_balance=0,  # Keep minimum balance of 0 ICX
                    margin_steps=500  # Additional step margin for safety
                )
        """
        from_address = self.get_wallet_address()
        pawn.console.log(f"[INFO] Starting ICX transfer from [bold]{from_address}[/bold] to [bold]{to_address}[/bold]")

        balance_hex = self.get_balance(return_as_hex=True)
        balance_loop = int(balance_hex, 16)
        balance_icx = Decimal(balance_loop) / Decimal('1e18')  # Convert to ICX
        pawn.console.log(f"[INFO] Sender Address: {from_address}")
        pawn.console.log(f"[INFO] Current Balance: {balance_icx:.18f} ICX ({balance_loop} LOOP)")

        payload = json_rpc(
            method="icx_sendTransaction",
            params={
                "from": from_address,
                "to": to_address,
            }
        )

        estimated_fee_icx = self.preview_transaction_fee(payload, margin_steps=margin_steps, use_decimal=True)
        transaction_fee_icx = Decimal(fee) if fee is not None else estimated_fee_icx
        transaction_fee_loop = int(transaction_fee_icx * Decimal('1e18'))
        pawn.console.log(f"[INFO] Transaction Fee: {transaction_fee_icx:.18f} ICX ({transaction_fee_loop} LOOP)")

        min_balance_icx = Decimal(min_balance)
        min_balance_loop = int(min_balance_icx * Decimal('1e18'))

        total_required_loop = transaction_fee_loop + min_balance_loop
        total_required_icx = transaction_fee_icx + min_balance_icx

        pawn.console.log(f"[DEBUG] Minimum Balance to Keep: {min_balance_icx:.18f} ICX ({min_balance_loop} LOOP)")
        pawn.console.log(f"[DEBUG] Total Required (Fee + Min Balance): {total_required_icx:.18f} ICX ({total_required_loop} LOOP)")

        transfer_amount_loop = balance_loop - total_required_loop
        transfer_amount_icx = Decimal(transfer_amount_loop) / Decimal('1e18')  # Convert to ICX

        if transfer_amount_loop <= 0:
            raise ValueError(f"Insufficient balance to cover transaction fee and minimum balance. "
                             f"Available: {balance_icx} ICX, Required: {total_required_icx} ICX")

        pawn.console.log(f"[INFO] Transfer Amount: {transfer_amount_icx:.18f} ICX ({transfer_amount_loop} LOOP)")

        payload['params']['value'] = hex(transfer_amount_loop)
        pawn.console.log(f"[DEBUG] Final Payload for Transaction: {payload}")

        try:
            self.sign_tx(payload=payload, step_limit=step_limit)
            result = self.sign_send()
            pawn.console.log(f"[SUCCESS] Transaction sent successfully. TX Hash: {result.get('result')}")
        except Exception as e:
            pawn.console.log(f"[ERROR] Transaction failed: {e}")
            raise

        remaining_balance_hex = self.get_balance(return_as_hex=True)
        remaining_balance_loop = int(remaining_balance_hex, 16)
        remaining_balance_icx = Decimal(remaining_balance_loop) / Decimal('1e18')  # Convert to ICX
        pawn.console.log(f"[INFO] Remaining Balance: {remaining_balance_icx:.18f} ICX ({remaining_balance_loop} LOOP)")

        if remaining_balance_loop <= min_balance_loop:
            pawn.console.log(f"[INFO] Remaining balance is within acceptable range.")
        else:
            pawn.console.log(f"[WARNING] Remaining balance is more than expected: {remaining_balance_icx:.18f} ICX ({remaining_balance_loop} LOOP)")

    def send_all_icx(self, to_address, fee=None, step_limit=None, min_balance=0, margin_steps=0, max_attempts=None, dry_run=False):
        """
        Transfer all available ICX from the wallet to the specified address, accounting for transaction fees.
        This version uses float instead of Decimal for comparison and calculations.

        :param to_address: The recipient address where the ICX will be sent.
        :type to_address: str
        :param fee: Optional. The transaction fee in ICX. If not provided, it will be automatically calculated.
        :type fee: float or None
        :param step_limit: Optional. Custom step limit for the transaction. If not provided, it will be calculated.
        :type step_limit: int or None
        :param min_balance: Optional. The minimum balance to keep in the wallet after the transfer. Defaults to 0 ICX.
        :type min_balance: float
        :param margin_steps: The additional margin to apply to the estimated step limit. Defaults to 0.
        :type margin_steps: int
        :return: None. Sends all available ICX except for the transaction fee and minimum balance.
        :rtype: None
        :raises ValueError: If the calculated transfer amount is less than or equal to zero.
        :raises Exception: If the transaction fails.

        Example usage:

            .. code-block:: python

                from pawnlib.utils.http import IconRpcHelper

                # Initialize the helper with the sender's wallet
                icon_rpc_helper = IconRpcHelper(wallet="your_wallet_private_key")

                # Transfer all ICX to the safety wallet
                icon_rpc_helper.send_all_icx_without_decimal(
                    to_address="hx8095412a43d07ed9869e55501c044849586ed671",
                    fee=0.00125,  # Optional fee
                    step_limit=100000,  # Optional step limit
                    min_balance=0,  # Keep minimum balance of 0 ICX
                    margin_steps=500  # Additional step margin for safety
                )
        """

        from_address = self.get_wallet_address()
        self.logger.info(f"Starting ICX transfer from [bold]{from_address}[/bold] to [bold]{to_address}[/bold]")
        balance_hex = self.get_balance(return_as_hex=True, use_hex_value=True)
        self.logger.info(f"{from_address}'s Balance: {balance_hex}")

        # Prepare transaction payload
        payload = json_rpc(
            method="icx_sendTransaction",
            params={
                "from": from_address,
                "to": to_address,
            }
        )
        estimated_fee = self.preview_transaction_fee(payload, margin_steps=margin_steps, use_decimal=False, use_hex_value=True)
        transaction_fee = fee if fee is not None else estimated_fee

        self.logger.info(f"Transaction Fee: {transaction_fee} ")

        min_balance = HexValue(min_balance * const.ICX_IN_LOOP)
        total_required = transaction_fee + min_balance

        self.logger.info(f"Minimum Balance to Keep: {min_balance} ")
        self.logger.info(f"Total Required (Fee + Min Balance): {total_required}")

        # Calculate the transfer amount
        transfer_amount = balance_hex  - total_required
        self.logger.info(f"Transfer amount = {transfer_amount}")

        if transfer_amount <= 0:
            raise ValueError(f"Insufficient balance to cover transaction fee and minimum balance. "
                             f"Available: {transfer_amount.tint} ICX, Required: {total_required.tint} ICX")

        payload['params']['value'] = transfer_amount.hex
        self.logger.info(f"Final Payload for Transaction: {payload}")

        if dry_run:
            pawn.console.rule("---- DRY-RUN----")
            return

        try:
            self.sign_tx(payload=payload, step_limit=step_limit)
            result = self.sign_send(max_attempts=max_attempts)
            self.logger.info(f"[SUCCESS] Transaction sent successfully. TX Hash: {result.get('result')}")
        except Exception as e:
            self.logger.error(f"Transaction failed: {e}")
            raise

        remaining_balance = self.get_balance(return_as_hex=True, use_hex_value=True)
        self.logger.info(f"Remaining Balance: {remaining_balance}")

        if remaining_balance <= min_balance:
            self.logger.info(f"Remaining balance is within acceptable range.")
        else:
            self.logger.warn(f"Remaining balance is more than expected: {remaining_balance}")

    def set_stake(self, url=None, step_limit=None, is_wait=True, value="",  return_key="result"):
        if not is_hex(value):
            try:
                value = hex(int(value * const.ICX_IN_LOOP))
            except (ValueError, TypeError):
                raise ValueError(f"Invalid value provided for staking: {value}")
        params = {
            "value": value
        }
        _response = self.governance_call(url, method="setStake", params=params, sign=True, step_limit=step_limit, is_wait=is_wait)
        response = self.handle_response_with_key(response=_response, return_key=return_key)
        return response

    def delegate_all_icx(self, fee=None, step_limit=None, min_balance=0, margin_steps=0):
        stake_info = self.get_stake(use_hex_value=True)
        delegation_info = self.get_delegation(return_key="result", use_hex_value=True)
        bond_info = self.get_bond(return_key="result", use_hex_value=True)

        delegation_raw = []
        for delegation in  delegation_info.get('delegations'):
            delegation_raw.append(
                {"address": delegation.get("address"), "value": delegation.get('value').hex}
            )

        # print_var(delegation_raw)
        total_voting = delegation_info.get('totalDelegated') + bond_info.get('totalBonded')
        available_delegation = stake_info - total_voting
        pawn.console.log(f"Stake Amount    = {stake_info.output()}")
        pawn.console.log(f"Total Delegated = {delegation_info.get('totalDelegated').output()}")
        pawn.console.log(f"Total Bonded     = {bond_info.get('totalBonded').output()}")
        pawn.console.log(f"Total Voted      = {total_voting.output()}")
        pawn.console.log(f"Available Delegation =  {available_delegation.output()}")

        if stake_info == total_voting:
            pawn.console.log(f"Already full delegation {stake_info.output()}")
            return

        from_address = self.get_wallet_address()
        payload = json_rpc(
            method="icx_sendTransaction",
            params={
                "from": from_address,
                "to": const.CHAIN_SCORE_ADDRESS,
                "dataType": "call",
                "data": {
                    "method": "setDelegation",
                    "params": {
                        "delegations": delegation_raw,
                    }
                }
            }
        )
        # Use preview_transaction_fee to estimate the transaction fee
        estimated_fee_icx = self.preview_transaction_fee(payload, margin_steps=margin_steps, use_decimal=False)
        transaction_fee_icx = fee if fee is not None else estimated_fee_icx
        transaction_fee_loop = int(transaction_fee_icx * const.ICX_IN_LOOP)
        self.logger.info(f"Transaction Fee: {transaction_fee_icx} ICX ({transaction_fee_loop} LOOP)")


        min_balance_loop = int(min_balance * const.ICX_IN_LOOP)
        total_required_loop = transaction_fee_loop + min_balance_loop
        total_required_icx = transaction_fee_icx + min_balance

        self.logger.debug(f"Minimum Balance to Keep: {min_balance} ICX ({min_balance_loop} LOOP)")
        self.logger.debug(f"Total Required (Fee + Min Balance): {total_required_icx} ICX ({total_required_loop} LOOP)")

        delegation_amount_loop = stake_info.tint - total_required_loop
        delegation_amount_icx = delegation_amount_loop / const.ICX_IN_LOOP  # Convert to ICX using float

        delegated_difference_decimal  = stake_info.decimal - delegation_info.get('totalDelegated').decimal - total_required_loop
        delegated_difference_tint  = stake_info.tint - delegation_info.get('totalDelegated').tint
        pawn.console.log(f"Diff : {delegated_difference_tint:,} ICX")

        delegation_target_address = ""
        delegation_target_value = "0x0"
        print_var(delegation_info)
        if delegation_raw and isinstance(delegation_raw, list):
            delegation_target_address = delegation_raw[0].get('address')
            delegation_target_value = HexValue(delegation_raw[0].get('value'))

        new_delegation = delegation_target_value + available_delegation
        pawn.console.log(f"New Delegation: {new_delegation.output()}")
        payload['params']['data']['params']['delegations'] = [{"address": delegation_target_address, "value": new_delegation.hex}]

        print_var(payload)

        try:
            self.sign_tx(payload=payload, step_limit=step_limit)
            result = self.sign_send()
            pawn.console.log(result.get('result'))
            pawn.console.log(f"[SUCCESS] Delegated {stake_info.tint} ICX successfully. TX Hash: {result.get('result')}")
        except Exception as e:
            pawn.console.log(f"[ERROR] Staking transaction failed: {e}")
            raise

        if delegated_difference_decimal:
            delegated_difference_hex = hex(int(delegated_difference_decimal))
            pawn.console.log(f"{delegated_difference_tint:,} ICX, {delegated_difference_decimal}, {delegated_difference_hex}")

    def stake_all_icx(self, fee=None, step_limit=None, min_balance=0, margin_steps=0, dry_run=False):
        """
        Stake all available ICX, accounting for transaction fees, using float for calculations.

        :param to_address: The staking contract address where ICX will be staked.
        :type to_address: str
        :param fee: Optional. The transaction fee in ICX. If not provided, it will be automatically calculated.
        :type fee: float or None
        :param step_limit: Optional. Custom step limit for the transaction. If not provided, it will be calculated.
        :type step_limit: int or None
        :param min_balance: Optional. The minimum balance to keep in the wallet after the transfer. Defaults to 0 ICX.
        :type min_balance: float
        :param margin_steps: The additional margin to apply to the estimated step limit. Defaults to 1000.
        :type margin_steps: int
        :return: None. Stakes all available ICX except for the transaction fee and minimum balance.
        :rtype: None
        :raises ValueError: If the calculated staking amount is less than or equal to zero.
        :raises Exception: If the transaction fails.

        Example usage:

            .. code-block:: python

                from icon_rpc_helper import IconRpcHelper

                # Initialize the helper with the sender's wallet
                icon_rpc_helper = IconRpcHelper(wallet="your_wallet_private_key")

                # Stake all available ICX
                icon_rpc_helper.stake_all_available_icx(
                    to_address="hx8095412a43d07ed9869e55501c044849586ed671",
                    fee=0.00125,  # Optional fee
                    step_limit=100000,  # Optional step limit
                    min_balance=0,  # Keep minimum balance of 0 ICX
                    margin_steps=500  # Additional step margin for safety
                )
        """
        current_balance = self.get_balance(use_hex_value=True)
        current_staked = self.get_stake(use_hex_value=True)

        pawn.console.log(f"[INFO] Current Balance: {current_balance.output()}")
        pawn.console.log(f"[INFO] Current Staked : {current_staked.output()}")

        # If the current balance is equal to the current staked amount, no need to perform staking
        if current_balance < 0.0017275:
            pawn.console.log(f"[INFO] No difference between current balance and staked amount. Staking is not required.")
            return

        # Prepare a dummy transaction to estimate the transaction fee
        from_address = self.get_wallet_address()
        payload = json_rpc(
            method="icx_sendTransaction",
            params={
                "from": from_address,
                "to": const.CHAIN_SCORE_ADDRESS,
                "dataType": "call",
                "data": {
                    "method": "setStake",
                    "params": {
                        "value": current_staked.hex
                    }
                }
            }
        )
        # Use preview_transaction_fee to estimate the transaction fee
        if not fee:
            transaction_fee = self.preview_transaction_fee(payload, margin_steps=margin_steps, use_hex_value=True)
        else:
            transaction_fee = HexTintValue(fee)

        min_balance = HexTintValue(min_balance)

        available_staking_amount = current_balance - transaction_fee - min_balance
        final_staking_amount = available_staking_amount + current_staked

        pawn.console.log(f"Transaction Fee:  {transaction_fee.output()}")
        pawn.console.log(f"Minimum Balance:  {min_balance.output()}")
        pawn.console.log(f"Available Staking Amount :  {available_staking_amount.output()}")
        pawn.console.log(f"Final Staking Amount:  {final_staking_amount.output()}")

        if dry_run:
            pawn.console.rule("---- DRY-RUN----")
            return

        # If the staking amount is less than or equal to zero, raise an error
        if available_staking_amount <= 0:
            raise ValueError(f"Insufficient balance to cover transaction fee and minimum balance for staking. Balance: {current_balance.tint} ICX,"
                             f" Available Staking Amount: {available_staking_amount.tint} ICX")

        # Update the payload with the final staking amount
        payload['params']['data']['params']['value'] = final_staking_amount.hex  # Convert ICX to LOOP

        # Sign and send the staking transaction
        try:
            self.sign_tx(payload=payload, step_limit=step_limit)
            result = self.sign_send()
            pawn.console.log(f"[SUCCESS] Staked {final_staking_amount.output()} successfully. TX Hash: {result.get('result')}")
        except Exception as e:
            pawn.console.log(f"[ERROR] Staking transaction failed: {e}")
            raise

        # Check the updated stake after the transaction
        updated_staked = self.get_stake(use_hex_value=True)
        now_balance = self.get_balance(use_hex_value=True)
        staked_difference = updated_staked - current_staked

        pawn.console.log(f"[INFO] Updated Staked Amount: {updated_staked.output()}, now_balance={now_balance.output()}")
        pawn.console.log(f"📈 [INFO] Staked increase: {staked_difference.output()}")

        if staked_difference > 0:
            pawn.console.log(f"🔼 Increased staking by: {staked_difference.output()} 🎉")
        elif staked_difference < 0:
            pawn.console.log(f"🔽 Decreased staking by: {abs(staked_difference.tint):.18f} ICX ⚠️")
        else:
            pawn.console.log("🟡 No change in staked amount.")

class JsonRequest:
    def __init__(self):
        """
        TODO: It will be generated the JSON or JSON-RPC request
        """
        pass


def disable_ssl_warnings():
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def append_scheme(url: str, default_scheme: str = "http") -> str:
    """
    Appends the specified scheme (e.g., http, https) to the URL if it is missing.

    :param url: The URL to validate and modify.
    :param default_scheme: The scheme to prepend if missing. Default is "http".
    :return: A URL with a scheme.
    """
    if not url:
        return url

    # Check if the URL starts with a valid scheme
    if "://" not in url.split("/")[0]:
        return f"{default_scheme}://{url}"

    # Return the original URL if scheme exists
    return url


def append_http(url):
    """

    Add http:// if it doesn't exist in the URL

    :param url:
    :return:
    """
    if not url:
        return url

    if not (url.startswith("http://") or url.startswith("https://")):
        url = f"http://{url}"
    return url


def append_s3(url):
    """

    Add http:// if it doesn't exist in the URL

    :param url:
    :return:
    """
    if not url:
        return url

    if not url.startswith("s3://"):
        url = f"s3://{url}"
    return url


def append_ws(url):
    """

    Add ws:// if it doesn't exist in the URL

    :param url:
    :return:
    """
    if not url:
        return url  # 또는 오류 처리, 예: raise ValueError("URL cannot be empty")

    if url.startswith("https://"):
        url = url.replace("https://", "wss://", 1)
    elif url.startswith("http://"):
        url = url.replace("http://", "ws://", 1)
    elif not (url.startswith("ws://") or url.startswith("wss://")):
        url = f"ws://{url}"

    return url


def append_api_v3(url):
    if "/api/v3" not in url:
        url = f"{url.rstrip('/')}/api/v3"
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
            pawn.console.log(f"[red]<SuccessCriteria Error>[/red] '{self.target_key}' is not attribute in {list(self.target.keys())}")
            pawn.console.log(
                f"[red]<SuccessCriteria Error>[/red] '{self.target_key}' not found. \n "
                f"Did you mean {guess_key(self.target_key, self.target.keys())} ?")

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

    def __init__(
            self,
            url=None,
            method: Literal["get", "post", "patch", "delete"] = "get",
            # method: Literal[AllowsHttpMethod.get] = "get",
            # method: AllowsHttpMethod = AllowsHttpMethod.get,
            # method: Literal[tuple(method for method in AllowsHttpMethod)],
            payload={},
            timeout=3000,
            ignore_ssl: bool = False,
            verify=False,
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
        self.verify = verify

        if self.ignore_ssl:
            disable_ssl_warnings()

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

    def print_http_response(self, response=None):
        if not response:
            response = self.response

        if hasattr(response, "json"):
            response_type = "json"
        else:
            response_type = "text"

        pawn.console.log(f"Response from '{self.method.upper()}' '{self.url}' 👉 {response} ({response_type.upper()})")
        if not response:
            style = "red"
        else:
            style = "rule.line"

        pawn.console.rule(f"{response} ", align='right', style=style, characters="═")
        if response.json:
            print_json(response.json)
        else:
            print_syntax(response.text, name="html", style="one-dark")

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
            if pawn.get("PAWN_DEBUG") and self.payload:
                print_json(_payload_string)

            func = getattr(requests, self.method)
            if self.method == "get":
                self.response = func(self.url, verify=self.verify, timeout=self.timeout, **self.kwargs)
            else:
                self.response = func(self.url, json=self.payload, verify=self.verify, timeout=self.timeout, **self.kwargs)

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
        self.response.response_time = _elapsed
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
                    if pconf().PAWN_DEBUG:
                        pawn.console.log(_criteria)
                    self._success_results.append(SuccessResponse(*_criteria))
                elif isinstance(criteria, dict):
                    criteria['target'] = _response_dict
                    self._success_results.append(SuccessResponse(**criteria))
            # pawn.console.log(self._success_results)

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
                result = [element.strip() for element in argument.split(operator)]
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


class HttpInspect:
    def __init__(self, url, method='GET', headers=None, auth=None, timeout=10, max_redirects=5, 
                 verify=True, data=None, max_response_length=700, output=None, dns_server=None, debug=False):
        """Initialize the HttpInspect class for HTTP request inspection.

        This class provides functionality to inspect HTTP requests and responses,
        including DNS resolution, timing analysis, and response handling.

        Args:
            url (str): The target URL to inspect. Will be prefixed with 'http://' if no scheme is provided.
            method (str, optional): HTTP method to use. Defaults to 'GET'.
            headers (dict, optional): Custom HTTP headers. Defaults to None.
            auth (tuple, optional): Authentication credentials. Defaults to None.
            timeout (int, optional): Request timeout in seconds. Defaults to 10.
            max_redirects (int, optional): Maximum number of redirects to follow. Defaults to 5.
            verify (bool, optional): Whether to verify SSL certificates. Defaults to True.
            data (dict, optional): Request body data. Defaults to None.
            max_response_length (int, optional): Maximum length of response to display. Defaults to 700.
            output (str, optional): Output format specification. Defaults to None.
            dns_server (str, optional): DNS server to use. Defaults to None.
            debug (bool, optional): Whether to enable debug mode. Defaults to False.
        """
        self.url = self._normalize_url(url)
        self.method = method.upper()
        self.headers = headers or {}
        self._headers_provided = headers is not None
        self.auth = auth
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.verify = verify
        self.data = data

        self.output = output
        self.console = Console()
                    
        parsed_url = urlparse(self.url)
        self.domain = parsed_url.netloc or parsed_url.path
        self.scheme = parsed_url.scheme
        self.hostname = parsed_url.hostname
        self.port = parsed_url.port or (443 if self.scheme == 'https' else 80)

        self.ip = None
        self.response = None
        self.max_response_length = max_response_length
        self.elapsed_time = None

        self.total_time = 0

        self.dns_records: Dict[str, List[str]] = {}
        self.waterfall_timings: List[Dict[str, Any]] = []
        self.dns_cache: Dict[str, str] = {}
        self.dns_server = dns_server
        
        self.debug = debug
                
        self._log_init_settings()

    def _normalize_url(self, url: str) -> str:
        """Normalize the URL to ensure it is always in a valid format."""
        if not url:
            raise ValueError("URL cannot be empty")
            
        if not url.startswith(('http://', 'https://')):            
            if ':443' in url:
                return f'https://{url}'
            return f'http://{url}'
        return url

    def _log_init_settings(self):
        """Logs the initial settings to the log."""
        if self.debug:
            self.console.print(Panel(
                f"[bold]URL:[/] {self.url}\n"
                f"[bold]Method:[/] {self.method}\n"
                f"[bold]Domain:[/] {self.domain}\n"
                f"[bold]Timeout:[/] {self.timeout}s\n"
                f"[bold]Max Redirects:[/] {self.max_redirects}\n"
                f"[bold]DNS Server:[/] {self.dns_server or 'System Default'}",
                title="HttpInspect Configuration", 
                expand=False
            ))

    def get_ip_address(self, domain: str = "", url: str = "") -> Optional[str]:
        """Get the IP address of the specified domain.
        
        Args:
            domain (str, optional): The domain name to lookup. Defaults to the domain extracted from the current URL.
            url (str, optional): The URL to include in timing information. Defaults to the current URL.
            
        Returns:
            Optional[str]: The resolved IP address or None if lookup fails
        """
        if self.headers.get('Host'):
            domain = self.headers.get('Host')
        elif not domain:
            domain = self.domain
        
        if not url:
            url = self.url

        ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        if re.match(ip_pattern, domain):
            self.dns_cache[domain] = domain
            self.ip = domain
            self._add_timing_info(url, dns_time=0, details=f'Using provided IP {domain}')
            return domain

        if domain in self.dns_cache:
            return self.dns_cache[domain]

        try:
            start_time = time.time()
            
            if self.dns_server:                
                resolver = dns.resolver.Resolver()
                resolver.nameservers = [self.dns_server]
                answers = resolver.resolve(domain, 'A')            
                self.ip = str(answers[0].address)
            else:
                self.ip = socket.gethostbyname(domain)

            dns_time = (time.time() - start_time) * 1000  # ms로 변환
                        
            self.dns_cache[domain] = self.ip
            self._add_timing_info(url, dns_time=dns_time, details=f'Resolved {domain} to {self.ip}')
            
            self.console.log(f"DNS 조회: {domain} => {self.ip} ({dns_time:.2f}ms)")
            return self.ip
            
        except (socket.gaierror, dns.resolver.NXDOMAIN, dns.resolver.NoAnswer) as e:
            self.console.print(f"[bold red]Error:[/] Could not resolve IP for {domain}: {str(e)}")
            return None
        except Exception as e:
            self.console.print(f"[bold red]Unexpected error during DNS resolution:[/] {str(e)}")
            return None

    def _add_timing_info(self, url: str, dns_time: float = 0, tcp_time: float = 0, 
                         tls_time: float = 0, ttfb_time: float = 0, total_time: float = 0, 
                         status: int = 0, http_version: str = '', details: str = '') -> None:
        """Add waterfall timing information."""
        self.waterfall_timings.append({
            'url': url,
            'dns_time': dns_time,
            'tcp_time': tcp_time,
            'tls_time': tls_time,
            'ttfb_time': ttfb_time,
            'total_time': total_time,
            'status': status,
            'http_version': http_version,
            'details': details,
            'real_url': ''  # 응답 수신 후 업데이트됨
        })

    def get_dns_records(self, domain: str, record_types: Optional[List[str]] = None) -> None:
        """Get the DNS records for the specified domain.
        
        Args:
            domain (str): The domain name to lookup.
            record_types (List[str], optional): The list of record types to lookup. Defaults to A, AAAA, CNAME, MX, TXT, NS.
        """
        if record_types is None:
            record_types = ["A", "AAAA", "CNAME", "MX", "TXT", "NS"]
            
        self.dns_records = {}
        resolver = dns.resolver.Resolver()
        
        if self.dns_server:
            resolver.nameservers = [self.dns_server]
        
        for rtype in record_types:
            try:
                answers = resolver.resolve(domain, rtype, lifetime=3)
                self.dns_records[rtype] = [str(r.to_text()) for r in answers]
                
                # A 레코드인 경우 첫 번째 IP를 기본 IP로 설정
                if rtype == "A" and not self.ip and answers:
                    self.ip = str(answers[0].to_text())
                    self.dns_cache[domain] = self.ip
                    
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
                self.dns_records[rtype] = []
            except Exception as e:
                self.console.print(f"[bold red]Error getting {rtype} records for {domain}:[/] {str(e)}")
                self.dns_records[rtype] = []

    def make_http_request(self) -> bool:
        """Perform an HTTP request and analyze the response.
        
        Returns:
            bool: Whether the request was successful
        """
        try:
            start_time = time.time()
            
            self.headers.setdefault("User-Agent", f"Pawnlib-HttpInspect/{pawn.version_number}")            
            self.ip = self.get_ip_address(self.domain, self.url)
            
            if not self.ip:
                raise ValueError("Could not get IP address")

            parsed_url = httpx.URL(self.url)
            
            if self.dns_server:
                connect_url = parsed_url.copy_with(scheme=parsed_url.scheme, host=self.ip, port=parsed_url.port)
                self.headers['Host'] = parsed_url.host
                self.console.log(f"[cyan]Connected URL: {connect_url}[/cyan]")
            else:            
                connect_url = self.url
    
            def on_request(request):
                request.start_time = time.time()
                parsed_request_url = httpx.URL(str(request.url))
                request_domain = parsed_request_url.host

                if request_domain == self.ip and self.domain:
                    request.headers['Host'] = self.domain
                
                if self.debug:
                    self.console.log(f"[cyan]Request URL: {request.url}[/cyan]")
                    self.console.log(f"[cyan]Request Headers: {request.headers}[/cyan]")

            def on_response(response):
                response.read()
                
                parsed_response_url = httpx.URL(str(response.url))
                if parsed_response_url.host == self.ip:
                    domain_url = parsed_response_url.copy_with(host=self.domain)
                else:
                    domain_url = parsed_response_url
                
                total_time = (time.time() - response.request.start_time) * 1000  # ms
                ttfb_time = response.elapsed.total_seconds() * 1000 if response.elapsed else 0
                
                connect_phase = total_time - ttfb_time
                tcp_time = connect_phase * 0.6  # TCP connection is estimated to be 60% of the connection phase 
                tls_time = connect_phase * 0.4 if str(response.url).startswith('https://') else 0  # HTTPS is 40% of the connection phase

                match_found = False
                for timing in self.waterfall_timings:
                    if timing['url'] == str(domain_url) and timing['status'] == 0:
                        timing.update({
                            'status': response.status_code,
                            'real_url': str(response.url),
                            'http_version': response.http_version.replace('HTTP/', 'H'),
                            'tcp_time': tcp_time,
                            'tls_time': tls_time,
                            'ttfb_time': ttfb_time,
                            'total_time': total_time,
                            'details': f'{response.request.method} {response.url} ({response.status_code})'
                        })
                        match_found = True
                        self.total_time += total_time
                        break
                
                if not match_found:
                    self._add_timing_info(
                        url=str(domain_url),
                        dns_time=0,  # DNS is already completed
                        tcp_time=tcp_time,
                        tls_time=tls_time,
                        ttfb_time=ttfb_time,
                        total_time=total_time,
                        status=response.status_code,
                        http_version=response.http_version.replace('HTTP/', 'H'),
                        details=f'{response.request.method} {response.url} ({response.status_code})'
                        
                    )
                    self.total_time += total_time
                    self.waterfall_timings[-1]['real_url'] = str(response.url)
            
            with httpx.Client(
                follow_redirects=True,
                timeout=self.timeout,
                verify=self.verify,
                headers=self.headers,
                auth=self.auth,
                max_redirects=self.max_redirects,
                event_hooks={
                    'request': [on_request],
                    'response': [on_response]
                }
            ) as client:
                if self.method == "GET":
                    self.response = client.get(connect_url, params=self.data)
                elif self.method == "POST":
                    self.response = client.post(connect_url, json=self.data if isinstance(self.data, dict) else None, 
                                               data=self.data if not isinstance(self.data, dict) else None)
                elif self.method == "PUT":
                    self.response = client.put(connect_url, json=self.data if isinstance(self.data, dict) else None,
                                              data=self.data if not isinstance(self.data, dict) else None)
                elif self.method == "DELETE":
                    self.response = client.delete(connect_url, params=self.data)
                elif self.method == "HEAD":
                    self.response = client.head(connect_url)
                elif self.method == "OPTIONS":
                    self.response = client.options(connect_url)
                elif self.method == "PATCH":
                    self.response = client.patch(connect_url, json=self.data if isinstance(self.data, dict) else None,
                                                data=self.data if not isinstance(self.data, dict) else None)
                else:
                    self.response = client.request(self.method, connect_url, data=self.data)
                
                self.response.encoding = 'utf-8'                
                self.elapsed_time = (time.time() - start_time) * 1000  # ms
                
                return True

        except httpx.RequestError as e:
            self.console.print(Panel(f"[bold red]Request Error:[/] {str(e)}", title="Request Failed"))
            return False
        except ValueError as e:
            self.console.print(Panel(f"[bold red]Value Error:[/] {str(e)}", title="Request Failed"))
            return False
        except Exception as e:
            self.console.print(Panel(f"[bold red]Unexpected Error:[/] {str(e)}", title="Request Failed"))
            return False
        
    def _status_emoji(self, code: int) -> str:
        """상태 코드에 맞는 이모지를 반환합니다."""
        if 100 <= code < 200:  # 정보
            return "🕑"
        if 200 <= code < 300:  # 성공
            return "✅"
        if 300 <= code < 400:  # 리다이렉션
            return "↪️"
        if 400 <= code < 500:  # 클라이언트 오류
            return "⚠️"
        if 500 <= code < 600:  # 서버 오류
            return "💥"
        return "❓"  # 알 수 없는 상태

    def display_results(self):
        """HTTP 요청 결과를 표시합니다."""
        if self.response is None:
            self.console.print(Panel("[bold red]Error: No response received", title="Request Failed"))
            return
    
        status_code = self.response.status_code
        if status_code < 400:
            status_style = "bold green"
        elif status_code < 500:
            status_style = "bold yellow"
        else:
            status_style = "bold red"
            
        emoji = self._status_emoji(status_code)

        self.console.print(Panel(
            f"[bold green]HTTP {self.method} Request:[/] {self.url}\n"
            f"[bold cyan]HTTP Version:[/] {self.response.http_version.upper()}\n"
            f"[bold cyan]Server IP:[/] {self.ip}\n"
            f"[{status_style}]Status Code:[/] {emoji} {status_code} {self.response.reason_phrase}\n"
            f"[bold cyan]Final URL:[/] {self.response.url}\n"
            # f"[bold cyan]Elapsed Time:[/] {self.elapsed_time:.2f} ms",
            f"[bold cyan]Elapsed Time:[/] {self.total_time:.2f} ms",
            title="Request Info"
        ))
        
        waterfall = Table(title="Waterfall Timing", expand=True)
        waterfall.add_column("#", justify="right", style="dim")
        waterfall.add_column("Status", style="cyan")
        waterfall.add_column("HTTP", style="cyan")
        waterfall.add_column("DNS (ms)", justify="right", style="blue")
        waterfall.add_column("TCP (ms)", justify="right", style="green")
        waterfall.add_column("TLS (ms)", justify="right", style="yellow")
        waterfall.add_column("TTFB (ms)", justify="right", style="magenta")
        waterfall.add_column("Total (ms)", justify="right", style="red bold")
        waterfall.add_column("URL", style="white", overflow="fold")

        ordered_timings = []
        
        for resp in self.response.history + [self.response]:
            for timing in self.waterfall_timings:
                if timing.get('real_url') == str(resp.url) and timing.get('status') == resp.status_code:
                    ordered_timings.append(timing)
                    break

        for idx, timing in enumerate(ordered_timings, 1):
            status_emoji = self._status_emoji(timing['status'])
            status_style = "green" if timing['status'] < 400 else "red"
            
            waterfall.add_row(
                str(idx),
                f"[{status_style}]{timing['status']} {status_emoji}[/{status_style}]",
                timing['http_version'],
                f"{timing['dns_time']:.1f}",
                f"{timing['tcp_time']:.1f}",
                f"{timing['tls_time']:.1f}",
                f"{timing['ttfb_time']:.1f}",
                f"{timing['total_time']:.1f}",
                timing['url']
            )

        self.console.print(waterfall)

        if self._headers_provided:
            req_header_table = Table(title="Request Headers", expand=True)
            req_header_table.add_column("Header", style="cyan", no_wrap=True)
            req_header_table.add_column("Value", style="white", overflow="fold")
            for k, v in self.headers.items():
                req_header_table.add_row(k, str(v))
            self.console.print(req_header_table)

        res_header_table = Table(title="📦 Response Headers", expand=True)
        res_header_table.add_column("Header", style="cyan", no_wrap=True)
        res_header_table.add_column("Value", style="white", overflow="fold")
        for k, v in self.response.headers.items():
            res_header_table.add_row(k, v)

        self.console.print(res_header_table)
        self._display_response_body()
        
    def _display_response_body(self):
        """Display the response body in the appropriate format."""
        if self.response is None:
            return
            
        should_skip = self.max_response_length is None or self.max_response_length < 0
        if should_skip:
            return
            
        content_type = self.response.headers.get("Content-Type", "")

        response_size = len(self.response.text)
        response_detail_str = f"Status: {self.response.status_code} | Reason: {self.response.reason_phrase} | Size: {convert_bytes(response_size)}"
                
        if "application/json" in content_type:
            try:
                json_data = self.response.json()
                formatted = json.dumps(json_data, indent=2, ensure_ascii=False)
                body = formatted if self.max_response_length == 0 else formatted[:self.max_response_length]
                
                if self.max_response_length > 0 and len(formatted) > self.max_response_length:
                    body += "\n\n... (truncated)"

                syntax = Syntax(body, "json", theme="monokai", line_numbers=True, word_wrap=True)
                self.console.print(Panel(syntax, title=f"🧾 Response Body (JSON) {response_detail_str}", expand=True))
                
            except Exception as e:
                self.console.print(f"[yellow]Warning: JSON parsing failed: {str(e)}[/yellow]")
                self._display_text_response()
        
        elif any(x in content_type.lower() for x in ["text/html", "application/xml", "text/xml"]):
            text = self.response.text if self.max_response_length == 0 else self.response.text[:self.max_response_length]
            
            if self.max_response_length > 0 and len(self.response.text) > self.max_response_length:
                text += "\n\n... (truncated)"
                
            syntax = Syntax(text, "html", theme="monokai", line_numbers=True, word_wrap=True)
            self.console.print(Panel(syntax, title=f"🧾 Response Body ({content_type.split(';')[0]}) {response_detail_str}", expand=True))
        
        else:
            self._display_text_response()
        

        if self.output:
            with open(self.output, 'w', encoding='utf-8') as f:
                f.write(self.response.text)
            self.console.print(f"[bold green]🧾 Response saved to {self.output}[/]")
            
    def _display_text_response(self):
        """Display a plain text response."""
        if self.response is None:
            return
            
        text = self.response.text if self.max_response_length == 0 else self.response.text[:self.max_response_length]
        
        if self.max_response_length > 0 and len(self.response.text) > self.max_response_length:
            text += "\n\n... (truncated)"
            
        content_type = self.response.headers.get("Content-Type", "text/plain").split(';')[0]
        self.console.print(Panel(text, title=f"🧾 Response Body ({content_type})", expand=True))

    def display_dns_records(self):
        """Display the DNS records."""
        if not self.dns_records:
            self.get_dns_records(self.domain)
            
        self.console.line()
        
        dns_table = Table(title=f"DNS Records for '{self.domain}'", expand=True)
        dns_table.add_column("Type", style="cyan", no_wrap=True)
        dns_table.add_column("Value", style="white", overflow="fold")
        
        has_records = False
        for rtype, records in self.dns_records.items():
            if records:
                has_records = True
                dns_table.add_row(rtype, "\n".join(records))
                
        if has_records:
            self.console.print(dns_table)
        else:
            self.console.print("[yellow]No DNS records found[/yellow]")

    def export_results(self, format='json', filename=None):
        """Export the results to a file.
        
        Args:
            format (str): The format to export ('json', 'text')
            filename (str, optional): The file name. Defaults to '{domain}_results.{format}'
        """
        if not self.response:
            self.console.print("[yellow]Warning: No results to export[/yellow]")
            return
            
        if not filename:
            filename = f"{self.domain}_results.{format}"
            
        result_data = {
            "url": self.url,
            "method": self.method,
            "domain": self.domain,
            "ip": self.ip,
            "status_code": self.response.status_code,
            "elapsed_time_ms": self.elapsed_time,
            "headers": dict(self.response.headers),
            "dns_records": self.dns_records,
            "waterfall_timings": self.waterfall_timings
        }
        
        if format.lower() == 'json':
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)
        else:  # text
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"URL: {self.url}\n")
                f.write(f"Method: {self.method}\n")
                f.write(f"Domain: {self.domain}\n")
                f.write(f"IP: {self.ip}\n")
                f.write(f"Status Code: {self.response.status_code}\n")
                f.write(f"Elapsed Time: {self.elapsed_time:.2f} ms\n\n")
                
                f.write("Headers:\n")
                for k, v in self.response.headers.items():
                    f.write(f"  {k}: {v}\n")
                    
                f.write("\nBody:\n")
                f.write(self.response.text)
                
        self.console.print(f"[bold green]Results exported to {filename}[/]")

    def run(self):
        """전체 검사 프로세스를 실행합니다."""
        self.console.print(Panel(f"[bold]HTTP Inspection: {self.url}[/]", 
                                style="bold blue", expand=False))
        
        self.ip = self.get_ip_address(self.domain, self.url)
        if not self.ip:
            self.console.print("[bold red]Aborting: Failed to resolve domain[/]")
            return False
                    
        if not self.make_http_request():
            self.console.print("[bold red]Aborting: HTTP request failed[/]")
            return False
            
        self.get_dns_records(self.domain)
        
        self.display_results()
        self.display_dns_records()           
        return True


def parse_auth(auth_str):    
    if ':' in auth_str:
        # Basic Auth
        username, password = auth_str.split(':', 1)
        return HTTPBasicAuth(username, password)
    else:
        # OAuth 토큰 (Bearer)
        return {'Authorization': f'Bearer {auth_str}'}

def parse_headers(headers_str):    
    headers = {}
    if isinstance(headers_str, dict):
        for key, value in headers_str.items():
            headers[key] = f"{value}".strip()
    else:
        for header in headers_str:
            key, value = header.split(':', 1)
            headers[key.strip()] = value.strip()
    return headers


class CheckSSL:
    """SSL Certificate Checker.

    This class is responsible for checking the SSL certificate of a given host.
    It retrieves SSL certificate information, checks its expiry status, and displays
    the relevant details in a formatted table.

    Attributes:
        host (str): The hostname of the server to check.
        port (int): The port number to connect to (default is 443).
        timeout (float): The timeout for the connection in seconds (default is 5.0).
        sni_hostname (str): The hostname to use for the SNI (Server Name Indication) handshake.
        ssl_info (dict): Stores the SSL certificate information.
    """
    
    def __init__(self, host, port=443, timeout=5.0, sni_hostname: str = ""):
        

        proper_url = append_scheme(host, "https")
        parsed_url = urlparse(proper_url)
        self._host = parsed_url.hostname  # "httpbin.org"가 추출됨
        self._port = port
        self._timeout = timeout
        self._sni_hostname = sni_hostname or self._host  
        self.ssl_info = None

        pawn.console.log(
            f"[cyan]Checking SSL certificate for TCP {self._host}:{self._port} [/cyan]"
            f"(SNI={self._sni_hostname})"
        )

    def get_ssl(self) -> dict: 
        """Retrieve the SSL certificate for the specified host.

        Returns:
            dict: The SSL certificate information.

        Raises:
            SystemExit: If there is a connection error.
        """
        try:
            context = ssl.create_default_context()
            with socket.create_connection((self._host, self._port), timeout=self._timeout) as sock:
                with context.wrap_socket(sock, server_hostname=self._sni_hostname) as conn:
                    return conn.getpeercert()
        except Exception as e:
            pawn.console.log(f"[red]Connect SSL Error: '{self._host}' -> {e}[/red]")
            # sys.exit(1)
    
    def _parse_date(self, date_str):
        """Parse SSL date format.

        Args:
            date_str (str): The date string to parse.

        Returns:
            datetime: The parsed date.
        """
        return datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')

    def check_expiry(self):
        """Check the expiry status of the SSL certificate.

        Returns:
            tuple: A status string and the number of days left until expiry.
        """
        not_after = self._parse_date(self.ssl_info.get('notAfter'))
        now = datetime.now()
        delta = not_after - now
        days_left = delta.days
        if days_left < 0:
            return "Expired", days_left
        elif days_left <= 15:
            return "Expiring Soon", days_left
        else:
            return "Valid", days_left

    def display(self):
        """Display the SSL certificate information in a formatted table."""
        if self.ssl_info is None:
            self.ssl_info = self.get_ssl()

        table = Table(title="SSL Certificate Information", expand=True)
        table.add_column("Field", justify="left", style="cyan")
        table.add_column("Value", justify="left")

        def format_dn(dn_tuple):
            return '\n '.join([f"{key}: {value}" for rdn in dn_tuple for (key, value) in rdn]) if dn_tuple else 'N/A'

        subject = self.ssl_info.get('subject', ())
        subject_str = format_dn(subject)
        table.add_row("Subject", f"{subject_str}")

        issuer = self.ssl_info.get('issuer', ())
        issuer_str = format_dn(issuer)
        table.add_row("Issuer", f"{issuer_str}")

        not_before = self.ssl_info.get('notBefore', 'N/A')
        not_after = self.ssl_info.get('notAfter', 'N/A')
        table.add_row("Not Before", f"{not_before}")
        table.add_row("Not After", f"{not_after}")

        status, days_left = self.check_expiry()
        if status == "Expired":
            status_str = f"[red]{status} (Expired {-days_left} days ago)[/red]"
        elif status == "Expiring Soon":
            status_str = f"[red]{status} (Expires in {days_left} days)[/red]"
        else:
            status_str = f"[green]{status} (Expires in {days_left} days)[/green]"
        table.add_row("Expiry Status", f"{status_str}")

        san = self.ssl_info.get('subjectAltName', ())
        san_str = ', '.join([f"{key}: {value}" for key, value in san]) if san else 'N/A'
        table.add_row("Subject Alt Names", f"{san_str}")

        pawn.console.print(table)


class CallWebsocket:
    def __init__(
            self,
            url: str,
            verbose: int = 0,
            timeout: int = 10,
            on_send: Callable[..., Any] = None,
            on_receive: Callable[..., Any] = None,
            enable_status_console: bool = False,
            ssl_options=None,
            headers=None,
            ping_interval: int = 20,
            max_retries: int = 3,
            max_fail_count: int = 10,
            logger=None,
    ):
        """
        Initialize the CallWebsocket.

        :param url: WebSocket URL for connection.
        :param verbose: Level of verbosity for logging.
        :param timeout: Timeout duration for the WebSocket connection.
        :param on_send: Callable function for sending messages.
        :param on_receive: Callable function for receiving messages.
        :param enable_status_console: If True, status console will be enabled.
        :param ssl_options: SSL options for secure WebSocket connections.
        :param headers: Optional headers for WebSocket connection.
        :param ping_interval: Interval in seconds for sending ping messages.
        :param max_retries: Number of retries for a single reconnection attempt.
        :param max_fail_count: Maximum allowed total failure count before giving up.
        """

        self.url = url
        self.verbose = verbose
        self.timeout = timeout
        self.on_send = on_send
        self.on_receive = on_receive
        self.enable_status_console = enable_status_console

        self.ssl_options = ssl_options or {"cert_reqs": ssl.CERT_NONE}
        self.headers = headers or {}
        self.ping_interval = ping_interval
        self.max_retries = max_retries
        self.max_fail_count = max_fail_count
        self.fail_count = 0

        self.logger = ConsoleLoggerAdapter(logger, "CallWebsocketLogger", verbose > 0)

        self.is_connected = False
        self.ws_url = append_ws(url)
        self.http_url = append_http(url)
        self.status_console = Null()  # Placeholder for status console
        self.icon_rpc_helper = IconRpcHelper(url=f"{self.http_url}/api/v3")
        self._ws: WebSocket = None

        # Enable detailed trace if verbosity level is high
        if self.verbose > 3:
            enableTrace(True)

    def connect(self, api_path: str = ""):
        """
        Establish a WebSocket connection.

        :param api_path: Additional API path to append to the WebSocket URL.
        """

        try:
            self._connect(api_path)
            self.is_connected = True
            self.fail_count = 0
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self.is_connected = False
            self.fail_count += 1
            self.reconnect(api_path)

    def reconnect(self, api_path: str = ""):
        """
        Attempt to reconnect to the WebSocket server.

        :param api_path: API path for WebSocket reconnection.
        """
        self.is_connected = False

        if self.fail_count >= self.max_fail_count:
            pawn.console.log(f"Exceeded max fail count of {self.max_fail_count}. Stopping reconnection attempts.")
            self.close()
            return

        for attempt in range(self.max_retries):
            try:
                # self.logger.info(f"Attempting to reconnect... ({attempt + 1}/{self.max_retries})")
                self._connect(api_path)
                # Check if the connection was successful
                if self.is_connected:
                    self.logger.info("Reconnection successful")
                    self._handle_communication()
                    return
            except Exception as e:
                self.logger.error(f"Reconnection attempt ({attempt + 1}/{self.max_retries}) failed: {e}")
                time.sleep(2)  # Wait before retrying

        # Increment fail count after all retry attempts fail
        self.fail_count += 1

        # If max retries are reached without success, log and close the connection.
        self.logger.info("Max reconnection attempts reached. Closing WebSocket.")
        self.close()
        sys_exit("Max reconnection attempts reached. Closing WebSocket.")

    def _connect(self, api_path: str = ""):
        parsed_url = urlparse(self.ws_url)
        _ws_url = f"{self.ws_url}{api_path}" if parsed_url.path == "" else self.ws_url

        self._ws = create_connection(
            _ws_url,
            timeout=self.timeout,
            sslopt=self.ssl_options,
            header=[f"{k}: {v}" for k, v in self.headers.items()]
        )
        self._ws.settimeout(self.timeout)

    def run(self, api_path: str = "/api/v3/icon_dex/block", use_status_console: bool = False):
        """
        Start the WebSocket communication.

        :param api_path: API path for the WebSocket connection.
        :param use_status_console: Enable status console during the communication.
        """
        self.connect(api_path)
        if self.enable_status_console or use_status_console:
            with pawn.console.status("Call WebSocket") as self.status_console:
                self._handle_communication()
        else:
            self._handle_communication()

    def _handle_communication(self):
        """
        Handles sending and receiving messages over the WebSocket.
        """
        try:
            # Send initial message if on_send is defined
            message = self.on_send()
            if message:
                self._ws.send(message)
                if self.verbose > 1:
                    self.logger.debug(f"Sent: {message}")

            # Start a loop for receiving messages and sending periodic pings
            last_ping_time = time.time()
            while True:
                try:
                    # Handle pings
                    current_time = time.time()
                    if current_time - last_ping_time > self.ping_interval:
                        self._ws.ping()
                        last_ping_time = current_time
                        if self.verbose > 1:
                            self.logger.debug("Ping sent")

                    # Receive messages
                    response = self._ws.recv()
                    if self.verbose > 1:
                        self.logger.debug(f"Received: {response}")
                    self.on_receive(response)

                except (ConnectionResetError, WebSocketConnectionClosedException) as e:
                    pawn.console.log(f"WebSocket connection error: {e}")
                    self.reconnect()
                    break
                except Exception as e:
                    self.logger.error(f"Unexpected error during message handling: {e}")
        except Exception as e:
            self.logger.error(f"Failed to send initial message: {e}")
            self.close()

    def close(self):
        """
        Close the WebSocket connection.
        """
        if self._ws:
            self._ws.close()
            self.is_connected = False
            self.logger.info("WebSocket connection closed.")


class GoloopWebsocket(CallWebsocket):

    def __init__(self,
                 url,
                 verbose=0,
                 timeout=10,
                 blockheight=0,
                 sec_thresholds=4,
                 monitoring_target=None,
                 ignore_ssl=True,
                 network_info: NetworkInfo = None,
                 on_send: Callable[..., Any] = None,
                 on_receive: Callable[..., Any] = None,
                 logger=None,
                 ):

        self.url = url
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
        self.preps_info = {}
        self.network_info = network_info

        self.blockheight_now = 0

        self.transfers = []  # Stores parsed transfer data for reuse


        if ignore_ssl:
            disable_ssl_warnings()

        if self.verbose > 0:
            use_status_console = True
        else:
            use_status_console = False

        super().__init__(
            url=self.url,
            verbose=self.verbose,
            timeout=self.timeout,
            on_send=on_send or self.request_blockheight_callback,
            on_receive=on_receive or self.parse_blockheight,
            enable_status_console=use_status_console,
            logger=logger,
        )

    def request_blockheight_callback(self):
        if self.blockheight == 0:
            self.blockheight = self.get_last_blockheight()

        if not self.blockheight:
            raise ValueError(f"Failed to retrieve the block height. blockheight: {self.blockheight},  response: {self.get_response_content()}")

        pawn.console.log(f"Call request_blockheight_callback - blockheight: {self.blockheight:,}")

        self.fetch_and_store_preps_info()

        send_data = {
            "height": hex(self.blockheight)
        }
        return json.dumps(send_data)

    @staticmethod
    def _multiple_keys_exists(dict_items, *keys):
        for key in keys:
            if not keys_exists(dict_items, key):
                return False
        return True

    def parse_transfer_tx(self, confirmed_transaction_list=[]):
        """
        Parse a list of confirmed transactions, store transfer details,
        and log them.

        :param confirmed_transaction_list: A list of confirmed transactions.
        :return: A list of parsed transfer details.
        """
        self.transfers = []  # Clear previous transfers

        if isinstance(confirmed_transaction_list, list):
            for transaction in confirmed_transaction_list:
                transfer_data = self._parse_transaction_data(transaction)
                if transfer_data:
                    self.transfers.append(transfer_data)
                    self._log_transfer(**transfer_data)

        return self.transfers

    def _parse_transaction_data(self, transaction):
        """
        Extract and parse transfer details from a transaction.

        :param transaction: A transaction dictionary.
        :return: A dictionary containing parsed transfer details, or None if invalid.
        """
        _from = shorten_text(transaction.get('from'), width=None, shorten_middle=True)
        _to = shorten_text(transaction.get('to'), width=None, shorten_middle=True)
        _value = transaction.get('value')

        if _from and _to and _value:
            try:
                _value = int(_value, 16) / const.TINT
                if _value > 0:
                    return {"from_address": _from, "to_address": _to, "value": _value}
            except ValueError:
                pawn.console.log(f"Invalid value conversion in transaction: {_value}")

        return None

    def _log_transfer(self, from_address: str, to_address: str, value: float):
        """
        Log transfer details to the console.

        :param from_address: The sender's address.
        :param to_address: The recipient's address.
        :param value: The amount transferred in ICX.
        """
        pawn.console.log(f"[TRANSFER] {from_address} 👉 {to_address} 💰 {value} ICX")

    def parse_blockheight(self, response=None):
        response_json = json.loads(response)
        self.compare_diff_time = {}

        if response_json and response_json.get('hash'):
            hash_result = self.get_block_hash(response_json.get('hash'))
            if not hash_result or not hash_result.get('confirmed_transaction_list'):
                return

            confirmed_transaction_list = hash_result.get('confirmed_transaction_list')
            if confirmed_transaction_list:
                self.parse_transfer_tx(confirmed_transaction_list)

            self.blockheight_now = hash_result.get("height")
            pawn.set(LAST_EXECUTE_POINT=self.blockheight_now)
            self.block_timestamp = hash_result.get("time_stamp")

            if self.block_timestamp_prev != 0:
                self.compare_diff_time['block'] = abs(self.block_timestamp_prev - self.block_timestamp)

            tx_list = hash_result.get('confirmed_transaction_list')
            self.tx_count = len(tx_list)

            peer_id = self.preps_info.get(hash_result.get('peer_id'))
            if peer_id:
                peer_name = shorten_text(peer_id.get('name'), width=16, placeholder="..")
            else:
                peer_name = ""

            _message = (f"[[bold dodger_blue1]📦 {self.blockheight_now:,}[/bold dodger_blue1]] 📅 {date_utils.timestamp_to_string(self.block_timestamp)}, "
                        f"tx_cnt: {self.tx_count}, tx_hash: {shorten_text(hash_result.get('block_hash'), width=10, placeholder='..', shorten_middle=True)}, Validator: {peer_name}")

            pawn.console.debug(_message)
            self.status_console.update(_message)

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

    def get_response_content(self):
        response = self.icon_rpc_helper.response
        if response.get('json'):
            return response.get('json')
        return response.get('text')

    def get_last_blockheight(self) -> int:
        return self.execute_rpc_call(method='icx_getLastBlock', return_key="result.height")

    def get_preps(self):
        return self.execute_rpc_call(governance_address=const.CHAIN_SCORE_ADDRESS, method='getPReps', return_key="result.preps")

    def get_validator_info(self):
        return self.execute_rpc_call(
            governance_address=const.CHAIN_SCORE_ADDRESS,
            method='getValidatorsInfo',
            params={"dataType": "all"},
            return_key="result.validators"
        )

    def fetch_and_store_preps_info(self):
        try:
            platform_name = getattr(self.network_info, "platform", "icon")

            platform_methods = {
                "icon": (self.get_preps, "nodeAddress"),
                "havah": (self.get_validator_info, "node")
            }

            pawn.console.log(platform_methods)

            if platform_name not in platform_methods:
                raise ValueError("Unsupported platform")

            fetch_method, key_name = platform_methods[platform_name]

            preps_list = fetch_method()
            for prep in preps_list:
                if isinstance(prep, dict) and key_name in prep:
                    self.preps_info[prep[key_name]] = prep

        except Exception as error:
            pawn.console.log(error)

    def execute_rpc_call(self, method=None, params={},return_key=None, governance_address=None):
        if governance_address:
            response = self.icon_rpc_helper.governance_call(method=method, params=params, governance_address=governance_address, return_key=return_key)
        else:
            response = self.icon_rpc_helper.rpc_call(method=method, params=params, return_key=return_key)
        if not response:
            pawn.console.log(f"[yellow]\[warn][/yellow] Response  is None. method='{method}', "
                             f"return_key='{return_key}', {self.get_response_content()}")

        return response

    def get_block_hash(self, tx_hash):
        res = jequest(
            method="post",
            url=f"{self.http_url}/api/v3",
            data=generate_json_rpc(method="icx_getBlockByHash", params={"hash": tx_hash})
        )
        if res.get('json'):
            return res['json'].get('result')
        else:
            pawn.console.log(f"[red] {res}")

    def _get_tx_result(self, tx_hash):
        res = jequest(
            method="post",
            url=f"{self.http_url}/api/v3",
            data=generate_json_rpc(method="icx_getTransactionResult", params={"txHash": tx_hash})
        )
        json_response = res.get('json')
        if json_response:
            pawn.console.log(json_response)
            if json_response.get('error'):
                return json_response['error'].get('message')
            return json_response.get('result')
        else:
            pawn.console.log(f"[red] {res}")

    def get_tx_result(self, tx_hash, max_attempts=None):
        resp = self.icon_rpc_helper.get_tx_wait(tx_hash, max_attempts=max_attempts)
        if isinstance(resp, dict) and resp.get('result'):
            if resp['result'].get('failure'):
                return resp['result']['failure'].get('message')
            else:
                return "OK"
        else:
            return resp


class AsyncCallWebsocket(LoggerMixinVerbose):
    def __init__(
            self,
            url: str,
            verbose: int = 0,
            timeout: int = 10,
            on_send: Callable[..., str] = None,
            on_receive: Callable[..., None] = None,
            ssl_options=None,
            headers=None,
            ping_interval: int = 20,
            max_retries: int = 3,
            max_fail_count: int = 10,
            enable_status_console: bool = False,
            logger=None,
            session=None,
            additional_tasks: Optional[List[Callable[[], Awaitable]]] = None,
            **kwargs
    ):
        self.url = url
        self.verbose = verbose
        self.timeout = timeout
        self.on_send = on_send
        self.on_receive = on_receive
        self.ping_interval = ping_interval
        self.max_retries = max_retries
        self.max_fail_count = max_fail_count
        self.fail_count = 0
        self.is_connected = False
        self._ws = None
        self.session = session
        self.tasks = additional_tasks or []

        self.api_path = "/api/v3/icon_dex/block"
        self.ws_url = append_ws(f"{self.url}{self.api_path}")

        self.enable_status_console = enable_status_console
        self.status_console = None  # For rich console status
        self.status_info = {
            "blockheight": 0,
            "skip_start_block": 0,  # The block height where skipping started
            "current_skipped_block": 0,  # The block height currently being skipped
        }

        self.on_last_status = ""

        # self.logger = ConsoleLoggerAdapter(logger, "AsyncCallWebsocket", verbose > 0)
        # self.logger = setup_logger(logger, "pawnlib.http.AsyncCallWebsocket", verbose)
        # self.logger = logger or self.get_logger()

        self.init_logger(logger, verbose)

        if ssl_options is None:
            self.ssl_options = ssl.create_default_context()
            self.ssl_options.check_hostname = False
            self.ssl_options.verify_mode = ssl.CERT_NONE
        else:
            self.ssl_options = ssl_options

        self.headers = headers or {}

    async def connect(self, api_path: str = ""):
        if not api_path:
            api_path = self.api_path

        try:
            await self._connect(api_path)
            self.is_connected = True
            self.fail_count = 0
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            self.is_connected = False
            self.fail_count += 1
            await self.reconnect(api_path)

    async def reconnect(self, api_path: str = ""):
        if not api_path:
            api_path = self.api_path

        self.is_connected = False

        if self.fail_count >= self.max_fail_count:
            self.logger.error(f"Exceeded max fail count of {self.max_fail_count}. Stopping reconnection attempts.")
            await self.close()
            return

        for attempt in range(self.max_retries):
            try:
                await self._connect(api_path)
                if self.is_connected:
                    self.logger.info(f"Reconnection successful. status={self.status_info}")
                    await self.run_tasks()
                    return
            except Exception as e:
                self.logger.error(f"Reconnection attempt ({attempt + 1}/{self.max_retries}) failed: {e}")
                await asyncio.sleep(2)

        self.fail_count += 1
        self.logger.error("Max reconnection attempts reached. Closing WebSocket.")
        await self.close()
        sys_exit("Max reconnection attempts reached. Closing WebSocket.")

    async def _connect(self, api_path: str = ""):
        if not api_path:
            api_path = self.api_path

        if not self.session:
            session = aiohttp.ClientSession()
        else:
            session = self.session

        self.ws_url = append_ws(f"{self.url}{api_path}")
        try:
            self._ws = await session.ws_connect(
                self.ws_url,
                ssl=self.ssl_options,
                headers=self.headers,
                timeout=self.timeout
            )
            self.is_connected = True
            self.logger.info(f"Connected to {self.ws_url}")
        except aiohttp.ClientConnectionError as e:
            self.is_connected = False
            self.logger.error(f"WebSocket connection failed: {e}")
            raise

    async def run_tasks(self):
        task_list = [self._handle_communication()]
        task_list.extend([asyncio.create_task(task()) for task in self.tasks])
        await asyncio.gather(*task_list)

    async def run(self, api_path: str = "/api/v3/icon_dex/block"):
        if self.enable_status_console:
            with pawn.console.status("[bold green]Connecting to WebSocket...") as status:
                self.status_console = status
                await self.connect(api_path)
        else:
            await self.connect(api_path)

        await self.run_tasks()

    async def _handle_communication(self):
        last_ping_time = asyncio.get_event_loop().time()
        ping_task = asyncio.create_task(self._ping_loop(last_ping_time))
        try:
            # Send message if available
            if self.on_send:
                message = await self.on_send() if asyncio.iscoroutinefunction(self.on_send) else self.on_send()
                function_name = getattr(self.on_send, '__name__', 'Unknown')
                self.logger.debug(f"Sending message from {function_name}: {message}, type: {type(message)}")

                if message and isinstance(message, str):
                    if self.is_connected and self._ws and not self._ws.closed:
                        if self.verbose >2:
                            self.logger.debug(f"Sending message to WebSocket at {self.ws_url}")
                        await self._ws.send_str(message)
                        if self.verbose >2:
                            self.logger.debug(f"Message sent: {message}")
                    else:
                        self.logger.error("WebSocket is closed or not connected, cannot send message.")
                        await self.reconnect()
                else:
                    self.logger.warn("Invalid message: either None or not a string.")

            # Main loop for handling received messages
            while True:
                msg = await self._ws.receive()

                if msg.type == aiohttp.WSMsgType.TEXT:
                    if self.verbose >2:
                        self.logger.debug(f"Received: {str(msg.data).strip()}")
                    if self.on_receive:
                        await self.on_receive(msg.data)

                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    self.logger.warning("WebSocket connection closed by server.")
                    await self.reconnect()
                    break

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"WebSocket error: {self._ws.exception()}")
                    await self.reconnect()
                    break

                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    self.logger.warning("WebSocket is closing...")
                    await self.close()
                    break

                else:
                    self.logger.warning(f"Unknown message type: {msg.type}")
                    await self.reconnect()
                    break

        except aiohttp.ClientConnectionError as e:
            self.logger.error(f"WebSocket connection error: {e}")
            await self.reconnect()

        except aiohttp.ContentTypeError as e:
            self.logger.error(f"Content type error: {e}")
            await self.reconnect()

        except asyncio.CancelledError:
            self.logger.warning("Task was cancelled.")

        except Exception as e:
            notify_exception(e, logger=self.logger, additional_message=self.on_last_status)
            await self.close(exit_code=1)

        finally:
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                self.logger.info("Ping task cancelled.")

    async def _ping_loop(self, last_ping_time):
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - last_ping_time > self.ping_interval:
                if self.is_connected and self._ws and not self._ws.closed:
                    await self._ws.ping()
                    last_ping_time = current_time
                    if self.verbose > 1:
                        self.logger.debug("Ping sent")
                else:
                    self.logger.warn("WebSocket is closed, skipping ping.")
                    await self.reconnect()
            await asyncio.sleep(1)

    async def close(self, exit_on_close=True, exit_code=0):
        if self._ws and not self._ws.closed:
            await self._ws.close()
            self.is_connected = False
            self.logger.info("WebSocket connection closed.")
        else:
            self.logger.warn("WebSocket was already closed.")

        # Stop any ongoing tasks or operations if WebSocket is closed
        if self.enable_status_console and self.status_console:
            self.status_console.stop()

        if self.session:
            await self.session.close()

        if exit_on_close:
            from pawnlib.asyncio.async_helper import shutdown_async_tasks
            await shutdown_async_tasks(exit_on_shutdown=True, logger=self.logger, exit_code=exit_code)

    async def graceful_close(self, exit_code=0):
        """
        Gracefully close the event loop and clean up resources before exit.
        Args:
             exit_code (int): Exit code to return when exiting the system (default is 0).
        """
        try:
            loop = asyncio.get_running_loop()

            if loop.is_running():
                pending = asyncio.all_tasks(loop)
                if pending:
                    self.logger.info(f"Cancelling {len(pending)} pending tasks.")
                    for task in pending:
                        if not task.done() and not task.cancelled():
                            task.cancel()

                    for task in pending:
                        try:
                            await task
                        except asyncio.CancelledError:
                            self.logger.info(f"Task {task} cancelled successfully.")
                        except Exception as e:
                            self.logger.error(f"Error during task cancellation: {e}")

            self.logger.info("Event loop closed gracefully.")

        except Exception as e:
            self.logger.error(f"Error during graceful close: {e}")
        finally:
            self.logger.info(f"System shutting down gracefully with exit code {exit_code}.")
            sys.exit(exit_code)


class AsyncGoloopWebsocket(AsyncCallWebsocket):
    BLOCKHEIGHT_FILE = "last_blockheight.txt"
    SLACK_BLOCKHEIGHT_FILE = "last_slack_blockheight.txt"

    def __init__(
            self,
            url: str,
            verbose: int = 0,
            timeout: int = 10,
            blockheight: int = 0,
            sec_thresholds: int = 4,
            monitoring_target: Optional[str] = None,
            ignore_ssl: bool = True,
            network_info: Optional[NetworkInfo] = None,
            on_send: Optional[Callable[..., Any]] = None,
            on_receive: Optional[Callable[..., Any]] = None,
            logger: Optional[Union[logging.Logger, Console, ConsoleLoggerAdapter, Null]] = None,
            process_transaction: Optional[Callable[..., Any]] = None,
            address_filter: Optional[list] = None,
            send_slack: bool = True,
            slack_webhook_url: str = "",
            max_retries: int = 3,
            max_transaction_attempts: int = 10,
            check_tx_result_enabled: bool = True,
            ignore_data_types: list = None,
            session = None,
            preps_refresh_interval: int = 600,
            use_shorten_tx_hash: bool = True,
            bps_interval: int = 0,
            skip_until: int = 0,
            base_dir: str = "./",
    ):
        self.url = url
        self.verbose = verbose
        self.timeout = timeout
        self.blockheight = blockheight
        self.sec_thresholds = sec_thresholds
        self.monitoring_target = monitoring_target or ["block"]
        self.compare_diff_time = {}
        self.delay_cnt = {}
        self.block_timestamp_prev = 0
        self.block_timestamp = None
        self.tx_count = 0
        self.tx_timestamp = 0
        self.tx_timestamp_dt = None
        self.preps_info = {}
        self.network_info = network_info
        self.blockheight_now = 0
        self.blockheight_last = 0
        self.transfers = []  # Stores parsed transfer data for reuse
        # self.blockheight = blockheight

        self.ignore_data_types = ignore_data_types or ['base']
        self.send_slack = send_slack
        self.slack_webhook_url = slack_webhook_url
        self.max_transaction_attempts = max_transaction_attempts
        self.check_tx_result_enabled = check_tx_result_enabled

        self.init_logger(logger, verbose)
        self.logger.info("Start AsyncGoloopWebsocket")

        self.preps_refresh_interval = preps_refresh_interval
        self.use_shorten_tx_hash = use_shorten_tx_hash
        self.bps_interval = bps_interval
        self.skip_until = skip_until
        self.base_dir = base_dir

        if self.base_dir and not self.base_dir.endswith("/"):
            self.base_dir += "/"

        self.status_info = {}

        self.metrics_start_time = 0
        self.tps_tx_count = 0
        self.bps_block_count = 0
        self.start_block_height = 0
        self.last_logged_time = 0

        self.address_filter = address_filter or []
        if self.address_filter:
            self.valid_addresses = self.validate_address_filter(self.address_filter)
        else:
            self.logger.warning("The address_filter is not defined, so all transactions will be logged.")

        self.process_transaction_callback = process_transaction or self.default_process_transaction
        self.api_client = AsyncIconRpcHelper(url=url, logger=logger, session=session)

        if ignore_ssl:
            disable_ssl_warnings()

        if self.verbose > 0:
            use_status_console = True
        else:
            use_status_console = False

        super().__init__(
            url=self.url,
            verbose=self.verbose,
            timeout=self.timeout,
            on_send=on_send or self.request_blockheight_callback,
            on_receive=on_receive or self.handle_confirmed_transaction_list,
            enable_status_console=use_status_console,
            logger=logger,
            session=session,
            max_retries=max_retries,
            additional_tasks=[self.periodic_preps_update],
        )

    def read_last_processed_blockheight(self, filename, skip_log=False):
        """Read the last processed block height from a file."""
        filename = f"{self.base_dir}{filename}"
        if os.path.exists(filename):
            try:
                with open(filename, "r") as file:
                    blockheight = int(file.read().strip())
                    if not skip_log:
                        self.logger.info(f"🫡 Read last processed blockheight : {blockheight} on '{filename}'")
                    return blockheight  # Assuming block height is stored in hex
            except (ValueError, IOError) as e:
                self.logger.error(f"Error reading block height file: {e} on '{filename}'")
        else:
            if not skip_log:
                self.logger.info(f"Block recorded file not found - '{filename}'")
        return None

    def write_last_processed_blockheight(self, filename, blockheight):
        """Write the last successfully processed block height to a file."""
        filename = f"{self.base_dir}{filename}"
        try:
            file_exists = os.path.exists(filename)

            with open(filename, "w") as file:
                file.write(f"{blockheight}")

            if not file_exists:
                self.logger.info(f"Block height file '{filename}' not found. Creating new file.")

            self.logger.debug(f"Successfully processed block {blockheight}. Block height recorded on '{filename}'.")

        except IOError as e:
            self.logger.error(f"Error writing block height to file: {e} on '{filename}'")

        except Exception as e:
            self.logger.error(f"Unexpected error occurred while writing block height: {e} on '{filename}'")


    async def run_from_blockheight(self, blockheight=None, api_path: str = "/api/v3/icon_dex/block"):
        """
        Run starting from a specified block height, the latest block, or the last recorded block height.

        :param blockheight: The block height to start from.
                            - If None, tries to resume from the last saved block.
                            - If 0, starts from the latest block.
                            - Otherwise, starts from the provided block height.
        """

        if blockheight and is_hex(blockheight):
            blockheight = hex_to_number(blockheight)

        try:
            latest_blockheight = await retry_operation(
                self.api_client.get_last_blockheight,
                max_attempts=self.max_transaction_attempts,
                delay=2,
                logger=self.logger
            )
        except Exception as e:
            self.logger.error(f"Failed to fetch block_height after {self.max_transaction_attempts} attempts: {e}")
            raise ValueError(f"Failed to fetch block_height after {self.max_transaction_attempts} attempts: {e}")

        if blockheight is not None and blockheight > 0:
            if blockheight > latest_blockheight:
                self.logger.warning(f"Requested block height {blockheight} is higher than the latest block {latest_blockheight}. Starting from the latest block.")
                self.blockheight = latest_blockheight
            else:
                self.blockheight = blockheight
                self.logger.info(f"Starting from specified block height: {blockheight}")
        elif blockheight == 0:
            self.blockheight = latest_blockheight
            self.logger.info(f"Starting from the most recent block height: {self.blockheight}")
            self.write_last_processed_blockheight(self.SLACK_BLOCKHEIGHT_FILE, latest_blockheight)
        else:
            self.blockheight = self.read_last_processed_blockheight(self.BLOCKHEIGHT_FILE)

            if not isinstance(self.blockheight, int) or self.blockheight > latest_blockheight:
                self.logger.warning(
                    f"Resumed block height {self.blockheight} exceeds the latest block height {latest_blockheight}. "
                    f"Starting from the latest block height instead."
                )
                self.blockheight = latest_blockheight

            elif self.blockheight:
                self.logger.info(f"Resuming from last processed block height: {self.blockheight}")

                if isinstance(latest_blockheight, int) and isinstance(self.blockheight, int):
                    difference = abs(latest_blockheight - self.blockheight)
                    threshold = 100
                    if difference > threshold:
                        self.logger.warning(f"⚠️⚠️ Latest blockheight = {latest_blockheight} ⛓️, "
                                            f"Current blockheight = {self.blockheight} ⛓️, "
                                            f"Difference = {difference} 🚨 exceeds threshold {threshold} 📉")
                    else:
                        self.logger.info(f"✅ Latest blockheight = {latest_blockheight} ⛓️, "
                                         f"Current blockheight = {self.blockheight} ⛓️, "
                                         f"Difference = {difference} 😊")
            else:
                self.blockheight = latest_blockheight
                self.logger.info(f"No previous block height found. Starting from the latest block: {self.blockheight}")

        # Connect to WebSocket and start running tasks
        if self.enable_status_console:
            with pawn.console.status("[bold green]Connecting to WebSocket...") as status:
                self.status_console = status
                await self.connect(api_path)
        else:
            await self.connect(api_path)

        await self.run_tasks()

    async def initialize(self, session=None):
        if session:
            self.session = session
        await self.api_client.initialize()

    async def periodic_preps_update(self):
        while True:
            try:
                await self.fetch_and_store_preps_info()
                self.logger.info(f"P-Reps information updated. blockheight={self.status_info.get('block_height')}")
            except Exception as e:
                self.logger.error(f"Failed to update P-Reps information: {e}. blockheight={self.status_info.get('block_height')}")
            await asyncio.sleep(self.preps_refresh_interval)

    async def request_blockheight_callback(self):
        if self.blockheight == 0:
            self.blockheight = await self.api_client.get_last_blockheight()

        if not self.blockheight:
            # raise ValueError(f"Failed to retrieve the block height. blockheight: {self.blockheight}, response: {await self.get_response_content()}")
            raise ValueError(f"Failed to retrieve the block height. blockheight: {self.blockheight}, response: ")

        self.logger.info(f"🚀 Requesting block height: {self.blockheight}")
        send_data = {
            "height": hex(self.blockheight)
        }
        return json.dumps(send_data)

    async def fetch_and_store_preps_info(self):
        try:
            platform_name = getattr(self.network_info, "platform", "icon")
            platform_methods = {
                "icon": (self.api_client.get_preps, "nodeAddress"),
                "havah": (self.api_client.get_validator_info, "node")
            }

            if platform_name not in platform_methods:
                raise ValueError("Unsupported platform")

            fetch_method, key_name = platform_methods[platform_name]
            preps_list = await fetch_method()
            for prep in preps_list:
                if isinstance(prep, dict) and key_name in prep:
                    self.preps_info[prep[key_name]] = prep
        except Exception as error:
            self.logger.error(f"Error fetching P-Reps with {fetch_method.__name__}(): {error}")

    async def parse_blockheight(self, response=None, delay=2):
        """
        Parse block height with retry logic.

        :param response: The response containing block height data.
        :param delay: Delay (in seconds) between retry attempts.
        """
        try:
            self.blockheight_now = await retry_operation(
                get_blockheight,
                max_attempts=self.max_transaction_attempts,
                delay=delay,
                response=response
            )
            self.logger.info(f"Block height parsed: {hex_to_number(self.blockheight_now, debug=True)}")
        except Exception as e:
            self.logger.error(f"Failed to parse block height after {self.max_transaction_attempts} attempts: {e}")

    async def calculate_tps_bps(self, block_height, tx_count):
        """ 10초 단위로 TPS 및 BPS 계산 """
        current_time = time.time()

        if self.metrics_start_time == 0:
            self.metrics_start_time = current_time  # 10초 측정 시작 시간
            self.tps_tx_count = 0  # 10초 동안 처리된 TX 개수
            self.bps_block_count = 0  # 10초 동안 수신된 블록 개수
            self.start_block_height = block_height  # 10초 동안의 시작 블록
            self.last_logged_time = current_time

        self.tps_tx_count += tx_count
        self.bps_block_count += 1

        if current_time - self.metrics_start_time >= self.bps_interval:
            elapsed_time = current_time - self.metrics_start_time
            end_block_height = block_height  # 마지막 블록 높이

            tps = self.tps_tx_count / elapsed_time if elapsed_time > 0 else 0
            bps = self.bps_block_count / elapsed_time if elapsed_time > 0 else 0

            # self.logger.info(
            #     f"📊 [{self.bps_interval}s Stats] TPS: {tps:.2f} TX/s | BPS: {bps:.2f} Blocks/s | "
            #     f"TXs: {self.tps_tx_count} | Blocks: {self.bps_block_count} | "
            #     f"Block Range: {self.start_block_height} → {end_block_height} | "
            #     f"Elapsed: {elapsed_time:.2f}s"
            # )

            self.logger.info(
                f"📊 [{self.bps_interval}s Stats] BPS: {bps:.2f} Blocks/s | "
                f"Blocks: {self.bps_block_count} | "
                f"Block Range: {self.start_block_height} → {end_block_height} | "
                f"Elapsed: {elapsed_time:.2f}s"
            )

            # # Slack 알림 전송
            # if self.bps_block_count > 0 or self.tps_tx_count > 0:
            #     slack_message = (
            #         f"🚀 [10s Network Update]\n"
            #         f"🔹 TPS: {tps:.2f} TX/s\n"
            #         f"🔹 BPS: {bps:.2f} Blocks/s\n"
            #         f"📈 TXs: {self.tps_tx_count} | Blocks: {self.bps_block_count}\n"
            #         f"🔄 Block Range: {self.start_block_height} → {end_block_height} | Elapsed: {elapsed_time:.2f}s"
            #     )
            #     await self.send_slack_notification(slack_message)

            self.metrics_start_time = current_time
            self.tps_tx_count = 0
            self.bps_block_count = 0
            self.start_block_height = block_height  # 새로운 10초 구간의 시작 블록

    async def handle_confirmed_transaction_list(self, response):
        try:
            response_json = json.loads(response)
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON response: {response}")
            return
        tx_hash = response_json.get('hash')
        block_height = hex_to_number(response_json.get('height'))
        self.blockheight_now = response_json.get("height")
        readable_block_height = hex_to_number(self.blockheight_now, debug=True)

        if self.bps_interval > 0:
            await self.calculate_tps_bps(block_height, 0)

        if self.skip_until:
           last_slack_blockheight = self.skip_until
        else:
            last_slack_blockheight = self.read_last_processed_blockheight(self.SLACK_BLOCKHEIGHT_FILE, skip_log=True)

        if block_height and last_slack_blockheight and block_height <  last_slack_blockheight + 1:
            if not self.status_info.get('skip_start_block'):
                self.logger.info(f"⏩ [Skipping Started] Block {block_height}  👉 {last_slack_blockheight} - Preventing duplicate processing.")
                self.status_info['skip_start_block'] = block_height

            self.write_last_processed_blockheight(self.BLOCKHEIGHT_FILE, block_height)
            self.logger.debug(f"⏩ Block {block_height} skipped to prevent duplicate processing, until last_slack_blockheight={last_slack_blockheight}")
            return  # Slack 전송 스킵

        if tx_hash:
            if self.status_info.get('skip_start_block'):
                self.status_info['skip_start_block'] = 0
                self.status_info['current_start_block'] = block_height
                self.logger.info(f"✅ [Skipping Stopped] Resuming at Block {block_height} - {self.status_info}")

            def is_success(result):
                if not result:
                    return False
                return check_key_and_type(result, "confirmed_transaction_list", list)

            block_data = {}
            try:
                block_data = await retry_operation(
                    self.api_client.get_block_hash,
                    max_attempts=self.max_transaction_attempts,
                    delay=2,
                    tx_hash=tx_hash,
                    success_criteria=is_success,
                    logger=self.logger
                )
            except (TimeoutError, ConnectionError) as e:
                self.logger.error(f"Network-related error while fetching block data on {readable_block_height}: {e}")
            except Exception as e:
                self.logger.error(f"Failed to parse transaction after {self.max_transaction_attempts} attempts for tx hash {tx_hash}: {e}")

            if block_data is None or not isinstance(block_data, dict):
                self.logger.error(f"Invalid block data received for tx hash {tx_hash}")
                from pawnlib.utils.notify import send_slack
                send_slack(
                    msg_text=f"Invalid block data received for tx hash {tx_hash} in blockheight {readable_block_height} block_data={str(block_data)}",
                    # msg_text=dict(Text=f"Invalid block data received for tx hash {tx_hash} in blockheight {readable_block_height}",
                    #               block_data={str(block_data)}),
                    status="failed",
                    msg_level="error",
                    icon_emoji=":alert:"
                )
                await self.graceful_close(1)
                # await shutdown_async_tasks(1)
                return

            try:
                validator_info = self.get_prep_info(block_data.get('peer_id'), apply_format=False)
                time_stamp = date_utils.timestamp_to_string(block_data.get('time_stamp', 0))
            except Exception as e:
                validator_info, time_stamp =  "",""
                self.logger.error(f"{e} - {block_data}")

            confirmed_transactions = block_data.get('confirmed_transaction_list', [])
            confirmed_transactions_length = len(confirmed_transactions)
            self.write_last_processed_blockheight(self.BLOCKHEIGHT_FILE, block_height)
            self.status_info['block_height'] = block_height

            if self.blockheight_now:
                # self.logger.info(f"Block height parsed: {hex_to_number(self.blockheight_now, debug=True)}, TX: {confirmed_transactions_length}, Validator={validator_info}, "
                #                  f" 📅 {time_stamp}")
                if self.verbose > 1:
                    self.logger.info(
                        f"🔗 Block: {hex_to_number(self.blockheight_now, debug=False)}, "
                        f"TXs: {confirmed_transactions_length}, "
                        f"📅 {time_stamp}, "
                        f"Validator: {validator_info} "
                    )
                # self.logger.info(f"Block height parsed: {hex_to_number(self.blockheight_now, debug=True)}, TX: {confirmed_transactions_length}")
            if confirmed_transactions:
                if self.verbose > 4:
                    self.logger.debug(f"block_data={block_data}")
                tasks = [self.process_transaction_callback(tx, block_height) for tx in confirmed_transactions]
                # await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.gather(*tasks)

            else:
                if isinstance(confirmed_transactions, list) and len(confirmed_transactions) == 0:
                    return
                self.logger.error(f"confirmed_transaction_list not found - {block_data}")

    def validate_address_filter(self, address_filter: Union[str, list, None]):
        valid_addresses = []
        invalid_addresses = []

        if isinstance(address_filter, str) and "," in address_filter:
            address_filter_list = address_filter.split(',')
        else:
            address_filter_list = address_filter

        for address in address_filter_list:
            _address = address.strip()
            if is_valid_token_address(_address):
                valid_addresses.append(_address)
            else:
                invalid_addresses.append(_address)

        if invalid_addresses:
            self.log_invalid_addresses(invalid_addresses)
            raise ValueError(f"Validation failed: {len(invalid_addresses)} invalid address(es) found in ADDRESS_FILTER.")

        return valid_addresses

    def log_invalid_addresses(self, invalid_addresses: list):
        for invalid_address in invalid_addresses:
            self.logger.error(f"[red] Invalid hx address - '{invalid_address}' (Please check the format or the address validity)")

    def highlight_address(self, address):
        """
        Highlights the address if it's part of the address_filter.
        """
        if address in self.address_filter:
            # Apply color for console log and bold for Slack messages
            return f"[bold red]{address}[/bold red]"  # For logs
        return address

    def get_prep_info(self, address=None, key="name", apply_format=True):
        """
        Retrieves the requested information from preps_info for a given address.

        :param address: The address to lookup in preps_info.
        :param key: The key for the desired value (default is 'name').
        :param apply_format: If True, applies format_text to the returned value for Slack formatting (default is False).
        :return: A formatted string with the value in parentheses, or an empty string if not found.
        """
        if address != "Unknown" and address in self.preps_info:
            return_value = FlatDict(self.preps_info[address]).get(key)
            if return_value:
                if apply_format:
                    return f" ({format_text(return_value, style='code')})"
                else:
                    return f"{return_value}"
        return ""

    async def default_process_transaction(self, tx, block_height):
        """
        Process the individual transactions.
        """
        tx_data = {}
        self.on_last_status = f"Blockheight: {block_height}"
        block_height_text = f"🧱{block_height:,}"
        try:
            tx_data = tx.get('data')
            data_type = tx.get('dataType', "send") if tx else None

            from_address = tx.get('from', 'Unknown')
            to_address = tx.get('to', 'Unknown')

            if data_type in self.ignore_data_types:
                # await self.log_message(f"IGNORED dataType: {data_type}", level="debug")
                return

            # Check for filtering
            from_highlighted = self.highlight_address(from_address)
            to_highlighted = self.highlight_address(to_address)

            from_prep_label = self.get_prep_info(from_address)
            to_prep_label = self.get_prep_info(to_address)

            if not from_address in self.address_filter and not to_address in self.address_filter:
                self.logger.debug(f"Transaction passed: {from_address}{from_prep_label} 👉{to_address}{to_prep_label}")
                return

            method = tx_data.get("method", "Send") if tx_data and isinstance(tx_data, dict) else "Send"
            tx_hash = tx.get('txHash', "")

            if self.use_shorten_tx_hash:
                shorten_tx_hash = get_shortened_tx_hash(tx_hash)
            else:
                shorten_tx_hash = ""

            if isinstance(self.network_info, NetworkInfo) and self.network_info.tracker:
                _tracker_api_url = f"{self.network_info.tracker}/transaction"
                full_tx_hash = format_link(f"{_tracker_api_url}/{tx_hash}", text=f"[Check the {self.network_info.network_name.title()} Tracker] " )
            else:
                full_tx_hash = f"_{str(tx_hash)}_"

            value = hex_to_number(tx.get('value', 0))

            if method == "setStake":
                stake_value = self.get_stake_value(tx_data)
                await self.log_message(
                    f"🔵 <Staking> {block_height_text} {from_highlighted}{from_prep_label} has staked 💰 {stake_value}.",
                    slack_additional_message=full_tx_hash,
                    level="info",
                    block_height=block_height
                )

            elif method == "unStake":
                stake_value = self.get_stake_value(tx_data)
                await self.log_message(
                    f"🔵 <Staking> {block_height_text} {from_highlighted}{from_prep_label} has unstaked 💰 {stake_value}.",
                    slack_additional_message=full_tx_hash,
                    level="info",
                    block_height=block_height
                )

            elif method == "Send":
                _value = self.formated_icx_value(tx.get('value', 0))

                if data_type == "send":
                    _data_type_text = ""
                else:
                    _data_type_text = f" {data_type}"

                await self.log_message(
                    f"{block_height_text} 💸 {shorten_tx_hash}<Send{_data_type_text}> {from_highlighted}{from_prep_label} 👉 {to_highlighted}{to_prep_label} 💰 {_value} ",
                    slack_additional_message=full_tx_hash,
                    level="info",
                    block_height=block_height
                )
                # await self.log_message(
                #     f"💸TX ID: <{shorten_tx_hash}> <Send{_data_type_text}> \n"
                #     f"🗄 From:  {from_highlighted}{from_prep_label} \n"
                #     f"👉 To:  {to_highlighted}{to_prep_label} \n"
                #     f"💰 Amount:  {_value} ",
                #     slack_additional_message=full_tx_hash,
                #     level="info"
                # )
            else:

                await self.log_message(
                    f"🔶 <{block_height_text}> <{method}> {from_highlighted} performed action with data: {tx_data}", level="info", block_height=block_height
                )
            if self.check_tx_result_enabled:
                # tx_result = await self.ws_instance.get_tx_result(tx_hash)
                tx_result = await self.api_client.get_tx_result(tx_hash)
                if tx_result == "OK":
                    await self.log_message(f"✅ {shorten_tx_hash} TX Result received: {tx_result}",
                                           slack_additional_message=full_tx_hash,
                                           level="info", block_height=block_height)
                else:
                    await self.log_message(f"❌ {shorten_tx_hash} Failed to retrieve TX Result: {tx_result}",
                                           slack_additional_message=full_tx_hash,
                                           level="error", block_height=block_height)
        except Exception as e:
            await self.log_message(f"Error processing transaction: {e}", level="error")

        finally:
            if tx_data and isinstance(tx_data, dict):
                tx_data.clear()  # Clear data to avoid memory leaks

    @staticmethod
    def formated_icx_value(value):
        try:
            int_value = hex_to_number(value, is_tint=True)
            return f"`{int_value:,} ICX` ({value})"
        except (KeyError, TypeError, ValueError):
            return f"`N/A ICX` ({value})"

    def get_stake_value(self, tx_data, is_tint=True):
        try:
            # return hex_to_number(tx_data['params']['value'], is_comma=True, is_tint=is_tint)
            return self.formated_icx_value(tx_data['params']['value'])
        except (KeyError, TypeError, ValueError):
            return "N/A"

    def get_send_value(self, tx_data, is_tint=True):
        try:
            return hex_to_number(tx_data['params']['value'], is_comma=True, is_tint=is_tint)
        except (KeyError, TypeError, ValueError):
            return "N/A"

    async def log_message(self, message, slack_additional_message="", level="info", stack_level=4, block_height=None):
        """
        Logs a message using the specified level and optionally sends to Slack.

        :param message: The message to log.
        :param slack_additional_message: Additional message to send along with Slack (optional).
        :param level: The logging level (e.g., 'info', 'error', 'debug').
        :param stack_level: stack level
        :param block_height: block height
        """
        try:
            # Log to console using the specified log level
            console_message = self.format_message(message, for_console=True)

            if hasattr(self.logger, level):
                log_method = getattr(self.logger, level)
                log_method(console_message, stacklevel=stack_level)
            else:
                self.logger.info(console_message, stacklevel=stack_level)

            # Optionally send to Slack asynchronously
            if self.send_slack and level != "debug":
                if block_height:
                    self.write_last_processed_blockheight(self.SLACK_BLOCKHEIGHT_FILE, block_height)

                asyncio.create_task(self.send_slack_notification(f"{message} {slack_additional_message}", level=level))

        except Exception as e:
            if hasattr(self.logger, "error"):
                self.logger.error(f"Logging failed with error: {e}")

    def format_message(self, message: str, for_console: bool = True):
        """
        Formats a message for either console or Slack.

        :param message: The original message.
        :param for_console: True if formatting for console, False for Slack.
        :return: Formatted message.
        """
        if for_console:
            return message
        else:
            return message.replace("[bold red]", "*").replace("[/bold red]", "*")  # Slack uses * for bold

    @staticmethod
    def get_slack_color_by_level(level):
        """
        Returns a color code for Slack messages based on log level.

        :param level: The log level (e.g., 'warn', 'error', 'info', 'critical').
        :return: Hex color code as a string.
        """
        if level in ["warn", "warning"]:
            return "#ffcc00"  # Yellow for warnings
        elif level == "error":
            return "#ff0000"  # Red for errors
        elif level == "critical":
            return "#ff4500"  # Orange for critical issues
        else:
            return "#36a64f"  # Green for info and other messages

    async def send_slack_notification(self, message, level="info"):
        """
        Send a message to Slack using attachments to add color and timestamp.

        :param message: The message to send to Slack.
        :param level: The log level (e.g., 'warn', 'error', 'info').
        """
        if self.slack_webhook_url:
            formatted_message = self.format_message(message, for_console=False)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "attachments": [
                            {
                                "fallback": f"Notification: {formatted_message}",
                                "color": self.get_slack_color_by_level(level),  # Green color for the attachment
                                "pretext": f"*Notification received at {timestamp}:*",
                                "text": formatted_message,
                                "mrkdwn_in": ["text", "pretext"],  # Enable Markdown in 'text' and 'pretext'
                            }
                        ]
                    }

                    # payload = {"text": formatted_message}  # Slack Markdown format

                    async with session.post(self.slack_webhook_url, json=payload) as response:
                        if response.status != 200:
                            self.logger.error(f"Failed to send Slack notification: {response.text}")
            except Exception as e:
                self.logger.error(f"Error sending Slack message: {e}")


class AsyncIconRpcHelper(LoggerMixinVerbose):
    """
    A helper class for making asynchronous RPC calls to the ICON network.
    Provides methods to interact with the ICON blockchain, such as fetching blocks,
    transactions, and network information.

    Attributes:
        url (str): The base URL for the RPC endpoint.
        logger (Optional[Union[logging.Logger, Console, ConsoleLoggerAdapter, Null]]): Logger instance for logging.
        session (aiohttp.ClientSession): HTTP session for making requests.
        verbose (bool): Flag to enable verbose logging.
        timeout (int): Request timeout in seconds.
        retries (int): Number of retry attempts for failed requests.
        return_with_time (bool): Whether to return elapsed time with responses.
        max_concurrency (int) : Number of max concurrency

    Methods:
        initialize(): Initializes the aiohttp session if not already initialized.
        close(): Closes the aiohttp session.
        execute_rpc_call(): Executes an RPC call to the ICON network.
        fetch(): Makes a generic HTTP request (GET or POST).
        get_block_hash(): Fetches block information by hash.
        get_last_blockheight(): Retrieves the height of the last block on the blockchain.
        get_network_info(): Fetches network information from the ICON blockchain.
        get_preps(): Retrieves a list of P-Reps from the ICON network.
        get_validator_info(): Retrieves validator information from the ICON network.
        get_tx_result(): Fetches transaction results, with optional retries and waiting.

    Example:

        .. code-block:: python

            import asyncio
            from pawnlib.utils.http import AsyncIconRpcHelper

            async def main():
                async with AsyncIconRpcHelper(url="https://icon-node-url.com") as rpc_helper:
                    # Fetch last block height
                    last_height = await rpc_helper.get_last_blockheight()
                    print(f"Last Block Height: {last_height}")

                    # Get block hash by transaction hash
                    block_hash = await rpc_helper.get_block_hash(tx_hash="0x1234...")
                    print(f"Block Hash: {block_hash}")

                    # Fetch P-Reps
                    preps = await rpc_helper.get_preps()
                    print(f"P-Reps: {preps}")

            asyncio.run(main())
    """

    def __init__(
            self,
            url: str = "",
            logger: Optional[Union[logging.Logger, Console, ConsoleLoggerAdapter, Null]] = None,
            session=None,
            verbose=True,
            timeout=10,
            retries=3,
            return_with_time: bool = False,
            max_concurrency: int = 20,
            # loop=None,
            **kwargs
    ):
        self.url = url
        # self.logger = logger
        self.timeout = timeout
        # self.logger = setup_logger(logger, "pawnlib.http.AsyncIconRpcHelper", verbose=verbose)
        self.init_logger(logger, verbose)
        # self.logger = self.get_logger()
        self.retries = retries
        self.return_with_time = return_with_time
        self.session = session
        self.max_concurrency = max_concurrency
        self.last_response = None
        self.semaphore = asyncio.Semaphore(max_concurrency)
        # self.loop = loop or asyncio.get_running_loop()
        self._own_session = False
        
        if session is None:
            self.session = None
        elif session == aiohttp.ClientSession:
            self.session = None
        else:            
            self.session = session
            self._own_session = False
            
        self.logger.info(f"Start AsyncIconRpcHelper with max_concurrency={self.max_concurrency}")
        
        self.connector = aiohttp.TCPConnector(
            limit=max_concurrency,
            ssl=kwargs.get('ssl', False),
            force_close=kwargs.get('force_close', True),
            ttl_dns_cache=kwargs.get('ttl_dns_cache', 300)
        )    

    async def adjust_concurrency(self, new_max: int):
        """
        Dynamically adjusts the maximum concurrency limit for asynchronous requests.

        Updates both the semaphore and TCP connector limits while migrating existing
        tasks to the new concurrency configuration.

        Args:
            new_max (int): New maximum number of concurrent connections (must be ≥1)

        Raises:
            ValueError: If new_max is less than 1
        """
        self.max_concurrency = new_max
        self.connector._limit = new_max
        old_sem = self.semaphore
        self.semaphore = asyncio.Semaphore(new_max)
        for _ in range(min(new_max, old_sem._value)):
            self.semaphore.release()

    @property
    def concurrency_usage(self):
        """
        Monitors current concurrency utilization.

        Returns:
            dict: Dictionary containing concurrency metrics:
                - active (int): Number of currently used connections
                - available (int): Number of available connections
                - max (int): Maximum allowed concurrent connections
        """
        return {
            "active": self.max_concurrency - self.semaphore._value,
            "available": self.semaphore._value,
            "max": self.max_concurrency
        }

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self):
        if self._own_session and hasattr(self, 'session') and self.session:
            if not self.session.closed:
                await self.session.close()
                self.logger.debug("Session explicitly closed")
            if self.session in _ACTIVE_SESSIONS:
                _ACTIVE_SESSIONS.remove(self.session)  # 추적 목록에서 제거
            self.session = None

    def __del__(self):
        if hasattr(self, 'session') and self.session and not self.session.closed:            
            self.logger.debug("Unclosed session will be handled at program exit")

    async def initialize(self):
        self.logger.debug(f"[INIT START] Session={self.session}, closed={self.session.closed if self.session else 'None'}")
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
            _ACTIVE_SESSIONS.add(self.session)  # 전역 목록에 세션 추가
            self._own_session = True
            self.logger.debug(f"[INIT] Created new session")
        else:
            if self.session not in _ACTIVE_SESSIONS:
                _ACTIVE_SESSIONS.add(self.session)  # 기존 세션도 추적
            self._own_session = False
            self.logger.debug("[INIT] Using existing session from parent")
        self.logger.debug(f"[INIT END] Session={self.session}, own_session={self._own_session}")
        return self
        
    def _check_session(self):
        if not self.session or self.session.closed:
            self.last_response = {
                "data": None,
                "status": 0,
                "error": "AIOHTTP session is closed or not initialized.",
                "elapsed_time_ms": 0
            }            
            error_message = "AIOHTTP session is closed or not initialized."
            self.logger.error(self.last_response["error"])
            raise RuntimeError(self.last_response["error"])

    async def execute_rpc_call(self, method=None, params: dict = {}, url=None, return_key=None, governance_address=None, return_on_error=True, keep_lists=True):
        """
        Execute an RPC call to the ICON network.
        """
        await self.initialize()

        if url:
            _url = url
        else:
            _url = self.url
        endpoint = append_api_v3(_url)
        if governance_address:
            request_data = {
                "jsonrpc": "2.0",
                "method": "icx_call",
                "params": {
                    "to": governance_address,
                    "dataType": "call",
                    "data": {
                        "method": method,
                        "params": params
                    }
                },
                "id": 1
            }
        else:
            request_data = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": 1
            }
        return await self._make_request(
            http_method="post",
            endpoint=endpoint,
            data=request_data,
            return_key=return_key,
            return_on_error=return_on_error,
            keep_lists=keep_lists,
        )

    async def fetch(self, path="", data="", http_method="get", url="", headers=None, return_key=None, return_on_error=True, return_first=False, list_index=None, retries=None):
    # async with self.semaphore:
        if url:
            endpoint = append_http(url)
        else:
            endpoint = f"{remove_path_from_url(self.url)}{path}"
        self.logger.debug(f"[FETCH START] {endpoint}, Session={self.session}")

        if not retries:
            retries = self.retries

        return await self._make_request(
            http_method=http_method,
            endpoint=endpoint,
            data=data,
            headers=headers,
            return_key=return_key,
            return_on_error=return_on_error,
            return_first=return_first,
            list_index=list_index,
            retries=retries
        )

    def check_aio_session(self, log_exception=True, return_on_error=False):
        if not self.session or self.session.closed:            
            self.last_response = {
                "data": None,
                "status": 0,
                "error": "AIOHTTP session is closed or not initialized.",
                "elapsed_time_ms": 0
            }            
            if log_exception:
                self.logger.exception(self.last_response["error"])
            else:
                self.logger.error(self.last_response["error"], exc_info=False)
            if return_on_error:
                return {}
            else:
                raise Exception(self.last_response['error'])

    async def _make_request(
            self,
            http_method: str,
            endpoint: str,
            data: Optional[Union[Dict, str]] = None,
            headers: Optional[Dict[str, str]] = None,
            return_key: Optional[str] = None,
            return_on_error: bool = True,
            return_first: bool = False,
            list_index: Optional[int] = None,
            retries: int = 3,
            backoff_factor: float = 0.5,
            keep_lists: bool = False,
            log_exception: bool = False,
            return_with_time: Optional[bool] = None
    ) -> Any:
        """
        Helper method to make HTTP requests with retry and timeout support.

        Args:
            http_method (str): HTTP method ('GET', 'POST', etc.).
            endpoint (str): API endpoint or full URL.
            data (dict or str, optional): Payload for POST requests or query parameters for GET.
            headers (dict, optional): HTTP headers.
            return_key (str, optional): Key to extract from the JSON response.
            return_on_error (bool, optional): Whether to return data on error responses.
            return_first (bool, optional): If True and response is a list, return the first item.
            list_index (int, optional): If provided and response is a list, return the item at this index.
            retries (int, optional): Number of retry attempts. Defaults to 3.
            backoff_factor (float, optional): Backoff factor for exponential delay. Defaults to 0.5.
            keep_lists (bool, optional): Whether to keep lists in flattened data.
            log_exception (bool, optional): Whether to log exceptions.
            return_with_time (bool, optional): If True, return response data along with the elapsed time.

        Returns:
            Any: Processed response data, or a tuple of response data and elapsed time.
        """
        # Use class-level default for return_with_time if not explicitly provided
        if return_with_time is None:
            return_with_time = getattr(self, "return_with_time", False)

        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self._check_session()
        self.logger.debug(f"Making {http_method.upper()} request to {endpoint} with data: {data}")

        # Ensure session is valid
        self.check_aio_session(log_exception, return_on_error=False)
        self.last_response = {}

        for attempt in range(1, retries + 1):
            start_time = time.time()  # Start timer for elapsed time
            try:
                response_text = ""

                timeout = aiohttp.ClientTimeout(total=self.timeout)
                if http_method.upper() == 'GET':
                    async with self.session.get(endpoint, params=data, headers=headers, timeout=timeout) as resp:                        
                        response_text = await resp.text()
                elif http_method.upper() == 'POST':
                    payload = json.dumps(data) if isinstance(data, dict) else data
                    async with self.session.post(endpoint, data=payload, headers=headers, timeout=timeout) as resp:
                        response_text = await resp.text()
                else:
                    self.logger.error(f"Unsupported HTTP method: {http_method}")
                    return ({}, 0.0) if return_with_time else {}

                elapsed_time = int((time.time() - start_time) * 1000)

                self.last_response = {
                    "data": response_text,
                    "status": resp.status,
                    "error": None,
                    "elapsed_time_ms": elapsed_time
                }

                # Handle successful response
                if resp.status == 200:
                    try:
                        response_json = await resp.json()
                        processed_response = self.handle_response_with_key(response_json, return_key=return_key, keep_lists=keep_lists)
                        if isinstance(processed_response, list):
                            if return_first:
                                processed_response = processed_response[0] if processed_response else None
                            elif list_index is not None:
                                processed_response = processed_response[list_index] if len(processed_response) > list_index else None

                        return (processed_response, elapsed_time) if return_with_time else processed_response
                    except json.JSONDecodeError:
                        self.logger.error(f"Failed to decode JSON response: {response_text}")
                        return (response_text, elapsed_time) if return_with_time else response_text if return_on_error else {}
                elif resp.status == 400:
                    try:
                        response_json = await resp.json()
                        processed_response = self.handle_response_with_key(response_json, return_key="error.message")

                        if isinstance(processed_response, str):
                            processed_response = processed_response.replace("Executing: ", "")

                        self.logger.info(f" ▶️ {get_shortened_tx_hash(data)} status={resp.status}, response={processed_response}")
                    except json.JSONDecodeError:
                        self.logger.error(f"▶️ Failed to decode JSON response: {response_text}")

                else:
                    self.logger.warning(f"Request failed with status {resp.status}: {response_text}")
                    if return_on_error:
                        try:
                            response_json = await resp.json()
                            processed_response = self.handle_response_with_key(response_json, return_key=return_key, keep_lists=keep_lists)
                            return (processed_response, elapsed_time) if return_with_time else processed_response
                        except json.JSONDecodeError:
                            return (response_text, elapsed_time) if return_with_time else response_text
                    return ({}, elapsed_time) if return_with_time else {}
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                elapsed_time = time.time() - start_time
                self.logger.warning(
                    f"Attempt {attempt}/{retries} failed: {e}. Method: {http_method.upper()}, URL: {endpoint}"
                )
                self.last_response['error'] = f"Attempt {attempt}/{retries} failed: {e}. Method: {http_method.upper()}, URL: {endpoint}"
                if attempt == retries and return_with_time:
                    return ({}, elapsed_time)
            except Exception as e:
                elapsed_time = time.time() - start_time
                self.logger.error(
                    f"Unexpected error: {e}. Method: {http_method.upper()}, URL: {endpoint}",
                    exc_info=log_exception
                )
                if attempt == retries:
                    if return_with_time:
                        return ({}, elapsed_time)
                    raise
            finally:
                if attempt < retries:
                    # Adding jitter to introduce randomness in the backoff time, preventing thundering herd problem.
                    jitter = uniform(0, 1)
                    sleep_time = backoff_factor * (2 ** (attempt - 1)) + jitter
                    if sleep_time > 1:
                        self.logger.debug(f"Retrying after {sleep_time:.2f} seconds..., URL: {endpoint}, data: {data}")
                    await asyncio.sleep(sleep_time)

        # Final fallback in case all retries fail
        self.logger.error(f"All {retries} attempts failed for {http_method.upper()} request to {endpoint}")
        return ({}, 0.0) if return_with_time else {}


    async def _make_request(
            self,
            http_method: str,
            endpoint: str,
            data: Optional[Union[Dict, str]] = None,
            headers: Optional[Dict[str, str]] = None,
            return_key: Optional[str] = None,
            return_on_error: bool = True,
            return_first: bool = False,
            list_index: Optional[int] = None,
            retries: int = 3,
            backoff_factor: float = 0.5,
            keep_lists: bool = False,
            log_exception: bool = False,
            return_with_time: Optional[bool] = None
    ) -> Any:
        """
        Helper method to make HTTP requests with retry and timeout support.
        Stores response in last_response and maintains legacy return behavior.

        Args:
            http_method (str): HTTP method ('GET', 'POST', etc.).
            endpoint (str): API endpoint or full URL.
            data (dict or str, optional): Payload for POST requests or query parameters for GET.
            headers (dict, optional): HTTP headers.
            return_key (str, optional): Key to extract from the JSON response.
            return_on_error (bool, optional): Whether to return data on error responses.
            return_first (bool, optional): If True and response is a list, return the first item.
            list_index (int, optional): If provided and response is a list, return the item at this index.
            retries (int, optional): Number of retry attempts. Defaults to 3.
            backoff_factor (float, optional): Backoff factor for exponential delay. Defaults to 0.5.
            keep_lists (bool, optional): Whether to keep lists in flattened data.
            log_exception (bool, optional): Whether to log exceptions.
            return_with_time (bool, optional): If True, return response data along with the elapsed time.

        Returns:
            Any: Processed response data, or a tuple of response data and elapsed time.
        """
        if return_with_time is None:
            return_with_time = self.return_with_time

        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self._check_session()
        self.logger.debug(f"Making {http_method.upper()} request to {endpoint} with data: {data}")

        for attempt in range(1, retries + 1):
            start_time = time.time()
            try:
                response = await self._execute_http_request(http_method, endpoint, data, headers)
                status = response["status"]
                response_text = response["response_text"]
                elapsed_time_ms = response["elapsed_time_ms"]

                if status == 200:
                    processed_response = self._process_success_response(response_text, return_key, keep_lists, return_first, list_index)
                    self.last_response = {
                        "data": processed_response,
                        "status": status,
                        "error": None,
                        "elapsed_time_ms": elapsed_time_ms
                    }
                    return (processed_response, elapsed_time_ms) if return_with_time else processed_response
                elif status == 400:
                    error_message = self._process_error_response(response_text, return_on_error)
                    self.last_response = {
                        "data": error_message if return_on_error else {},
                        "status": status,
                        "error": error_message,
                        "elapsed_time_ms": elapsed_time_ms
                    }
                    self.logger.info(f" ▶️ {get_shortened_tx_hash(data)} status={status}, error={error_message}")
                    return (self.last_response["data"], elapsed_time_ms) if return_with_time else self.last_response["data"]
                else:
                    self.last_response = {
                        "data": {} if return_on_error else {},
                        "status": status,
                        "error": f"Request failed with status {status}: {response_text}",
                        "elapsed_time_ms": elapsed_time_ms
                    }
                    self.logger.warning(self.last_response["error"])
                    processed_response = self._process_error_response(response_text, return_on_error, return_key, keep_lists)
                    self.last_response["data"] = processed_response
                    return (processed_response, elapsed_time_ms) if return_with_time else processed_response
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                elapsed_time_ms = int((time.time() - start_time) * 1000)
                self.last_response = {
                    "data": {} if return_on_error else {},
                    "status": 0,
                    "error": f"Attempt {attempt}/{retries} failed: {e}",
                    "elapsed_time_ms": elapsed_time_ms
                }
                self.logger.warning(f"{self.last_response['error']}. Method: {http_method.upper()}, URL: {endpoint}")
                if attempt == retries:
                    return (self.last_response["data"], elapsed_time_ms) if return_with_time else self.last_response["data"]
            except Exception as e:
                elapsed_time_ms = int((time.time() - start_time) * 1000)
                self.last_response = {
                    "data": {} if return_on_error else {},
                    "status": 0,
                    "error": f"Unexpected error: {e}",
                    "elapsed_time_ms": elapsed_time_ms
                }
                self.logger.error(f"{self.last_response['error']}. Method: {http_method.upper()}, URL: {endpoint}", exc_info=log_exception)
                if attempt == retries:
                    return (self.last_response["data"], elapsed_time_ms) if return_with_time else self.last_response["data"]
            finally:
                if attempt < retries:
                    sleep_time = backoff_factor * (2 ** (attempt - 1))
                    if sleep_time > 1:
                        self.logger.debug(f"Retrying after {sleep_time:.2f} seconds..., URL: {endpoint}, data: {data}")
                    await asyncio.sleep(sleep_time)

        self.last_response = {
            "data": {} if return_on_error else {},
            "status": 0,
            "error": f"All {retries} attempts failed for {http_method.upper()} request to {endpoint}",
            "elapsed_time_ms": 0
        }
        self.logger.error(self.last_response["error"])
        return (self.last_response["data"], 0.0) if return_with_time else self.last_response["data"]

    async def _execute_http_request(self, http_method: str, endpoint: str, data: Optional[Union[Dict, str]], headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Executes the HTTP request and returns response details.
        """
        start_time = time.time()
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        if http_method.upper() == 'GET':
            async with self.session.get(endpoint, params=data, headers=headers, timeout=timeout) as resp:
                status = resp.status
                response_text = await resp.text()
        elif http_method.upper() == 'POST':
            payload = json.dumps(data) if isinstance(data, dict) else data
            async with self.session.post(endpoint, data=payload, headers=headers, timeout=timeout) as resp:
                status = resp.status
                response_text = await resp.text()
        else:
            raise ValueError(f"Unsupported HTTP method: {http_method}")
        elapsed_time_ms = int((time.time() - start_time) * 1000)
        return {
            "status": status,
            "response_text": response_text,
            "elapsed_time_ms": elapsed_time_ms
        }

    def _process_success_response(self, response_text: str, return_key: Optional[str], keep_lists: bool, return_first: bool, list_index: Optional[int]) -> Any:
        """
        Processes successful (200) response.
        """
        try:
            response_json = json.loads(response_text)
            processed_response = self.handle_response_with_key(response_json, return_key=return_key, keep_lists=keep_lists)
            if isinstance(processed_response, list):
                if return_first:
                    return processed_response[0] if processed_response else None
                elif list_index is not None:
                    return processed_response[list_index] if len(processed_response) > list_index else None
            return processed_response
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON response: {response_text}")
            return response_text

    def _process_error_response(self, response_text: str, return_on_error: bool, return_key: Optional[str] = None, keep_lists: bool = False) -> Any:
        """
        Processes error response.
        """
        try:
            response_json = json.loads(response_text)
            if return_key:
                return self.handle_response_with_key(response_json, return_key=return_key, keep_lists=keep_lists)
            return response_json if return_on_error else {}
        except json.JSONDecodeError:
            return response_text if return_on_error else {}
        

    @staticmethod
    def handle_response_with_key(response=None, return_key=None, keep_lists=True):
        if isinstance(response, (dict, list)):
            if return_key and response:
                flat = Flattener(response, keep_lists=keep_lists)
                # return Flattener(response, keep_lists=keep_lists).get(return_key)
                return FlatDict(response).get(return_key)
            return response
        return response.get('text')

    async def get_block_hash(self, tx_hash: str= "", url: Optional[str] = None) -> dict:
        target_url = url or self.url
        hash_info = {}
        try:
            hash_info = await self.execute_rpc_call(url=target_url, method='icx_getBlockByHash', params={"hash": tx_hash}, return_key="result")
        except Exception as e:
            self.logger.error(f"Error during operation get_block_hash(): {str(e)}", exc_info=False)
        return hash_info

    async def get_last_blockheight(self, url: Optional[str] = None) -> int:
        target_url = url or self.url
        response = await self.execute_rpc_call(url=target_url, method='icx_getLastBlock', return_key="result.height")        
        return response if response else 0

    async def get_network_info(self, url: Optional[str] = None) -> int:
        target_url = url or self.url
        response = await self.execute_rpc_call(url=target_url, method='icx_getNetworkInfo', return_key="result")
        return response if response else 0

    async def get_preps(self, url: Optional[str] = None, return_dict_key=""):
        target_url = url or self.url
        result = await self.execute_rpc_call(url=target_url, governance_address=const.CHAIN_SCORE_ADDRESS, method='getPReps', return_key="result.preps")

        if return_dict_key:
            return list_to_dict_by_key(result, return_dict_key)
        return result

    async def get_balance(self, address="", return_as_hex=True, return_key="result", use_hex_value=None, url: Optional[str] = None):
        target_url = url or self.url
        return_value = await self.execute_rpc_call(
            url=target_url,
            method='icx_getBalance',
            params={
                "address": address
            },
            return_key=return_key
        )

        if use_hex_value:
            return HexValueParser(return_value)

        if return_as_hex:
            return return_value
        return hex_to_number(return_value, is_tint=True)

    async def get_stake(self, address="", return_as_hex=False, return_key="result", use_hex_value=None, url: Optional[str] = None):
        target_url = url or self.url
        return_value = await self.execute_rpc_call(
            url=target_url,
            governance_address=const.CHAIN_SCORE_ADDRESS,
            method='getStake',
            params={
                "address": address
            },
            return_key=return_key
        )

        # use_hex_value = use_hex_value or self.use_hex_value
        if use_hex_value:
            return HexValueParser(return_value)

        if return_as_hex:
            return return_value
        return hex_to_number(return_value, is_tint=True)

    async def get_delegation(self, address="", return_as_hex=False, return_key="result", use_hex_value=None,  url: Optional[str] = None):
        target_url = url or self.url
        return_value = await self.execute_rpc_call(
            url=target_url,
            governance_address=const.CHAIN_SCORE_ADDRESS,
            method='getDelegation',
            params={
                "address": address
            },
            return_key=return_key
        )
        # use_hex_value = use_hex_value or self.use_hex_value
        if use_hex_value:
            return HexValueParser(return_value)

        if return_as_hex:
            return return_value
        return hex_to_number(return_value, is_tint=True)


    async def get_bond(self, address="",return_as_hex=False, return_key="result", use_hex_value=None,url: Optional[str] = None):
        target_url = url or self.url
        return_value = await self.execute_rpc_call(
            url=target_url,
            governance_address=const.CHAIN_SCORE_ADDRESS,
            method='getBond',
            params={
                "address": address
            },
            return_key=return_key
        )

        # use_hex_value = use_hex_value or self.use_hex_value
        if use_hex_value:
            return HexValueParser(return_value)

        if return_as_hex:
            return return_value
        return hex_to_number(return_value, is_tint=True)

    async def get_iscore(self, address="",return_as_hex=False, return_key="result", use_hex_value=None,url: Optional[str] = None):
        target_url = url or self.url
        return_value = await self.execute_rpc_call(
            url=target_url,
            governance_address=const.CHAIN_SCORE_ADDRESS,
            method='queryIScore',
            params={
                "address": address
            },
            return_key=return_key
        )

        # use_hex_value = use_hex_value or self.use_hex_value
        if use_hex_value:
            return HexValueParser(return_value)

        if return_as_hex:
            return return_value
        return hex_to_number(return_value, is_tint=True)
    

    async def get_node_name_by_address(self, url: Optional[str] = None):
        """
        Retrieves a dictionary mapping node addresses to their corresponding names.

        This function calls `get_preps` to fetch the full dictionary of P-Rep information
        and then filters it to create a new dictionary where the keys are `nodeAddress`
        and the values are `name`.

        :return: A dictionary with `nodeAddress` as keys and `name` as values.
        :rtype: dict

        Example:
            .. code-block:: python

                # Example output
                {
                    "hx12ffd8a005f9bc0a3164c2d133a0ed5ecfe70c21": "Clue",
                    "hx34a8e8a005f9bc0b3164c2d133a0ed5ecfe70c22": "NodeX",
                    ...
                }
        """
        preps_info = await self.get_preps(url=url, return_dict_key="nodeAddress")

        # Create a new dictionary with nodeAddress as the key and name as the value
        result = {address: info['name'] for address, info in preps_info.items()}
        return result

    async def get_validator_info(self, url: Optional[str] = None):
        target_url = url or self.url
        return await self.execute_rpc_call(
            url=target_url,
            governance_address=const.CHAIN_SCORE_ADDRESS,
            method='getValidatorsInfo',
            params={"dataType": "all"},
            return_key="result.validators"
        )

    async def _get_tx_result(self, tx_hash, url: Optional[str] = None):
        target_url = url or self.url
        return  await self.execute_rpc_call(url=target_url, method='icx_getTransactionResult',params={"txHash": tx_hash})

    async def get_tx_result(self, tx_hash, max_attempts=5, is_wait=True, return_key="result", url: Optional[str] = None):
        target_url = url or self.url
        tx_result = await self._get_tx_result(tx_hash, url=target_url)
        if not is_wait:
            return self.handle_response_with_key(tx_result, return_key=tx_result)

        attempt = 0
        while attempt < max_attempts:
            if attempt > 2:
                self.logger.info(f"Requesting transaction result for tx_hash: {tx_hash} (Attempt {attempt+1}/{max_attempts})")

            tx_result = await self._get_tx_result(tx_hash, url=target_url)
            if isinstance(tx_result, dict):
                flatten_tx_result = FlatDict(tx_result)

                self.logger.debug(f"{flatten_tx_result}")
                if flatten_tx_result.get('result.failure'):
                    return flatten_tx_result.get('result.failure')

                if not flatten_tx_result.get('error.message'):
                    return "OK"

            attempt += 1
            await asyncio.sleep(2)  # Wait before retrying

        self.logger.error(f"Max attempts reached. Failed to get transaction result for tx_hash: {tx_hash}")
        return "Failed to get transaction result"


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


def jequest(url, method="get", payload={}, elapsed=False, print_error=False, timeout=None, ipaddr=None, verify=True, **kwargs) -> dict:
    """
    This functions will be called the http requests.

    :param url:
    :param method:
    :param payload:
    :param elapsed:
    :param print_error:
    :param timeout: Timeout seconds
    :param ipaddr: Change the request IP address in http request
    :param verify: verify SSL
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
            response = func(url, verify=verify, timeout=timeout, **kwargs)
        else:
            response = func(url, json=payload, verify=verify, timeout=timeout, **kwargs)
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


async def get_blockheight(response=None):
    """
    Function to parse block height from a response.

    :param response: The response containing block height data.
    :return: Parsed block height.
    :raises: Exception if block height parsing fails.
    """
    response_json = json.loads(response)
    blockheight = response_json.get("height")
    if not blockheight:
        raise ValueError("Block height not found in the response")
    return blockheight


async def retry_operation(operation, max_attempts=3, delay=2, success_criteria=None, logger=None, verbose=0, *args, **kwargs):
    """
    Retry the given operation multiple times in case of failure or based on the success criteria.

    :param operation: The operation to retry (function).
    :param max_attempts: Maximum number of retry attempts.
    :param delay: Delay between retries.
    :param success_criteria: A function that takes the result and returns True if the result is valid/successful.
    :param logger: Logger for logging messages (optional).
    :param verbose: Verbosity level for logging.
    :param args: Positional arguments to pass to the operation.
    :param kwargs: Keyword arguments to pass to the operation.
    :return: The result of the operation if successful.
    :raises: Exception if the operation fails after max_attempts or success criteria is not met.
    """
    attempts = 0

    _logger = setup_logger(logger, "retry_operation", verbose)

    while attempts < max_attempts:
        try:
            result = await operation(*args, **kwargs)
            if success_criteria:
                if success_criteria(result):
                    return result
                else:
                    if success_criteria:
                        success_criteria_name = success_criteria.__name__
                    else:
                        success_criteria_name = success_criteria
                    _logger.error(f"Operation result did not meet success criteria (Attempt {attempts+1}/{max_attempts}), success_criteria={success_criteria_name}")
            else:
                return result

        except Exception as e:
            _logger.error(f"Error during operation: {e} (Attempt {attempts+1}/{max_attempts})")

        attempts += 1
        if attempts < max_attempts:
            _logger.error(f"Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
        else:
            _logger.error(f"Max attempts reached. Operation failed after {max_attempts} attempts.")
            raise Exception(f"Operation failed after {max_attempts} attempts")


def remove_path_from_url(url: str) -> str:
    """
    Removes the path, query, and fragment from a URL, leaving only the scheme and domain.

    Args:
        url (str): The original URL.

    Returns:
        str: The URL without the path, query, or fragment.
    """
    # Find the position of "://" to identify where the scheme ends
    scheme_end = url.find("://")
    if scheme_end == -1:
        raise ValueError("Invalid URL: Missing scheme (e.g., 'http://').")

    # Find the first slash after the domain
    domain_end = url.find("/", scheme_end + 3)
    if domain_end == -1:
        # No path, query, or fragment in the URL
        return url

    # Extract and return the URL up to the domain
    return url[:domain_end]


icon_rpc_call = IconRpcHelper().rpc_call