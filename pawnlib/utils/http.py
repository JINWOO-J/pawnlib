import re
import requests
import json
from pawnlib.config.globalconfig import pawnlib_config as pawn, global_verbose
from pawnlib import output
from pawnlib.resource import net
from pawnlib import logger

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


def remove_http(url):
    """
    Remove the r'https?://' string

    :param url:
    :return:

    """
    return re.sub(r"https?://", '', url)


def jequest(url, method="get", payload={}, elapsed=False, print_error=False, timeout=None, ipaddr=None, **kwargs):
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

    return data
