#!/usr/bin/env python3
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf
from pawnlib.typing import StackList, list_to_oneline_string, str2bool, shorten_text, get_procfs_path
from pawnlib.resource import (
    SystemMonitor, get_cpu_load, get_interface_ips, get_platform_info,
    get_mem_info, get_netstat_count, get_hostname, ProcessMonitor
)
from pawnlib.models.response import CriticalText
from pawnlib.resource.net import ProcNetMonitor
import os

from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.align import Align
from rich.panel import Panel
from rich import box
from pawnlib.typing import todaydate
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter
import time

__description__ = "A simple and powerful tool for monitoring server resources in real time."

__epilog__ = (
    "This tool is a comprehensive solution for monitoring your server's resource usage. \n\n"
    "Features include real-time tracking of network traffic, CPU, memory, and disk usage, \n"
    "making it an indispensable tool for system administrators and DevOps professionals.\n\n"
    "Here are some usage examples to get you started:\n\n"
    "  1. **Basic Monitoring:** Monitor system resources with default settings. \n"
    "     Example: `pawns top`\n\n"
    "  2. **Detailed View:** Use `-v` to increase verbosity and get more detailed logs.\n"
    "     Example: `pawns top -v`\n\n"
    "  3. **Minimal Output:** Use `-q` for quiet mode to suppress standard output.\n"
    "     Example: `pawns top -q`\n\n"
    "  4. **Custom Update Interval:** Adjust the refresh rate with `-i` to set the interval in seconds.\n"
    "     Example: `pawns top -i 5`\n\n"
    "  5. **Output Formats:** Choose between 'live' and 'line' output styles with `-t`.\n"
    "     Example: `pawns top -t live`\n\n"
    "  6. **Network-Specific Monitoring:** Focus solely on network traffic and protocols.\n"
    "     Example: `pawns top net`\n\n"
    "  7. **Advanced Filters:** Use advanced options to filter processes by PID, name, or network protocols.\n"
    "     Example: `pawns top proc --pid-filter 1234 --protocols tcp udp`\n\n"
    "Key options:\n"
    "  --top-n              Specify the number of top processes to display.\n"
    "  --refresh-rate       Set the data refresh rate in seconds.\n"
    "  --unit               Choose the unit for network traffic (e.g., Mbps, Gbps).\n"
    "  --group-by           Group processes by PID or name.\n\n"
    "This flexibility allows you to tailor the tool to your specific needs. \n"
    "For more detailed usage, run `--help` or refer to the documentation."
)

PROCFS_PATH = get_procfs_path()

def get_parser():
    parser = CustomArgumentParser(
        description='monitor',
        epilog=__epilog__,
        formatter_class=ColoredHelpFormatter
    )
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument('command', help='command to execute. For example, "net" retrieves network information.', type=str, nargs='?', default="resource")
    parser.add_argument('-c', '--config-file', type=str, help='config', default="config.ini")
    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level (default: %(default)s)', default=1)
    parser.add_argument('-q', '--quiet', action='count', help='Quiet mode. Dont show any messages. (default: %(default)s)', default=0)
    parser.add_argument('-i', '--interval', type=float, help='interval sleep time seconds. (default: %(default)s)', default=1)
    parser.add_argument('-b', '--base-dir', type=str, help='base dir for httping (default: %(default)s)', default=os.getcwd())
    parser.add_argument('-t', '--print-type', type=str, help='printing type  %(default)s)', default="line", choices=["live", "layout", "line"])


    parser.add_argument(
        '--top-n', type=int, default=10,
        help="The number of top processes to display in the table. Default: %(default)s."
    )
    # parser.add_argument(
    #     '--refresh-rate', type=int, default=2,
    #     help="The data refresh rate in seconds. Default: %(default)s."
    # )
    parser.add_argument(
        '--group-by', type=str, default="pid", choices=["pid", "name"],
        help="Criteria for grouping processes (e.g., 'pid' or 'name'). Default: %(default)s."
    )
    parser.add_argument(
        '--unit', type=str, default="Mbps", choices=['bps', 'Kbps', 'Mbps', 'Gbps', 'Tbps', 'Pbps'],
        help="Unit for displaying network traffic (e.g., 'bps', 'Kbps', 'Mbps', 'Gbps', 'Tbps', 'Pbps'). Default: %(default)s."
    )
    parser.add_argument(
        '--protocols', nargs='+', default=["tcp", "udp"],
        help="List of protocols to monitor. Defaults to %(default)s."
    )
    parser.add_argument(
        '--pid-filter', type=int, nargs='*',
        help="Filter processes by specific process IDs."
    )
    parser.add_argument(
        '--proc-filter', type=str, nargs='*',
        help="Filter processes by name."
    )
    parser.add_argument(
        '--min-bytes-threshold', type=int, default=0,
        help="Minimum bytes threshold for displaying processes. Default: %(default)s."
    )
    parser.add_argument(
        '--callback', type=str,
        help="Path to a user-defined Python script to execute when data is updated."
    )
    return parser


