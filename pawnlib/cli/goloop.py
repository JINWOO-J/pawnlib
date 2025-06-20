#!/usr/bin/env python3
import asyncio
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf, create_app_logger
from pawnlib.utils.http import  NetworkInfo, AsyncIconRpcHelper, append_http
from pawnlib.typing import StackList
import os
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter
import json
import aiohttp

from pawnlib.blockchain.goloop.p2p import P2PNetworkParser
from pawnlib.blockchain.goloop.monitor import NodeStatsMonitor, ChainMonitor
from pawnlib.blockchain.goloop.info import NodeInfoFetcher, NodeInfoFormatter
import argparse
import re


__description__ = "A powerful and flexible tool for real-time blockchain node and network monitoring."

__epilog__ = (
    "Available Commands:",
    "-------------------",
    "- **stats**: Monitors the blockchain node status, calculates TPS, and estimates synchronization times.",
    "- **info**: Fetches and displays detailed information about the node and network configuration.",
    "",
    "Key Features:",
    "-------------",
    "- **Blockchain Node Monitoring**: Analyze synchronization status, transaction rates (TPS),",
    "  and block differences in real time.",
    "- **Comparison Support**: Compare local node performance with external nodes to identify",
    "  synchronization gaps.",
    "- **Customizable Intervals**: Set data refresh intervals for dynamic tracking of metrics.",
    "- **Detailed Logging**: Leverage verbosity levels to control log output and view additional details.",
    "",
    "Examples:",
    "---------",
    "1. **Monitor Node Stats**:",
    "   pawns goloop stats --url http://localhost:9000",
    "",
    "2. **View Node Information**:",
    "   pawns goloop info --url http://localhost:9000",
    "",
    "3. **Add Comparison with External Node**:",
    "   pawns goloop stats --url http://localhost:9000 --compare-url http://external-node.com",
    "",
    "4. **Set Custom Update Interval**:",
    "   pawns goloop stats --url http://localhost:9000 --interval 2",
    "",
    "5. **Verbose Output for Debugging**:",
    "   pawns goloop stats --url http://localhost:9000 --verbose",
    "",
    "6. **Quiet Mode for Minimal Logs**:",
    "   pawns goloop stats --url http://localhost:9000 --quiet",
    "",
    "Options:",
    "--------",
    "- `command`        The action to perform. Choices are `stats` or `info` (default: `stats`).",
    "- `--url`          The target node's API endpoint (required).",
    "- `--compare-url`  Optional external API endpoint for node comparison.",
    "- `--interval`     Update interval in seconds (default: 1).",
    "- `--verbose`      Increase verbosity for detailed logs.",
    "- `--quiet`        Suppress output for minimal logging.",
    "",
    "Get Started:",
    "------------",
    "This tool offers in-depth analysis for monitoring blockchain nodes and network metrics.",
    "Run `--help` for more details or consult the documentation."
)
from aiohttp import ClientSession
import atexit


_SESSION_POOL = None

def get_session_pool():
    global _SESSION_POOL
    if _SESSION_POOL is None:
        _SESSION_POOL = ClientSession(connector=aiohttp.TCPConnector(limit=20, force_close=True))
    return _SESSION_POOL

async def cleanup_session_pool():
    global _SESSION_POOL
    if _SESSION_POOL is not None and not _SESSION_POOL.closed:
        await _SESSION_POOL.close()
        _SESSION_POOL = None

# 프로그램 종료 시 세션 풀 정리
def cleanup_on_exit():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(cleanup_session_pool())
    loop.close()

atexit.register(cleanup_on_exit)


def get_parser():
    parser = CustomArgumentParser(
        description='monitor',
        epilog=__epilog__,
        formatter_class=ColoredHelpFormatter
    )
    parser = get_arguments(parser)
    return parser


