import re
import requests
import json
from pawnlib.config.globalconfig import pawnlib_config as pawn, global_verbose
from pawnlib import output
from pawnlib.resource import net
from pawnlib.typing.converter import append_suffix, append_prefix, hex_to_number
from pawnlib.typing.constants import const
from pawnlib.typing.generator import json_rpc, random_token_address
import time
from pawnlib.utils.operate_handler import WaitStateLoop
from pawnlib import logger
from functools import partial


class IconRpcHelper:
    def __init__(self, url="", wallet=None):
        self.url = append_suffix(url, "/api/v3")
        self.debug_url = append_suffix(url, "/api/v3d")
        self.wallet = wallet
        self.governance_address = f"cx{'0'*39}1"

    def initialize(self):
        pass

    def _decorator_enforce_kwargs(func):
        def from_kwargs(self, *args, **kwargs):
            func_name = func.__name__
            pawn.console.debug(f"Start '{func_name}' function")
            ret = func(self, *args, **kwargs)
            return ret

        return from_kwargs

    def rpc_call(self, url=None, method=None, params: dict = {}, payload: dict = {}, print_error=False) -> dict:
        if url:
            _url = url
        else:
            _url = self.url

        if payload:
            _payload = payload
        else:
            _payload = json_rpc(method=method, params=params)

        response = jequest(
            url=append_api_v3(_url),
            payload=_payload,
            method="post"
        )
        if print_error and response.get('status_code') != 200:
            if response.get('json') and response['json'].get('error'):
                pawn.console.log(f"[red][ERROR] status_code={response['status_code']}, error={response['json']['error']}")
                pawn.console.log(f"[ERROR] payload={_payload}")
            else:
                pawn.console.log(f"[red]{response.get('status_code')} {response.get('text')}")
        return response.get('json')

    def _governance_call(self, url=None, method=None, params={}, governance_address=None):
        if governance_address:
            self.governance_address = governance_address
        response = self.rpc_call(
            url=url,
            method="icx_call",
            params={
                "to": self.governance_address,
                "dataType": "call",
                "data": {
                    "method": method,
                    "params": params
                }
            },
            print_error=True
        )
        return response.get('result')

    def get_step_price(self, url=None):
        response = self._governance_call(url=url, method="getStepPrice")
        return response

    def _get_step_costs(self, url=None):
        response = self._governance_call(url=url, method="getStepCosts")
        return response

    def get_step_cost(self, step_kind="apiCall"):
        return self._get_step_costs().get(step_kind)

    def get_estimate_step(self, url=None, tx=None):
        if url:
            self.debug_url = url
        if isinstance(tx, dict):
            tx['method'] = "debug_estimateStep"
            res = self.rpc_call(
                url=self.debug_url,
                payload=tx,
                print_error=True
            )
            res_json = res
            pawn.console.log(res_json)
            if res_json.get('error'):
                pawn.console.log(f"[red] debug_estimateStep={res_json.get('error')}")
            return res.get('result')

        else:
            raise ValueError(f"TX is not dict. tx => {tx}")

    def get_step_limit(self, url=None, tx=None, step_kind="apiCall") :
        estimate_step = self.get_estimate_step(url, tx)
        step_cost = self.get_step_cost(step_kind)
        step_price = self.get_step_price(url)
        step_limit = hex(hex_to_number(estimate_step) + hex_to_number(step_cost))

        icx_fee = hex_to_number(estimate_step) * hex_to_number(step_price) / const.TINT
        pawn.console.debug(f"fee = {icx_fee} => estimate[i]({hex_to_number(estimate_step, debug=True)})[/i] * "
                           f"step_price[i]({hex_to_number(step_price, debug=True)})[/i]")

        pawn.console.debug(f"step_limit => {hex_to_number(step_limit, debug=True)}")
        return step_limit


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
                    text = f"{prefix_text}[OK] {resp['result']}"
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

    pawn.console.debug(f"url={url}, method={method}, payload={payload}, kwargs={kwargs}, error={error}")

    return data


icon_rpc_call = IconRpcHelper().rpc_call
