#!/usr/bin/env python3
import os
import asyncio
from pawnlib.config import pawn
from pawnlib.output import color_print
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.resource.monitor import SSHMonitor
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter

__description__ = "SSH Monitoring Tool"
__epilog__ = (
    "\nUsage examples:\n\n"
    "1. Start monitoring SSH log files:\n"
    "     `pawns mon ssh -f /var/log/secure /var/log/auth.log`\n\n"
    "\nNote:\n"
    "  You can monitor multiple log files by providing multiple `-f` arguments.\n"
)

def get_parser():
    parser = CustomArgumentParser(
        description='Command Line Interface for SSH Monitoring',
        formatter_class=ColoredHelpFormatter,
        epilog=__epilog__
    )
    parser = get_arguments(parser)
    return parser

def get_arguments(parser=None):
    if not parser:
        parser = CustomArgumentParser()

    parser.add_argument(
        'command',
        help='Command to execute',
        nargs="?",
        choices=['ssh']
    )
    parser.add_argument(
        '-f', '--file',
        metavar='log_file',
        help='SSH log file(s) to monitor',
        nargs='+',  # This allows for multiple files to be passed
        default=None
    )
    parser.add_argument(
        '-b', '--base-dir',
        metavar='base_dir',
        help='Base directory for the application',
        default="."
    )
    return parser

# def monitor_ssh(args):
#     log_file_paths = args.file
#     slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL', '')
#
#     for log_file_path in log_file_paths:
#         ssh_monitor = SSHMonitor(
#             log_file_path=log_file_path,
#             slack_webhook_url=slack_webhook_url,
#             alert_interval=60,
#         )
#
#         async def run_async_monitor():
#             await ssh_monitor.monitor_ssh()
#
#         try:
#             loop = asyncio.get_running_loop()
#             loop.create_task(run_async_monitor())
#             loop.run_forever()
#         except RuntimeError:
#             asyncio.run(run_async_monitor())


def monitor_ssh(args):
    log_file_path = args.file
    slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL', '')

    ssh_monitor = SSHMonitor(
        log_file_path=log_file_path,
        slack_webhook_url=slack_webhook_url,
        alert_interval=60,

    )
    async def run_async_monitor():
        await ssh_monitor.monitor_ssh()

    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # If we're here, it means the loop is already running
        loop.create_task(run_async_monitor())
        # Keep the program running to allow background tasks to execute
        loop.run_forever()
    except RuntimeError:
        # No event loop is running, so we can start a new one
        asyncio.run(run_async_monitor())


def main():
    banner = generate_banner(
        app_name="SSH Monitoring Tool",
        author="jinwoo",
        description="Monitor SSH logs with Slack notifications",
        font="graffiti",
        version=_version
    )

    parser = get_parser()
    args, unknown = parser.parse_known_args()
    args.file = args.file if args.file else ['/var/log/secure']

    print(banner)
    pawn.console.log(f"Parsed arguments: {args}")

    if args.command == "ssh":
        pawn.console.log(f"Starting SSH monitoring {args.file}")
        monitor_ssh(args)

main.__doc__ = (
    f"{__description__}\n{__epilog__}"
)

if __name__ == '__main__':
    main()
