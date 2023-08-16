import resource as __resource
import time
import platform
import os
import subprocess
import re
import socket
from pawnlib.utils import http
from pawnlib.typing import is_valid_ipv4
from pawnlib.config import pawn
from typing import Callable
from collections import OrderedDict

import socket
import fcntl
import array
import struct
import errno


def hex_mask_to_cidr(hex_mask):
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
            # if 'addr' in address:
            #     ip_addresses.append(address.split('addr')[1])
    else:
        raise ValueError("Only Linux and macOS are supported")
    return ip_addresses


def get_ip_and_netmask(interface):
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
                    ip_info.append(str(cidr_netmask))
                # else:
                #     ip_info.append("")
    return ip_info


def get_interface_ips(ignore_interface=[], colorize=False, detail=True):
    interfaces_and_ips = []
    interface_names = get_interface_names()
    default_route, default_interface = parse_proc_route()

    for interface_name in interface_names:
        if interface_name not in ignore_interface:
            if detail:
                ip_address = " /".join(get_ip_and_netmask(interface_name))
            else:
                ip_address = " ".join(get_ip_addresses(interface_name))

            if ip_address:
                if default_interface and default_route and interface_name == default_interface:
                    # interface_name = f"[bold blue][on #050B27]{interface_name:<8}[/bold blue]"
                    ip_address = f"{ip_address}, G/W: {default_route}"
                interfaces_and_ips.append((interface_name, ip_address))
    return interfaces_and_ips


def get_interface_ips_dict(ignore_interface=[], colorize=False):
    interface_dict = {}
    default_route, default_interface = parse_proc_route()
    for interface, ipaddr in get_interface_ips(ignore_interface=ignore_interface, colorize=colorize):
        interface_dict[interface] = ipaddr


def parse_proc_route():
    try:
        if platform.system() == 'Linux':
            with open('/proc/net/route', 'r') as route_file:
                for line in route_file.readlines()[1:]:
                    parts = line.strip().split()
                    if len(parts) >= 11 and parts[1] == '00000000':
                        default_interface = parts[0]
                        default_route = '.'.join([str(int(parts[2][i:i+2], 16)) for i in range(6, -1, -2)])
                        return default_route, default_interface

        elif platform.system() == 'Darwin':
            # Run the "netstat -rn" command on macOS
            route_output = subprocess.check_output(['netstat', '-rn']).decode('utf-8')

            for line in route_output.splitlines():
                if 'default' in line:
                    parts = re.split(r'\s+', line.strip())
                    default_route = parts[1]
                    default_interface = parts[3]
                    if is_valid_ipv4(default_route):
                        return default_route, default_interface
            return None, None

    except FileNotFoundError:
        print("Error: /proc/net/route file not found.")
        return None, None


