import re

from pawnlib.config.globalconfig import pawnlib_config as pawn
import socket
import time
from pawnlib.utils import http

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

    return http.jequest("http://checkip.amazonaws.com").get('text', "").strip()


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
    return ipaddr


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
    The listen_socket function creates a socket object and binds it to the host and port
    provided. The function then listens for incoming connections on that socket, with a maximum of 5
    connections in the queue.

    :param host: Specify the hostname of the machine where the server is running
    :param port: Specify the port number that the server will listen on
    :return: A socket object
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
