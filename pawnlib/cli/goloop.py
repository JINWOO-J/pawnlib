#!/usr/bin/env python3
import asyncio
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf
from pawnlib.utils.http import  NetworkInfo, AsyncIconRpcHelper, append_http
from pawnlib.typing import StackList, format_hx_addresses_recursively, filter_by_key
from pawnlib.metrics.tracker import TPSCalculator, SyncSpeedTracker, BlockDifferenceTracker, calculate_reset_percentage, calculate_pruning_percentage
from collections import deque
import os
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter
from pawnlib.typing.date_utils import format_seconds_to_hhmmss, second_to_dayhhmm
import time
from rich.tree import Tree
import json


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


def get_parser():
    parser = CustomArgumentParser(
        description='monitor',
        epilog=__epilog__,
        formatter_class=ColoredHelpFormatter
    )
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument('command',
                        help='The action to perform. Choose "stats" to monitor the node or "info" to display node details.',
                        choices=['stats', 'check', 'info'],
                        type=str, nargs='?', default="stats"
                        )
    parser.add_argument('-c', '--config-file', type=str, help='config', default="config.ini")
    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level (default: %(default)s)', default=1)
    parser.add_argument('-q', '--quiet', action='count', help='Quiet mode. Dont show any messages. (default: %(default)s)', default=0)
    parser.add_argument('-i', '--interval', type=float, help='interval sleep time seconds. (default: %(default)s)', default=2)
    parser.add_argument('-b', '--base-dir', type=str, help='base dir for httping (default: %(default)s)', default=os.getcwd())
    parser.add_argument('-u', '--url', type=str, help='printing type  %(default)s)', default="localhost:9000")
    parser.add_argument('-cu', '--compare-url', type=str, help='compare url  %(default)s)', default=None)
    parser.add_argument('-f', '--filter', type=str, help='Filtering key', default=None)
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


def build_flat_key(key_path, key):
    """
    Constructs a flattened key path.

    :param key_path: Current key path as a string.
    :param key: Current key.
    :return: New flattened key path.
    """
    return f"{key_path}.{key}" if key_path else key


def add_items_to_tree(tree, data, filter_key=None):
    """
    Recursively adds items from the dictionary to the tree.

    :param tree: The Rich Tree object to add items to.
    :param data: The current data (dict or list).
    :param filter_key: Optional key to filter and display only the corresponding data.
    :type filter_key: str or None

    """
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "preps_name_info":
                continue

            if key == 'network':
                network_tree = format_network_info(value, filter_key=filter_key)
                tree.add(network_tree)
            elif isinstance(value, dict):
                branch = tree.add(f"[bold blue]{key}[/bold blue]")
                add_items_to_tree(branch, value, filter_key=filter_key)
            elif isinstance(value, list):
                branch = tree.add(f"[bold green]{key}[/bold green] ({len(value)})")
                add_items_to_tree(branch, value, filter_key=filter_key)
            else:
                tree.add(f"[bold cyan]{key}[/bold cyan]: [green]{value}[/green]")
    elif isinstance(data, list):
        for index, item in enumerate(data):
            if isinstance(item, dict):
                branch = tree.add(f"[bold magenta]{index}[/bold magenta]")
                add_items_to_tree(branch, item, filter_key=filter_key)
            elif isinstance(item, list):
                branch = tree.add(f"[bold magenta]{index}[/bold magenta] (List)")
                add_items_to_tree(branch, item, filter_key=filter_key)
            else:
                tree.add(f"[bold magenta]{index}[/bold magenta]: [green]{item}[/green]")
    else:
        tree.add(f"[green]{data}[/green]")


def add_subsection_to_tree(tree, title, items, formatter=lambda x: x):
    """
    Adds a subsection to the tree.

    :param tree: The Rich Tree object to add the subsection to.
    :param title: Title of the subsection.
    :param items: List or dict of items in the subsection.
    :param formatter: Function to format each item.
    """
    if isinstance(items, list):
        subsection = tree.add(f"{title} ({len(items)})")
        if items:
            for item in items:
                subsection.add(formatter(item))
        else:
            subsection.add("None")
    elif isinstance(items, dict):
        subsection = tree.add(f"{title} ({len(items)})")
        if items:
            for key, value in items.items():
                subsection.add(f"{key}: {value}")
        else:
            subsection.add("None")
    else:
        tree.add(f"{title}: {items if items else 'None'}")


def get_node_name(preps_name_info={}, node_address=None):
    node_name = f"({preps_name_info.get(node_address)})"
    return f"{node_address}{node_name}"


