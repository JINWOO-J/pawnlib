#!/usr/bin/env python3
from rich.console import Console
from rich.table import Table
from rich.live import Live

# from bcc import BPF

import time
import signal
import sys
import subprocess
import os
import common
from pawnlib.config import pawn
from pawnlib.resource.net import ProcNetMonitor
import threading

def user_callback(data):
    print("Updated data:", data)
    # Signal the monitor to exit
    return "EXIT"  # Return a specific value to indicate exit

if __name__ == "__main__":



    monitor = ProcNetMonitor(
        top_n=10,
        refresh_rate=3,
        callback=user_callback
    )

    proc_net_thread = threading.Thread(target=monitor.run, daemon=True)
    proc_net_thread.start()

    res = monitor.get_top_n(3)
    pawn.console.log(res)
    exit()


    monitor = ProcNetMonitor(
        top_n=10,
        refresh_rate=3,
        callback=lambda msg: (
            print(msg),
            sys.exit(0)
        )
    )
    monitor.run()

    monitor = ProcNetMonitor(
        top_n=10,
        refresh_rate=3,
        callback=user_callback
    )
    monitor.run()

    # monitor = ProcNetMonitor(
    #     top_n=10,
    #     refresh_rate=3,
    #     callback=lambda msg:  print(msg),
    # )
    # monitor.run()

    # monitor = ProcNetMonitor(top_n=10, refresh_rate=2, proc_filter="ping")
    monitor = ProcNetMonitor(top_n=10, refresh_rate=2)
    monitor.run_live()
