#!/usr/bin/env python3
from datetime import time

import common
from pawnlib.resource import net, ProcessMonitor
from pawnlib.config import pawn
from rich.console import Console
from rich.table import Table


if __name__ == '__main__':
    monitor = ProcessMonitor()
    print("Top 5 memory-consuming processes:")
    print(monitor.get_top_processes(n=5, resource="memory"))

    print("\nTop 5 CPU-consuming processes:")
    print(monitor.get_top_processes(n=5, resource="cpu"))

    print("\nTop 5 I/O-consuming processes:")
    print(monitor.get_top_processes(n=5, resource="io"))


    memory_processes = monitor.get_top_processes(n=5, resource="memory")
    monitor.display_as_table(memory_processes, resource="memory")

    # CPU usage
    cpu_processes = monitor.get_top_processes(n=5, resource="cpu")
    monitor.display_as_table(cpu_processes, resource="cpu")

    # I/O usage
    io_processes = monitor.get_top_processes(n=5, resource="io")
    monitor.display_as_table(io_processes, resource="io")

