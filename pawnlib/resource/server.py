import resource as __resource
import time
import platform
import os
import subprocess
import re
from typing import Callable, Union, Dict, List
from collections import OrderedDict, defaultdict
from pawnlib.utils import http
from pawnlib.typing import is_valid_ipv4, split_every_n, format_size
from pawnlib.config import pawn
from pawnlib.typing.converter import PrettyOrderedDict, dict_to_line, format_network_traffic
from pawnlib.resource.net import ProcNetMonitor

import shutil
import random
import string

import socket
import fcntl
import struct
import statistics
from concurrent.futures import ThreadPoolExecutor
from rich.progress import Progress, TaskID, TextColumn, BarColumn, TimeRemainingColumn, TimeElapsedColumn
import json

try:
    import psutil
except Exception as e:
    pawn.console.log(f"[red]{e}")

import signal
import sys

from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.console import Console
import threading
import requests
import logging
import aiohttp
import asyncio
logger = logging.getLogger(__name__)


def hex_mask_to_cidr(hex_mask):
    """
    Converts a hexadecimal mask to a CIDR value.

    :param hex_mask: The hexadecimal mask to convert.
    :return: The CIDR value of the mask.

    Example:

        .. code-block:: python

            from pawnlib.resource import server

            server.hex_mask_to_cidr("FFFF")
            # >> 16

            server.hex_mask_to_cidr("FF00")
            # >> 8
    """
    try:
        # Convert hexadecimal mask to integer
        mask_int = int(hex_mask, 16)

        # Convert integer mask to binary string
        bin_mask = bin(mask_int)[2:]  # Remove the '0b' prefix

        # Count the number of '1's to get the CIDR value
        cidr = bin_mask.count('1')

        return cidr

    except ValueError:
        return None


def get_interface_names():
    """
    Get a list of interface names on the system.

    :return: a list of interface names

    Example:

        .. code-block:: python

            from pawnlib.resource import server
            server.get_interface_names()
            # >> ['lo', 'enp0s31f6', 'wlp0s20f3']
    """
    if platform.system() == 'Linux':
        with open('/proc/net/dev') as f:
            data = f.readlines()
        interfaces = [line.split(':')[0].strip() for line in data if ':' in line]
    elif platform.system() == 'Darwin':
        interfaces = [if_name[1] for if_name in socket.if_nameindex()]
    else:
        raise ValueError("Only Linux and macOS are supported")
    return interfaces


def get_ip_addresses(interface):
    """
    Get a list of IP addresses associated with a given network interface.

    :param interface: A string representing the name of the network interface.
    :return: A list of IP addresses associated with the given network interface.

    Example:

        .. code-block:: python

            from pawnlib.resource import server
            server.ip_addresses = get_ip_addresses('eth0')
            # >> ['192.168.0.1', '192.168.0.2']

    """
    ip_addresses = []
    if platform.system() == 'Linux':
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ip_address = socket.inet_ntoa(fcntl.ioctl(
                sock.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', interface.encode('utf-8')[:15])
            )[20:24])
            ip_addresses.append(ip_address)
        except IOError:
            pass
    elif platform.system() == 'Darwin':
        output = subprocess.check_output(['ifconfig', interface])
        lines = output.decode().split('\n')
        addresses = [line.split()[1] for line in lines if 'inet ' in line]
        for address in addresses:
            ip_addresses.append(address)
    else:
        raise ValueError("Only Linux and macOS are supported")
    return ip_addresses


def get_ip_and_netmask(interface):
    """
    Get IP address and netmask of the given interface.

    :param interface: The name of the interface.
    :return: A list containing the IP address and netmask.

    Example:

        .. code-block:: python

            from pawnlib.resource import server
            server.ip_info = get_ip_and_netmask('eth0')
            print(ip_info)
            # >> ['192.168.0.2', '255.255.255.0']

    """
    ip_info = []

    if platform.system() == 'Linux':
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Get IP address
            ip_address = socket.inet_ntoa(fcntl.ioctl(
                sock.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', interface.encode('utf-8')[:15])
            )[20:24])
            ip_info.append(ip_address)

            # Get netmask
            netmask = socket.inet_ntoa(fcntl.ioctl(
                sock.fileno(),
                0x891b,  # SIOCGIFNETMASK
                struct.pack('256s', interface.encode('utf-8')[:15])
            )[20:24])
            ip_info.append(netmask)

        except IOError:
            pass
    elif platform.system() == 'Darwin':
        output = subprocess.check_output(['ifconfig', interface])
        lines = output.decode().split('\n')
        for line in lines:
            if 'inet ' in line:
                parts = line.split()
                ip_info.append(parts[1])
                netmask = parts[3]
                cidr_netmask = hex_mask_to_cidr(netmask)
                if cidr_netmask:
                    ip_info.append(str(subnet_mask_to_decimal(cidr_netmask)))

    return ip_info


def subnet_mask_to_decimal(subnet_mask):
    """
    Convert subnet mask to decimal.

    :param subnet_mask: Subnet mask in integer format.
    :type subnet_mask: int
    :return: Decimal subnet mask.
    :rtype: str

    Example:

        .. code-block:: python

            from pawnlib.resource import server
            server.subnet_mask_to_decimal(24)
            # >> '255.255.255.0'

            server.subnet_mask_to_decimal(16)
            # >> '255.255.0.0'

    """
    if 0 <= subnet_mask <= 32:
        binary_subnet = "1" * subnet_mask + "0" * (32 - subnet_mask)
        decimal_subnet = [str(int(binary_subnet[i:i+8], 2)) for i in range(0, 32, 8)]
        return ".".join(decimal_subnet)
    return None


def get_interface_ips(ignore_interfaces=None, detail=False, is_sort=True, ip_only=False):
    """
    Get the IP addresses of the interfaces.

    :param ignore_interfaces: A list of interface names to ignore.
    :param detail: Whether to show detailed information or not.
    :param is_sort: Whether to sort the results or not.
    :param ip_only: If True, return only the IP addresses.
    :return: A list of tuples containing interface name and IP address, a dictionary with IP, subnet, and gateway, or just IPs if ip_only is True.


    Example:

        .. code-block:: python

            from pawnlib.resource import server

            server.get_interface_ips()
            # >> [('lo', '127.0.0.1 / 8'), ('wlan0', '192.168.0.10, G/W: 192.168.0.1')]

            server.get_interface_ips(detail=True)
            # >>  [ ('en0', {'ip': '20.22.1.13', 'subnet': '255.255.252.0', 'gateway': '20.22.0.1'}),('utun4', {'ip': '43.62.13.6'})]

            server.get_interface_ips(ip_only=True)
            # >> ['127.0.0.1', '192.168.0.10']

    """
    interfaces_and_ips = []

    if ignore_interfaces is None:
        ignore_interfaces = []

    interface_names = get_interface_names()
    default_route, default_interface = get_default_route_and_interface()

    for interface_name in interface_names:
        if interface_name in ignore_interfaces:
            continue

        if detail:
            ip_and_netmask = get_ip_and_netmask(interface_name)
            ip_dict = {}

            # Only add to the dict if the IP value exists
            if ip_and_netmask and len(ip_and_netmask) > 0:
                ip_dict["ip"] = ip_and_netmask[0]
                if len(ip_and_netmask) > 1:
                    ip_dict["subnet"] = ip_and_netmask[1]
                if default_interface and interface_name == default_interface and default_route:
                    ip_dict["gateway"] = default_route

            ip_address = ip_dict
        else:
            ip_address = " ".join(get_ip_addresses(interface_name))

            # if default_interface and default_route and interface_name == default_interface:
            #     ip_address += f", G/W: {default_route}"

        if ip_address:
            interfaces_and_ips.append((interface_name, ip_address))

    if is_sort:
        interfaces_and_ips.sort(key=lambda x: 'gateway' in x[1] if isinstance(x[1], dict) else 'G/W' in x[1], reverse=True)

    if ip_only:
        return [ip for _, ip in interfaces_and_ips]

    return interfaces_and_ips


def get_interface_ips_dict(ignore_interfaces=[]):
    """
    Get the IP addresses of all interfaces in a dictionary format.

    :param ignore_interfaces: list of interfaces to be ignored
    :return: dictionary with interface names as keys and their IP addresses as values

    Example:

        .. code-block:: python

            from pawnlib.resource import server

            server.get_interface_ips_dict(ignore_interfaces=['lo', 'eth0'])
            # >> {'wlan0': '192.168.1.100'}

    """
    interface_dict = {}
    for interface, ipaddr in get_interface_ips(ignore_interfaces=ignore_interfaces):
        interface_dict[interface] = ipaddr
    return interface_dict


def get_default_route_and_interface():
    """
    Parse the route of the process based on the platform.

    Example:

        .. code-block:: python

            from pawnlib.resource import server

            get_default_route_and_interface()
            # If Linux:
            # >> ('192.168.1.1', 'eth0')
            # If MacOS:
            # >> ('192.168.1.1', 'en0')
            # If other platform:
            # >> ("Unsupported platform.", None)

    """
    try:
        if platform.system() == 'Linux':
            return get_default_route_and_interface_linux()
        elif platform.system() == 'Darwin':
            return get_default_route_and_interface_macos()
        else:
            print("Unsupported platform.")
            return None, None
    except FileNotFoundError:
        print("Error: /proc/net/route file not found.")
        return None, None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None, None


def get_default_route_and_interface_linux():
    """
    Parse the Linux route.

    Example:

        .. code-block:: python

            from pawnlib.resource import server

            server.get_default_route_and_interface_linux()
            # >> ('192.168.1.1', 'eth0')

    """
    with open('/proc/net/route', 'r') as route_file:
        for line in route_file.readlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 11 and parts[1] == '00000000':
                default_interface = parts[0]
                default_route = '.'.join([str(int(parts[2][i:i+2], 16)) for i in range(6, -1, -2)])
                return default_route, default_interface