class SystemMonitor:
    def __init__(self, interval=1):
        self.instance_data_total = []
        self.prev_net_data = self.parse_net_dev()
        self.prev_cpu_data = self.parse_cpu_stat()
        self.prev_disk_stats = self.read_disk_stats()
        self.interval = interval

        if self.interval < 0:
            raise ValueError("Interval must be positive number or greater than 0")

        self.last_data = {
            "cpu": {},
            "network": {},
        }

    # @staticmethod
    # def read_net_dev_file():
    #     with open("/proc/net/dev") as f:
    #         lines = f.readlines()
    #     return lines

    def parse_net_dev(self):
        lines = self.read_stats_file("/proc/net/dev")
        data = {}
        for line in lines[2:]:
            line = line.split()
            iface = line[0].strip(':')
            if iface == "lo" or iface.startswith("sit"):
                continue
            data[iface] = {
                'received': int(line[1]),
                'sent': int(line[9]),
                'packets_recv': int(line[2]),
                'packets_sent': int(line[10]),
            }
        return data

    def get_network_cpu_status(self):
        time.sleep(self.interval)
        cpu_status = self.get_cpu_status(period=0)
        network_status = self.get_network_status(period=0)
        disk_stats = self.get_disk_usage()
        return network_status, cpu_status, disk_stats

    def get_network_status(self, period=1):
        time.sleep(period)
        curr_net_data = self.parse_net_dev()

        total_received = 0
        total_sent = 0
        total_packets_recv = 0
        total_packets_sent = 0

        interface_data = OrderedDict({})
        for iface in curr_net_data:
            prev_received = self.prev_net_data[iface]['received']
            prev_sent = self.prev_net_data[iface]['sent']
            prev_packets_recv = self.prev_net_data[iface]['packets_recv']
            prev_packets_sent = self.prev_net_data[iface]['packets_sent']

            curr_received = curr_net_data[iface]['received']
            curr_sent = curr_net_data[iface]['sent']
            curr_packets_recv = curr_net_data[iface]['packets_recv']
            curr_packets_sent = curr_net_data[iface]['packets_sent']

            diff_received = (curr_received - prev_received) * 8 / 1_000_000 / self.interval  # Bytes to Megabits
            diff_sent = (curr_sent - prev_sent) * 8 / 1_000_000 / self.interval  # Bytes to Megabits
            diff_packets_recv = curr_packets_recv - prev_packets_recv
            diff_packets_sent = curr_packets_sent - prev_packets_sent

            total_received += diff_received
            total_sent += diff_sent
            total_packets_recv += diff_packets_recv
            total_packets_sent += diff_packets_sent

            interface_data[iface] = {
                "recv": diff_received,
                "sent": diff_sent,
                "packets_recv": diff_packets_recv,
                "packets_sent": diff_packets_sent,
            }

            # pawn.console.log(f"{iface:<9}: {diff_received:.2f} Mb/s In, {diff_sent:.2f} Mb/s Out, "
            #                  f"{diff_packets_recv} Packets In, {diff_packets_sent} Packets Out")

        # total_string = "Total"
        # pawn.console.log(f"📶 [white bold]{total_string:<9}[/white bold]: {total_received:.2f} Mb/s In, {total_sent:.2f} Mb/s Out, "
        #                  f"{total_packets_recv} Packets In, {total_packets_sent} Packets Out ")

        interface_data["Total"] = {
            "recv": total_received,
            "sent": total_sent,
            "packets_recv": total_packets_recv,
            "packets_sent": total_packets_sent,
        }
        interface_data.move_to_end("Total", False)

        # for data in interface_data:
        #     iface, diff_received, diff_sent, diff_packets_recv, diff_packets_sent = data
        #     pawn.console.log(f"📶 {iface:<9}: {diff_received:.2f} Mb/s In, {diff_sent:.2f} Mb/s Out, "
        #                      f"{diff_packets_recv} Packets In, {diff_packets_sent} Packets Out")
        # print("")
        self.prev_net_data = curr_net_data
        return interface_data

    def print_network_status(self):
        interface_data = self.get_network_status()
        for iface, value in interface_data.items():
            # iface, diff_received, diff_sent, diff_packets_recv, diff_packets_sent = data
            pawn.console.log(f"📶 {iface:<9}: {value.get('recv'):.2f} Mb/s In, {value.get('sent'):.2f} Mb/s Out, "
                             f"{value.get('packets_recv')} Packets In, {value.get('packets_sent')} Packets Out")
        print("")

    # @staticmethod
    # def read_stat_file():
    #     with open("/proc/stat") as f:
    #         lines = f.readlines()
    #     return lines

    def parse_cpu_stat(self):
        cpu_line = ""
        for line in self.read_stats_file("/proc/stat"):
            if line.startswith("cpu"):
                cpu_line = line
                break

        cpu_values = cpu_line.strip().split()[1:]
        cpu_values = [int(value) for value in cpu_values]
        return cpu_values

    def get_cpu_status(self, period=1):
        start_values = self.prev_cpu_data
        end_values = self.parse_cpu_stat()

        diff_values = [end - start for start, end in zip(start_values, end_values)]
        total_diff = sum(diff_values)

        us_percent = 100 * diff_values[0] / total_diff
        sy_percent = 100 * diff_values[2] / total_diff
        id_percent = 100 * diff_values[3] / total_diff
        io_wait = 100 * diff_values[4] / total_diff   # Added for iowait
        return {
            'usr': round(us_percent, 2),
            'sys': round(sy_percent, 2),
            'idle': round(id_percent, 2),
            'io_wait': round(io_wait, 2)
        }
        # print(f"CPU Usage --> {us_percent:.2f}% us  :  {sy_percent:.2f}% sy  :  {id_percent:.2f}% id  :  {io_wait:.2f}% iowait")  # Edited for iowait

    def read_disk_stats(self):
        disk_stats = {}
        for line in self.read_stats_file("/proc/diskstats"):
            fields = line.strip().split()
            disk_name = fields[2]
            #disk_types = ["sd", "vd", "nvme"]
            # if disk_name.startswith('sd') or disk_name.startswith('nvme') or disk_name.startswith('vd'):
            if not any(c.isdigit() for c in disk_name):
                disk_stats[disk_name] = {
                    'read_ios': int(fields[3]),
                    'read_bytes': int(fields[5]) * 512,  # Convert to bytes
                    'write_ios': int(fields[7]),
                    'write_bytes': int(fields[9]) * 512,  # Convert to bytes
                }
        return disk_stats

    def get_disk_usage(self):
        curr_disk_stats = self.read_disk_stats()
        disk_usage = {}
        total_read_ios = 0
        total_write_ios = 0
        total_read_bytes = 0
        total_write_bytes = 0

        for disk, curr_stats in curr_disk_stats.items():
            if disk in self.prev_disk_stats:
                prev_stats = self.prev_disk_stats[disk]
                read_ios = curr_stats['read_ios'] - prev_stats['read_ios']
                read_bytes = curr_stats['read_bytes'] - prev_stats['read_bytes']
                write_ios = curr_stats['write_ios'] - prev_stats['write_ios']
                write_bytes = curr_stats['write_bytes'] - prev_stats['write_bytes']

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

    @staticmethod
    def read_stats_file( filename=""):
        with open(filename) as f:
            lines = f.readlines()
        return lines

    def parse_meminfo(self, lines):
        meminfo = {}
        for line in lines:
            key, value = line.strip().split(":")
            meminfo[key] = int(value.strip().split(" ")[0])
        return meminfo

    def get_memory_status(self, unit="GB"):
        meminfo = self.read_stats_file("/proc/meminfo")
        parsed_meminfo = self.parse_meminfo(meminfo)

        unit_multiplier = 1
        if unit.upper() == "KB":
            unit_multiplier = 1
        elif unit.upper() == "MB":
            unit_multiplier = 1024
        elif unit.upper() == "GB":
            unit_multiplier = 1024 * 1024
        else:
            raise ValueError("Invalid unit. Valid values are KB, MB, and GB.")

        total_memory = parsed_meminfo["MemTotal"] / unit_multiplier
        free_memory = parsed_meminfo["MemFree"] / unit_multiplier
        available_memory = parsed_meminfo["MemAvailable"] / unit_multiplier

        used_memory = total_memory - free_memory
        percent_used = 100 * used_memory / total_memory

        # print(f"Memory Usage --> {percent_used:.2f}% ({used_memory:.2f} {unit} Used / {total_memory:.2f} {unit} Total)")
        return {
            "total": round(total_memory, 2),
            "used":round(used_memory, 2),
            "free": round(free_memory, 2),
            "percent": round(percent_used,2),
            "unit": unit
        }

    def print_memory_status(self):
        memory_status = self.get_memory_status()
        unit = memory_status.get('unit')
        print(f"Memory Usage --> {memory_status.get('percent'):.2f}% ({memory_status.get('used'):.2f} {unit} Used "
              f"/ {memory_status.get('total'):.2f} {unit} Total)")