def format_p2p_info(p2p, filter_key=None):
    """
    Formats the P2P information into a Rich Tree with optional filtering.

    :param p2p: Dictionary containing P2P information.
    :param filter_key: Optional key to filter and display only the corresponding data.
    :type filter_key: str or None
    :return: A Rich Tree object representing the P2P information.
    """
    p2p_tree = Tree("p2p")
    preps_name = pawn.get('preps_name_info')

    # Define subsections
    subsections = {
        "children": p2p.get('children', []),
        "friends": p2p.get('friends', []),
        "nephews": p2p.get('nephews', []),
        "orphanages": p2p.get('orphanages', []),
        "others": p2p.get('others', []),
        "parent": p2p.get('parent', {}),
        "roots": p2p.get('roots', {}),
        "seeds": p2p.get('seeds', {}),
        "self": p2p.get('self', {}),
        "trustSeeds": p2p.get('trustSeeds', {}),
        "uncles": p2p.get('uncles', [])
    }

    # Apply filtering if filter_key is provided
    if filter_key:
        subsections = {filter_key: subsections.get(filter_key, None)}

    subsections = format_hx_addresses_recursively(subsections, preps_name)

    for title, items in subsections.items():
        if title in ["friends", "nephews", "orphanages", "uncles"]:
            add_subsection_to_tree(
                p2p_tree,
                title.capitalize(),
                items,
                formatter=lambda x: f"ID: {x.get('id', 'N/A')}, Addr: {x.get('addr', 'N/A')}, In: {x.get('in', 'N/A')}, Role: {x.get('role', 'N/A')}"
            )
        elif title in ["roots", "seeds", "trustSeeds"]:
            add_subsection_to_tree(
                p2p_tree,
                title.capitalize(),
                items,
            )
        # elif title == "self":
        elif title in ["self", "parent"]:
            self_info = p2p.get(title, {})
            if self_info:
                self_str = f"ID: {self_info.get('id', 'N/A')}, Addr: {self_info.get('addr', 'N/A')}, In: {self_info.get('in', 'N/A')}, Role: {self_info.get('role', 'N/A')}"
                p2p_tree.add(f"{title.title()}: {self_str}")
            else:
                p2p_tree.add(f"{title.title()}: None")
        else:
            # Handle Children, Others, Uncles which are lists
            add_subsection_to_tree(
                p2p_tree,
                title.capitalize(),
                items,
                formatter=lambda x: str(x)
            )

    return p2p_tree

def format_network_info(network, filter_key=None):
    """
    Formats the entire network information into a Rich Tree.

    :param network: Dictionary containing network information.
    :param filter_key: Optional key to filter and display only the corresponding data.
    :type filter_key: str or None
    :return: A Rich Tree object representing the network information.
    """
    network_tree = Tree("network")
    p2p = network.get('p2p', {})
    if p2p:
        p2p_tree = format_p2p_info(p2p, filter_key=filter_key)
        network_tree.add(p2p_tree)
    else:
        network_tree.add("p2p: None")

    return network_tree


async def fetch_icon_data(url="", guessed_network_endpoint=""):
    rpc_helper = AsyncIconRpcHelper(
        url=url,
        logger=pawn.console
    )
    if not await check_network_api_availability(url):
        pawn.console.log(f"Cannot connect to {url}")
        return {}

    await rpc_helper.initialize()

    if guessed_network_endpoint:
        preps_name_info =  await rpc_helper.get_node_name_by_address()
    else:
        preps_name_info = {}

    pawn.set(preps_name_info=preps_name_info)

    last_block_height = await rpc_helper.get_last_blockheight()
    chain_info = await rpc_helper.fetch("/admin/chain", return_first=True)
    node_info =  await rpc_helper.fetch("/admin/chain/icon_dex")
    network_info =  await rpc_helper.get_network_info()

    await rpc_helper.session.close()

    return {
        "node_info": node_info,
        "network_info": network_info,
        "chain_info": chain_info,
        "last_block_height": last_block_height,
        "preps_name_info": preps_name_info
    }