def get_default_route_and_interface_macos():
    """
    Parse the Linux route.

    Example:

        .. code-block:: python

            from pawnlib.resource import server

            server.get_default_route_and_interface_macos()
            # >> ('192.168.1.1', 'eth0')

    """
    route_output = subprocess.check_output(['netstat', '-rn']).decode('utf-8')
    for line in route_output.splitlines():
        if 'default' in line:
            parts = re.split(r'\s+', line.strip())
            default_route = parts[1]
            default_interface = parts[3]
            if is_valid_ipv4(default_route):
                return default_route, default_interface
    return None, None



class ProcessMonitor:
    def __init__(self, console: Console = None, n: int = 5):
        self.console = console if console else Console()
        self.process_number = n
        self.previous_usage = {}
        self.stop_event = threading.Event()
        self.proc_net_monitor =  ProcNetMonitor(
                                                        top_n=5,
                                                        refresh_rate=1,
                                                        group_by="pid",
                                                        unit="Mbps",
                                                        protocols=["tcp", "udp"]
                                                )

        self._proc_net_monitor_thread = threading.Thread(target=self._run_proc_net_monitor, daemon=True)
        self._proc_net_monitor_thread.start()

    def _run_proc_net_monitor(self):
        """
        ProcNetMonitor.run()을 실행하는 스레드.
        """
        self.proc_net_monitor.run()


    def stop(self):
        """
        모든 작업 종료
        """
        # self.stop_event.set()
        # self.proc_net_monitor.is_running = False  # 종료 신호 설정
        # self._proc_net_monitor_thread.join()
        # self.console.print("ProcNetMonitor stopped.", style="bold green")


        self.console.print("Stopping ProcessMonitor...", style="bold yellow")
        self.proc_net_monitor.is_running = False  # 종료 신호 설정

        if self._proc_net_monitor_thread:
            self._proc_net_monitor_thread.join()
            self.console.print("ProcessMonitor stopped.", style="bold green")

    def stop(self):
        """
        모든 모니터링 작업을 종료합니다.
        """
        self.console.print("Stopping ProcessMonitor...", style="bold yellow")
        self.proc_net_monitor.is_running = False  # ProcNetMonitor 루프 종료 신호 설정
        self._proc_net_monitor_thread.join()  # 스레드가 종료될 때까지 대기
        self.console.print("ProcessMonitor stopped.", style="bold green")


    def get_top_processes(self, n: int = 5, resource: str = "memory") -> List[Dict[str, Union[str, float]]]:
        processes = []
        all_processes = list(psutil.process_iter(['pid', 'name']))

        if resource == "cpu":
            for proc in all_processes:
                try:
                    proc.cpu_percent(interval=None)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError):
                    pass
            time.sleep(1)

        for proc in all_processes:
            try:
                if resource == "memory":
                    memory_percent = proc.memory_percent()
                    processes.append({
                        'pid': proc.pid,
                        'name': proc.name(),
                        'memory_percent': memory_percent
                    })
                elif resource == "cpu":
                    cpu_percent = proc.cpu_percent(interval=None)
                    processes.append({
                        'pid': proc.pid,
                        'name': proc.name(),
                        'cpu_percent': cpu_percent
                    })
                elif resource == "io":
                    if sys.platform == "darwin":
                        continue  # macOS에서는 I/O 카운터를 지원하지 않습니다.

                    io_counters = proc.io_counters()

                    if io_counters:
                        processes.append({
                            'pid': proc.pid,
                            'name': proc.name(),
                            'io_read_bytes': io_counters.read_bytes,
                            'io_write_bytes': io_counters.write_bytes
                        })
                # elif resource == "network":
                #     net_usage = self.get_process_network_usage(proc.pid)
                #     if net_usage:
                #         processes.append(net_usage)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError):
                continue

        # 정렬 및 상위 n개 반환
        if resource in ["memory", "cpu"]:
            key = 'memory_percent' if resource == "memory" else 'cpu_percent'
            return sorted(processes, key=lambda x: x.get(key, 0), reverse=True)[:n]
        elif resource == "io":
            return sorted(
                processes,
                key=lambda x: x.get('io_read_bytes', 0) + x.get('io_write_bytes', 0),
                reverse=True
            )[:n]
        elif resource == "network":
            return sorted(
                processes,
                key=lambda x: x.get('tx_bytes', 0) + x.get('rx_bytes', 0),
                reverse=True
            )[:n]
        else:
            return []


    def get_network_usage_from_monitor(self) -> List[Dict[str, Union[int, str, float]]]:
        """
        Fetch network usage data from ProcNetMonitor.

        Returns:
            List[Dict[str, Union[int, str, float]]]: Process network usage data.
        """
        if not self.proc_net_monitor:
            self.console.print("[red]ProcNetMonitor instance is not available![/red]")
            return []

        try:
            # Use ProcNetMonitor to fetch top N processes
            # res = self.proc_net_monitor.get_top_n(self.process_number)
            return self.proc_net_monitor.get_top_n(self.process_number)
        except Exception as e:
            self.console.print(f"[red]Error fetching network usage: {e}[/red]")
            return []


    def create_resource_table(self, processes: List[Dict[str, Union[str, float]]], resource: str) -> Table:
        """
        리소스 데이터에 대한 리치 테이블 생성.
        """
        table = Table(title=f"Top Processes by {resource.capitalize()} Usage", expand=True)

        table.add_column("PID", justify="right", style="cyan", width=8)
        table.add_column("Name", style="green", width=25)

        if resource == "memory":
            table.add_column("Memory %", justify="right", style="magenta", width=10)
        elif resource == "cpu":
            table.add_column("CPU %", justify="right", style="magenta", width=10)
        elif resource == "io":
            table.add_column("IO Read (MB)", justify="right", style="yellow", width=12)
            table.add_column("IO Write (MB)", justify="right", style="yellow", width=12)
        elif resource == "network":
            table.add_column("RX Bytes", justify="right", style="blue", width=15)
            table.add_column("TX Bytes", justify="right", style="blue", width=15)

        for proc in processes:
            if resource == "memory":
                table.add_row(
                    str(proc['pid']),
                    proc['name'],
                    f"{proc.get('memory_percent', 0):.2f}%"
                )
            elif resource == "cpu":
                table.add_row(
                    str(proc['pid']),
                    proc['name'],
                    f"{proc.get('cpu_percent', 0):.2f}%"
                )
            elif resource == "io":
                read_mb = proc.get('io_read_bytes', 0) / (1024 * 1024)
                write_mb = proc.get('io_write_bytes', 0) / (1024 * 1024)
                table.add_row(
                    str(proc['pid']),
                    proc['name'],
                    f"{read_mb:.2f}",
                    f"{write_mb:.2f}"
                )
            elif resource == "network":
                row = [
                    str(proc.get('pid', 'N/A')),
                    proc['comm'],
                    format_network_traffic(proc.get('tcp_sent_rate', 0)),
                    format_network_traffic(proc.get('tcp_recv_rate', 0)),
                ]
                table.add_row(*row)
        return table


    def create_dashboard(self) -> Layout:
        try:
            memory_processes = self.get_top_processes(n=self.process_number, resource="memory")
            cpu_processes = self.get_top_processes(n=self.process_number, resource="cpu")
            io_processes = self.get_top_processes(n=self.process_number, resource="io")

            # Fetch network data from ProcNetMonitor
            network_processes = self.get_network_usage_from_monitor()
            memory_table = self.create_resource_table(memory_processes, resource="memory")
            cpu_table = self.create_resource_table(cpu_processes, resource="cpu")
            io_table = self.create_resource_table(io_processes, resource="io")
            network_table = self.create_resource_table(network_processes, resource="network")

            memory_panel = Panel(memory_table, title="[bold magenta]Memory Usage[/bold magenta]", border_style="magenta")
            cpu_panel = Panel(cpu_table, title="[bold cyan]CPU Usage[/bold cyan]", border_style="cyan")
            io_panel = Panel(io_table, title="[bold yellow]I/O Usage[/bold yellow]", border_style="yellow")
            network_panel = Panel(network_table, title="[bold yellow]Network Usage[/bold yellow]", border_style="yellow")

            layout = Layout()
            layout.split_column(
                Layout(name="row1", ratio=1),
                Layout(name="row2", ratio=1)
            )

            layout["row1"].split_row(
                Layout(memory_panel, name="memory"),
                Layout(cpu_panel, name="cpu")
            )
            layout["row2"].split_row(
                Layout(io_panel, name="io"),
                Layout(network_panel, name="network")
            )

            return layout
        except Exception as e:
            self.console.print(f"[red]Error in create_dashboard: {e}[/red]")
            return Layout()


    def run_live(self):
        """
        실시간 대시보드를 표시합니다.
        """
        with Live(self.create_dashboard(), refresh_per_second=1, console=self.console) as live:
            try:
                while self.proc_net_monitor.is_running:
                    live.update(self.create_dashboard())
                    time.sleep(1)
            except KeyboardInterrupt:
                self.console.print("Stopping NetworkMonitor.", style="bold yellow")
                self.stop()


