import resource as __resource
import time
import platform
import os
import subprocess
import re
from pawnlib.utils import http
from typing import Callable


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
        # if 'Memory:' in line:
        #     data['memory'] = _line_split(line=line, sep=":", d=1)

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
