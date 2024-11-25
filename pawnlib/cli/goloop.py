#!/usr/bin/env python3
import argparse
import asyncio
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf
from pawnlib.utils.http import IconRpcHelper, NetworkInfo, AsyncIconRpcHelper, CallHttp
from pawnlib.typing import StackList, list_to_oneline_string, str2bool, shorten_text, get_procfs_path, dict_to_line
from collections import deque
import os
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter
from pawnlib.typing.date_utils import format_seconds_to_hhmmss, second_to_dayhhmm
import time
from rich.tree import Tree

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
    parser.add_argument('-u', '--url', type=str, help='printing type  %(default)s)', default="localhost:9000")
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


def build_flat_key(key_path, key):
    """
    Constructs a flattened key path.

    :param key_path: Current key path as a string.
    :param key: Current key.
    :return: New flattened key path.
    """
    return f"{key_path}.{key}" if key_path else key


def add_items_to_tree(tree, data):
    """
    Recursively adds items from the dictionary to the tree.

    :param tree: The Rich Tree object to add items to.
    :param data: The current data (dict or list).
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'network':
                # Special handling for 'network' section
                network_tree = format_network_info(value)
                tree.add(network_tree)
            elif isinstance(value, dict):
                # Create a branch for the dictionary
                branch = tree.add(f"[bold blue]{key}[/bold blue]")
                add_items_to_tree(branch, value)
            elif isinstance(value, list):
                # Create a branch for the list
                branch = tree.add(f"[bold green]{key}[/bold green] ({len(value)})")
                add_items_to_tree(branch, value)
            else:
                # Leaf node
                tree.add(f"[bold cyan]{key}[/bold cyan]: [green]{value}[/green]")
    elif isinstance(data, list):
        for index, item in enumerate(data):
            if isinstance(item, dict):
                # Create a branch for the dictionary item
                branch = tree.add(f"[bold magenta]{index}[/bold magenta]")
                add_items_to_tree(branch, item)
            elif isinstance(item, list):
                # Create a branch for the list item
                branch = tree.add(f"[bold magenta]{index}[/bold magenta] (List)")
                add_items_to_tree(branch, item)
            else:
                # Leaf node
                tree.add(f"[bold magenta]{index}[/bold magenta]: [green]{item}[/green]")
    else:
        # Leaf node
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


def format_p2p_info(p2p):
    """
    Formats the P2P information into a Rich Tree.

    :param p2p: Dictionary containing P2P information.
    :return: A Rich Tree object representing the P2P information.
    """
    p2p_tree = Tree("p2p")

    # Define subsections with their titles and corresponding data
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

    for title, items in subsections.items():
        if title in ["friends", "nephews", "orphanages"]:
            # For these, format each item as a string with key details
            add_subsection_to_tree(
                p2p_tree,
                title.capitalize(),
                items,
                formatter=lambda x: f"ID: {x.get('id', 'N/A')}, Addr: {x.get('addr', 'N/A')}, In: {x.get('in', 'N/A')}, Role: {x.get('role', 'N/A')}"
            )
        elif title in ["roots", "seeds", "trustSeeds"]:
            # These are dicts with addr: id or similar
            add_subsection_to_tree(
                p2p_tree,
                title.capitalize(),
                items
            )
        elif title == "self":
            # Single dict
            self_info = p2p.get('self', {})
            if self_info:
                self_str = f"ID: {self_info.get('id', 'N/A')}, Addr: {self_info.get('addr', 'N/A')}, In: {self_info.get('in', 'N/A')}, Role: {self_info.get('role', 'N/A')}"
                p2p_tree.add(f"Self: {self_str}")
            else:
                p2p_tree.add("Self: None")
        else:
            # Handle Children, Others, Uncles which are lists
            add_subsection_to_tree(
                p2p_tree,
                title.capitalize(),
                items,
                formatter=lambda x: str(x)
            )

    return p2p_tree

def format_network_info(network):
    """
    Formats the entire network information into a Rich Tree.

    :param network: Dictionary containing network information.
    :return: A Rich Tree object representing the network information.
    """
    network_tree = Tree("network")

    # Currently, only handling 'p2p' as per your request
    p2p = network.get('p2p', {})
    if p2p:
        p2p_tree = format_p2p_info(p2p)
        network_tree.add(p2p_tree)
    else:
        network_tree.add("p2p: None")

    return network_tree

async def fetch_icon_data(url=""):
    rpc_helper = AsyncIconRpcHelper(
        url=url,
        logger=pawn.console
    )
    await rpc_helper.initialize()
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
    }

# async def fetch_admin_chain(target_url="", external_url=""):
#     rpc_helper = AsyncIconRpcHelper(
#         # url=url,
#         logger=pawn.console,
#         timeout=2,
#         return_with_time=True
#
#     )
#     await rpc_helper.initialize()
#     target_node, target_node_time = await rpc_helper.fetch( url=f"{target_url}/admin/chain", return_first=True)
#     external_node_blockheight, external_node_time = await rpc_helper.get_last_blockheight( url=external_url)
#     await rpc_helper.session.close()
#
#     if isinstance(target_node, dict):
#         target_node['elapsed'] = target_node_time
#
#     if external_node_blockheight:
#         external_node = { 'elapsed': external_node_time, 'height': external_node_blockheight}
#     else:
#         external_node = {}
#
#     return {
#         "target_node": target_node,
#         "external_node": external_node,
#     }


async def fetch_admin_chain(target_url="", external_url=""):
    """
    Fetches data from the target and external ICON nodes.

    Args:
        target_url (str): URL of the target ICON node.
        external_url (str): URL of the external ICON node.

    Returns:
        dict: A dictionary containing data from the target and external nodes with elapsed time.
    """
    async with AsyncIconRpcHelper(logger=pawn.console, timeout=2, return_with_time=True) as rpc_helper:
        try:
            # Fetch data from the target node
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

    return {
        "target_node": target_node,
        "external_node": external_node,
    }


class TPSCalculator:
    def __init__(self, history_size=100, sleep_time=2, variable_time=False):
        """
        Initializes the TPSCalculator.

        :param history_size: Number of recent TPS values to keep for averaging.
        :param sleep_time: Fixed interval between API calls in seconds.
        :param variable_time: If True, calculate TPS based on actual elapsed time.
        """
        self.previous_height = None
        self.previous_time = None
        self.tps_history = deque(maxlen=history_size)
        self.call_count = 0  # To track the number of API calls
        self.sleep_time = sleep_time
        self.variable_time = variable_time
        self.total_transactions = 0

    def calculate_tps(self, current_height, current_time=None):
        """
        Calculates the current TPS and updates the TPS history.

        :param current_height: The current block height.
        :param current_time: The current timestamp. If None and variable_time is False, uses fixed sleep_time.
        :return: Tuple of (current_tps, average_tps)
        """
        if not self.variable_time:
            time_diff = self.sleep_time
        else:
            if current_time is None:
                current_time = time.time()
            if self.previous_time is not None:
                time_diff = current_time - self.previous_time
            else:
                time_diff = self.sleep_time  # Default to sleep_time if previous_time is not set

        if self.previous_height is not None:
            height_diff = current_height - self.previous_height
            if time_diff > 0:
                current_tps = height_diff / time_diff
                self.tps_history.append(current_tps)
                self.total_transactions += height_diff
            else:
                current_tps = 0
        else:
            current_tps = 0

        # Update previous height and time
        self.previous_height = current_height
        if self.variable_time:
            self.previous_time = current_time

        # Calculate average TPS
        average_tps = sum(self.tps_history) / len(self.tps_history) if self.tps_history else 0

        # Increment call counter
        self.call_count += 1

        return current_tps, average_tps

    # def get_total_transactions(self):
    #     """
    #     Calculates the total transactions over the entire monitoring period.
    #
    #     :return: Total number of transactions.
    #     """
    #     return self.previous_height - (self.initial_height if hasattr(self, 'initial_height') else 0)

    def processed_tx(self):
        """
        Returns the total number of transactions since monitoring started.
        :return: Total transactions as integer.
        """
        return self.total_transactions

    def last_n_tx(self):
        """
        Returns the number of transactions in the last n seconds (sleep_time).
        :return: Transactions count in last n seconds.
        """
        # Assuming n seconds is sleep_time
        if self.tps_history:
            return self.tps_history[-1] * self.sleep_time
        else:
            return 0

    def reset(self):
        """
        Resets the TPSCalculator to initial state.
        """
        self.previous_height = None
        self.previous_time = None
        self.tps_history.clear()
        self.call_count = 0

