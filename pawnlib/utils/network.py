import ssl
import warnings
import requests
from urllib3.exceptions import InsecureRequestWarning


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
