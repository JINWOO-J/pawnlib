from pawnlib.utils.http import AsyncIconRpcHelper
from pawnlib.utils.network import check_network_api_availability
from pawnlib.config import pawn, LoggerMixinVerbose
from pawnlib.typing import StackList, format_hx_addresses_recursively, filter_by_key
from typing import Optional, List, Any
from rich.tree import Tree

import asyncio


class NodeInfoFetcher(LoggerMixinVerbose):
    """
    Fetches detailed information about a Goloop node in a single operation.
    """
    def __init__(self, helper: Optional[AsyncIconRpcHelper] = None, logger=None, filter_keys: Optional[List[str]] = None):
        """
        Initialize the NodeInfoFetcher.

        :param helper: An optional AsyncIconRpcHelper instance for RPC calls.
                       If None, a new helper will be created.
        :param logger: An optional logger instance. If None, a default logger is initialized.
        :param filter_keys: An optional list of keys to limit which data fields are fetched.
        """


        self.init_logger(logger=logger, verbose=1)
        self.helper = helper or AsyncIconRpcHelper(logger=self.logger)
        self.final_result = {}
        self.filter_keys = filter_keys
        self.preps_name_info = {}

    async def fetch_all(self, url: str, filter_keys: Optional[List[str]] = None, target_key: Optional[str] = '') -> dict:
        """
        Retrieve node, chain, and network information from the given RPC endpoint.

        :param url: The RPC URL of the target Goloop node.
        :param filter_keys: A list of data keys to fetch (e.g., "node_info", "chain_info").
                            If None, all available data is fetched.
        :param target_key: If provided, only the specified key is returned from the final result.
        :return: A dictionary mapping each requested key to its corresponding data,
                 or None for any key that failed to fetch.
        """
        fetch_all_data = not filter_keys
        self.logger.info(f"Fetching detailed node info from {url} with filter_key: {filter_keys or 'None'}...")

        if not await check_network_api_availability(url):
            self.logger.error(f"Cannot connect to {url}")
            return {}


        results = {}

        tasks = {}

        if fetch_all_data or (filter_keys is not None and "preps_name_info" in filter_keys):
            tasks["preps_name_info"] = self.helper.get_node_name_by_address(url=url)

        if fetch_all_data or (filter_keys is not None and "last_block_height" in filter_keys):
            tasks["last_block_height"] = self.helper.get_last_blockheight(url=url)

        if fetch_all_data or (filter_keys is not None and "chain_info" in filter_keys):
            tasks["chain_info"] = self.helper.fetch(url=f"{url}/admin/chain", return_first=True)

        if fetch_all_data or (filter_keys is not None and "node_info" in filter_keys):
            tasks["node_info"] = self.helper.fetch(url=f"{url}/admin/chain/icon_dex")

        if fetch_all_data or (filter_keys is not None and "network_info" in filter_keys):
            tasks["network_info"] = self.helper.get_network_info(url=url)

        if tasks:
            done, pending = await asyncio.wait(
                [asyncio.create_task(coro, name=key) for key, coro in tasks.items()],
                return_when=asyncio.ALL_COMPLETED
            )

            for task in done:
                try:
                    key = task.get_name()
                    results[key] = task.result()
                except Exception as e:
                    self.logger.error(f"Error fetching {task.get_name()}: {e}")
                    results[task.get_name()] = None

            for task in pending:
                task.cancel()

        self.final_result = {
            "node_info": results.get("node_info"),
            "network_info": results.get("network_info"),
            "chain_info": results.get("chain_info"),
            "last_block_height": results.get("last_block_height"),
            "preps_name_info": results.get("preps_name_info")
        }

        if target_key:
            self.final_result = filter_by_key(self.final_result, target_key)

        if filter_keys:
            filtered_output = {key: self.final_result.get(key) for key in filter_keys if key in self.final_result}
            return filtered_output

        return self.final_result