class MemoryStatus:
    def __init__(self, proc_path="/proc"):
        self.proc_path = proc_path
        self.last_check_time = 0
        self.cached_result = None
        self.cache_duration = 1  # 캐시 유효 시간 (초)
        self.memory_history = []
        self.pressure_paths_checked = True  # 경로 확인 여부

    @staticmethod
    def read_stats_file(file_path: str) -> str:
        try:
            with open(file_path, 'r') as f:
                return f.read()
        except IOError as e:
            raise IOError(f"Error reading file {file_path}: {e}")

    @staticmethod
    def parse_meminfo(meminfo: str) -> Dict[str, int]:
        result = {}
        for line in meminfo.splitlines():
            if ':' in line:
                key, value = line.split(':')
                result[key.strip()] = int(value.split()[0])
        return result

    def get_memory_pressure(self) -> Dict[str, float]:

        if self.pressure_paths_checked:
            paths = [f'{self.proc_path}/pressure/memory', '/sys/fs/cgroup/memory.pressure']
            for path in paths:
                try:
                    with open(path, 'r') as f:
                        pressure = f.read().strip().split()
                        self.pressure_paths_checked = True
                        return {
                            "some_avg10": float(pressure[1].split('=')[1]),
                            "some_avg60": float(pressure[2].split('=')[1]),
                            "some_avg300": float(pressure[3].split('=')[1]),
                            "full_avg10": float(pressure[5].split('=')[1]),
                            "full_avg60": float(pressure[6].split('=')[1]),
                            "full_avg300": float(pressure[7].split('=')[1])
                        }
                except:
                    # self.pressure_paths_checked = False
                    continue
            self.pressure_paths_checked = False
            return {}

    @staticmethod
    def get_top_memory_processes(n: int = 5) -> List[Dict[str, Union[str, float]]]:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'memory_percent': proc.info['memory_percent']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:n]

    def get_huge_pages_info(self) -> Dict[str, int]:
        meminfo = self.parse_meminfo(self.read_stats_file(f"{self.proc_path}/meminfo"))
        return {
            "HugePages_Total": meminfo.get("HugePages_Total", 0),
            "HugePages_Free": meminfo.get("HugePages_Free", 0),
            "HugePages_Rsvd": meminfo.get("HugePages_Rsvd", 0),
            "HugePages_Surp": meminfo.get("HugePages_Surp", 0),
            "Hugepagesize": meminfo.get("Hugepagesize", 0)
        }

    def get_memory_status(self, unit: str = "GB", output_format: str = "dict") -> Union[Dict, str]:
        current_time = time.time()
        if current_time - self.last_check_time < self.cache_duration and self.cached_result:
            return self.cached_result

        try:
            meminfo = self.read_stats_file(f"{self.proc_path}/meminfo")
            meminfo_dict = self.parse_meminfo(meminfo)
        except IOError as e:
            raise RuntimeError(f"Failed to read memory information: {e}")

        units = {"KB": 1, "MB": 1024, "GB": 1024 * 1024, "TB": 1024 * 1024 * 1024}
        if unit.upper() not in units:
            raise ValueError(f"Invalid unit: {unit}. Choose from KB, MB, GB, TB.")
        unit_multiplier = units[unit.upper()]

        total_mem = meminfo_dict["MemTotal"] / unit_multiplier
        free_mem = meminfo_dict["MemFree"] / unit_multiplier
        avail_mem = meminfo_dict["MemAvailable"] / unit_multiplier
        cached_mem = meminfo_dict["Cached"] / unit_multiplier
        buffers_mem = meminfo_dict.get("Buffers", 0) / unit_multiplier
        swap_total = meminfo_dict.get("SwapTotal", 0) / unit_multiplier
        swap_free = meminfo_dict.get("SwapFree", 0) / unit_multiplier

        used_mem = total_mem - free_mem - cached_mem - buffers_mem
        swap_used = swap_total - swap_free
        percent_used = 100 * (total_mem - avail_mem) / total_mem
        swap_percent = 100 * swap_used / swap_total if swap_total > 0 else 0

        result = {
            "total": round(total_mem, 2),
            "used": round(used_mem, 2),
            "free": round(free_mem, 2),
            "available": round(avail_mem, 2),
            "cached": round(cached_mem, 2),
            "buffers": round(buffers_mem, 2),
            "percent": round(percent_used, 2),
            "swap_total": round(swap_total, 2),
            "swap_used": round(swap_used, 2),
            "swap_free": round(swap_free, 2),
            "swap_percent": round(swap_percent, 2),
            "unit": unit,
            "pressure": self.get_memory_pressure(),
            "top_processes": self.get_top_memory_processes(),
            "huge_pages": self.get_huge_pages_info()
        }

        self.memory_history.append((current_time, percent_used))
        if len(self.memory_history) > 60:
            self.memory_history.pop(0)

        result["memory_trend"] = [{"time": t, "percent": p} for t, p in self.memory_history]

        self.last_check_time = current_time
        self.cached_result = result

        if output_format == "dict":
            return result
        elif output_format == "json":
            return json.dumps(result, indent=2)
        elif output_format == "text":
            return "\n".join([f"{k}: {v}" for k, v in result.items()])
        else:
            raise ValueError(f"Invalid output format: {output_format}. Choose from dict, json, text.")

    def check_memory_threshold(self, threshold: float = 90.0) -> bool:
        """메모리 사용량이 임계값을 초과하는지 확인"""
        status = self.get_memory_status()
        return status['percent'] > threshold


class SystemMonitor:
    def __init__(self, interval=1, proc_path="/proc"):
        if interval <= 0:
            raise ValueError("Interval must be a positive number greater than 0")

        self.interval = interval
        self.proc_path = proc_path
        self.prev_net_data = self.parse_net_dev()
        self.prev_cpu_data = self.parse_cpu_stat()
        self.prev_disk_stats = self.read_disk_stats()

        self.mem_status = MemoryStatus(proc_path=self.proc_path)
        self.cached_result = None
        self.cache_duration = 1

    @staticmethod
    def read_stats_file(filename=""):
        with open(filename) as f:
            return f.readlines()

    def parse_net_dev(self):
        lines = self.read_stats_file(f"{self.proc_path}/net/dev")
        data = {}
        for line in lines[2:]:
            parts = line.split()
            iface = parts[0].strip(':')
            if iface == "lo" or iface.startswith("sit"):
                continue
            data[iface] = {
                'recv': int(parts[1]),
                'sent': int(parts[9]),
                'packets_recv': int(parts[2]),
                'packets_sent': int(parts[10]),
            }
        return data

    def parse_cpu_stat(self):
        for line in self.read_stats_file(f"{self.proc_path}/stat"):
            if line.startswith("cpu "):
                values = line.split()[1:]
                return list(map(int, values))

    def get_cpu_status(self, decimal=1):
        end_values = self.parse_cpu_stat()
        start_values = self.prev_cpu_data
        self.prev_cpu_data = end_values

        diff = [end - start for start, end in zip(start_values, end_values)]
        total_diff = sum(diff)

        us_percent = 100 * diff[0] / total_diff
        sy_percent = 100 * diff[2] / total_diff
        id_percent = 100 * diff[3] / total_diff
        io_wait = 100 * diff[4] / total_diff

        return {
            'usr': round(us_percent, decimal),
            'sys': round(sy_percent, decimal),
            'idle': round(id_percent, decimal),
            'io_wait': round(io_wait, decimal)
        }

    def collect_system_status(self):
        time.sleep(self.interval)
        cpu_status = self.get_cpu_status()
        network_status = self.get_network_status()
        disk_stats = self.get_disk_usage()
        return network_status, cpu_status, disk_stats

    def get_network_status(self):
        curr_net_data = self.parse_net_dev()
        interface_data = OrderedDict()
        total_received = total_sent = total_packets_recv = total_packets_sent = 0

        for iface, curr in curr_net_data.items():
            prev = self.prev_net_data.get(iface)
            if prev:
                diff_recv = (curr['recv'] - prev['recv']) * 8 / 1_000_000 / self.interval  # Bytes to Mb
                diff_sent = (curr['sent'] - prev['sent']) * 8 / 1_000_000 / self.interval  # Bytes to Mb
                diff_packets_recv = curr['packets_recv'] - prev['packets_recv']
                diff_packets_sent = curr['packets_sent'] - prev['packets_sent']

                total_received += diff_recv
                total_sent += diff_sent
                total_packets_recv += diff_packets_recv
                total_packets_sent += diff_packets_sent

                interface_data[iface] = {
                    "recv": diff_recv,
                    "sent": diff_sent,
                    "packets_recv": diff_packets_recv,
                    "packets_sent": diff_packets_sent,
                }

        interface_data["Total"] = {
            "recv": total_received,
            "sent": total_sent,
            "packets_recv": total_packets_recv,
            "packets_sent": total_packets_sent,
        }
        self.prev_net_data = curr_net_data
        return interface_data

    def read_disk_stats(self):
        disk_stats = {}
        lines = self.read_stats_file(f"{self.proc_path}/diskstats")
        for line in lines:
            parts = line.split()
            disk_name = parts[2]
            if any(disk_name.startswith(prefix) for prefix in ["sd", "vd", "nvme"]):
                disk_stats[disk_name] = {
                    'read_ios': int(parts[3]),
                    'read_bytes': int(parts[5]) * 512,
                    'write_ios': int(parts[7]),
                    'write_bytes': int(parts[9]) * 512,
                }
        return disk_stats

    def get_disk_usage(self):
        curr_disk_stats = self.read_disk_stats()
        disk_usage = {}
        total_read_ios = total_write_ios = total_read_bytes = total_write_bytes = 0

        for disk, curr in curr_disk_stats.items():
            if disk in self.prev_disk_stats:
                prev = self.prev_disk_stats[disk]
                read_ios = curr['read_ios'] - prev['read_ios']
                read_bytes = curr['read_bytes'] - prev['read_bytes']
                write_ios = curr['write_ios'] - prev['write_ios']
                write_bytes = curr['write_bytes'] - prev['write_bytes']

                disk_usage[disk] = {
                    'read_ios': read_ios,
                    'read_bytes': read_bytes,
                    'write_ios': write_ios,
                    'write_bytes': write_bytes,
                    'read_mb': round(read_bytes / (1024 * 1024), 2),
                    'write_mb': round(write_bytes / (1024 * 1024), 2)
                }

                total_read_ios += read_ios
                total_write_ios += write_ios
                total_read_bytes += read_bytes
                total_write_bytes += write_bytes

        disk_usage['Total'] = {
            'read_ios': total_read_ios,
            'read_bytes': total_read_bytes,
            'write_ios': total_write_ios,
            'write_bytes': total_write_bytes,
            'read_mb': round(total_read_bytes / (1024 * 1024), 2),
            'write_mb': round(total_write_bytes / (1024 * 1024), 2)
        }
        self.prev_disk_stats = curr_disk_stats
        return disk_usage

    def get_memory_status(self, unit="GB"):
        result = self.mem_status.get_memory_status(unit=unit)
        return result

    def get_system_status(self):
        time.sleep(self.interval)
        network_status = self.get_network_status()
        cpu_status = self.get_cpu_status()
        disk_stats = self.get_disk_usage()
        return network_status, cpu_status, disk_stats

    def print_memory_status(self):
        mem_status = self.get_memory_status()
        print(f"Memory Usage --> {mem_status['percent']:.2f}% ({mem_status['used']:.2f} {mem_status['unit']} Used / {mem_status['total']:.2f} {mem_status['unit']} Total)")