def _line_split(line="", sep=":", d=0, data_type: Callable = str):
    data = line.split(sep)
    if len(data) >= d:
        return data_type(data[d].strip())
    return data_type()


def get_rlimit_nofile():
    """

    Returns a dict (soft, hard) with the current soft and hard limits of resource

    :return:

    Example:

        .. code-block:: python

            from pawnlib.resource import server
            server.get_rlimit_nofile()


    """
    soft, hard = __resource.getrlimit(__resource.RLIMIT_NOFILE)
    return {"soft": soft, "hard": hard}


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


def get_platform_info():
    """

    Returns a dict with platform information

    :return:

    Example:

        .. code-block:: python

            from pawnlib.resource import server
            server.get_platform_info()

            ## > {'system': 'Darwin', 'version': 'Darwin Kernel Version 21.6.0: Wed Aug 10 14:28:23 PDT 2022; root:xnu-8020.141.5~2/RELEASE_ARM64_T6000', 'release': '21.6.0', 'machine': 'arm64', 'processor': 'arm', 'python_version': '3.9.13', 'model': 'Apple M1 Pro', 'cores': 10}


    """

    try:
        uname = platform.uname()
        python_version = platform.python_version()
        platform_info = {
            "system": uname.system,
            "version": uname.version,
            "release": uname.release,
            "machine": uname.machine,
            "processor": uname.processor,
            "python_version": python_version,
        }
    except:
        platform_info = {}

    if platform_info.get('system') == "Darwin":
        platform_info.update(**get_mac_platform_info())

    else:
        try:
            with open('/proc/cpuinfo') as f:
                cpu_count = 0
                model = None
                for line in f:
                    # Ignore the blank line separating the information between
                    # details about two processing units
                    if line.strip():
                        if line.rstrip('\n').startswith('model name'):
                            model_name = line.rstrip('\n').split(':')[1]
                            model = model_name
                            model = model.strip()
                            cpu_count += 1
                platform_info['model'] = model
                platform_info['cores'] = cpu_count
        except Exception as e:
            print(e)
    return platform_info


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
            cpu_load_result = cpu_load.split(" ")
            return {
                "1min": round(float(cpu_load_result[0]), 2),
                "5min": round(float(cpu_load_result[1]), 2),
                "15min": round(float(cpu_load_result[2]), 2),
            }


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
    load_list = load_raw.split(' ')
    return {
        "1min": round(float(load_list[0]), 2),
        "5min": round(float(load_list[1]), 2),
        "15min": round(float(load_list[2]), 2)
    }


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

    if unit == "MB":
        convert_unit = 1024
    elif unit == "GB":
        convert_unit = 1024 * 1024
    else:
        convert_unit = 1
        unit = "KB"

    data = {'mem_total': 0, 'mem_used': 0, 'mem_free': 0,
            'swap_total': 0, 'swap_used': 0, 'swap_free': 0,
            'buffers': 0, 'cached': 0}

    if platform.uname().system == "Darwin":
        data.update(**get_mem_osx_info())
    else:
        with open('/proc/meminfo', 'r') as fh:
            lines = fh.read()
            fh.close()

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
                elif fields[0] == 'SwapFree:':
                    data['swap_free'] = int(fields[1], 10)
                    break
            data['mem_used'] = data['mem_total'] - data['mem_free']
            data['swap_used'] = data['swap_total'] - data['swap_free']

    for k, v in data.items():
        if isinstance(v, int) or isinstance(v, float):
            data[k] = round(v / convert_unit, 2)
    data['unit'] = unit

    return data


