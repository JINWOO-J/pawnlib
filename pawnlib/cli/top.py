#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf
from pawnlib.typing import StackList
from pawnlib.resource import SystemMonitor, get_cpu_load, get_interface_ips, get_platform_info, get_mem_info
import os
import re

from rich.live import Live
from rich.table import Table
from rich.align import Align
from rich.text import Text
from pawnlib.typing import todaydate

__description__ = "This is a tool to measure your server's resources."


def get_parser():
    parser = argparse.ArgumentParser(description='monitor')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument('url', help='url', type=str, nargs='?', default="")
    parser.add_argument('-c', '--config-file', type=str, help='config', default="config.ini")
    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level (default: %(default)s)', default=1)
    parser.add_argument('-q', '--quiet', action='count', help='Quiet mode. Dont show any messages. (default: %(default)s)', default=0)
    parser.add_argument('-i', '--interval', type=float, help='interval sleep time seconds. (default: %(default)s)', default=1)
    parser.add_argument('-b', '--base-dir', type=str, help='base dir for httping (default: %(default)s)', default=os.getcwd())
    return parser


class CriticalText:
    def __init__(self, column="", value="",  cores=1, warning_percent=75, medium_percent=50):
        self.column = column
        self.value = value
        self.number_value = self.extract_first_number(value)

        self.critical_limit_dict = {
            "NET IN": 100,
            "NET OUT": 100,
            "usr": 80,
            "sys": 80,
            "mem_used": 99.5,
            "disk_read":  100,
            "disk_write":  100,
            "load":  int(cores),
            "io_wait":  int(cores) * 2,
        }
        self.warning_percent = warning_percent
        self.medium_percent = medium_percent

    @staticmethod
    def extract_first_number(text):
        match = re.match(r'\d+(\.\d+)?', text)
        if match:
            return float(match.group())
        return None

    def check_limit(self):
        limit_value = self.critical_limit_dict.get(self.column)
        if limit_value:
            if self.number_value >= limit_value:
                return "bold red"
            elif self.number_value >= (limit_value * self.warning_percent / 100):
                return "#FF9C3F"
            elif self.number_value >= (limit_value * self.medium_percent / 100):
                return "yellow"
        return "white"

    def return_text(self):
        return Text(self.value, self.check_limit())

    def __str__(self):
        return Text(self.value, self.check_limit())


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
        PAWN_LOGGER=dict(
            log_level="INFO",
            stdout_level="INFO",
            log_path=f"{args.base_dir}/logs",
            stdout=stdout,
            use_hook_exception=True,
            show_path=False, #hide line numbers
        ),
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
            )
        )
    print_banner()

    lines = []
    system_info = get_platform_info()

    system_monitor = SystemMonitor(interval=args.interval)
    with Live(console=pawn.console, refresh_per_second=1) as live_table:
        while True:
            columns, rows = os.get_terminal_size()
            diff_rows = len(lines) - rows

            table = Table(title=f"Server status <{system_info.get('model')},  {system_info.get('cores')} cores, {get_mem_info().get('mem_total')} GB>")
            memory = system_monitor.get_memory_status()
            network, cpu, disk = system_monitor.get_network_cpu_status()

            data = {
                "Time": todaydate("time"),
                "NET IN": f"{network['Total'].get('recv'):.2f} Mbps",
                "NET OUT": f"{network['Total'].get('sent'):.2f} Mbps",
                "PK  IN": f"{network['Total'].get('packets_recv')} p/s",
                "PK OUT": f"{network['Total'].get('packets_sent')} p/s",
                "load": f"{get_cpu_load()['1min']}",
                "usr": f"{cpu.get('usr')}%",
                "sys": f"{cpu.get('sys')}%",
                "io_wait": f"{cpu.get('io_wait')}",
                "disk_read":  f"{disk['Total'].get('read_mb')} M/s",
                "disk_write":  f"{disk['Total'].get('write_mb')} M/s",
                "mem_used": f"{memory.get('percent')}%",
                "mem_free": f"{memory.get('free')} {memory.get('unit')}",
            }

            line = []
            for column_key, value in data.items():
                table.add_column(column_key)
                line.append(CriticalText(column_key, value, cores=system_info.get('cores', 1)).return_text())
            lines.append(line)

            for line in lines:
                table.add_row(*line)

            if len(lines) >= rows - 5:
                lines.pop(0)
            if diff_rows > -6:
                del lines[:6]

            live_table.update(Align.center(table))
            # live_table.update(table)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        pawn.console.log(e)