def print_banner():
    banner = generate_banner(
        app_name=pconf().app_name,
        author="jinwoo",
        description=f"{__description__} \n"
                    f" - base_dir    : {pconf().args.base_dir} \n" 
                    f" - logs_dir    : {pconf().args.base_dir}/logs \n",
        font="graffiti",
        version=_version
    )
    print(banner)


def main():
    app_name = 'monitor'
    parser = get_parser()
    args, unknown = parser.parse_known_args()
    config_file = args.config_file

    is_hide_line_number = args.verbose > 2
    stdout = not args.quiet

    pawn.set(
        PAWN_CONFIG_FILE=config_file,
        PAWN_PATH=args.base_dir,
        PAWN_CONSOLE=dict(
            redirect=True,
            record=True,
            log_path=is_hide_line_number, # hide line number on the right side
        ),
        app_name=app_name,
        args=args,
        try_pass=False,
        last_execute_point=0,
        data={
            "response_time": StackList(),
        },
        fail_count=0,
        total_count=0,

    )
    if args.verbose > 2:
        pawn.set(
            PAWN_LOGGER=dict(
                log_level="DEBUG",
                stdout_level="DEBUG",
                # log_path=f"{args.base_dir}/logs",
                stdout=stdout,
                use_hook_exception=True,
                show_path=False, #hide line numbers
            ),
        )
    print_banner()
    system_info = get_platform_info()
    hostname = shorten_text(get_hostname(), width=20, placeholder='...')
    system_monitor = SystemMonitor(interval=args.interval, proc_path=PROCFS_PATH)
    table_title = f"🐰 {hostname} <{system_info.get('model')},  {system_info.get('cores')} cores, {get_mem_info().get('mem_total')} GB> 🐰"

    if args.command == "proc_net":
        net_mon = ProcNetMonitor(
            top_n=args.top_n,
            refresh_rate=args.interval,
            group_by=args.group_by,
            unit=args.unit,
            protocols=args.protocols,
            pid_filter=args.pid_filter,
            proc_filter=args.proc_filter,
            min_bytes_threshold=args.min_bytes_threshold,
        )
        net_mon.run_live()

    elif args.command == "proc":
        proc_mon = ProcessMonitor(
            n=args.top_n,
        )
        proc_mon.run_live()

    elif args.print_type == "live":
        print_rich_live_type_status(table_title=table_title,  system_info=system_info, system_monitor=system_monitor)
    # elif args.print_type == "tab":
    #     print_tabulate_status(system_monitor=system_monitor)
    elif args.print_type == "line":
        print_simple_line_type_status(table_title=table_title, system_info=system_info, system_monitor=system_monitor, args=args)

    elif args.print_type == "layout":
        print_rich_layout_type_status(table_title=table_title, system_info=system_info, system_monitor=system_monitor, args=args)


def print_simple_line_type_status(table_title, system_info, system_monitor, args):
    count = 0

    while True:
        columns, term_rows = os.get_terminal_size()
        data = get_resources_status(system_monitor=system_monitor, args=args)

        column_widths = {
            "time": 8,
            "net_in": 9,
            "net_out": 9,
            "pk_in": 10,
            "pk_out": 10,
            "load": 5,
            "usr": 6,
            "sys": 6,
            "i/o": 6,
            "mem_%": 6,
        }

        for column_key, value in data.items():
            align_space = max(len(str(value)), len(column_key)) + 3
            if column_key not in column_widths:  # Avoid overwriting custom values
                column_widths[column_key] = align_space

        # Prepare headers and lines with calculated widths
        headers = []
        line = []
        for column_key, value in data.items():
            align_space = column_widths[column_key]
            headers.append(f"[blue][u]{column_key:>{align_space}}[/u][/blue]")
            _value = CriticalText(column_key, value, cores=system_info.get('cores', 1), align_space=align_space)
            line.append(_value)

        if count % term_rows == 0:
            pawn.console.print(Panel(table_title, expand=False))
            print_line_status(headers)

        print_line_status(line)
        count += 1