def get_cpu_time():
    cpu_infos = {}
    if os.path.exists('/proc/stat'):
        with open('/proc/stat', 'r') as file_stat:
            cpu_lines = []
            for lines in file_stat.readlines():
                for line in lines.split('\n'):
                    if line.startswith('cpu'):
                        cpu_lines.append(line.split(' '))
            for cpu_line in cpu_lines:
                if '' in cpu_line:
                    cpu_line.remove('')  # First row(cpu) exist '' and Remove ''
                cpu_id = cpu_line[0]
                cpu_line = [float(item) for item in cpu_line[1:]]
                user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice = cpu_line

                idle_time = idle + iowait
                non_idle_time = user + nice + system + irq + softirq + steal
                total = idle_time + non_idle_time

                cpu_infos.update({cpu_id: {'total': total, 'idle': idle_time, 'iowait': iowait}})
    return cpu_infos


def get_cpu_usage_percentage():
    start = get_cpu_time()
    time.sleep(1)
    end = get_cpu_time()
    cpu_usages = {}
    iowait_usages = []
    for cpu in start:
        diff_total = end[cpu]['total'] - start[cpu]['total']
        diff_idle = end[cpu]['idle'] - start[cpu]['idle']
        diff_iowait = end[cpu].get('iowait', 0) - start[cpu].get('iowait', 0)
        iowait_usages.append(diff_iowait)
        cpu_usage_percentage = (diff_total - diff_idle) / diff_total * 100
        cpu_usages.update({cpu: round(cpu_usage_percentage, 2)})
    if cpu_usages:
        cpu_usages['avg'] = round(sum(cpu_usages.values()) / len(cpu_usages.values()), 2)
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
            # pawn.console.log(r)
            if r.get('json'):
                d[l] = r.get('json')
            else:
                d[l] = r.get('text')