def get_netstat_count(proc_path="/proc", detail=False):
    netstate_kind = {
        '01': 'ESTAB',
        '02': 'SYN_SENT',
        '03': 'SYN_RECV',
        '04': 'FIN_WAIT1',
        '05': 'FIN_WAIT2',
        '06': 'TIME_WAIT',
        '07': 'CLOSE',
        '08': 'CLOSE_WAIT',
        '09': 'LAST_ACK',
        '0A': 'LISTEN',
        '0B': 'CLOSING'
    }

    netstate_result = {
        "COUNT": defaultdict(int),
        # "DETAIL": defaultdict(lambda: defaultdict(int))
    }
    for net_key, net_value  in netstate_kind.items():
        netstate_result["COUNT"][net_value] = 0

    if detail:
        netstate_result['DETAIL'] = defaultdict(lambda: defaultdict(int))

    try:
        with open(f'{proc_path}/net/tcp') as f:
            lineno = 0
            for line in f:
                lineno += 1
                if lineno == 1:
                    continue
                line_list = re.split(r'\s+', line.strip())
                local = convert_hex_to_ip_port(line_list[1])
                remote = convert_hex_to_ip_port(line_list[2])
                kind = netstate_kind.get(line_list[3])

                netstate_result["COUNT"][kind] += 1

                if detail:
                    local_port = local.split(":")[1]
                    remote_port = remote.split(":")[1]

                    if "TIME_WAIT" in kind:
                        port = remote_port
                    else:
                        port = local_port

                    netstate_result["DETAIL"][port][kind] += 1

    except Exception as e:
        print(e)

    return netstate_result


def convert_hex_to_ip_port(address):
    hex_addr, hex_port = address.split(':')
    addr_list = [hex_addr[i:i+2] for i in range(0, len(hex_addr), 2)]
    addr_list.reverse()
    addr = ".".join(str(int(x, 16)) for x in addr_list)
    port = str(int(hex_port, 16))
    return "{}:{}".format(addr, port)


def _line_split(line="", sep=":", d=0, data_type: Callable = str):
    data = line.split(sep)
    if len(data) >= d:
        return data_type(data[d].strip())
    return data_type()


def get_rlimit_nofile(detail=False):
    """
    Returns a dict with the current soft and hard limits of resource.
    If detail is True, it also includes the number of used file handles
    and their usage percentage.

    :param detail: If True, include used_handles and usage_percentage.
    :return: A dictionary containing 'soft', 'hard', and optionally 'used_handles', 'usage_percentage'.

    Example:

        .. code-block:: python

            from pawnlib.resource import server
            server.get_rlimit_nofile(detail=True)

            ## > {'soft': 1024, 'hard': 4096, 'used_handles': 512, 'usage_percentage': 50.0}

    """
    soft, hard = __resource.getrlimit(__resource.RLIMIT_NOFILE)

    result = {
        "soft": soft,
        "hard": hard
    }

    if detail:
        # Use lsof to count the number of currently open file handles
        used_handles = int(subprocess.check_output("lsof 2>&1 | grep -v 'no pwd entry for UID'| wc -l", shell=True).strip())

        # Calculate the percentage of used file handles
        usage_percentage = (used_handles / soft) * 100 if soft > 0 else 0

        # Add these details to the result
        result["used_handles"] = used_handles
        result["usage_percentage"] = round(usage_percentage, 2)  # Round to two decimal places

    return result


def get_mac_platform_info():
    """

    :return:

    Example:

        .. code-block:: python

            from pawnlib.resource import server
            server.get_mac_platform_info()


    """
    task = subprocess.Popen(
        ['system_profiler', 'SPHardwareDataType'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    data = {}
    output, err = task.communicate()

    for line in output.decode('utf-8').split('\n'):
        if 'Chip:' in line:
            data['model'] = _line_split(line=line, sep=":", d=1)
        if 'Total Number of Cores:' in line:
            tmp = _line_split(line=line, sep=":", d=1)
            tmp = _line_split(line=tmp, sep="(", d=0, data_type=int)
            data['cores'] = tmp
    return data


def get_platform_info(**kwargs):
    """
    Returns a dict with platform information, including the specific operating system.

    :return: A dictionary containing platform information.

    Example:

        .. code-block:: python

            from pawnlib.resource import server
            server.get_platform_info()

            ## > {'system': 'Darwin', 'os': 'macOS', 'version': 'Darwin Kernel Version 21.6.0: Wed Aug 10 14:28:23 PDT 2022; root:xnu-8020.141.5~2/RELEASE_ARM64_T6000', 'release': '21.6.0', 'machine': 'arm64', 'processor': 'arm', 'python_version': '3.9.13', 'model': 'Apple M1 Pro', 'cores': 10}

    """

    try:
        uname = platform.uname()
        python_version = platform.python_version()
        os_name = "Unknown"

        if uname.system == "Darwin":
            os_name = "macOS"
        elif uname.system == "Linux":
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("ID="):
                            os_name = line.strip().split("=")[1].strip('"')
                            break
        elif uname.system == "Windows":
            os_name = "Windows"

        platform_info = {
            "system": uname.system,
            "os": os_name,
            "version": uname.version,
            "release": uname.release,
            "machine": uname.machine,
            "processor": uname.processor,
            "python_version": python_version,
        }
    except Exception as e:
        print(e)
        platform_info = {}

    if platform_info.get('system') == "Darwin":
        platform_info.update(**get_mac_platform_info())
    else:
        try:
            with open('/proc/cpuinfo') as f:
                cpu_count = 0
                model = None
                for line in f:
                    if line.strip():
                        if line.rstrip('\n').startswith('model name'):
                            model_name = line.rstrip('\n').split(':')[1].strip()
                            model = model_name
                            cpu_count += 1
                platform_info['model'] = model
                platform_info['cores'] = cpu_count
        except Exception as e:
            print(e)

    if isinstance(kwargs, dict):
        platform_info.update(kwargs)

    return platform_info


def parse_cpu_load(load_str):
    load_list = load_str.split()
    cpu_load_dict = PrettyOrderedDict()
    cpu_load_dict["1min"] = round(float(load_list[0]), 2)
    cpu_load_dict["5min"] = round(float(load_list[1]), 2)
    cpu_load_dict["15min"] = round(float(load_list[2]), 2)
    return cpu_load_dict


def get_cpu_load():
    """
    Returns dict with current cpu load average
    :return:

    Example:

        .. code-block:: python

            from pawnlib.resource import server
            server.get_cpu_load()
            ## > {'1min': 12.29, '5min': 11.01, '15min': 11.09}


    """
    if platform.uname().system == "Darwin":
        return get_uptime_cmd()
    else:
        with open('/proc/loadavg') as f:
            cpu_load = f.read()
            return parse_cpu_load(cpu_load)


def parse_proc_stat():
    with open('/proc/stat', 'r') as f:
        lines = f.readlines()

    cpu_line = [line for line in lines if line.startswith('cpu ')][0]
    values = cpu_line.split()[1:]  # Skip the 'cpu' prefix
    values = list(map(int, values))

    return values


def calculate_iowait_linux(interval=1):
    initial_values = parse_proc_stat()
    time.sleep(interval)
    final_values = parse_proc_stat()

    total_initial = sum(initial_values)
    total_final = sum(final_values)

    total_diff = total_final - total_initial
    iowait_diff = final_values[4] - initial_values[4]  # iowait is the 5th value (index 4)

    iowait_percentage = (iowait_diff / total_diff) * 100

    return round(iowait_percentage, 2)


def run_command(command):
    try:
        output = subprocess.check_output(command).decode('utf-8')
        return output.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command {' '.join(command)}: {e}")
        return None


def get_iowait():
    system = platform.system()
    if system == 'Linux':
        return calculate_iowait_linux()
    else:
        pawn.console.debug(f"Unsupported operating system: {system}")


def get_uptime():
    if os.name == 'posix':
        if "Darwin" in os.uname().sysname:
            uptime_seconds = float(subprocess.check_output("sysctl -n kern.boottime | awk '{print $4}' | sed 's/,//'", shell=True).strip())
            current_time = time.time()
            uptime_seconds = current_time - uptime_seconds
        else:  # Linux
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])

        uptime_days = uptime_seconds // (24 * 3600)
        uptime_seconds %= (24 * 3600)
        uptime_hours = uptime_seconds // 3600
        uptime_seconds %= 3600
        uptime_minutes = uptime_seconds // 60

        return f" {int(uptime_days)} days, {int(uptime_hours)} hours, {int(uptime_minutes)} minutes"
    else:
        return "Not supported Uptime on this OS"