def print_line_status(line):
    pawn.console.print("", end="│")
    for cell in line:
        pawn.console.print(cell, end="│")
    print()


def print_rich_live_type_status(table_title="", system_info={}, system_monitor: SystemMonitor = None):
    lines = []  # Buffer to store rows of data
    with Live(console=pawn.console, auto_refresh=False, refresh_per_second=10, screen=False) as live_table:
        while True:
            columns, rows = os.get_terminal_size()
            if columns < 20 or rows < 5:  # Check minimum terminal size
                pawn.console.print("[red]Terminal size too small to render the table![/red]")
                time.sleep(1)
                continue

            data = get_resources_status(system_monitor=system_monitor)
            table = Table(title=table_title, box=box.SIMPLE)
            data_keys = list(data.keys())
            for column_key in data_keys:
                table.add_column(column_key, justify='right')

            line = [
                CriticalText(column_key, value, cores=system_info.get("cores", 1)).return_text()
                for column_key, value in data.items()
            ]

            if len(line) < len(data_keys):
                line.extend([""] * (len(data_keys) - len(line)))  # Fill missing columns with empty strings
            elif len(line) > len(data_keys):
                line = line[:len(data_keys)]  # Trim excess columns
            lines.append(line)

            if len(lines) > rows - 6:  # Leave space for title and padding
                lines.pop(0)

            for idx, line in enumerate(lines):
                try:
                    table.add_row(*line)
                except IndexError as e:
                    pawn.console.print(f"[red]Error adding row at index {idx}: {line}[/red]")
                    pawn.console.print(f"[red]Expected columns: {len(data_keys)}, Got: {len(line)}[/red]")
                    raise e
            live_table.update(Align.center(table))
            live_table.refresh()


def print_rich_layout_type_status(table_title="", system_info={}, system_monitor=None):

    layout = Layout()
    layout.split(
        Layout(name="header", size=3),  # Header section with fixed size
        Layout(name="body"),           # Body section for the table (dynamic size)
        Layout(name="footer", size=3)  # Footer section with fixed size
    )

    layout["header"].update(f"[bold magenta]{table_title}[/bold magenta]")
    layout["footer"].update("[green]Press Ctrl+C to exit[/green]")

    lines = []  # Buffer to store rows of data

    with Live(layout, console=pawn.console, auto_refresh=False, refresh_per_second=10, screen=False) as live_layout:
        while True:
            columns, rows = os.get_terminal_size()
            if columns < 20 or rows < 10:  # Check minimum terminal size
                pawn.console.print("[red]Terminal size too small to render the table![/red]")
                time.sleep(1)
                continue

            data = get_resources_status(system_monitor=system_monitor)

            table = Table(title=table_title, box=box.SIMPLE)
            data_keys = list(data.keys())

            for column_key in data_keys:
                table.add_column(column_key, justify='right')

            line = [
                CriticalText(column_key, value, cores=system_info.get("cores", 1)).return_text()
                for column_key, value in data.items()
            ]

            if len(line) < len(data_keys):
                line.extend([""] * (len(data_keys) - len(line)))  # Fill missing columns with empty strings
            elif len(line) > len(data_keys):
                line = line[:len(data_keys)]  # Trim excess columns

            lines.append(line)

            if len(lines) > rows - 8:  # Leave space for header and footer
                lines.pop(0)

            for idx, line in enumerate(lines):
                try:
                    table.add_row(*line)
                except IndexError as e:
                    pawn.console.print(f"[red]Error adding row at index {idx}: {line}[/red]")
                    pawn.console.print(f"[red]Expected columns: {len(data_keys)}, Got: {len(line)}[/red]")
                    raise e

            layout["body"].update(Align.center(table))
            live_layout.refresh()
            time.sleep(0.6)  # Simulate delay between updates (adjust as needed)