class NodeInfoFormatter(LoggerMixinVerbose):
    """
    Goloop 노드 정보를 Rich Tree 형식으로 포매팅하고 출력하는 클래스.
    """
    def __init__(self, preps_name_info: Optional[dict] = None, logger=None):
        self.init_logger(logger=logger, verbose=1)
        self.preps_name_info = preps_name_info if preps_name_info is not None else {}


    def print_tree(self, result: dict):
        """
        주어진 노드 정보 딕셔너리를 Rich Tree로 포매팅하여 출력합니다.
        """
        tree = Tree("Node Info")
        self.preps_name_info = result.get("preps_name_info", {})
        self.add_items_to_tree(tree, result)
        pawn.console.log(tree)

    def add_items_to_tree(self, tree, data, filter_key=None):
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
                    network_tree = self.format_network_info(value)
                    tree.add(network_tree)
                elif isinstance(value, dict):
                    branch = tree.add(f"[bold blue]{key}[/bold blue]")
                    self.add_items_to_tree(branch, value)
                elif isinstance(value, list):
                    branch = tree.add(f"[bold green]{key}[/bold green] ({len(value)})")
                    self.add_items_to_tree(branch, value)
                else:
                    tree.add(f"[bold cyan]{key}[/bold cyan]: [green]{value}[/green]")
        elif isinstance(data, list):
            for index, item in enumerate(data):
                if isinstance(item, dict):
                    branch = tree.add(f"[bold magenta]{index}[/bold magenta]")
                    self.add_items_to_tree(branch, item)
                elif isinstance(item, list):
                    branch = tree.add(f"[bold magenta]{index}[/bold magenta] (List)")
                    self.add_items_to_tree(branch, item)
                else:
                    tree.add(f"[bold magenta]{index}[/bold magenta]: [green]{item}[/green]")
        else:
            tree.add(f"[green]{data}[/green]")

    def format_network_info(self, network: dict) -> Tree:
        """
        Formats the entire network information into a Rich Tree.
        """
        network_tree = Tree("network")
        p2p = network.get('p2p', {})
        if p2p:
            p2p_tree = self.format_p2p_info(p2p)
            network_tree.add(p2p_tree)
        else:
            network_tree.add("p2p: None")
        return network_tree

    def format_p2p_info(self, p2p: dict) -> Tree:
        """
        Formats the P2P information into a Rich Tree.
        """
        p2p_tree = Tree("p2p")

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

        formatted_subsections = format_hx_addresses_recursively(subsections, self.preps_name_info)

        for title, items in formatted_subsections.items():
            if title in ["friends", "nephews", "orphanages", "uncles"]:
                self.add_subsection_to_tree(
                    p2p_tree,
                    title.capitalize(),
                    items,
                    formatter=lambda x: f"ID: {x.get('id', 'N/A')}, Addr: {x.get('addr', 'N/A')}, In: {x.get('in', 'N/A')}, Role: {x.get('role', 'N/A')}"
                )
            elif title in ["roots", "seeds", "trustSeeds"]:
                self.add_subsection_to_tree(
                    p2p_tree,
                    title.capitalize(),
                    items,
                )
            elif title in ["self", "parent"]:
                self_info = p2p.get(title, {})
                if self_info:
                    addr = self_info.get('addr', 'N/A')
                    display_addr = self.preps_name_info.get(addr, addr)
                    self_str = f"ID: {self_info.get('id', 'N/A')}, Addr: {display_addr}, In: {self_info.get('in', 'N/A')}, Role: {self_info.get('role', 'N/A')}"
                    p2p_tree.add(f"{title.title()}: {self_str}")
                else:
                    p2p_tree.add(f"{title.title()}: None")
            else:
                self.add_subsection_to_tree(
                    p2p_tree,
                    title.capitalize(),
                    items,
                    formatter=lambda x: str(x)
                )
        return p2p_tree

    def add_subsection_to_tree(self, tree: Tree, title: str, items: Any, formatter=lambda x: x):
        """
        Adds a subsection to the tree.
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
            tree.add(f"{title}: {items if items is not None else 'None'}")



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
