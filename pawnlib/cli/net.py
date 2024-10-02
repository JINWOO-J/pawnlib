#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn, pconf
from pawnlib.utils import disable_ssl_warnings
from pawnlib.resource import net, wait_for_port_open
from pawnlib.typing import is_valid_ipv4, sys_exit

from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter

NONE_STRING = "__NOT_DEFINED_VALUE__"
__description__ = "This is a tool to measure your server's resources."

__epilog__ = (
    "This script provides various options to check the network status.\n\n"
    "Usage examples:\n"
    "  1. Network check in verbose mode:\n\n"
    "     - Executes the 'check' command for network testing, with '--verbose' option for additional output.\n\n"
    "     `pawns net check --verbose`\n"


    "  2. Wait for a specific host and port to be available:\n\n"
    "     - Uses the 'wait' command to wait until the port (80) on the specified host (192.168.1.1) is open.\n\n"
    "     `pawns net wait --host 192.168.1.1 --port 80`\n"
    
    "  3. Scan a range of hosts and ports:\n\n"
    "     - Runs the 'scan' command to scan the specified host range (192.168.1.1 to 192.168.1.255) and port range (20 to 80).\n"
    "     - Sets the maximum number of concurrent workers to 50 with '--worker 50'.\n"
    "     - Outputs only open ports with the '--view-type open' option.\n\n"
    "     `pawns net scan --host-range 192.168.1.1-192.168.1.255 --port-range 20-80 --worker 50 --view-type open`\n\n"
    

    "For more details, use the -h or --help flag."
)

def validate_ipv4_or_exit(ipaddr):
    if is_valid_ipv4(ipaddr):
        return True
    else:
        raise ValueError(f"Invalid IP address -> {ipaddr}")


def validate_host_range(host_range_str):
    if "-" not in host_range_str:
        try:
            validate_ipv4_or_exit(host_range_str)
            return host_range_str, host_range_str
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid IP address: '{host_range_str}'")

    try:
        start_ip, end_ip = host_range_str.split('-')
        validate_ipv4_or_exit(start_ip)
        validate_ipv4_or_exit(end_ip)
        return start_ip, end_ip
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid host range: '{host_range_str}'. Format should be: start_ip-end_ip")

def validate_port_range(port_range_str):
    if "-" not in port_range_str:
        try:
            port = int(port_range_str)
            if port < 0 or port > 65535:
                raise ValueError
            return port, port
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid port: '{port_range_str}'. Port should be within 0-65535")

    # 포트 범위의 경우
    try:
        start_port, end_port = map(int, port_range_str.split('-'))
        if start_port < 0 or end_port > 65535 or start_port > end_port:
            raise ValueError
        return start_port, end_port
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid port range: '{port_range_str}'. Format should be: start_port-end_port and within 0-65535")


def get_parser():
    parser = CustomArgumentParser(
        description='NET',
        epilog=__epilog__,
        formatter_class=ColoredHelpFormatter
    )

    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument(
        'command',
        help='Command to execute (check, wait, scan)',
        nargs='?',
        choices=['check', 'wait', 'scan'],
    )
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode (True/False)')
    parser.add_argument('-v', '--verbose', action='count', help='Verbose mode (view level)', default=0)

    parser.add_argument('-p', '--port', type=int, help='Port number (e.g., 80)', default=80)
    parser.add_argument('--host', type=str, help='Single host IP (e.g., 192.168.1.1)', default="localhost")
    parser.add_argument('--host-range', type=str, help='Host IP range (e.g., 192.168.1.1-192.168.1.255)', default="")
    parser.add_argument('--port-range', type=str, help='Port range (e.g., 20-80)', default="0-65535")
    parser.add_argument('-w', '--worker', type=int, help='Max concurrency worker count', default=10000)
    parser.add_argument('-t', '--timeout', type=float, help='timeout', default=1)
    parser.add_argument('-b', '--batch-size', type=int, help='timeout', default=1000)
    parser.add_argument('-f', '--fast-scan', action='store_true', help='fast scan mode', default=False)

    parser.add_argument('--view-type', type=str, choices=['open', 'closed', 'all'], help='Type of results to view (open, closed, all)', default="open")

    return parser


def print_banner():
    banner = generate_banner(
        app_name="NET",
        author=f"jinwoo",
        description="Network checker",
        font="graffiti",
        version=_version
    )
    print(banner)


def initialize_arguments():
    parser = get_parser()
    args, unknown = parser.parse_known_args()
    args.subparser_name = "net"
    pawn.set(
        PAWN_DEBUG=args.debug,
        data=dict(
            args=args
        )
    )
    print_banner()
    return args, parser


def find_fastest_region(args):
    ff_region = net.FindFastestRegion(verbose=args.verbose)
    ff_region.run()
    ff_region.print_results()


def format_range(range_tuple):
    return f"'{range_tuple[0]}' ⏩'{range_tuple[1]}'"


def main():
    args, parser = initialize_arguments()

    disable_ssl_warnings()
    pawn.console.log(args)

    # if not args.command:
    #     parser.error("ssss")

    if not args.command:
        parser.print_help()
        parser.error("command not found")

    elif args.command == "check":
        find_fastest_region(args)

    elif args.command == "wait":
        wait_for_port_open(args.host, args.port, timeout=args.timeout)

    elif args.command == "scan":
        if not args.host_range and args.host:
            args.host_range = f"{args.host}-{args.host}"

        host_range = validate_host_range(args.host_range)
        port_range = validate_port_range(args.port_range)
        pawn.console.log(f"🔎 Start scanning worker={args.worker}, view_type={args.view_type} 🔎\n Host range:{format_range(host_range)} , Port range:{format_range(port_range)} ")

        scanner = net.AsyncPortScanner(
            ip_range=host_range,
            port_range=port_range,
            max_concurrency=args.worker,
            batch_size=args.batch_size,
            timeout=args.timeout,
        )
        scanner.run_scan(fast_scan=args.fast_scan)
        print("\n\n")
        scanner.print_scan_results(view=args.view_type)


main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':
    main()
