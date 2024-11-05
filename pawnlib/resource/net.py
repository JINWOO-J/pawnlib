import re

from pawnlib.config.globalconfig import pawnlib_config as pawn
import socket
import time
import asyncio
import requests
from concurrent.futures import ThreadPoolExecutor
from timeit import default_timer
from pawnlib.utils import http, timing
from pawnlib.typing import is_valid_ipv4, todaydate, shorten_text
from pawnlib.output import PrintRichTable
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn


try:
    from typing import Literal, Tuple, List
except ImportError:
    from typing_extensions import Literal, Tuple, List

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


def get_public_ip(use_cache=False):
    """
    The get_public_ip function returns the public IP address of the machine it is called on.

    :param use_cache: Whether to use the cached public IP if available
    :type use_cache: bool

    :return: The public ip address of the server


    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.get_public_ip()

            net.get_public_ip(use_cache=True)

    """
    try:
        if use_cache and pawn.get('CACHED_PUBLIC_IP'):
            return pawn.get('CACHED_PUBLIC_IP')

        public_ip = http.jequest("http://checkip.amazonaws.com", timeout=2).get('text', "").strip()

        if is_valid_ipv4(public_ip):

            if use_cache:
                pawn.set(CACHED_PUBLIC_IP=public_ip)
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


