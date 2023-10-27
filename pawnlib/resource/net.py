import re

from pawnlib.config.globalconfig import pawnlib_config as pawn
import socket
import time
import asyncio
import requests
from concurrent.futures import ThreadPoolExecutor
from timeit import default_timer
from pawnlib.utils import http
from pawnlib.typing import is_valid_ipv4, todaydate, shorten_text
from pawnlib.output import PrintRichTable


try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

prev_getaddrinfo = socket.getaddrinfo


class OverrideDNS:
    """

    Change the Domain Name using socket

    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.OverrideDNS(domain=domain, ipaddr=ipaddr).set()

    """
    _dns_cache = {}

    def __init__(self, domain="", ipaddr="", port=80):
        self._dns_cache[domain] = ipaddr
        self.prv_getaddrinfo = prev_getaddrinfo

    def new_getaddrinfo(self, *args):
        if args[0] in self._dns_cache:
            if pawn.verbose:
                print("Forcing FQDN: {} to IP: {}".format(args[0], self._dns_cache[args[0]]))
            return self.prv_getaddrinfo(self._dns_cache[args[0]], *args[1:])
        else:
            return self.prv_getaddrinfo(*args)

    def set(self):
        socket.getaddrinfo = self.new_getaddrinfo

    def unset(self):
        socket.getaddrinfo = self.prv_getaddrinfo


def get_public_ip():
    """
    The get_public_ip function returns the public IP address of the machine it is called on.


    :return: The public ip address of the server

    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.get_public_ip()


    """
    try:
        public_ip = http.jequest("http://checkip.amazonaws.com", timeout=2).get('text', "").strip()
        if is_valid_ipv4(public_ip):
            return public_ip
        else:
            pawn.error_logger.error(f"An error occurred while fetching Public IP address. Invalid IPv4 address - '{public_ip}'")
            pawn.console.debug(f"An error occurred while fetching Public IP address. Invalid IPv4 address - '{public_ip}'")

    except Exception as e:
        pawn.error_logger.error(f"An error occurred while fetching Public IP address - {e}")
        pawn.console.debug(f"An error occurred while fetching Public IP address - {e}")

    return ""


class FindFastestRegion:
    def __init__(self, verbose=True, aws_regions=None):
        self.results = []
        self.verbose = verbose
        if aws_regions:
            self.aws_regions = aws_regions
        else:
            self.aws_regions = {
                "Seoul": "ap-northeast-2",
                "Tokyo": "ap-northeast-1",
                "Virginia": "us-east-1",
                "Hongkong": "ap-east-1",
                "Singapore": "ap-southeast-1",
                "Mumbai": "ap-south-1",
                "Frankfurt": "eu-central-1",
                "Ohio": "us-east-2",
                "California": "us-west-1",
                "US-West": "us-west-2",
                "Ceentral":"ca-central-1",
                "Ireland": "eu-west-1",
                "London": "eu-west-2",
                "Sydney": "ap-southeast-2",
                "São Paulo": "sa-east-1",
                "Beijing": "cn-north-1",
            }

    def run(self):
        self.results = []
        loop = asyncio.get_event_loop()
        future = asyncio.ensure_future(self.find_fastest_region())
        loop.run_until_complete(future)
        self.sorted_results()
        return self.results

    async def find_fastest_region(self):
        tasks = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            loop = asyncio.get_event_loop()
            for region_name, region_code in self.aws_regions.items():
                url = f'https://s3.{region_code}.amazonaws.com/ping?x=%s' % todaydate("ms")
                tasks.append(loop.run_in_executor(executor, self.get_time, *(url, region_name)))
            await asyncio.gather(*tasks)

    def get_time(self, url, name="NULL"):
        start_time = default_timer()
        try:
            response = requests.get(f'{url}', timeout=3)
            response_text = response.text
            response_time = round(response.elapsed.total_seconds(), 3)
            status_code = response.status_code
        except:
            response_time = None
            response_text = None
            status_code = 999
        elapsed = round(default_timer() - start_time, 3)

        data = {
            "region": name,
            "time": response_time,
            "run_time": elapsed,
            "url": shorten_text(url, 50),
            # "text": response_text,
            "status_code": status_code
        }
        if data.get('time') and data.get("run_time") and data.get("status_code") == 200:
            self.results.append(data)
            if self.verbose:
                print(data)
        return data

    def sorted_results(self, key="run_time"):
        self.results = sorted(self.results, key=(lambda x: x.get(key)), reverse=False)

    def print_results(self):
        PrintRichTable(title="fast_region", data=self.results)
        pawn.console.log(f"Fastest Region={self.results[0]['region']}, time={self.results[0]['run_time']} sec")