def get_swap_usage():
    if os.name != 'posix':
        return "Swap Usage: Not supported on this OS"

    if "Darwin" in os.uname().sysname:  # macOS
        return get_macos_swap_usage()
    else:  # Linux
        return get_linux_swap_usage()


def get_macos_swap_usage():
    try:
        swap_info = subprocess.check_output("sysctl vm.swapusage", shell=True).decode().strip()
        match = re.search(r'total = (\d+\.\d+)M.*used = (\d+\.\d+)M', swap_info)
        if not match:
            raise ValueError("Unexpected swap info format")

        total_swap, used_swap = map(float, match.groups())
        total_swap_gb = total_swap / 1024
        used_swap_gb = used_swap / 1024

        return format_swap_usage(used_swap_gb, total_swap_gb)
    except (subprocess.CalledProcessError, ValueError) as e:
        return f"Error getting swap usage: {str(e)}"


def get_linux_swap_usage():
    try:
        with open('/proc/meminfo') as f:
            meminfo = f.read()

        total_swap = parse_meminfo_line(meminfo, "SwapTotal")
        free_swap = parse_meminfo_line(meminfo, "SwapFree")

        total_swap_gb = total_swap / 1024 / 1024
        used_swap_gb = (total_swap - free_swap) / 1024 / 1024

        return format_swap_usage(used_swap_gb, total_swap_gb)
    except (IOError, ValueError) as e:
        return f"Error getting swap usage: {str(e)}"


def parse_meminfo_line(meminfo, key):
    for line in meminfo.splitlines():
        if key in line:
            return int(line.split()[1])
    raise ValueError(f"{key} not found in meminfo")


def format_swap_usage(used_swap_gb, total_swap_gb):
    if total_swap_gb == 0:
        return "No swap configured"

    usage_percentage = (used_swap_gb / total_swap_gb) * 100
    return f"{used_swap_gb:.2f} GB / {total_swap_gb:.2f} GB ({usage_percentage:.2f}%)"


def get_uptime_cmd() -> dict:
    """
    Returns dict with current cpu load average using uptime command
    :return:

    Example:

        .. code-block:: python

            from pawnlib.resource import server
            server.get_uptime_cmd()
            ## > {'1min': 12.29, '5min': 11.01, '15min': 11.09}


    """

    raw = subprocess.check_output('uptime').decode("utf8").replace(',', '')
    load_raw = raw.split('load averages:')[1].strip()
    # load_list = load_raw.split(' ')
    return parse_cpu_load(load_raw)


def get_load_average():
    load1, load5, load15 = os.getloadavg()
    return f"{load1:.2f}, {load5:.2f}, {load15:.2f} (1, 5, 15 minutes)"


def get_total_memory_usage() -> float:
    """

    Returns float with current memory usage using ps command
    :return: kilo bytes

    Example:

        .. code-block:: python

            from pawnlib.resource import server
            server.get_total_memory_usage()

            ## > 24246272.0


    """
    ps = subprocess.Popen(['ps', '-caxm', '-orss,comm'], stdout=subprocess.PIPE).communicate()[0].decode()
    process_lines = ps.split('\n')
    sep = re.compile('[\s]+')
    rss_total = 0  # kB
    for row in range(1, len(process_lines)):
        row_text = process_lines[row].strip()
        row_elements = sep.split(row_text)
        try:
            rss = float(row_elements[0]) * 1024
        except:
            rss = 0  # ignore...
        rss_total += rss

    return float(rss_total / 1024)


def get_mem_osx_info():
    vm = subprocess.Popen(['vm_stat'], stdout=subprocess.PIPE).communicate()[0].decode()
    # Process vm_stat
    vm_lines = vm.split('\n')
    sep = re.compile(':[\s]+')
    vm_stats = {}
    for row in range(1, len(vm_lines) - 2):
        row_text = vm_lines[row].strip()
        row_elements = sep.split(row_text)
        vm_stats[(row_elements[0])] = int(row_elements[1].strip('\.')) * 4096

    # print('Wired Memory:\t\t%d MB' % (vm_stats["Pages wired down"] / 1024 / 1024))
    # print('Active Memory:\t\t%d MB' % (vm_stats["Pages active"] / 1024 / 1024))
    # print('Inactive Memory:\t%d MB' % (vm_stats["Pages inactive"] / 1024 / 1024))
    # print('Free Memory:\t\t%d MB' % (vm_stats["Pages free"] / 1024 / 1024))
    # print('Real Mem Total (ps):\t%.3f MB' % (rssTotal/1024/1024))

    data = {
        'mem_total': os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 1024,
        'mem_free': (vm_stats["Pages free"] + vm_stats["Pages inactive"]) / 1024,
        'total': (vm_stats["Pages wired down"] + vm_stats["Pages active"] + vm_stats["Pages inactive"] + vm_stats["Pages free"]) / 1024
    }
    return data


def get_mem_info(unit="GB"):
    """
    Read in the /proc/meminfo and return a dictionary of the memory and swap
    usage for all processes.
    """
    units = {"KB": 1, "MB": 1024, "GB": 1024 * 1024}
    if unit not in units:
        raise ValueError(f"Invalid unit. Expected one of: {list(units.keys())}")

    convert_unit = units[unit]

    data = {'mem_total': 0, 'mem_used': 0, 'mem_free': 0,
            'swap_total': 0, 'swap_used': 0, 'swap_free': 0,
            'buffers': 0, 'cached': 0}

    if platform.uname().system == "Darwin":
        data.update(**get_mem_osx_info())
    else:
        with open('/proc/meminfo', 'r') as fh:
            lines = fh.read()
            for line in lines.split('\n'):
                fields = line.split(None, 2)
                if fields[0] == 'MemTotal:':
                    data['mem_total'] = int(fields[1], 10)
                elif fields[0] == 'MemFree:':
                    data['mem_free'] = int(fields[1], 10)
                elif fields[0] == 'Buffers:':
                    data['buffers'] = int(fields[1], 10)
                elif fields[0] == 'Cached:':
                    data['cached'] = int(fields[1], 10)
                elif fields[0] == 'SwapTotal:':
                    data['swap_total'] = int(fields[1], 10)
                elif fields[0] == 'SwapFree:': \
                        data['swap_free'] = int(fields[1], 10)
                break
            data['mem_used'] = data['mem_total'] - data['mem_free']
            data['swap_used'] = data['swap_total'] - data['swap_free']

    data = convert_values_to_unit(data, convert_unit)
    data['unit'] = unit

    return data


def convert_values_to_unit(data, convert_unit):
    for k, v in data.items():
        if isinstance(v, (int, float)):
            data[k] = round(v / convert_unit, 2)
    return data


def get_cpu_time() -> Dict[str, Dict[str, float]]:
    """
    Reads /proc/stat to gather CPU time statistics for each CPU core.
    Returns a dictionary with CPU IDs and their respective time metrics.
    """
    cpu_infos = {}
    if not os.path.exists('/proc/stat'):
        return cpu_infos  # Return empty dict if /proc/stat is unavailable

    with open('/proc/stat', 'r') as file_stat:
        for line in file_stat:
            if not line.startswith('cpu'):
                continue
            fields = [field for field in line.split() if field]  # Remove empty strings
            if len(fields) < 5:  # Basic validation for expected fields
                continue

            cpu_id = fields[0]
            times = [float(t) for t in fields[1:]]  # Convert to floats
            user, nice, system, idle, iowait = times[:5]  # Core fields
            # Optional fields (irq, softirq, etc.) may not always be present
            irq = times[5] if len(times) > 5 else 0
            softirq = times[6] if len(times) > 6 else 0
            steal = times[7] if len(times) > 7 else 0

            idle_time = idle + iowait
            non_idle_time = user + nice + system + irq + softirq + steal
            total_time = idle_time + non_idle_time

            cpu_infos[cpu_id] = {
                'total': total_time,
                'idle': idle_time,
                'iowait': iowait
            }
    return cpu_infos


def get_cpu_usage_percentage(interval: float = 1.0) -> Dict[str, float]:
    """
    Calculates CPU usage percentage over a given interval.
    Returns a dictionary with CPU usage percentages per core, average, and iowait.
    """
    start = get_cpu_time()
    if not start:
        return {}

    time.sleep(interval)
    end = get_cpu_time()
    if not end:
        return {}

    cpu_usages = {}
    iowait_usages = []

    for cpu in start:
        if cpu not in end:
            continue  # Skip if CPU data is missing in end snapshot
        try:
            diff_total = end[cpu]['total'] - start[cpu]['total']
            diff_idle = end[cpu]['idle'] - start[cpu]['idle']
            diff_iowait = end[cpu]['iowait'] - start[cpu]['iowait']

            if diff_total <= 0:  # Avoid division by zero or negative time
                cpu_usage_percentage = 0.0
            else:
                cpu_usage_percentage = (diff_total - diff_idle) / diff_total * 100

            cpu_usages[cpu] = round(cpu_usage_percentage, 2)
            iowait_usages.append(diff_iowait)
        except KeyError as e:
            print(f"Warning: Missing data for {cpu}: {e}")
            continue

    if cpu_usages:
        cpu_usages['avg'] = round(sum(cpu_usages.values()) / len(cpu_usages), 2)
        cpu_usages['iowait'] = round(sum(iowait_usages) / len(iowait_usages), 2)

    return cpu_usages


def get_aws_metadata(meta_ip="169.254.169.254", timeout=2):
    meta_url = f'http://{meta_ip}/latest'
    # those 3 top subdirectories are not exposed with a final '/'
    metadict = {'dynamic': {}, 'meta-data': {}, 'user-data': {}}
    for sub_sect in metadict.keys():
        aws_data_crawl('{0}/{1}/'.format(meta_url, sub_sect), metadict[sub_sect], timeout=timeout)

    return metadict


