#!/usr/bin/env python3
import unittest

try:
    import common
except:
    pass

from functools import partial
from pawnlib.resource.net import *
from pawnlib.utils.operate_handler import *
from pawnlib.config import pawnlib_config as pawn

from pawnlib.resource import server

# system_profiler SPHardwareDataType
# Hardware:
#
# Hardware Overview:
#
# Model Name: MacBook Pro
# Model Identifier: MacBookPro18,3
# Chip: Apple M1 Pro
# Total Number of Cores: 10 (8 performance and 2 efficiency)
# Memory: 32 GB
# System Firmware Version: 7459.141.1
# OS Loader Version: 7459.141.1
# Serial Number (system): KT0JNWTKWG
# Hardware UUID: 08155041-A21D-5FBF-9043-12EE68CAFDC9
# Provisioning UDID: 00006000-0014310A1ED2801E
# Activation Lock Status: Disabled

try:
    dump(server.get_mac_platform_info())
except Exception as e:
    print(e)

try:
    dump(server.get_mem_osx_info())
except Exception as e:
    print(e)

pawn.console.rule(f"[bold green] --- System Information ----")
dump(server.get_platform_info())

pawn.console.rule(f"[bold green] --- Memory Information ----")
print(f"{server.get_mem_info()}")

pawn.console.rule(f"[bold green] --- rlimit Information ----")
print(server.get_rlimit_nofile())

pawn.console.rule(f"[bold green] --- CPU LOAD Information ----")
print(dict(server.get_cpu_load()))

pawn.console.rule(f"[bold green] --- CPU Percentage Information ----")
print(server.get_cpu_usage_percentage())

pawn.console.rule(f"[bold green] --- Memory Information ----")
print(server.get_mem_info(unit="GB"))

# class TestNetworkUtils(unittest.TestCase):
# import subprocess
# import re
#
# # Get process info
# ps = subprocess.Popen(['ps', '-caxm', '-orss,comm'], stdout=subprocess.PIPE).communicate()[0].decode()
# vm = subprocess.Popen(['vm_stat'], stdout=subprocess.PIPE).communicate()[0].decode()
#
# # Iterate processes
# processLines = ps.split('\n')
# sep = re.compile('[\s]+')
# rssTotal = 0 # kB
# for row in range(1, len(processLines)):
#     rowText = processLines[row].strip()
#     rowElements = sep.split(rowText)
#     try:
#         rss = float(rowElements[0]) * 1024
#     except:
#         rss = 0 # ignore...
#     rssTotal += rss
#
# # Process vm_stat
# vmLines = vm.split('\n')
# sep = re.compile(':[\s]+')
# vmStats = {}
# for row in range(1, len(vmLines)-2):
#     rowText = vmLines[row].strip()
#     rowElements = sep.split(rowText)
#     vmStats[(rowElements[0])] = int(rowElements[1].strip('\.')) * 4096
#
# print('Wired Memory:\t\t%d MB' % (vmStats["Pages wired down"]/1024/1024))
# print('Active Memory:\t\t%d MB' % (vmStats["Pages active"]/1024/1024))
# print('Inactive Memory:\t%d MB' % (vmStats["Pages inactive"]/1024/1024))
# print('Free Memory:\t\t%d MB' % (vmStats["Pages free"]/1024/1024))
# print('Real Mem Total (ps):\t%.3f MB' % (rssTotal/1024/1024))