async def fetch_admin_chain(target_url="", external_url=""):
    """
    Fetches data from the target and external ICON nodes.

    Args:
        target_url (str): URL of the target ICON node.
        external_url (str): URL of the external ICON node.

    Returns:
        dict: A dictionary containing data from the target and external nodes with elapsed time.
    """
    async with AsyncIconRpcHelper(logger=pawn.console, timeout=2, return_with_time=True, retries=1) as rpc_helper:
        try:
            # await check_network_api_availability(target_url)
            target_node, target_node_time = await rpc_helper.fetch(
                url=f"{target_url}/admin/chain", return_first=True
            )
            target_node = (
                {"elapsed": target_node_time, **target_node}
                if isinstance(target_node, dict)
                else {"elapsed": target_node_time, "error": "Invalid target node response"}
            )
        except Exception as e:
            target_node = {"elapsed": None, "error": f"Failed to fetch target node data: {str(e)}"}

        if external_url:
            try:
                # Fetch block height from the external node
                external_node_blockheight, external_node_time = await rpc_helper.get_last_blockheight(url=external_url)
                external_node = {
                    "elapsed": external_node_time,
                    "height": external_node_blockheight,
                } if external_node_blockheight else {
                    "elapsed": external_node_time,
                    "error": "Failed to fetch external node block height"
                }
            except Exception as e:
                external_node = {"elapsed": None, "error": f"Failed to fetch external node data: {str(e)}"}
        else:
            external_node = {"elapsed": None, "error": f"external url not provided: {external_url}"}

    return {
        "target_node": target_node,
        "external_node": external_node,
    }