def aws_data_crawl(url, d, timeout):
    r = http.jequest(url, timeout=timeout)
    if r.get('status_code') == 404 or r.get('status_code') == 999:
        return

    for l in r.get('text').split('\n'):
        if not l: # "instance-identity/\n" case
            continue
        new_url = '{0}{1}'.format(url, l)
        # a key is detected with a final '/'
        if l.endswith('/'):
            new_key = l.split('/')[-2]
            d[new_key] = {}
            aws_data_crawl(new_url, d[new_key], timeout=timeout)

        else:
            r = http.jequest(new_url, timeout=timeout)
            if r.get('json'):
                d[l] = r.get('json')
            else:
                d[l] = r.get('text')


def get_kakao_metadata(meta_ip="169.254.169.254", timeout=2.0):
    """
    Retrieves metadata from Kakao Cloud instance.

    Parameters:
        meta_ip (str): IP address of the metadata service
        timeout (float): Timeout for HTTP requests in seconds

    Returns:
        dict: Metadata from Kakao Cloud instance

    Raises:
        MetadataError: When metadata retrieval fails
    """
    base_url = f"http://{meta_ip}/latest"
    headers = {'X-aws-ec2-metadata-token': 'required'}

    try:
        metadata = {
            "dynamic": {},
            "meta-data": {},
            "user-data": {}
        }

        # Get meta-data
        meta_data = metadata["meta-data"]
        meta_data["ami-id"] = requests.get(f"{base_url}/meta-data/ami-id", headers=headers, timeout=timeout).text
        meta_data["ami-launch-index"] = requests.get(f"{base_url}/meta-data/ami-launch-index", headers=headers, timeout=timeout).text
        meta_data["ami-manifest-path"] = requests.get(f"{base_url}/meta-data/ami-manifest-path", headers=headers, timeout=timeout).text

        # Get block-device-mapping
        meta_data["block-device-mapping"] = {
            "ami": requests.get(f"{base_url}/meta-data/block-device-mapping/ami", headers=headers, timeout=timeout).text,
            "ebs0": requests.get(f"{base_url}/meta-data/block-device-mapping/ebs0", headers=headers, timeout=timeout).text,
            "root": requests.get(f"{base_url}/meta-data/block-device-mapping/root", headers=headers, timeout=timeout).text
        }

        # Get instance information
        meta_data["hostname"] = requests.get(f"{base_url}/meta-data/hostname", headers=headers, timeout=timeout).text
        meta_data["instance-action"] = requests.get(f"{base_url}/meta-data/instance-action", headers=headers, timeout=timeout).text
        meta_data["instance-id"] = requests.get(f"{base_url}/meta-data/instance-id", headers=headers, timeout=timeout).text
        meta_data["instance-type"] = requests.get(f"{base_url}/meta-data/instance-type", headers=headers, timeout=timeout).text
        meta_data["local-hostname"] = requests.get(f"{base_url}/meta-data/local-hostname", headers=headers, timeout=timeout).text
        meta_data["local-ipv4"] = requests.get(f"{base_url}/meta-data/local-ipv4", headers=headers, timeout=timeout).text

        # Get placement information
        meta_data["placement"] = {
            "availability-zone": requests.get(f"{base_url}/meta-data/placement/availability-zone", headers=headers, timeout=timeout).text
        }

        # Get network information
        meta_data["public-hostname"] = requests.get(f"{base_url}/meta-data/public-hostname", headers=headers, timeout=timeout).text
        meta_data["public-ipv4"] = requests.get(f"{base_url}/meta-data/public-ipv4", headers=headers, timeout=timeout).text

        # Get security information
        meta_data["public-keys"] = {"0=kakao": requests.get(f"{base_url}/meta-data/public-keys/0/openssh-key", headers=headers, timeout=timeout).text}
        meta_data["reservation-id"] = requests.get(f"{base_url}/meta-data/reservation-id", headers=headers, timeout=timeout).text
        meta_data["security-groups"] = requests.get(f"{base_url}/meta-data/security-groups", headers=headers, timeout=timeout).text

        return metadata

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to retrieve Kakao Cloud metadata: {str(e)}")


def get_gcp_metadata(meta_ip="metadata.google.internal", timeout=2):
    meta_url = f'http://{meta_ip}/computeMetadata/v1/'
    headers = {'Metadata-Flavor': 'Google'}
    metadict = {}

    def fetch_metadata(path=''):
        url = f"{meta_url}{path}"
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 200:
                text = response.text
                return text.split('\n')
            else:
                logger.error(f"Non-200 status code {response.status_code} for URL: {url}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching GCP metadata at {url}: {e}")
            return []

    def crawl(path=''):
        items = fetch_metadata(path)
        for item in items:
            if not item:
                continue
            if item.endswith('/'):
                key = item.rstrip('/')
                metadict[key] = {}
                crawl(f"{path}{item}")
            else:
                item_url = f"{meta_url}{path}{item}"
                try:
                    response = requests.get(item_url, headers=headers, timeout=timeout)
                    if response.status_code == 200:
                        metadict[item] = response.text
                    else:
                        logger.error(f"Failed to fetch metadata for {item}. Status code: {response.status_code}")
                        metadict[item] = None
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error fetching GCP metadata at {item_url}: {e}")
                    metadict[item] = None

    crawl()
    return metadict


async def get_oci_metadata_async(meta_ip="169.254.169.254", timeout=2):
    meta_url = f'http://{meta_ip}/opc/v1/'
    headers = {'Authorization': 'Bearer Oracle'}
    metadict = {}

    async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async def fetch_metadata(path=''):
            url = f'{meta_url}{path}'
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    text = await response.text()
                    return text
            except Exception as e:
                return None

        # 예제: 주요 메타데이터 항목만 수집
        paths = [
            "instance/id",
            "instance/ocid",
            "instance/region",
            "instance/display-name",
            "instance/availability-domain",
            "instance/compartment-id",
        ]

        async def crawl():
            tasks = []
            for path in paths:
                tasks.append(asyncio.create_task(fetch_metadata(path)))
            results = await asyncio.gather(*tasks)
            for path, data in zip(paths, results):
                key = path.split('/')[-1]
                metadict[key] = data

        await crawl()

    return metadict

def get_oci_metadata(meta_ip="169.254.169.254", timeout=2):
    return asyncio.run(get_oci_metadata_async(meta_ip, timeout))


def io_flags_to_string(flags):
    flag_descriptions = {
        os.O_RDONLY: 'O_RDONLY',
        os.O_WRONLY: 'O_WRONLY',
        os.O_RDWR: 'O_RDWR',
        os.O_CREAT: 'O_CREAT',
        os.O_EXCL: 'O_EXCL',
        os.O_TRUNC: 'O_TRUNC',
        os.O_APPEND: 'O_APPEND',
        os.O_NONBLOCK: 'O_NONBLOCK',
        os.O_SYNC: 'O_SYNC',
        os.O_DSYNC: 'O_DSYNC'
    }
    if hasattr(os, 'O_RSYNC'):
        flag_descriptions[os.O_RSYNC] = 'O_RSYNC'

    result = []
    for value, name in flag_descriptions.items():
        if flags & value:
            result.append(name)
    return '|'.join(result)