class AsyncPortScanner:
    """
    Asynchronous Port Scanner class.

    :param ip_range: Tuple of start and end IP addresses to scan.
    :param port_range: Tuple of start and end ports to scan. Default is all ports (0, 65535).
    :param max_concurrency: Maximum number of concurrent scans. Default is 30.

    Example:

        .. code-block:: python

            scanner = AsyncPortScanner(("192.168.0.1", "192.168.0.255"), (1, 1024), 50)
            asyncio.run(scanner.scan_all())
    """

    def __init__(self, ip_range: Tuple[str, str], port_range: Tuple[int, int] = (0, 65535),
                 max_concurrency: int = 30, timeout=1, ping_timeout=0.05, fast_scan_ports: List[int] = [22, 80, 443], batch_size=50000):
        self.start_ip, self.end_ip = ip_range
        self.start_port, self.end_port = port_range
        self.scan_results = {}
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.timeout = timeout
        self.ping_timeout = ping_timeout
        self.fast_scan_ports = fast_scan_ports
        self.batch_size = batch_size

    async def ping_host(self, ip: str) -> bool:
        common_ports = [22, 80, 443]
        for port in common_ports:
            try:
                await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=self.ping_timeout)
                return ip  # 연결 성공, 호스트가 살아 있음
            except Exception:
                continue  # 해당 포트에 대한 연결 실패, 다음 포트 시도
        return False  # 모든 시도 실패, 호스트가 닫혀 있음

    async def try_ping_host(self, ip: str, progress: Progress, task_id: int):
        progress.advance(task_id)
        for port in self.fast_scan_ports:
            try:
                await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=self.timeout)
                if progress is not None and task_id is not None:
                    progress.advance(task_id)  # 성공적으로 핑을 완료하면 진행 상황을 업데이트합니다.
                return ip
            except (asyncio.TimeoutError, Exception):
                continue  # 해당 포트에서 연결 실패, 다음 포트로 계속 시도합니다.
        return False

    async def scan_all(self, fast_scan: bool = False):
        if fast_scan:
            tasks = [self.check_and_scan_host(ip) for ip in self._generate_ips()]
        else:
            tasks = [
                self.wrap_scan(ip, port)
                for ip in self._generate_ips()
                for port in range(self.start_port, self.end_port + 1)
            ]
        await asyncio.gather(*tasks)

    async def check_and_scan_host(self, ip):
        if await self.ping_host(ip):
            print(f"{ip} is up, scanning ports...")
            tasks = [self.wrap_scan(ip, port) for port in range(self.start_port, self.end_port + 1)]
            await asyncio.gather(*tasks)
        else:
            print(f"{ip} is down, skipping...")

    async def scan_port(self, ip: str, port: int) ->(str, int, bool):
        async with (self.semaphore):
            pawn.console.debug(f"Scanning {ip}:{port} - Acquired semaphore, timeout={self.timeout}")
            try:
                await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=self.timeout)
                pawn.console.debug(f"Connection successful: {ip}:{port}")
                return ip, port, True
            except asyncio.TimeoutError:
                pawn.console.debug(f"Timeout: {ip}:{port}")
                return ip, port, False
            except Exception as e:
                if "Too many" in str(e):
                    pawn.console.log(f"Error scanning -> [red]{e}[/red]")
                else:
                    pawn.console.debug(f"Error scanning {ip}:{port} - {e}")
                return ip, port, False
            # finally:
            #     pawn.console.log(f"Releasing semaphore: {ip}:{port}")

    def calculate_scan_range(self):
        start_ip_int = self.ip_to_int(self.start_ip)
        end_ip_int = self.ip_to_int(self.end_ip)
        total_ips = end_ip_int - start_ip_int + 1
        total_ports = self.end_port - self.start_port + 1
        total_tasks = total_ips * total_ports
        return start_ip_int, end_ip_int, total_tasks

    async def scan(self, fast_scan: bool = False, progress: Progress = None):
        tasks = []
        ips_to_scan = await self.get_ips_to_scan(fast_scan, progress)
        if fast_scan:
            if ips_to_scan:
                pawn.console.log(f"<FAST SCAN> Alive IPs: {ips_to_scan}")
            else:
                pawn.console.log(f"<FAST SCAN> [red]No open servers found on ports {self.fast_scan_ports}.[/red]")

        total_ports = self.end_port - self.start_port + 1
        total_tasks = len(ips_to_scan) * total_ports
        fast_scan_string = "FastScan" if fast_scan else ""
        task_id = progress.add_task(f"[cyan]Scanning {fast_scan_string}...", total=total_tasks)
        if fast_scan:
            pawn.console.log(f"Alive IP: {ips_to_scan}")

        for ip in ips_to_scan:
            for port in range(self.start_port, self.end_port + 1):
                task = self.wrap_scan(ip, port, progress, task_id)
                tasks.append(task)
                if len(tasks) >= self.batch_size:
                    await asyncio.gather(*tasks)
                    tasks.clear()

        if tasks:
            await asyncio.gather(*tasks)

    async def get_ips_to_scan(self, fast_scan: bool, progress: Progress) -> List[str]:
        ips = self._generate_ips()
        if not fast_scan:
            return ips

        task_id = progress.add_task("Checking IPs...", total=len(ips))
        ping_tasks = [self.try_ping_host(ip, progress, task_id) for ip in ips]

        results = await asyncio.gather(*ping_tasks)
        alive_ips = [result for result in results if result]
        return alive_ips

    async def wrap_scan(self, ip, port, progress, task_id):
        async with self.semaphore:
            result = await self.scan_port(ip, port)
            progress.update(task_id, advance=1)
            self._process_results(result)
            return result

    def _generate_ips(self) -> List[str]:
        start_int = self.ip_to_int(self.start_ip)
        end_int = self.ip_to_int(self.end_ip)
        return [self.int_to_ip(ip_int) for ip_int in range(start_int, end_int + 1)]

    @staticmethod
    def ip_to_int(ip: str) -> int:
        return sum([int(octet) << (8 * i) for i, octet in enumerate(reversed(ip.split('.')))])

    @staticmethod
    def int_to_ip(ip_int: int) -> str:
        return '.'.join(str((ip_int >> (8 * i)) & 0xFF) for i in reversed(range(4)))

    def _process_results(self, results: List[Tuple[str, int, bool]]):
        if isinstance(results, tuple):
            results = [results]
        for ip, port, is_open in results:
            if ip not in self.scan_results:
                self.scan_results[ip] = {"open": [], "closed": []}

            if is_open:
                self.scan_results[ip]["open"].append(port)
            else:
                self.scan_results[ip]["closed"].append(port)

    def get_results(self):
        return self.scan_results

    def print_scan_results(self, view="all"):
        for ipaddr, result in self.scan_results.items():
            parsed_data = ""
            for is_open, port in result.items():
                if view == "all" or view == is_open and port:
                    # pawn.console.print(f"\t \[{is_open}] {port}")
                    parsed_data = f"\t \[{is_open}] {port}"
                    # is_data = True

            if parsed_data:
                pawn.console.print(ipaddr)
                pawn.console.print(parsed_data)

    def run_scan(self, fast_scan: bool = False):
        with Progress(
                TextColumn("[bold blue]{task.description}", justify="right"),
                BarColumn(bar_width=None),
                TextColumn("{task.completed}/{task.total} • [progress.percentage]{task.percentage:>3.0f}%"),
                "•",
                TimeRemainingColumn(),
                transient=True  # Hide the progress bar when done
        ) as progress:
            # asyncio.get_event_loop().run_until_complete(self.scan(progress))
            asyncio.get_event_loop().run_until_complete(self.scan(fast_scan, progress))


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

    if not host:
        raise ValueError(f"Host must be specified. inputs: host={host}")

    if protocol not in ["tcp", "udp"]:
        raise ValueError(f"Invalid protocol specified. Only 'tcp' and 'udp' are supported. inputs: {protocol}")

    if not port:
        host, port = extract_host_port(host)
        pawn.console.debug(f"[red] Parsed from host -> host={host}, port={port}")

    port = int(port)
    pawn.console.debug(f"host={host}, port={port} ({type(port).__name__}), protocol={protocol}, timeout={timeout}")

    socket_protocol = socket.SOCK_STREAM if protocol == "tcp" else socket.SOCK_DGRAM

    # if timeout:
    #     socket.setdefaulttimeout(float(timeout))  # seconds (float)

    with socket.socket(socket.AF_INET, socket_protocol) as sock:
        host = http.remove_http(host)
        sock.settimeout(timeout)  # Set timeout directly on the socket
        try:
            result = sock.connect_ex((host, port))
        except Exception as e:
            pawn.console.debug(f"[FAIL] {e}")
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