async def is_port_open(host, port):
    """
    Checks if a specific port on a host is open.

    :param host: The hostname or IP address to check.
    :param port: The port number to check.
    :return: True if the port is open, False otherwise.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False

async def check_network_api_availability(network_api):
    """
    Checks if the network API is available and the port is open.

    :param network_api: The network API URL to check.
    :return: True if the network API is available, False otherwise.
    """
    from urllib.parse import urlparse
    parsed_url = urlparse(append_http(network_api))

    host = parsed_url.hostname
    port = parsed_url.port

    if not host or not port:
        pawn.console.log("[red]Invalid network API URL provided.[/red]")
        return False

    is_open = await is_port_open(host, port)

    if not is_open:
        pawn.console.log(f"[red]Port {port} on {host} is not open.[/red]")
        return False
    pawn.console.log(f"[green]Port {port} on {host} is open and accessible.[/green]")
    return True


def display_stats(network_api, compare_api=None, history_size=100, interval=2, log_interval=20):
    """
    Fetches data from a network API, calculates TPS (Transactions Per Second), and logs the results.

    This function periodically calls a specified network API to retrieve blockchain-related data,
    calculates various metrics such as TPS and synchronization speed, and logs the information
    in a structured format. It also estimates the time required for synchronization if applicable.

    :param network_api: The API endpoint to fetch data from.
    :type network_api: str
    :param compare_api: An optional external API endpoint to compare synchronization status.
    :type compare_api: str, optional
    :param history_size: The size of the history buffer for calculating moving averages of TPS and sync speed.
    :type history_size: int
    :param interval: The time interval (in seconds) between API calls.
    :type interval: int
    :param log_interval: The number of calls after which static information is re-logged.
    :type log_interval: int

    Example:
        .. code-block:: python

            # Basic usage with default parameters
            display_stats(network_api="http://localhost:9000/api/v1/status")

            # With an external API for comparison
            display_stats(
                network_api="http://localhost:9000/api/v1/status",
                compare_api="http://external-node.com/api/v1/status"
            )

            # Custom history size and intervals
            display_stats(
                network_api="http://localhost:9000/api/v1/status",
                history_size=200,
                interval=5,
                log_interval=50
            )
    """
    tps_calculator = TPSCalculator(history_size=history_size, variable_time=True)
    block_tracker = BlockDifferenceTracker(history_size=history_size)
    sync_speed_tracker = SyncSpeedTracker(history_size=history_size)

    while True:
        try:
            start_time = time.time()

            result = asyncio.run(fetch_admin_chain(target_url=network_api, external_url=compare_api))

            target_node = result.get('target_node', {})
            current_height = target_node.get('height')
            current_time = time.time()

            if current_height is None or not isinstance(current_height, int):
                pawn.console.log(f"[red]Error:[/red] Invalid 'height' value received from {network_api}.")
                time.sleep(2)
                return

            sync_speed_tracker.update(current_height, current_time)
            average_sync_speed = sync_speed_tracker.get_average_sync_speed()

            external_height = result.get("external_node", {}).get("height", 0)
            block_difference = external_height - current_height
            block_tracker.add_difference(block_difference)

            if block_difference > 1:
                if average_sync_speed and average_sync_speed > 0:
                    estimated_sync_time_seconds = block_difference / average_sync_speed
                    estimated_sync_time_display = second_to_dayhhmm(estimated_sync_time_seconds)
                else:
                    average_block_time = 2
                    estimated_sync_time_seconds = block_difference * average_block_time
                    estimated_sync_time_display = second_to_dayhhmm(estimated_sync_time_seconds)
                show_sync_time = True
            else:
                estimated_sync_time_display = None
                show_sync_time = False

            current_tps, average_tps = tps_calculator.calculate_tps(current_height, current_time)
            last_tx = tps_calculator.last_n_tx()

            # Prepare dynamic log message
            dynamic_parts = [
                f"Height: {current_height}",
                f"TPS: {current_tps:.2f} (Avg: {average_tps:.2f})",
                f"TX Count: {last_tx:.2f}",
                f"Diff: {block_difference}",
            ]

            if show_sync_time and estimated_sync_time_display:
                dynamic_parts.append(f"Sync Time: {estimated_sync_time_display}")

            if target_node.get('state') != "started" or target_node.get('lastError'):
                target_state = target_node.get('state')
                percent_state = ""
                target_state_pct = ""

                if "reset" in target_state:
                    try:
                        percent_state = calculate_reset_percentage(target_state)
                        target_state_pct = f"Progress  {percent_state.get('progress')}% | "
                    except:
                        pass

                elif "pruning" in target_state:
                    try:
                        percent_state = calculate_pruning_percentage(target_state)
                        target_state_pct = f"Progress  {percent_state.get('progress')}% ({percent_state.get('resolve_progress_percentage')}%) | "
                    except:
                        pass
                else:
                    target_state_pct = ""
                dynamic_parts.append(f"[red]{target_state_pct}State: {target_node['state']} | lastError: {target_node['lastError']}")

            dynamic_log_message = " | ".join(dynamic_parts)

            if (tps_calculator.call_count % log_interval) == 1:
                static_parts = [
                    f"{network_api}",
                    f"channel: {target_node.get('channel', 'N/A')}",
                    f"cid: {target_node.get('cid', 'N/A')}",
                    f"nid: {target_node.get('nid', 'N/A')}"
                ]
                static_log_message = ", ".join(static_parts)
                full_log_message = f"[bold blue]{static_log_message}[/bold blue]\n{dynamic_log_message}"
            else:
                full_log_message = dynamic_log_message

            pawn.console.log(full_log_message)

            elapsed_time = time.time() - start_time
            sleep_time = interval - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)

        except Exception as e:
            pawn.console.log(f"[red]Exception occurred:[/red] {e}")
            time.sleep(interval)


async def find_open_ports(start_port=9000, end_port=9999):

    tasks = [check_port(port) for port in range(start_port, end_port + 1)]
    results = await asyncio.gather(*tasks)
    open_ports = [port for port, is_open in results if is_open]
    pawn.console.log(f"Checking for open ports... ({start_port} ~ {end_port}), Found: {open_ports}")
    return open_ports


async def check_port(port):
    loop = asyncio.get_event_loop()
    try:
        await loop.create_connection(lambda: asyncio.Protocol(), 'localhost', port)
        pawn.console.debug(f"Port {port} is open.")
        return port, True
    except:
        return port, False


def calculate_tps(heights, times, sleep_duration=1):
    if len(heights) < 2:
        return 0, 0
        # 최근 TPS 및 평균 TPS 계산
    recent_tx_count = heights[-1] - heights[-2]
    avg_tx_count = heights[-1] - heights[0]

    recent_tps = recent_tx_count / sleep_duration if sleep_duration > 0 else 0
    avg_tps = avg_tx_count / (times[-1] - times[0]) if (times[-1] - times[0]) > 0 else 0

    return recent_tps, avg_tps, recent_tx_count


async def find_and_check_stat(sleep_duration=2):
    refresh_interval = 30  # 포트 갱신 간격 (초)
    last_refresh_time = asyncio.get_event_loop().time()

    # 초기 포트 스캔
    open_ports = await find_open_ports()
    if not open_ports:
        pawn.console.log("No open ports found. Exiting.")
        return

    block_heights = {port: deque(maxlen=60) for port in open_ports}
    block_times = {port: deque(maxlen=60) for port in open_ports}
    consecutive_failures = {port: 0 for port in open_ports}

    async with AsyncIconRpcHelper(logger=pawn.console, timeout=2, return_with_time=False, retries=1) as rpc_helper:

        while True:
            current_time = asyncio.get_event_loop().time()

            # 주기적 포트 갱신 (초기 스캔 이후)
            if current_time - last_refresh_time >= refresh_interval:
                new_open_ports = await find_open_ports()
                last_refresh_time = current_time

                # 새로운 포트 추가
                for port in new_open_ports:
                    if port not in open_ports:
                        open_ports.append(port)
                        block_heights[port] = deque(maxlen=60)
                        block_times[port] = deque(maxlen=60)
                        consecutive_failures[port] = 0

                # 닫힌 포트 제거
                closed_ports = [port for port in open_ports if port not in new_open_ports]
                for port in closed_ports:
                    open_ports.remove(port)
                    del block_heights[port]
                    del block_times[port]
                    del consecutive_failures[port]

            # tasks = [fetch_chain(rpc_helper.session, port) for port in open_ports]
            # tasks = [rpc_helper.fetch(f":{port}/admin/chain", return_first=True) for port in open_ports]
            tasks = [rpc_helper.fetch(url=f"http://localhost:{port}/admin/chain", return_first=True) for port in open_ports]
            results = await asyncio.gather(*tasks)

            active_ports = 0
            total_ports = len(open_ports)

            for port, result in zip(open_ports, results):
                if result is not None:
                    active_ports += 1
                    nid = result['nid']
                    height = result['height']
                    state = result['state']
                    if state == "started":
                        state = ""
                    elif "reset" in state:
                        _state = calculate_reset_percentage(state)
                        state = f"reset {_state.get('reset_percentage')}%"
                    elif "pruning" in state:
                        _state = calculate_pruning_percentage(state)
                        # state = f"reset {_state.get('reset_percentage')}%"
                        state = f"Progress  {_state.get('progress')}% ({_state.get('resolve_progress_percentage')}%) | "

                    block_heights[port].append(height)
                    block_times[port].append(current_time)

                    if len(block_heights[port]) >= 2:
                        recent_tps, avg_tps, recent_tx_count = calculate_tps(
                            list(block_heights[port]),
                            list(block_times[port]),
                            sleep_duration=sleep_duration
                        )
                        status = "ok"
                        consecutive_failures[port] = 0
                    else:
                        recent_tps = avg_tps = recent_tx_count = 0
                        status = 'initializing'
                else:
                    status = 'no result'
                    nid = 'N/A'
                    height = 'N/A'
                    recent_tps = avg_tps = recent_tx_count = 0
                    consecutive_failures[port] += 1

                if consecutive_failures[port] >= 3:
                    status = 'warn'

                if status != "ok":
                    status_color = "[red]"
                elif avg_tps == 0 and recent_tps == 0:
                    status_color = "[red]"
                elif avg_tps and avg_tps > 1:
                    status_color = "[yellow]"
                else:
                    status_color = "[dim]"

                try:
                    pawn.console.log(f'{status_color}Port {port}: Status={status:<3}, Height={height:,}, nid={nid}, '
                                     f'TPS(AVG)={avg_tps:5.2f}, [dim]TPS={recent_tps:5.2f}[/dim], '
                                     f'TX Cnt={recent_tx_count:<3},{state}')
                except Exception as e:
                    pawn.console.log(f"Error: {e}")

            pawn.console.debug(f"Active Ports: {active_ports}/{total_ports}")
            await asyncio.sleep(sleep_duration)


def main():
    app_name = 'goloop'
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
    pawn.console.log(args)
    network_info = NetworkInfo(network_api=append_http(args.url))

    if args.command == "info":
        try:
            guessed_network = guess_network(network_info)
            guessed_network.get('endpoint')

            result = asyncio.run(fetch_icon_data(network_info.endpoint, guessed_network.get('endpoint')))

            if args.filter:
                filtered_result = filter_by_key(result, args.filter)
                pawn.console.rule(f"[bold blue]Filtered by '{args.filter}'[/bold blue]")
                # pawn.console.log(filtered_result[args.filter])

                root_tree = Tree(f"Filtered: {args.filter}")
                add_items_to_tree(root_tree, filtered_result, filter_key=args.filter)
                pawn.console.log(root_tree)

            else:
                root_tree = Tree("Result")
                add_items_to_tree(root_tree, result)
                pawn.console.rule("[bold blue]Node Info[/bold blue]")
                pawn.console.print(root_tree)
        except Exception as e:
            pawn.console.log(f"[red]Error fetching node info:[/red] {e}")
    elif args.command == "stats":
        _compare_api = None
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

        try:
            display_stats(network_api=network_info.network_api, compare_api=_compare_api, interval=args.interval)
        except Exception as e:
            pawn.console.log(f"[red]Error during stats display:[/red] {e}")
        display_stats(network_api=network_info.network_api, compare_api=_compare_api, interval=args.interval)

    elif args.command == "check":
        asyncio.run(find_and_check_stat(sleep_duration=args.interval))


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
        main()
    except Exception as e:
        pawn.console.log(e)