def get_resources_status(system_monitor: SystemMonitor = None, args=None):
    if not args:
        args = pconf().args

    if args.command == "net":
        netstat = get_netstat_count(proc_path=PROCFS_PATH)
        data = {
            "time": todaydate("time_sec"),
        }
        data.update(netstat.get('COUNT'))
        time.sleep(args.interval)

    elif args.command == "mem":
        memory = system_monitor.get_memory_status()
        memory_unit = memory.get('unit')
        data = {
            "time": todaydate("time_sec"),
            # "total": f"{memory.get('total'):.1f}{memory_unit}",
            "used": f"{memory.get('used'):.1f}{memory_unit}",
            "free": f"{memory.get('free'):.1f}{memory_unit}",
            # "available": f"{memory.get('available'):.1f}{memory_unit}",
            "cached": f"{memory.get('cached'):.1f}{memory_unit}",
            "buff": f"{memory.get('buffers'):.1f}{memory_unit}",
            "use_%": f"{memory.get('percent'):.1f}%",
            "swp_tot": f"{memory.get('swap_total'):.1f}{memory_unit}",
            "swp_use": f"{memory.get('swap_used'):.1f}{memory_unit}",
            "swp_free": f"{memory.get('swap_free'):.1f}{memory_unit}",
            "swp_%": f"{memory.get('swap_percent'):.1f}%",
            # "memory_trend": f"{memory.get('memory_trend')}",
        }

        pressure = memory.get('pressure', {})
        if pressure:
            data.update({
                "pressure_some_10": f"{pressure.get('some_avg10', 0):.2f}",
                "pressure_some_60": f"{pressure.get('some_avg60', 0):.2f}",
                "pressure_full_10": f"{pressure.get('full_avg10', 0):.2f}",
                "pressure_full_60": f"{pressure.get('full_avg60', 0):.2f}",
            })

        # Huge Pages 정보 추가
        huge_pages = memory.get('huge_pages', {})
        if huge_pages:
            data.update({
                # "huge_total": str(huge_pages.get('HugePages_Total', 0)),
                # "huge_free": str(huge_pages.get('HugePages_Free', 0)),
                # "huge_rsvd": str(huge_pages.get('HugePages_Rsvd', 0)),
                # "huge_surp": str(huge_pages.get('HugePages_Surp', 0)),
                "huge_size": f"{huge_pages.get('Hugepagesize', 0) / 1024:.0f}MB",
            })

        time.sleep(args.interval)

    elif args.command == "top_mem":
        top_processes = system_monitor.mem_status.get_top_memory_processes(n=5)
        data = {
            "time": todaydate("time_sec"),
        }
        for i, proc in enumerate(top_processes, 1):
            data[f"proc_mem_{i}"] = f"{proc['name']}({proc['pid']}): {proc['memory_percent']:.2f}%"
        time.sleep(args.interval)

    else:
        memory = system_monitor.get_memory_status()
        network, cpu, disk = system_monitor.collect_system_status()
        memory_unit = memory.get('unit')

        data = {
            "time": todaydate("time_sec"),
            "net_in": f"{network['Total'].get('recv'):.2f}M",
            "net_out": f"{network['Total'].get('sent'):.2f}M",
            "pk_in": f"{network['Total'].get('packets_recv')}",
            "pk_out": f"{network['Total'].get('packets_sent')}",
            "load": f"{get_cpu_load()['1min']}",
            "usr": f"{cpu.get('usr')}%",
            "sys": f"{cpu.get('sys')}%",
            "i/o": f"{cpu.get('io_wait'):.2f}",
            "disk_rd": f"{disk['Total'].get('read_mb')}M",
            "disk_wr": f"{disk['Total'].get('write_mb')}M",
            # "mem_total": f"{memory.get('total'):.1f}{memory_unit}",
            # "mem_free": f"{memory.get('free'):.1f}{memory_unit}",
            # "cached": f"{memory.get('cached'):.1f}{memory_unit}",
            "mem_%": f"{memory.get('percent'):.1f}%",
        }
    return data

main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':

    try:
        main()
    except Exception as e:
        pawn.console.log(e)

