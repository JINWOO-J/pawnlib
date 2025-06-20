import ssl
import warnings
import requests
from urllib3.exceptions import InsecureRequestWarning
from pawnlib.utils.http import append_http
import asyncio
from pawnlib.config import pawn

def disable_requests_ssl_warnings():
    """
    Disable SSL warnings specifically for the 'requests' library by suppressing InsecureRequestWarning.

    This function disables warnings triggered by unverified HTTPS requests in 'requests' library.
    """
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def disable_global_ssl_warnings():
    """
    Globally disable SSL warnings for all HTTPS requests by modifying the SSL context and suppressing warnings.

    This function disables SSL verification and suppresses warnings across all HTTPS requests, not limited
    to specific libraries like 'requests'. It modifies the default SSL context and ignores 'Unverified HTTPS request' warnings.
    """
    ssl._create_default_https_context = ssl._create_unverified_context
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")


async def is_port_open(host, port):
    """
    Checks if a specific port on a host is open.

    :param host: The hostname or IP address to check.
    :param port: The port number to check.
    :return: True if the port is open, False otherwise.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False

async def check_network_api_availability(network_api):
    """
    Checks if the network API is available and the port is open.

    :param network_api: The network API URL to check.
    :return: True if the network API is available, False otherwise.
    """
    from urllib.parse import urlparse
    parsed_url = urlparse(append_http(network_api))

    host = parsed_url.hostname
    port = parsed_url.port

    if not host or not port:
        pawn.console.log("[red]Invalid network API URL provided.[/red]")
        return False

    is_open = await is_port_open(host, port)

    if not is_open:
        pawn.console.log(f"[red]Port {port} on {host} is not open.[/red]")
        return False
    pawn.console.log(f"[green]Port {port} on {host} is open and accessible.[/green]")
    return True
