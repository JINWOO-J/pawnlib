#!/usr/bin/env python3
from datetime import time

import common
from pawnlib.resource import net, ProcessMonitor
from pawnlib.config import pawn
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
import time
from rich.live import Live

if __name__ == '__main__':
    console = Console()
    monitor = ProcessMonitor(n=15)
    # monitor = monitor.display_as_table()
    monitor.run_live()

    # # Use rich.live.Live for real-time updates
    # with Live(console=console, refresh_per_second=1) as live:
    #     while True:
    #         # Update the dashboard every second
    #         dashboard = create_dashboard(monitor)
    #         live.update(dashboard)
    #         time.sleep(1)
