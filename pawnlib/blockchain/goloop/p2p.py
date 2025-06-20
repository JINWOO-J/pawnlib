from typing import Optional
# from aiohttp import ClientSession
import aiohttp
import asyncio
import time
from pawnlib.config import pawn, LoggerMixinVerbose
from pawnlib.utils.http import NetworkInfo, AsyncIconRpcHelper, append_http
from pawnlib.blockchain.goloop.models import PeerEndpoint, PeerInfo


class P2PNetworkParser(LoggerMixinVerbose):
    """
    P2PNetworkParser is a utility to explore and map the P2P network of ICON nodes
    starting from a given URL. It recursively fetches peer information,
    collects IP addresses and their associated HX (Hexadecimal) addresses,
    and organizes them into structured data.
    """
    def __init__(
            self,
            url: str,
            max_concurrent: int = 10,
            timeout: int = 5,
            max_depth: int = 5,
            verbose: int = 0,
            logger=None,
            nid=None,
    ):
        """
        Initializes the P2PNetworkParser.

        :param url: The starting URL of an ICON node (e.g., "http://localhost:9000").
        :type url: str
        :param max_concurrent: The maximum number of concurrent asynchronous requests to make. Defaults to 10.
        :type max_concurrent: int
        :param timeout: The timeout for HTTP requests in seconds. Defaults to 5.
        :type timeout: int
        :param max_depth: The maximum recursion depth for exploring the P2P network. Defaults to 5.
        :type max_depth: int
        :param verbose: The verbosity level for logging. Inherited from LoggerMixinVerbose. Defaults to 0 (no debug output).
        :type verbose: int
        :param logger: An optional logger object. If None, a default logger is initialized.
        :type logger: Any, optional
        :param nid: Optional NID (Network ID) to specify for RPC calls. If None, it will be automatically discovered.
        :type nid: Optional[Any]

        Example:

            .. code-block:: python

                import asyncio
                from pawnlib.utils import pawn # Assuming pawnlib is available

                # Example 1: Basic initialization with default settings
                parser1 = P2PNetworkParser(url="http://127.0.0.1:9000", logger=pawn.console)
                # await parser1.run()

                # Example 2: Custom concurrency and timeout
                parser2 = P2PNetworkParser(
                    url="http://node.example.com:9000",
                    max_concurrent=20,
                    timeout=10,
                    max_depth=3,
                    verbose=1,
                    logger=pawn.console
                )
                # await parser2.run()
        """
        self.init_logger(logger=logger, verbose=verbose)
        self.logger.info("Start P2PNetworkParser")

        self.start_url = url
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.max_depth = max_depth

        self.verbose = verbose

        # Resources for asynchronous operations
        self.session: Optional[aiohttp.ClientSession] = None
        """An aiohttp client session for making HTTP requests."""
        self.rpc_helper: Optional[AsyncIconRpcHelper] = None
        """An AsyncIconRpcHelper instance for simplified RPC calls."""
        self.semaphore: Optional[asyncio.Semaphore] = None
        """A semaphore to control the maximum number of concurrent requests."""

        self.visited = set()
        """A set of URLs that have already been visited to prevent redundant processing."""
        self.ip_set = set()
        """A set of unique IP addresses discovered in the network."""
        self.ip_to_hx = {}
        """A dictionary mapping IP addresses to their corresponding HX addresses and peer types."""
        self.hx_to_ip = {}
        """A dictionary mapping HX addresses to :class:`PeerInfo` objects, containing associated IP addresses."""
        self.start_time = time.time()
        """The timestamp when the parser started its execution."""
        self.nid = nid
        """The network ID being parsed."""
        self.preps_info = {}
        """Cached information about P-Reps, typically fetched once."""

        self.logger.info(f"***** P2PNetworkParser Initialized with max_concurrent={max_concurrent}")

    def extract_ip_and_port(self, url_str: str) -> (str, str):
        """
        Extracts the IP address and port from a URL string.

        :param url_str: The URL string (e.g., "http://127.0.0.1:9000").
        :type url_str: str
        :returns: A tuple containing the extracted IP address and port as strings.
                  Defaults to "7100" if no port is specified in the URL.
        :rtype: tuple[str, str]

        Example:

            .. code-block:: python

                ip, port = P2PNetworkParser("").extract_ip_and_port("http://192.168.1.1:8080")
                # ip will be "192.168.1.1", port will be "8080"

                ip, port = P2PNetworkParser("").extract_ip_and_port("node.example.com")
                # ip will be "node.example.com", port will be "7100"
        """
        url_str = url_str.replace("http://", "").replace("https://", "")
        if ":" in url_str:
            ip, port = url_str.split(":", 1)
        else:
            ip, port = url_str, "7100"
        return ip, port

    def add_hx_to_ip(self, hx: str, ip: str, peer_type: str, rtt: Optional[float] = None):
        """
        Adds or updates the HX address and associated IP information in the internal mappings.

        This method ensures that for each HX address, a :class:`PeerInfo` object is maintained.
        It adds new IP addresses to the `PeerInfo` object or increments the count for existing ones,
        and updates `peer_type` and `rtt` if provided.

        :param hx: The HX address (node ID).
        :type hx: str
        :param ip: The IP address string associated with the HX.
        :type ip: str
        :param peer_type: The type of peer relationship (e.g., 'friends', 'children', 'self').
        :type peer_type: str
        :param rtt: The Round Trip Time for this peer, if available. Defaults to None.
        :type rtt: Optional[float], optional

        Example:

            .. code-block:: python

                parser = P2PNetworkParser(url="http://localhost:9000")
                parser.preps_info = {"hx123": {"name": "NodeA"}} # Mock preps_info

                parser.add_hx_to_ip("hx123", "192.168.1.1", "friends", rtt=0.05)
                # parser.hx_to_ip["hx123"] will be a PeerInfo object with ip_addresses including "192.168.1.1"

                parser.add_hx_to_ip("hx123", "192.168.1.1", "friends", rtt=0.06)
                # The count for "192.168.1.1" in hx_to_ip["hx123"].ip_addresses will increment, rtt updated.

                parser.add_hx_to_ip("hx456", "192.168.1.2", "children")
                # A new PeerInfo object for "hx456" will be created.
        """
        if hx not in self.hx_to_ip:
            node_name = self.preps_info.get(hx, {}).get('name', "")
            self.hx_to_ip[hx] = PeerInfo(hx=hx, name=node_name)

        peer_info = self.hx_to_ip[hx]

        if ip not in peer_info.ip_addresses:
            peer_info.ip_count += 1  # 새로운 IP 등록
            peer_info.ip_addresses[ip] = PeerEndpoint(count=1, peer_type=peer_type, rtt=rtt)
        else:
            ip_attr = peer_info.ip_addresses[ip]
            ip_attr.count += 1

            if peer_type:
                ip_attr.peer_type = peer_type
            if rtt is not None:
                ip_attr.rtt = rtt

    async def initialize_resources(self):
        """
        Initializes asynchronous resources, including `aiohttp.ClientSession`,
        `AsyncIconRpcHelper`, and `asyncio.Semaphore`. These resources are
        created if they do not exist or are closed.
        """
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
            self.logger.debug("[SESSION INIT] Created new session")

        self.rpc_helper = AsyncIconRpcHelper(
            session=self.session,
            logger=None,
            verbose=self.verbose if self.verbose > 1 else -1,
            timeout=self.timeout,
            max_concurrent=self.max_concurrent,
            retries=1
        )

        self.logger.debug("[RPC HELPER INIT] Created single AsyncIconRpcHelper")
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.logger.debug(f"[SEMAPHORE INIT] max_concurrent={self.max_concurrent}")

    async def close_resources(self):
        """
        Closes the asynchronous resources, specifically the `aiohttp.ClientSession`,
        to ensure proper cleanup.
        """
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.debug("[SESSION CLOSED]")

    async def collect_ips(self, current_url: str, depth: int = 0):
        """
        Recursively collects IP addresses of P2P nodes by querying their RPC endpoints.
        It explores 'friends', 'children', 'nephews', and 'orphanages' connections
        up to `max_depth`.

        :param current_url: The URL of the current node to query.
        :type current_url: str
        :param depth: The current recursion depth. Defaults to 0.
        :type depth: int
        """
        # async with self.semaphore:
        self.logger.debug(f"[COLLECT_IPS] {current_url}, depth={depth}")
        if current_url in self.visited or depth > self.max_depth:
            return
        self.visited.add(current_url)

        ip, _ = self.extract_ip_and_port(current_url)
        if not ip:
            self.logger.warning(f"[FORMAT ERROR] Invalid URL: {current_url}")
            return

        query_url = f"http://{ip}:9000"
        try:
            # self.logger.info(f"Start ::: {query_url}")

            if not self.preps_info:
                self.preps_info = await self.rpc_helper.get_preps(url=query_url, return_dict_key="nodeAddress")

            if not self.nid:
                chain_info = await self.rpc_helper.fetch(url=f"{query_url}/admin/chain", return_first=True)
                self.logger.debug(f"[IP RESPONSE] {query_url} - {chain_info}")
                if not chain_info or 'nid' not in chain_info:
                    return
                nid = chain_info['nid']
                self.nid = nid
            else:
                nid = self.nid

            detailed_info = await self.rpc_helper.fetch(url=f"{query_url}/admin/chain/{nid}")
            self.logger.debug(f"[IP DETAIL RESPONSE] {query_url} - {detailed_info}")
            if not detailed_info or 'module' not in detailed_info:
                return

            p2p_info = detailed_info['module']['network'].get('p2p', {})
            self_info = p2p_info.get('self', {})
            if self_info.get('addr'):
                self.ip_set.add(self_info['addr'])

            peers_to_explore = []
            for peer_type in ['friends', 'children', 'nephews', 'orphanages']:
                for peer in p2p_info.get(peer_type, []):
                    peer_ip = peer.get('addr', '')
                    if peer_ip and peer_ip not in self.visited:
                        self.ip_set.add(peer_ip)
                        peers_to_explore.append(peer_ip)

            # 재귀 호출
            tasks = [self.collect_ips(peer_ip, depth + 1) for peer_ip in peers_to_explore]
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            self.logger.error(f"[IP ERROR] {query_url} - {e}")

    async def collect_hx(self, ip: str):
        """
        Collects HX (Hexadecimal) address information for a given IP address.
        This involves querying the node's `/admin/chain/{nid}` endpoint to get
        detailed P2P information and then mapping HX addresses to their IPs
        using the `add_hx_to_ip` method.

        :param ip: The IP address of the node to query.
        :type ip: str
        """
        async with self.semaphore:
            self.logger.debug(f"[COLLECT_HX] {ip}")
            base_ip, _ = self.extract_ip_and_port(ip)
            if not base_ip:
                return
            query_url = f"http://{base_ip}:9000"
            try:
                chain_info = await self.rpc_helper.fetch(url=f"{query_url}/admin/chain", return_first=True)
                self.logger.debug(f"[HX NID RESPONSE] {query_url} - {chain_info}")
                if not chain_info or 'nid' not in chain_info:
                    return
                nid = chain_info['nid']

                detailed_info = await self.rpc_helper.fetch(url=f"{query_url}/admin/chain/{nid}")
                self.logger.debug(f"[HX DETAIL RESPONSE] {query_url} - {detailed_info}")
                if not detailed_info or 'module' not in detailed_info:
                    return

                p2p_info = detailed_info['module']['network'].get('p2p', {})
                # children/friends/orphanages/others/parent
                for item in ['children', 'friends', 'orphanages', 'others', 'parent']:
                    value = p2p_info.get(item)
                    if isinstance(value, list):
                        for peer in value:
                            self.add_hx_to_ip(peer['id'], peer['addr'], peer_type=item, rtt=peer.get('rtt'))
                    elif isinstance(value, dict):
                        # parent가 dict인 경우 등
                        peer = value
                        if peer.get('id'):
                            self.add_hx_to_ip(peer.get('id'), peer['addr'], peer_type=item, rtt=peer.get('rtt'))

                # roots/seed
                for p2p_attr in ['roots', 'seed']:
                    if p2p_attr in p2p_info:
                        for ip_addr, hx in p2p_info[p2p_attr].items():
                            self.add_hx_to_ip(hx, ip_addr, peer_type=p2p_attr)

                # self 정보
                self_info = p2p_info.get('self', {})
                if self_info.get('id'):
                    self.add_hx_to_ip(self_info['id'], ip, peer_type="self")
            except Exception as e:
                self.logger.error(f"[HX ERROR] {query_url} - {e}")

    async def run(self):
        """
        Executes the main process of parsing the P2P network.
        This involves two main phases:
        1. **IP Collection**: Recursively traverses the network from the `start_url`
           to discover all reachable IP addresses of peer nodes up to `max_depth`.
        2. **HX Collection**: For each discovered IP address, it queries the node
           to get detailed P2P information, including HX addresses, and populates
           the `hx_to_ip` mapping.

        Finally, it cleans up asynchronous resources and returns the collected data.

        :returns: A dictionary containing two main mappings:
                  - "ip_to_hx": A dictionary mapping IP addresses to their corresponding HX addresses and peer types.
                  - "hx_to_ip": A dictionary mapping HX addresses to :class:`PeerInfo` objects.
        :rtype: dict

        Example:

            .. code-block:: python

                import asyncio
                from pawnlib.utils import pawn

                parser = P2PNetworkParser(url="http://localhost:9000", max_concurrent=5, logger=pawn.console)
                network_data = await parser.run()

                # Access collected data
                # print(network_data["ip_to_hx"])
                # print(network_data["hx_to_ip"])
                # print(f"Total unique IPs found: {len(network_data['ip_to_hx'])}")
                # print(f"Total unique HXs found: {len(network_data['hx_to_ip'])}")
        """
        # 1) 자원 초기화
        await self.initialize_resources()

        # [PHASE 1] IP 수집
        self.logger.info("[PHASE 1] Collecting IPs")
        await self.collect_ips(self.start_url, depth=0)
        self.logger.info(f"[PHASE 1 COMPLETE] IPs collected: {len(self.ip_set)}")

        # [PHASE 2] HX 수집
        self.logger.info("[PHASE 2] Collecting HX addresses")
        tasks = [self.collect_hx(ip) for ip in self.ip_set]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for ip_addr, result in zip(self.ip_set, results):
            if isinstance(result, Exception):
                self.logger.error(f"[HX TASK ERROR] {ip_addr} - {result}")
            else:
                self.logger.debug(f"[HX TASK SUCCESS] {ip_addr}")

        self.logger.info(f"[PHASE 2 COMPLETE] HX collected for {len(self.ip_to_hx)} IPs")

        total_elapsed = time.time() - self.start_time
        self.logger.info(
            f"[TOTAL COMPLETE] Total time: {total_elapsed:.2f}s, "
            f"IPs: {len(self.ip_set)}, Visited: {len(self.visited)}"
        )
        await self.close_resources()
        return {"ip_to_hx": self.ip_to_hx, "hx_to_ip": self.hx_to_ip}
