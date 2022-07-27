import socket
from pawnlib.utils import http


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