def calculate_sync_status(result, average_block_difference, elapsed_time):
    """
    Calculate block difference and estimated time to sync.

    Args:
        result (dict): A dictionary containing `target_node` and `external_node` data.
        average_block_difference (float): The average block difference for smoothing.
        elapsed_time (float): The time taken to process one block.

    Returns:
        dict: A dictionary with block difference and estimated sync time.
    """
    # Extract relevant information
    target_height = result.get("target_node", {}).get("height", 0)
    external_height = result.get("external_node", {}).get("height", 0)

    # Calculate block difference
    block_difference = external_height - target_height

    # If average block difference is available, use it for estimated sync time
    effective_difference = average_block_difference or block_difference

    # Ignore estimated sync time if block difference is 1 or less
    if block_difference <=1:
        return {
            "block_difference": block_difference,
            "estimated_sync_time": None  # No sync time needed
        }

    # Estimate time to sync
    estimated_sync_time = effective_difference * elapsed_time * 2  # Add margin for safety

    return {
        "block_difference": block_difference,
        "estimated_sync_time": second_to_dayhhmm(estimated_sync_time),
    }


class BlockDifferenceTracker:
    def __init__(self, history_size=100):
        """
        Initialize the tracker to store recent block differences.

        :param history_size: Number of recent block differences to track.
        """
        self.differences = deque(maxlen=history_size)

    def add_difference(self, block_difference):
        """
        Add a new block difference to the tracker.

        :param block_difference: The current block difference.
        """
        self.differences.append(block_difference)

    def get_average_difference(self):
        """
        Calculate the average block difference.

        :return: The average of the tracked block differences.
        """
        if not self.differences:
            return 0
        return sum(self.differences) / len(self.differences)