def get_local_ip():
    """

    Get the local IP address

    :return:

    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.get_local_ip()

    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ipaddr = s.getsockname()[0]
    except Exception:
        ipaddr = '127.0.0.1'
    finally:
        s.close()

    if is_valid_ipv4(ipaddr):
        return ipaddr
    else:
        pawn.error_logger.error("An error occurred while fetching Local IP address. Invalid IPv4 address")
        pawn.console.debug("An error occurred while fetching Local IP address. Invalid IPv4 address")
    return ""


def get_hostname():
    """

    Get the local hostname

    :return:

    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.get_hostname()

    """
    return socket.gethostname()


def extract_host_port(host):
    """
    The extract_host_port function extracts the host and port from a string.

    :param host: Extract the hostname from the url
    :return: A tuple of the host and port number

    Example:

    .. code-block:: python

        from pawnlib.resource import net
        net.extract_host_port("http://127.0.0.1:8000")

    """
    http_regex = '^((?P<proto>https?)(://))?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'

    regex_res = re.search(http_regex, host)
    port = 0
    if regex_res:
        if regex_res.group('port'):
            port = int(regex_res.group('port'))
        else:
            if regex_res.group('proto'):
                if regex_res.group('proto') == "http":
                    port = 80
                elif regex_res.group('proto') == "https":
                    port = 443
            else:
                port = 80
        host = regex_res.group('host')
        pawn.console.debug(f"[Regex] host={host}, port={port}, {regex_res.groupdict()}")

    return host, port


def check_port(host: str = "", port: int = 0, timeout: float = 3.0, protocol: Literal["tcp", "udp"] = "tcp") -> bool:
    """
    Returns boolean with checks if the port is open

    :param host: ipaddress os hostname
    :param port: destination port number
    :param timeout: timeout sec
    :param protocol: type of protocol
    :return: boolean

    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.check_port()

    """

    if not port:
        host, port = extract_host_port(host)
    else:
        pawn.console.debug(f"[red][Not Matched] host={host}, port={port}")

    pawn.console.debug(f"host={host}, port={port}, protocol={protocol}")

    if protocol == "tcp":
        socket_protocol = socket.SOCK_STREAM
    elif protocol == "udp":
        socket_protocol = socket.SOCK_DGRAM
    else:
        raise ValueError("Invalid socket type argument, tcp or udp")

    if host == "" or port == 0:
        raise ValueError(f"Invalid host or port, inputs: host={host}, port={port}")

    if timeout:
        socket.setdefaulttimeout(float(timeout))  # seconds (float)

    with socket.socket(socket.AF_INET, socket_protocol) as sock:
        host = http.remove_http(host)
        try:
            result = sock.connect_ex((host, port))
        except Exception as e:
            pawn.error_logger.error(f"[FAIL] {e}")
            return False

    if result == 0:
        pawn.console.debug(f"[OK] Opened port -> {host}:{port}")
        return True
    else:
        pawn.error_logger.error(f"[FAIL] Closed port -> {host}:{port}")
    return False


def listen_socket(host, port):
    """
    Create a socket object and bind it to the host and port provided.
    Listen for incoming connections on that socket, with a maximum of 5 connections in the queue.

    :param host: str - hostname of the machine where the server is running
    :param port: int - port number that the server will listen on
    :return: socket - a socket object

    Example:
        .. code-block:: python

            # create a socket object and bind it to localhost and port 8080
            sock = listen_socket("localhost", 8080)

            # listen for incoming connections
            conn, addr = sock.accept()

    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(5)
    return sock


def wait_for_port_open(host: str = "", port: int = 0, timeout: float = 3.0, protocol: Literal["tcp", "udp"] = "tcp") -> bool:
    """

    Wait for a port to open. Useful when writing scripts which need to wait for a server to be available.

    :param host: hostname or ipaddress
    :param port: port
    :param timeout: timeout seconds (float)
    :param protocol: tcp or udp
    :return:

    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.wait_for_port_open("127.0.0.1", port)

            ## ⠏  Wait for port open 127.0.0.1:9900 ... 6


    """
    message = f"[bold green] Wait for port open {host}:{port} ..."
    count = 0
    with pawn.console.status(message) as status:
        while True:
            if check_port(host, port, timeout, protocol):
                status.stop()
                pawn.console.debug(f"[OK] Activate port -> {host}:{port}")
                pawn.app_logger.info(f"[OK] Activate port -> {host}:{port}")
                return True
            status.update(f"{message} {count}")
            count += 1
            time.sleep(1)