def parse_port_range(range_str: str) -> list[int]:
    """
    Parse a port range in the form "START-END" and return a list of ports.
    """
    match = re.match(r'^(\d+)\s*-\s*(\d+)$', range_str)
    if not match:
        raise argparse.ArgumentTypeError(f"Invalid port range '{range_str}'. Expected START-END.")
    start, end = map(int, match.groups())
    if not (1 <= start <= 65535 and 1 <= end <= 65535 and start <= end):
        raise argparse.ArgumentTypeError(
            f"Port numbers must be 1–65535 and START ≤ END: '{range_str}'."
        )
    return list(range(start, end + 1))


def get_arguments(parser):
    parser.add_argument('command',
                        help='The action to perform. Choose "stats" to monitor the node or "info" to display node details.',
                        choices=['stats', 'check', 'info', 'p2p'],
                        type=str, nargs='?', default="stats"
                        )
    parser.add_argument('-c', '--config-file', type=str, help='config', default="config.ini")
    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level (default: %(default)s)', default=1)
    parser.add_argument('-q', '--quiet', action='count', help='Quiet mode. Dont show any messages. (default: %(default)s)', default=0)
    parser.add_argument('-i', '--interval', type=float, help='interval sleep time seconds. (default: %(default)s)', default=2)
    parser.add_argument('-b', '--base-dir', type=str, help='base dir for httping (default: %(default)s)', default=os.getcwd())
    parser.add_argument('-u', '--url', type=str, help='printing type  %(default)s)', default="localhost:9000")
    parser.add_argument('-cu', '--compare-url', type=str, help='compare url  %(default)s)', default=None)
    parser.add_argument('-f', '--filter',
                        nargs='*',
                        type=str,
                        help='Filtering keys to fetch from the network (e.g., --filter node_info chain_info)',
                        default=[])
    parser.add_argument('-t', '--target-key',
                        type=str,
                        help='Recursively extract a specific key\'s value from the fetched data.',
                        default=None)
    parser.add_argument('--host', type=str, help='host (default: %(default)s)', default="localhost")
    parser.add_argument('-p', '--ports', nargs='+', type=int, help='List of ports to connect to', default=None)
    parser.add_argument('-r', '--port-range', nargs='+', type=parse_port_range, default=[], help='Port range(s) to connect to (e.g. -r 8000-8010 9000-9005)'
    )


    parser.add_argument( '--log-type', choices=['console', 'file', 'both'], default='console', help='Choose logger type: console or file (default: console)')
    parser.add_argument('--max-concurrent', type=int, help='Maximum concurrent connections for P2P analysis (default: %(default)s)', default=5)
    parser.add_argument('--timeout', type=int, help='timeout  (default: %(default)s)', default=5)
    parser.add_argument('--max-depth', type=int, help='depth  (default: %(default)s)', default=3)

    return parser


def save_output(data, file_path, format='text'):
    """
    Saves output to a file in the specified format.

    :param data: The data to be saved.
    :param file_path: The path to the output file.
    :param format: The format of the output, 'json' or 'text'.
    """
    try:
        if format == 'json':
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
        elif format == 'text':
            with open(file_path, 'w') as f:
                if isinstance(data, str):
                    f.write(data)
                else:
                    f.write(json.dumps(data, indent=4))
        print(f"[green]Output saved to {file_path} in {format} format.[/green]")
    except Exception as e:
        print(f"[red]Failed to save output:[/red] {e}")


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