class DiskUsage:
    def __init__(self):
        self.ignore_partitions = [
            "/System/Volumes", "/private/var/folders/", "/sys", "/proc", "/dev", "/run/docker/netns", "/var/lib/docker",
            "/run", "/snap", "/boot/efi", "/var/lib/nfs/rpc_pipefs",
            "/var/run",  "/var/lock", "/media" , "/mnt",
        ]
        self.unit_factors = {
            "B": 1,
            "KB": 1024,
            "MB": 1024**2,
            "GB": 1024**3,
            "TB": 1024**4,
            "PB": 1024**5
        }

    def match_list(self, patterns, text):
        """
        Check if the text matches any pattern in the list.
        """
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False

    def get_mount_points(self):
        """
        Get a list of all mount points along with their device names.
        """
        mount_points = []
        if platform.system() == 'Darwin':  # macOS
            try:
                output = subprocess.check_output(['df']).decode('utf-8')
                lines = output.splitlines()[1:]
                for line in lines:
                    parts = line.split()
                    device_name = parts[0]
                    mount_point = parts[-1]
                    if not self.match_list(self.ignore_partitions, mount_point):
                        mount_points.append((device_name, mount_point))
            except subprocess.CalledProcessError as e:
                print(f"Error occurred while running df: {e}")
        elif platform.system() == 'Linux':  # Linux
            with open('/proc/mounts', 'r') as f:
                for line in f.readlines():
                    parts = line.split()
                    if len(parts) >= 2:
                        device_name = parts[0]
                        mount_point = parts[1]
                        if not self.match_list(self.ignore_partitions, mount_point):
                            mount_points.append((device_name, mount_point))
        else:
            raise NotImplementedError("Unsupported operating system")
        return mount_points



    def get_disk_usage(self, mount_point="/", unit="GB", precision=2):
        """
        Get disk usage information for a specific mount point or all mount points.

        :param mount_point: Mount point to check. Use "/", "/home", or "all".
        :param unit: Unit for disk usage. Can be "B", "KB", "MB", "GB", "TB", or "auto". Default is "GB".
        :param precision: Number of decimal places for the output. Default is 2.
        :return: Disk usage information.
        """
        if unit not in self.unit_factors and unit != "auto":
            raise ValueError(f"Unsupported unit: {unit}. Supported units are B, KB, MB, GB, TB, auto.")

        disk_info = {}

        if mount_point == "all":
            for device_name, mp in self.get_mount_points():
                if os.path.ismount(mp):
                    disk_info[mp] = {
                        'device': device_name,
                        **self.calculate_disk_usage_with_auto_unit(mp, precision, unit)
                    }
        else:
            if os.path.ismount(mount_point):
                device_name = next((dev for dev, mp in self.get_mount_points() if mp == mount_point), None)
                disk_info[mount_point] = {
                    'device': device_name,
                    **self.calculate_disk_usage_with_auto_unit(mount_point, precision, unit)
                }
            else:
                raise ValueError(f"{mount_point} is not a valid mount point")

        return disk_info

    # @staticmethod
    # def calculate_disk_usage(mount_point, factor, precision, unit):
    #     """
    #     Helper function to calculate disk usage for a given mount point.
    #     """
    #     total, used, free = shutil.disk_usage(mount_point)
    #     return {
    #         "total": round(total / factor, precision),
    #         "used": round(used / factor, precision),
    #         "free": round(free / factor, precision),
    #         "percent": round(used / total * 100, precision) if total > 0 else 0,
    #         "unit": unit
    #     }
    #
    # def calculate_disk_usage_with_auto_unit(self, mount_point, precision, unit):
    #     """
    #     Calculate disk usage with automatic unit selection if 'auto' is specified.
    #     """
    #     total, used, free = shutil.disk_usage(mount_point)
    #
    #     if unit == "auto":
    #         if total >= self.unit_factors["PB"]:
    #             factor = self.unit_factors["PB"]
    #             unit = "PB"
    #         elif total >= self.unit_factors["TB"]:
    #             factor = self.unit_factors["TB"]
    #             unit = "TB"
    #         elif total >= self.unit_factors["GB"]:
    #             factor = self.unit_factors["GB"]
    #             unit = "GB"
    #         elif total >= self.unit_factors["MB"]:
    #             factor = self.unit_factors["MB"]
    #             unit = "MB"
    #         elif total >= self.unit_factors["KB"]:
    #             factor = self.unit_factors["KB"]
    #             unit = "KB"
    #         else:
    #             factor = self.unit_factors["B"]
    #             unit = "B"
    #     else:
    #         factor = self.unit_factors[unit]
    #
    #     return {
    #         "total": round(total / factor, precision),
    #         "used": round(used / factor, precision),
    #         "free": round(free / factor, precision),
    #         "percent": round(used / total * 100, precision) if total > 0 else 0,
    #         "unit": unit
    #     }

    @staticmethod
    def calculate_disk_usage(mount_point, factor, precision, unit):
        """
        Helper function to calculate disk usage for a given mount point.
        """
        total, used, free = shutil.disk_usage(mount_point)
        return {
            "total": round(total / factor, precision),
            "used": round(used / factor, precision),
            "free": round(free / factor, precision),
            "percent": round(used / total * 100, precision) if total > 0 else 0,
            "unit": unit
        }

    def calculate_disk_usage_with_auto_unit(self, mount_point, precision, unit):
        """
        Calculate disk usage with automatic unit selection if 'auto' is specified.
        """
        total, _, _ = shutil.disk_usage(mount_point)

        if unit == "auto":
            for unit_name in ["PB", "TB", "GB", "MB", "KB", "B"]:
                if total >= self.unit_factors[unit_name]:
                    unit = unit_name
                    break

        return self.calculate_disk_usage(
            mount_point,
            self.unit_factors[unit],
            precision,
            unit
        )


class DiskPerformanceTester:
    """
    Class to test disk performance by measuring read and write speeds.

    :param file_path: Path to the file used for testing.
    :param file_size_mb: Size of the test file in megabytes.
    :param iterations: Number of iterations for the test.
    :param block_size_kb: Size of each block in kilobytes.
    :param num_threads: Number of threads to use for the test.
    :param io_pattern: I/O pattern, e.g., "sequential" or "random".
    :param decimal_places: Number of decimal places for results.
    :param console: Console object for logging.
    :param verbose: Flag to enable verbose logging.
    :param additional_info: Additional info for result file

    Example:

        .. code-block:: python

            tester = DiskPerformanceTester("/tmp/testfile", 100)

            tester.run_parallel_tests()

            # or

            tester.measure_write_speed("/tmp/testfile", task_id, progress)
            tester.measure_read_speed("/tmp/testfile", task_id, progress)
            tester.cleanup_and_exit()
    """

    def __init__(self, file_path, file_size_mb, iterations=5, block_size_kb=1024, num_threads=1, io_pattern="sequential", decimal_places=2, console=None, verbose=False, additional_info=None):
        self.base_file_path = file_path
        self.file_size_mb = file_size_mb
        self.iterations = iterations
        self.block_size_kb = block_size_kb
        self.num_threads = num_threads
        self.io_pattern = io_pattern
        self.data = bytearray(os.urandom(self.block_size_kb * 1024))  # Random data for write
        self.write_speeds = []
        self.read_speeds = []
        self.total_write_duration = 0
        self.total_read_duration = 0
        self.average_write_speed = 0
        self.average_read_speed = 0
        self.test_files = []  # List to track generated test files
        self.verbose = verbose
        self.additional_info = additional_info
        if console:
            self.console = console
        else:
            self.console = pawn.console

        self.decimal_places = decimal_places
        signal.signal(signal.SIGINT, self.cleanup_and_exit)
        signal.signal(signal.SIGTERM, self.cleanup_and_exit)

    def log_with_progress(self, progress: Progress, task_id: TaskID, message: str):
        """Helper function to log messages with progress"""
        if self.verbose:
            progress.console.log(message)
        progress.update(task_id, advance=0)

    def get_write_flags(self):
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_SYNC
        if hasattr(os, 'O_RSYNC'):
            flags |= os.O_RSYNC
        return flags

    def measure_write_speed(self, file_path, task_id, progress):
        total_speed = 0
        total_duration = 0
        speeds = []
        for i in range(self.iterations):
            start_time = time.time()
            flags = self.get_write_flags()
            try:
                fd = os.open(file_path, flags)
                self.log_with_progress(progress, task_id, f"[{i}] Opened file {file_path} for writing with fd {fd} (flags: {io_flags_to_string(flags)})")
                for _ in range(self.file_size_mb * 1024 // self.block_size_kb):
                    os.write(fd, self.data)
                os.close(fd)
                self.log_with_progress(progress, task_id, f"[{i}] Closed file {file_path} with fd {fd}")
            except OSError as e:
                self.log_with_progress(progress, task_id, f"[{i}] OS error writing to file {file_path}: {e}")
            except Exception as e:
                self.log_with_progress(progress, task_id, f"[{i}] Unexpected error writing to file {file_path}: {e}")
            end_time = time.time()
            duration = end_time - start_time
            total_duration += duration
            if duration > 0:
                speed = self.file_size_mb / duration  # MB/s
                speeds.append(round(speed, self.decimal_places))
                total_speed += speed
            progress.update(task_id, advance=1)
        average_speed = total_speed / self.iterations # Sum of all speeds in this thread
        self.console.log(f"Write total speed for {file_path}: {average_speed:.2f} MB/s")
        return speeds, total_duration

    def measure_read_speed(self, file_path, task_id, progress):
        total_speed = 0
        total_duration = 0
        speeds = []
        for i in range(self.iterations):
            self.prepare_file(file_path, task_id, progress)  # Ensure the file is ready to be read
            start_time = time.time()
            flags = os.O_RDONLY | os.O_SYNC
            try:
                fd = os.open(file_path, flags)
                self.log_with_progress(progress, task_id, f"[{i}] Opened file {file_path} for reading with fd {fd} (flags: {io_flags_to_string(flags)})")
                while os.read(fd, self.block_size_kb * 1024):
                    pass
                os.close(fd)
                self.log_with_progress(progress, task_id, f"[{i}] Closed file {file_path} with fd {fd}")
            except OSError as e:
                self.log_with_progress(progress, task_id, f"[{i}] OS error reading from file {file_path}: {e}")
            except Exception as e:
                self.log_with_progress(progress, task_id, f"[{i}] Unexpected error reading from file {file_path}: {e}")
            end_time = time.time()
            duration = end_time - start_time
            total_duration += duration
            if duration > 0:
                speed = self.file_size_mb / duration  # MB/s
                speeds.append(round(speed, self.decimal_places))
                total_speed += speed
            progress.update(task_id, advance=1)
        average_speed = total_speed / self.iterations # Sum of all speeds in this thread
        self.console.log(f"Read total speed for {file_path}: {average_speed:.2f} MB/s")
        return speeds, total_duration

    def prepare_file(self, file_path, task_id, progress):
        # Ensure the file is ready to be read
        try:
            fd = os.open(file_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_SYNC)
            self.log_with_progress(progress, task_id, f"Preparing file {file_path} for reading with fd {fd} (O_SYNC)")
            for _ in range(self.file_size_mb * 1024 // self.block_size_kb):
                os.write(fd, self.data)
            os.close(fd)
            self.log_with_progress(progress, task_id, f"Prepared and closed file {file_path} with fd {fd}")
        except OSError as e:
            self.log_with_progress(progress, task_id, f"OS error preparing file {file_path}: {e}")
        except Exception as e:
            self.log_with_progress(progress, task_id, f"Unexpected error preparing file {file_path}: {e}")

    def cleanup(self, file_path):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.verbose and self.console.log(f"Deleted file {file_path}")
        except OSError as e:
            self.console.log(f"OS error deleting file {file_path}: {e}")
        except Exception as e:
            self.console.log(f"Unexpected error deleting file {file_path}: {e}")

    def cleanup_files(self):
        for file_path in self.test_files:
            self.cleanup(file_path)

    def cleanup_and_exit(self, signum, frame):
        self.console.log(f"Signal {signum} received. Cleaning up and exiting.")
        self.cleanup_files()
        exit(0)

    def run_test(self, task_name, measure_func, progress):
        task = progress.add_task(task_name, total=self.num_threads * self.iterations)
        speeds = []
        total_duration = 0

        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = []
            for i in range(self.num_threads):
                file_path = f'{self.base_file_path}_{task_name.lower()}_{i}'
                self.test_files.append(file_path)
                futures.append(executor.submit(measure_func, file_path, task, progress))

            for future in futures:
                speed, duration = future.result()
                speeds.append(speed)
                total_duration += duration

        return speeds, total_duration

    def run_parallel_tests(self):
        write_speeds, total_write_duration = [], 0
        read_speeds, total_read_duration = [], 0

        with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.0f}%",
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=self.console) as progress:

            write_speeds, total_write_duration = self.run_test("Write Test", self.measure_write_speed, progress)
            read_speeds, total_read_duration = self.run_test("Read Test", self.measure_read_speed, progress)

        # Flatten the list of speeds
        flat_write_speeds = [speed for sublist in write_speeds for speed in sublist]
        flat_read_speeds = [speed for sublist in read_speeds for speed in sublist]

        # Calculate overall average speeds
        self.write_speeds = self.validate_speeds(flat_write_speeds)
        self.read_speeds = self.validate_speeds(flat_read_speeds)

        total_write_size_mb = self.file_size_mb * self.iterations * self.num_threads
        total_read_size_mb = self.file_size_mb * self.iterations * self.num_threads

        if total_write_duration > 0:
            self.average_write_speed = round(total_write_size_mb / total_write_duration, self.decimal_places)
        else:
            self.average_write_speed = 0

        if total_read_duration > 0:
            self.average_read_speed = round(total_read_size_mb / total_read_duration, self.decimal_places)
        else:
            self.average_read_speed = 0

        # Cleanup all test files
        self.cleanup_files()
        results = self.create_results_dict()

        # Print summary
        # self.print_summary()

        # Save results
        # self.save_results()

        # Visualize results
        # self.visualize_results()
        return results

    def validate_speeds(self, speeds):
        # Validate and filter out unrealistic speed values
        if not speeds:
            return []

        if len(speeds) == 1:
            # If there is only one speed, return it as it is
            return speeds

        mean = statistics.mean(speeds)
        stdev = statistics.stdev(speeds)

        # Accept speeds within 3 standard deviations of the mean
        return [speed for speed in speeds if mean - 3 * stdev <= speed <= mean + 3 * stdev]

    def print_summary(self):
        self.console.log(f"Write speeds: {self.write_speeds}")
        threads_write_result = ""
        threads_read_result = ""
        if self.num_threads > 1:
            threads_write_result = f"(Threads: {self.average_write_speed*self.num_threads:.2f} MB/s per thread)"
            threads_read_result = f"(Threads: {self.average_read_speed*self.num_threads:.2f} MB/s per thread)"

        self.console.log(f"Average write speed: {self.average_write_speed:.2f} MB/s {threads_write_result}")
        self.console.log(f"Read speeds: {self.read_speeds}")
        self.console.log(f"Average read speed: {self.average_read_speed:.2f} MB/s {threads_read_result}")
        self.console.log(f"CPU load during test: {dict_to_line(get_cpu_load(), end_separator=', ')}")

    def create_results_dict(self):
        results = {
            "write_speeds": self.write_speeds,
            "average_write_speed": self.average_write_speed,
            "read_speeds": self.read_speeds,
            "average_read_speed": self.average_read_speed,
        }
        if self.additional_info:
            results["additional_info"] = self.additional_info
        return results

    def save_results(self):
        results = self.create_results_dict()

        with open("disk_performance_results.json", "w") as f:
            json.dump(results, f, indent=4)
        self.console.log("Results saved to disk_performance_results.json")


