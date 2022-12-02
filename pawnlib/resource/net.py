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
    Get the public IP address

    :return:

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
    if protocol == "tcp":
        socket_protocol = socket.SOCK_STREAM
    elif protocol == "udp":
        socket_protocol = socket.SOCK_DGRAM
    else:
        raise Exception("Invalid socket type argument, tcp or udp")

    if host == "" or port == 0:
        raise Exception(f"Invalid host or port, inputs: host={host}, port={port}")

    with socket.socket(socket.AF_INET, socket_protocol) as sock:
        host = http.remove_http(host)
        socket.setdefaulttimeout(timeout)  # seconds (float)
        result = sock.connect_ex((host, port))

    if result == 0:
        pawn.app_logger.info(f"[OK] Opened port -> {host}:{port}")
        return True
    else:
        pawn.error_logger.error(f"[FAIL] Closed port -> {host}:{port}")
    return False


def listen_socket(host, port):
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
