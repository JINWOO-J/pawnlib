from pawnlib.config.globalconfig import pawnlib_config as pawn
import socket
from pawnlib.utils import http

prev_getaddrinfo = socket.getaddrinfo


class OverrideDNS:
    _dns_cache = {}

    def __init__(self, domain="", ipaddr="", port=80):
        self._dns_cache[domain] = ipaddr
        self.prv_getaddrinfo = prev_getaddrinfo

        # socket.getaddrinfo = self.new_getaddrinfo

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
    Get public ipaddress
    :return:
    """

    return http.jequest("http://checkip.amazonaws.com").get('text', None).strip()


def get_local_ip():
    """
    Get local ipaddress
    :return:
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
    return socket.gethostname()