class FileSystemTester:
    def __init__(self, test_dir, file_count=1000, file_size=1024, iterations=5, decimal_places=3, verbose=False, console=None):
        self.test_dir = test_dir
        self.file_count = file_count
        self.file_size = file_size  # in bytes
        self.iterations = iterations
        self.verbose = verbose
        self.decimal_places = decimal_places

        if console:
            self.console = console
        else:
            self.console = pawn.console

    def setup(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

    def cleanup(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def generate_random_string(self, size):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=size))

    def test_file_creation(self, progress, task_id):
        self.verbose and self.console.log("Start File creation test")
        durations = []
        for _ in range(self.iterations):
            self.setup()
            start_time = time.time()
            for i in range(self.file_count):
                with open(os.path.join(self.test_dir, f'file_{i}.txt'), 'w') as f:
                    f.write(self.generate_random_string(self.file_size))
                progress.update(task_id, advance=1)
            end_time = time.time()
            duration = end_time - start_time
            durations.append(duration)
            self.cleanup()
        avg_duration = sum(durations) / len(durations)
        self.verbose and self.console.log(f'File creation test completed in {avg_duration:.4f} seconds (average over {self.iterations} iterations)')
        return avg_duration

    def test_file_reading(self, progress, task_id):
        self.verbose and self.console.log("Start File reading test")
        durations = []
        for _ in range(self.iterations):
            self.setup()
            # Create files first
            for i in range(self.file_count):
                with open(os.path.join(self.test_dir, f'file_{i}.txt'), 'w') as f:
                    f.write(self.generate_random_string(self.file_size))
            start_time = time.time()
            for i in range(self.file_count):
                with open(os.path.join(self.test_dir, f'file_{i}.txt'), 'r') as f:
                    content = f.read()
                progress.update(task_id, advance=1)
            end_time = time.time()
            duration = end_time - start_time
            durations.append(duration)
            self.cleanup()
        avg_duration = sum(durations) / len(durations)
        self.verbose and self.console.log(f'File reading test completed in {avg_duration:.4f} seconds (average over {self.iterations} iterations)')
        return avg_duration

    def test_file_deletion(self, progress, task_id):
        self.verbose and self.console.log("Start File deletion test")
        durations = []
        for _ in range(self.iterations):
            self.setup()
            # Create files first
            for i in range(self.file_count):
                with open(os.path.join(self.test_dir, f'file_{i}.txt'), 'w') as f:
                    f.write(self.generate_random_string(self.file_size))
            start_time = time.time()
            for i in range(self.file_count):
                os.remove(os.path.join(self.test_dir, f'file_{i}.txt'))
                progress.update(task_id, advance=1)
            end_time = time.time()
            duration = end_time - start_time
            durations.append(duration)
            self.cleanup()
        avg_duration = sum(durations) / len(durations)
        self.verbose and self.console.log(f'File deletion test completed in {avg_duration:.4f} seconds (average over {self.iterations} iterations)')
        return avg_duration

    def test_directory_traversal(self, progress, task_id):
        durations = []
        for _ in range(self.iterations):
            self.setup()
            # Create files first
            for i in range(self.file_count):
                with open(os.path.join(self.test_dir, f'file_{i}.txt'), 'w') as f:
                    f.write(self.generate_random_string(self.file_size))
            start_time = time.time()
            for root, dirs, files in os.walk(self.test_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                progress.update(task_id, advance=1)
            end_time = time.time()
            duration = end_time - start_time
            durations.append(duration)
            self.cleanup()
        avg_duration = sum(durations) / len(durations)
        self.verbose and self.console.log(f'Directory traversal test completed in {avg_duration:.4f} seconds (average over {self.iterations} iterations)')
        return avg_duration

    def run_tests(self, is_print=False):
        self.console.log(f'Starting file system tests with {self.file_count} files of {self.file_size} bytes each, running {self.iterations} iterations')

        total_tasks = self.iterations * self.file_count * 4
        with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=self.console
        ) as progress:
            creation_task = progress.add_task("File Creation", total=self.iterations * self.file_count)
            reading_task = progress.add_task("File Reading", total=self.iterations * self.file_count)
            deletion_task = progress.add_task("File Deletion", total=self.iterations * self.file_count)
            traversal_task = progress.add_task("Directory Traversal", total=self.iterations * self.file_count)

            file_creation_time = round(self.test_file_creation(progress, creation_task), self.decimal_places)
            file_reading_time = round(self.test_file_reading(progress, reading_task), self.decimal_places)
            file_deletion_time = round(self.test_file_deletion(progress, deletion_task), self.decimal_places)
            directory_traversal_time = round(self.test_directory_traversal(progress, traversal_task), self.decimal_places)

            progress.update(creation_task, completed=self.iterations * self.file_count)
            progress.update(reading_task, completed=self.iterations * self.file_count)
            progress.update(deletion_task, completed=self.iterations * self.file_count)
            progress.update(traversal_task, completed=self.iterations * self.file_count)

        results = {
            "file_creation_time": file_creation_time,
            "file_reading_time": file_reading_time,
            "directory_traversal_time": directory_traversal_time,
            "file_deletion_time": file_deletion_time
        }

        if is_print:
            self.print_results(results)
        return results

    def print_results(self, results):
        table = Table(title="File System Test Results")
        table.add_column("Test", style="cyan", no_wrap=True)
        table.add_column("Duration (s)", style="magenta")

        for key, value in results.items():
            table.add_row(key.replace("_", " ").title(), str(value))

        self.console.print(table)

class SSHLogPathResolver:
    log_file_mapping = {
        'ubuntu': '/var/log/auth.log',
        'centos': '/var/log/secure',
        'rocky': '/var/log/secure',
        'macos': '/var/log/system.log',
        'debian': '/var/log/auth.log',
        'fedora': '/var/log/secure',
        'amzn': '/var/log/secure',
    }

    def __init__(self, os_name=None, raise_on_failure=False):
        if os_name:
            self.os_name = os_name.lower()
        else:
            os_info = get_platform_info()
            self.os_name = os_info.get("os", "").lower()

        self.raise_on_failure = raise_on_failure
        self.log_file_path = self.get_path()

    def get_path(self):
        log_path = self.log_file_mapping.get(self.os_name)
        if log_path:
            return log_path
        elif self.raise_on_failure:
            raise ValueError(f"Unsupported OS: {self.os_name}")
        else:
            return '/var/log/secure'
    def extract_directory(self):
        return str(os.path.dirname(self.log_file_path))