def display_stats(network_api, history_size=100, interval=2, log_interval=20):
    """
    Fetches data from the network API, calculates TPS, and logs the results.

    :param network_api: The API endpoint to call.
    :param history_size: Number of recent TPS values to keep for averaging.
    :param interval: Time interval between API calls in seconds.
    :param log_interval: Number of calls after which to log static information again.
    """
    tps_calculator = TPSCalculator(history_size=history_size, sleep_time=interval)
    block_tracker = BlockDifferenceTracker(history_size=history_size)


    while True:
        try:
            # Make the HTTP call

            result = asyncio.run(fetch_admin_chain(target_url=network_api, external_url="100.65.0.36:9000"))

            # calculated_status = calculate_sync_status(result)
            #
            #
            # # response = CallHttp(f"{network_api}/admin/chain").run().response.as_dict()
            #

            # # Extract elapsed time and JSON result

            # json_result = response.get('json')[0]  # Assuming the first element

            # Add block difference to tracker
            target_node = result.get('target_node')
            elapsed = target_node.get('elapsed')  # in milliseconds
            target_height = result.get("target_node", {}).get("height", 0)
            external_height = result.get("external_node", {}).get("height", 0)
            block_difference = external_height - target_height
            block_tracker.add_difference(block_difference)

            # Calculate average block difference
            avg_difference = block_tracker.get_average_difference()

            # Calculate sync status using average block difference
            elapsed_time = result.get("target_node", {}).get("elapsed", 0)
            calculated_status = calculate_sync_status(result, avg_difference, elapsed_time)


            # Extract current block height
            current_height = target_node.get('height')
            if current_height is None:
                pawn.console.log("[red]Error:[/red] 'height' not found in the JSON response.")
                # Decide whether to continue or break; here we continue
                continue

            # Calculate TPS
            current_tps, average_tps = tps_calculator.calculate_tps(current_height)
            total_tx = tps_calculator.processed_tx()
            last_tx = tps_calculator.last_n_tx()

            # Prepare dynamic log message
            dynamic_parts = [
                f"height: {current_height}",
                f"elapsed: {elapsed}ms",
                f"TPS: {current_tps:.2f}",
                # f"Avg TPS (last {len(tps_calculator.tps_history)}): {average_tps:.2f} total_tx={total_tx}, last_tx={last_tx}"
                f"Avg TPS: {average_tps:.2f} total_tx={total_tx}, last_tx={last_tx}",
                f"diff={calculated_status.get('block_difference')} , left_time={calculated_status.get('estimated_sync_time')}"
            ]
            dynamic_log_message = ", ".join(dynamic_parts)

            # Prepare static information
            channel = target_node.get('channel', 'N/A')
            cid = target_node.get('cid', 'N/A')
            nid = target_node.get('nid', 'N/A')

            # Determine if static info should be logged
            should_log_static = (tps_calculator.call_count % log_interval) == 1  # Log at first call and every log_interval calls

            if should_log_static:
                static_parts = [
                    f"channel: {channel}",
                    f"cid: {cid}",
                    f"nid: {nid}"
                ]
                static_log_message = ", ".join(static_parts)
                full_log_message = f"[bold blue]{static_log_message}[/bold blue], {dynamic_log_message}"
            else:
                full_log_message = dynamic_log_message

            # Log the message
            pawn.console.log(full_log_message)

            # Sleep for the specified interval
            time.sleep(interval)

        except Exception as e:
            pawn.console.log(f"[red]Exception occurred:[/red] {e}")
            # Optionally, sleep before retrying to avoid rapid failure loops
            time.sleep(interval)

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
    # NetworkInfo.MANDATORY_KEYS = ["channel", "nid", "platform", "latest"]

    # pawn.console.log(network_info)
    # pawn.console.log(network_info.nid)
    # pawn.console.log(network_info.symbol)
    # pawn.console.log(network_info.network_api)
    # pawn.console.log(f"endpoint={network_info.endpoint}")
    # # pawn.console.log(network_info.__dict__)

    network_info = NetworkInfo(network_api=args.url)

    if args.command == "info":
        result = asyncio.run(fetch_icon_data(network_info.endpoint))
        root_tree = Tree("Result")
        add_items_to_tree(root_tree, result)
        pawn.console.rule("Node Info")
        pawn.console.print(root_tree)
    elif args.command == "stats":
        display_stats(network_api=network_info.network_api, interval=args.interval)
        # pawn.console.log
        # response = CallHttp(f"{network_info.network_api}/admin/chain").run().response.as_dict()
        # elapsed = response.get('elapsed')
        # json_result = response.get('json')[0]
        # print(json_result)
        # pretty_json_result = dict_to_line(json_result, end_separator=", ")
        # pawn.console.log(f"{pretty_json_result}, {elapsed}ms")






main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':

    try:
        main()
    except Exception as e:
        pawn.console.log(e)