def wait_for_port_open(host: str = "", port: int = 0, timeout: float = 3.0, protocol: Literal["tcp", "udp"] = "tcp", sleep: float =1) -> bool:
    """

    Wait for a port to open. Useful when writing scripts which need to wait for a server to be available.

    :param host: hostname or ipaddress
    :param port: port
    :param timeout: timeout seconds (float)
    :param protocol: tcp or udp
    :param sleep: sleep fime seconds (float)
    :return:

    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.wait_for_port_open("127.0.0.1", port)

            ## ⠏  Wait for port open 127.0.0.1:9900 ... 6


    """
    message = f"[bold green] Wait for port open[/bold green] {host}:{port} ........."
    count = 0
    with pawn.console.status(message) as status:
        while True:
            if check_port(host, port, timeout, protocol):
                status.stop()
                pawn.console.debug(f"[OK] Activate port -> {host}:{port}")
                pawn.app_logger.info(f"[OK] Activate port -> {host}:{port}")
                return True
            status.update(f"{message}[cyan] {count}[/cyan]")
            count += 1
            time.sleep(sleep)


def get_location(ipaddress=""):
    try:
        response = requests.get(
        f"https://ipinfo.io/widget/demo/{ipaddress}",
            headers={
                'referer': 'https://ipinfo.io/',
                'content-type': 'application/json',
            },
            timeout=2,
        )
        return response.json().get('data')
    except Exception as e:
        pawn.console.debug(f"Error getting location - {e}")
        return {}


def get_location_with_ip_api():
    try:
        response = requests.get(
            f"http://ip-api.com/json",
            headers={
                'content-type': 'application/json',
            },
            timeout=2,
        )
        return response.json()
    except Exception as e:
        pawn.console.debug(f"Error getting location - {e}")
        return {}