async def run_stats_command(args, network_info):
    _compare_api = ""
    try:
        if args.compare_url:
            pawn.console.log(f"[yellow]Using user-provided compare URL:[/yellow] {args.compare_url}")
            _compare_api = args.compare_url
        else:
            pawn.console.log(f"[yellow]Attempting to find network information for platform:[/yellow] {network_info.platform}, [yellow]NID:[/yellow] {network_info.nid}")
            guessed_network = network_info.find_network_by_platform_and_nid(
                platform=network_info.platform,
                nid=network_info.nid
            )
            pawn.console.log(f"[green]Guessed network info:[/green] {guessed_network}")
            pawn.console.log(f"[green]Guessed network name:[/green] {guessed_network.get('network_name')}")
            _compare_api = guessed_network.get('network_api')

        if not _compare_api:
            pawn.console.log("[red]Could not determine a compare API endpoint. Please provide a valid --compare-url.[/red]")
    except ValueError as e:
        pawn.console.log(f"[red]Error finding network by platform and NID:[/red] {e}")
    except Exception as e:
        pawn.console.log(f"[red]Unexpected error while finding compare API:[/red] {e}")

    if _compare_api:
        pawn.console.log(f"[green]Compare API set to:[/green] {_compare_api}")

    async with aiohttp.ClientSession() as session:
        helper = AsyncIconRpcHelper(session=session, logger=pawn.console, timeout=2, return_with_time=True, retries=1)
        monitor = NodeStatsMonitor(
            network_api=args.url,
            compare_api=_compare_api,
            helper=helper,
            interval=args.interval,
            logger=pawn.console
        )
        await monitor.run()


async def main():
    app_name = 'goloop_stats'
    parser = get_parser()
    args, unknown = parser.parse_known_args()
    config_file = args.config_file

    is_hide_line_number = args.verbose > 2
    stdout = not args.quiet

    logger = create_app_logger(
        app_name=app_name,
        log_type=args.log_type,
        verbose=args.verbose,
        propagate=True,
    )

    pawn.set(
        # PAWN_CONFIG_FILE=config_file,
        # PAWN_PATH=args.base_dir,
        # PAWN_CONSOLE=dict(
        #     redirect=True,
        #     record=True,
        #     log_path=is_hide_line_number, # hide line number on the right side
        # ),
        app_name=app_name,
        args=args,
        try_pass=False,
        last_execute_point=0,
        data={
            "response_time": StackList(),
        },
        # logger=logger,
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
    logger.info(args)
    network_info = NetworkInfo(network_api=append_http(args.url))

    if args.command == "info":
        fetcher = NodeInfoFetcher()
        pawn.console.log(network_info)
        node_data = await fetcher.fetch_all(url=network_info.network_api, filter_keys=args.filter, target_key=args.target_key)
        formatter = NodeInfoFormatter(logger=pawn.console)
        formatter.print_tree(node_data)
    elif args.command == "stats":
        try:
            await run_stats_command(args, network_info)
        except Exception as e:
            pawn.console.log(f"[red]Error during stats display:[/red] {e}")
    elif args.command == "check":
        # await find_and_check_stat(sleep_duration=args.interval, host=args.host, ports=args.ports)

        monitor = ChainMonitor(sleep_duration=args.interval, host=args.host, ports=args.ports)
        await monitor.run()

    elif args.command == "p2p":
        try:
            parser = P2PNetworkParser(
                args.url,
                max_concurrent=args.max_concurrent,
                timeout=args.timeout, logger=logger, max_depth=args.max_depth, verbose=args.verbose
            )
            ip_to_hx_map = await parser.run()

            pawn.console.rule("[bold blue]P2P Network Analysis[/bold blue]")
            total_peer_ip_count = len(ip_to_hx_map.get('ip_to_hx'))
            pawn.console.log(f"Total Peer Count = {total_peer_ip_count}")

            for hx_address, peer_info in ip_to_hx_map['hx_to_ip'].items():
                if peer_info.ip_count > 1 and peer_info.hx:
                    pawn.console.log(peer_info)
        except Exception as e:
            pawn.console.log(f"[red]Error during P2P analysis:[/red] {e}")


def guess_network(network_info):
    try:
        guessed_network = network_info.find_network_by_platform_and_nid(
            platform=network_info.platform,
            nid=network_info.nid
        )
        pawn.console.log(f"[green]Guessed network info:[/green] {guessed_network}")
        pawn.console.log(f"[green]Guessed network name:[/green] {guessed_network.get('network_name')}")
        return guessed_network
    except Exception as e:
        pawn.console.log(f"{e}")
        return {}


main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':

    try:
        asyncio.run(main())
    except Exception as e:
        pawn.console.log(e)
