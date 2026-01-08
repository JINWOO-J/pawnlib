from typing import Optional
# from aiohttp import ClientSession
import aiohttp
import asyncio
import time
from pawnlib.config import pawn, LoggerMixinVerbose
from pawnlib.utils.http import NetworkInfo, AsyncIconRpcHelper, append_http
from pawnlib.blockchain.goloop.models import PeerEndpoint, PeerInfo
from pawnlib.output import print_var


def convert_peer_info_to_dict(peer_info_dict: dict) -> dict:
    """
    PeerInfo 객체들을 포함한 딕셔너리를 완전히 dict로 변환합니다.
    중첩된 PeerEndpoint 객체도 함께 변환됩니다.
    원본 딕셔너리는 수정하지 않습니다.
    
    Args:
        peer_info_dict (dict): hx를 키로 하고 PeerInfo 객체를 값으로 하는 딕셔너리
        
    Returns:
        dict: 모든 객체가 dict로 변환된 결과
        
    Example:
        >>> result = convert_peer_info_to_dict(self.hx_to_ip)
        >>> # 결과는 완전히 JSON 직렬화 가능한 dict
    """
    result = {}
    for hx, peer_info in peer_info_dict.items():
        # PeerInfo 객체인 경우 to_dict() 호출, 이미 dict인 경우 그대로 사용
        if hasattr(peer_info, 'to_dict'):
            result[hx] = peer_info.to_dict()
        elif isinstance(peer_info, dict):
            result[hx] = peer_info
        else:
            result[hx] = peer_info.__dict__ if hasattr(peer_info, '__dict__') else peer_info
    return result


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
            platform="icon"
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
        :param platform: The blockchain platform type. Defaults to "icon".
        :type platform: str


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
        self.error_count = 0
        """Number of errors encountered during parsing."""
        self.timeout_count = 0
        """Number of timeout errors encountered."""
        self.platform = platform
        """The blockchain platform type, e.g., "icon"."""

        self.logger.info(f"***** P2PNetworkParser Initialized with max_concurrent={max_concurrent}")

    def extract_ip_and_port(self, url_str: str) -> tuple:
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
        
        # peer_info가 dict로 변환되어 있는 경우 PeerInfo 객체로 복원
        if isinstance(peer_info, dict):
            # dict에서 PeerInfo 객체로 복원
            restored_peer_info = PeerInfo(
                hx=peer_info.get('hx', hx),
                name=peer_info.get('name', ''),
                ip_count=peer_info.get('ip_count', 0)
            )
            # ip_addresses 복원
            if 'ip_addresses' in peer_info:
                for ip_addr, endpoint_data in peer_info['ip_addresses'].items():
                    if isinstance(endpoint_data, dict):
                        restored_peer_info.ip_addresses[ip_addr] = PeerEndpoint(
                            count=endpoint_data.get('count', 0),
                            peer_type=endpoint_data.get('peer_type', ''),
                            rtt=endpoint_data.get('rtt')
                        )
                    else:
                        restored_peer_info.ip_addresses[ip_addr] = endpoint_data
            
            # 복원된 객체로 교체
            self.hx_to_ip[hx] = restored_peer_info
            peer_info = restored_peer_info

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
        # 방문 체크는 semaphore 밖에서 (빠른 리턴)
        self.logger.info(f"[COLLECT_IPS START] URL={current_url}, depth={depth}, visited={len(self.visited)}, ips_found={len(self.ip_set)}")
        
        if current_url in self.visited:
            self.logger.debug(f"[COLLECT_IPS SKIP] Already visited: {current_url}")
            return
        
        if depth > self.max_depth:
            self.logger.debug(f"[COLLECT_IPS SKIP] Max depth reached: {current_url}")
            return
        
        # semaphore는 실제 네트워크 요청 시에만 사용
        async with self.semaphore:
            # 다시 한번 체크 (race condition 방지)
            if current_url in self.visited:
                return
            self.visited.add(current_url)

            ip, _ = self.extract_ip_and_port(current_url)
            if not ip:
                self.logger.warning(f"[FORMAT ERROR] Invalid URL: {current_url}")
                return

            query_url = f"http://{ip}:9000"
            peers_to_explore = []
            
            try:
                # P-Reps 정보는 한 번만 조회
                if not self.preps_info:
                    self.logger.info(f"[PREPS FETCH] Fetching P-Reps info from {query_url}")
                    try:
                        if self.platform == "icon":
                            # AsyncIconRpcHelper가 자체 timeout을 가지고 있으므로 wait_for 제거
                            self.preps_info = await self.rpc_helper.get_preps(url=query_url, return_dict_key="nodeAddress")
                        elif self.platform == "havah":
                            self.preps_info = await self.rpc_helper.get_validator_info(url=query_url, return_dict_key="node")
                        else:
                            self.logger.info(f"Unsupported platform: {self.platform}")
                            
                        self.logger.info(f"[PREPS FETCHED] Total P-Reps: {len(self.preps_info)}")
                        
                    except asyncio.TimeoutError:
                        self.timeout_count += 1
                        self.logger.warning(f"[PREPS TIMEOUT] {query_url}")
                        return
                    except Exception as e:
                        self.error_count += 1
                        self.logger.error(f"[PREPS ERROR] {query_url} - {e}")
                        return

                # Chain detail 조회 (항상 icon_dex 사용)
                self.logger.debug(f"[CHAIN DETAIL FETCH] Fetching chain details from {query_url}/admin/chain/icon_dex")
                try:
                    detailed_info = await self.rpc_helper.fetch(url=f"{query_url}/admin/chain/icon_dex")
                except asyncio.TimeoutError:
                    self.timeout_count += 1
                    self.logger.warning(f"[CHAIN DETAIL TIMEOUT] {query_url}")
                    return
                except Exception as e:
                    self.error_count += 1
                    self.logger.error(f"[CHAIN DETAIL ERROR] {query_url} - {e}")
                    return
                    
                self.logger.debug(f"[IP DETAIL RESPONSE] {query_url} - {detailed_info}")
                if not detailed_info or 'module' not in detailed_info:
                    self.logger.warning(f"[CHAIN DETAIL ERROR] Invalid response from {query_url}")
                    return

                p2p_info = detailed_info['module']['network'].get('p2p', {})
                self_info = p2p_info.get('self', {})
                if self_info.get('addr'):
                    self.ip_set.add(self_info['addr'])
                    self.logger.debug(f"[SELF IP ADDED] {self_info['addr']}")

                peer_counts = {}
                for peer_type in ['friends', 'children', 'nephews', 'orphanages']:
                    peers = p2p_info.get(peer_type, [])
                    peer_counts[peer_type] = len(peers)
                    for peer in peers:
                        peer_ip = peer.get('addr', '')
                        if peer_ip and peer_ip not in self.visited:
                            self.ip_set.add(peer_ip)
                            peers_to_explore.append(peer_ip)
                            self.logger.debug(f"[PEER FOUND] type={peer_type}, ip={peer_ip}")

                self.logger.info(
                    f"[COLLECT_IPS DONE] {query_url} - "
                    f"friends={peer_counts.get('friends', 0)}, "
                    f"children={peer_counts.get('children', 0)}, "
                    f"nephews={peer_counts.get('nephews', 0)}, "
                    f"orphanages={peer_counts.get('orphanages', 0)}, "
                    f"new_peers={len(peers_to_explore)}"
                )

            except asyncio.TimeoutError:
                self.timeout_count += 1
                self.logger.warning(f"[IP TIMEOUT] {query_url} (total timeouts: {self.timeout_count})")
            except Exception as e:
                self.error_count += 1
                self.logger.error(f"[IP ERROR] {query_url} - {e} (total errors: {self.error_count})")
        
        # 재귀 호출은 semaphore 밖에서 실행 (데드락 방지)
        if peers_to_explore:
            self.logger.info(f"[RECURSIVE CALL] Exploring {len(peers_to_explore)} new peers at depth {depth + 1}")
            tasks = [self.collect_ips(peer_ip, depth + 1) for peer_ip in peers_to_explore]
            # 재귀 호출 - return_exceptions=True로 예외를 결과로 반환
            await asyncio.gather(*tasks, return_exceptions=True)

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
            self.logger.info(f"[COLLECT_HX START] IP={ip} (semaphore acquired)")
            base_ip, _ = self.extract_ip_and_port(ip)
            if not base_ip:
                self.logger.warning(f"[COLLECT_HX SKIP] Invalid IP: {ip}")
                return
            query_url = f"http://{base_ip}:9000"
            try:
                # Chain detail 조회 (항상 icon_dex 사용)
                self.logger.debug(f"[HX DETAIL FETCH] Fetching from {query_url}/admin/chain/icon_dex")
                try:
                    detailed_info = await self.rpc_helper.fetch(url=f"{query_url}/admin/chain/icon_dex")
                except asyncio.TimeoutError:
                    self.timeout_count += 1
                    self.logger.warning(f"[HX DETAIL TIMEOUT] {query_url}")
                    return
                except Exception as e:
                    self.error_count += 1
                    self.logger.error(f"[HX DETAIL ERROR] {query_url} - {e}")
                    return
                    
                self.logger.debug(f"[HX DETAIL RESPONSE] {query_url} - {detailed_info}")
                if not detailed_info or 'module' not in detailed_info:
                    self.logger.warning(f"[HX DETAIL ERROR] Invalid response from {query_url}")
                    return

                p2p_info = detailed_info['module']['network'].get('p2p', {})
                
                # P2P 정보 파싱 및 매핑
                hx_count_before = len(self.hx_to_ip)
                self._parse_p2p_peers(p2p_info, ip)
                hx_count_after = len(self.hx_to_ip)
                new_hx_count = hx_count_after - hx_count_before
                
                self.logger.info(f"[COLLECT_HX DONE] {ip} - Found {new_hx_count} new HX addresses (total: {hx_count_after})")

            except asyncio.TimeoutError:
                self.timeout_count += 1
                self.logger.warning(f"[HX TIMEOUT] {query_url} (total timeouts: {self.timeout_count})")
            except Exception as e:
                self.error_count += 1
                self.logger.error(f"[HX ERROR] {query_url} - {e} (total errors: {self.error_count})")

    def _parse_p2p_peers(self, p2p_info: dict, current_ip: str):
        """
        P2P 정보를 파싱하여 HX-IP 매핑을 생성합니다.
        
        :param p2p_info: P2P 네트워크 정보 딕셔너리
        :type p2p_info: dict
        :param current_ip: 현재 조회 중인 노드의 IP 주소
        :type current_ip: str
        """
        parsed_counts = {}
        
        # children/friends/orphanages/others/parent 처리
        for item in ['children', 'friends', 'orphanages', 'others', 'parent']:
            value = p2p_info.get(item)
            count = 0
            if isinstance(value, list):
                for peer in value:
                    if peer.get('id') and peer.get('addr'):
                        self.add_hx_to_ip(peer['id'], peer['addr'], peer_type=item, rtt=peer.get('rtt'))
                        count += 1
            elif isinstance(value, dict) and value.get('id'):
                # parent가 dict인 경우
                self.add_hx_to_ip(value['id'], value['addr'], peer_type=item, rtt=value.get('rtt'))
                count += 1
            if count > 0:
                parsed_counts[item] = count

        # roots/seed 처리
        for p2p_attr in ['roots', 'seed']:
            if p2p_attr in p2p_info:
                count = 0
                for ip_addr, hx in p2p_info[p2p_attr].items():
                    self.add_hx_to_ip(hx, ip_addr, peer_type=p2p_attr)
                    count += 1
                if count > 0:
                    parsed_counts[p2p_attr] = count

        # self 정보 처리
        self_info = p2p_info.get('self', {})
        if self_info.get('id'):
            self.add_hx_to_ip(self_info['id'], current_ip, peer_type="self")
            parsed_counts['self'] = 1
        
        if parsed_counts:
            self.logger.debug(f"[PARSE P2P] {current_ip} - Parsed: {parsed_counts}")

    async def run(self)-> dict: 
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
        self.logger.info("[INIT] Initializing resources...")
        await self.initialize_resources()
        self.logger.info("[INIT COMPLETE] Resources initialized")

        # [PHASE 1] IP 수집
        self.logger.info("=" * 80)
        self.logger.info("[PHASE 1 START] Collecting IPs from P2P network")
        self.logger.info(f"[PHASE 1 CONFIG] start_url={self.start_url}, max_depth={self.max_depth}, max_concurrent={self.max_concurrent}")
        phase1_start = time.time()
        
        await self.collect_ips(self.start_url, depth=0)
        
        phase1_elapsed = time.time() - phase1_start
        self.logger.info("=" * 80)
        self.logger.info("[PHASE 1 COMPLETE] IP Collection Summary:")
        self.logger.info(f"  - Time elapsed: {phase1_elapsed:.2f}s")
        self.logger.info(f"  - Total IPs collected: {len(self.ip_set)}")
        self.logger.info(f"  - Nodes visited: {len(self.visited)}")
        self.logger.info(f"  - Errors so far: {self.error_count}")
        self.logger.info(f"  - Timeouts so far: {self.timeout_count}")

        # [PHASE 2] HX 수집
        self.logger.info("=" * 80)
        self.logger.info(f"[PHASE 2 START] Collecting HX addresses for {len(self.ip_set)} IPs")
        phase2_start = time.time()
        
        tasks = [self.collect_hx(ip) for ip in self.ip_set]
        self.logger.info(f"[PHASE 2 TASKS] Created {len(tasks)} tasks, max_concurrent={self.max_concurrent}")
        
        # 개별 task의 timeout으로 충분하므로 전체 timeout 제거
        # return_exceptions=True로 예외를 결과로 반환하여 CancelledError 방지
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = 0
        error_count = 0
        for ip_addr, result in zip(self.ip_set, results):
            if isinstance(result, Exception):
                error_count += 1
                self.logger.error(f"[HX TASK ERROR] {ip_addr} - {result}")
            else:
                success_count += 1
                self.logger.debug(f"[HX TASK SUCCESS] {ip_addr}")

        phase2_elapsed = time.time() - phase2_start
        self.logger.info("=" * 80)
        self.logger.info("[PHASE 2 COMPLETE] HX Collection Summary:")
        self.logger.info(f"  - Time elapsed: {phase2_elapsed:.2f}s")
        self.logger.info(f"  - IPs processed: {len(self.ip_set)}")
        self.logger.info(f"  - Successful: {success_count}")
        self.logger.info(f"  - Failed: {error_count}")
        self.logger.info(f"  - Total unique HX addresses: {len(self.hx_to_ip)}")

        # [PHASE 3] 데이터 매핑 생성
        self.logger.info("=" * 80)
        self.logger.info("[PHASE 3 START] Building reverse mappings (ip_to_hx)")
        
        for hx, peer_info in self.hx_to_ip.items():
            for ip_addr in peer_info.ip_addresses:
                if ip_addr not in self.ip_to_hx:
                    self.ip_to_hx[ip_addr] = []
                self.ip_to_hx[ip_addr].append({
                    'hx': hx,
                    'name': peer_info.name,
                    'peer_type': peer_info.ip_addresses[ip_addr].peer_type,
                    'rtt': peer_info.ip_addresses[ip_addr].rtt
                })
        
        self.logger.info(f"[PHASE 3 COMPLETE] Mapped {len(self.ip_to_hx)} IPs to HX addresses")
        
        # 최종 통계
        total_elapsed = time.time() - self.start_time
        
        # 상세 통계 계산
        total_ip_hx_relations = sum(len(hx_list) for hx_list in self.ip_to_hx.values())
        
        # HX별 IP 개수 계산 (PeerInfo 객체 또는 dict 모두 처리)
        total_hx_ip_relations = sum(
            peer_info.get('ip_count', 0) if isinstance(peer_info, dict) else peer_info.ip_count 
            for peer_info in self.hx_to_ip.values()
        )
        
        # 여러 IP를 가진 HX 개수 (PeerInfo 객체 또는 dict 모두 처리)
        multi_ip_hx_count = sum(
            1 for peer_info in self.hx_to_ip.values() 
            if (peer_info.get('ip_count', 0) if isinstance(peer_info, dict) else peer_info.ip_count) > 1
        )
        
        # 여러 HX를 가진 IP 개수
        multi_hx_ip_count = sum(1 for hx_list in self.ip_to_hx.values() if len(hx_list) > 1)
        
        # P-Reps 기반 노드 분류
        registered_preps = set(self.preps_info.keys()) if self.preps_info else set()
        discovered_hx = set(self.hx_to_ip.keys())
        
        # Validator 노드 (P-Reps에 등록된 노드)
        validator_nodes = registered_preps & discovered_hx
        
        # Citizen 노드 (P-Reps에 등록되지 않은 노드)
        citizen_nodes = discovered_hx - registered_preps
        
        # 발견되지 않은 P-Reps (등록은 되어있지만 네트워크에서 발견 안됨)
        missing_preps = registered_preps - discovered_hx
        
        self.logger.info("=" * 80)
        self.logger.info("[PARSING COMPLETE] ✓ Final Statistics")
        self.logger.info("=" * 80)
        self.logger.info("Network Discovery:")
        self.logger.info(f"  ├─ Total IPs collected: {len(self.ip_set)}")
        self.logger.info(f"  ├─ Nodes visited: {len(self.visited)}")
        self.logger.info(f"  └─ Unique HX addresses: {len(self.hx_to_ip)}")
        self.logger.info("")
        
        if self.preps_info:
            self.logger.info("Node Classification (based on P-Reps):")
            self.logger.info(f"  ├─ Total registered P-Reps: {len(registered_preps)}")
            self.logger.info(f"  ├─ Validator nodes (P-Reps found): {len(validator_nodes)} ({len(validator_nodes)/len(registered_preps)*100:.1f}%)")
            self.logger.info(f"  ├─ Citizen nodes (non-P-Reps): {len(citizen_nodes)}")
            self.logger.info(f"  └─ Missing P-Reps (not discovered): {len(missing_preps)} ({len(missing_preps)/len(registered_preps)*100:.1f}%)")
            self.logger.info("")
        
        self.logger.info("Mapping Statistics:")
        self.logger.info(f"  ├─ IPs with HX mapping: {len(self.ip_to_hx)}")
        self.logger.info(f"  ├─ Total IP→HX relations: {total_ip_hx_relations} (one IP can have multiple HX)")
        self.logger.info(f"  ├─ Total HX→IP relations: {total_hx_ip_relations} (one HX can have multiple IPs)")
        self.logger.info(f"  ├─ IPs with multiple HX: {multi_hx_ip_count}")
        self.logger.info(f"  ├─ HX with multiple IPs: {multi_ip_hx_count}")
        self.logger.info(f"  └─ Avg HX per IP: {total_ip_hx_relations / len(self.ip_to_hx) if self.ip_to_hx else 0:.2f}")
        self.logger.info("")
        self.logger.info("Performance:")
        self.logger.info(f"  ├─ Total time: {total_elapsed:.2f}s")
        self.logger.info(f"  ├─ IPs per second: {len(self.ip_set) / total_elapsed:.2f}")
        self.logger.info(f"  ├─ Total errors: {self.error_count}")
        self.logger.info(f"  └─ Total timeouts: {self.timeout_count}")
        self.logger.info("=" * 80)
        
        await self.close_resources()
        
        # 결과 데이터 구성
        result = {
            "ip_to_hx": self.ip_to_hx,
            "hx_to_ip": convert_peer_info_to_dict(self.hx_to_ip),
            "statistics": {
                "total_ips": len(self.ip_set),
                "total_hx": len(self.hx_to_ip),
                "total_preps": len(registered_preps),
                "validator_nodes": list(validator_nodes),
                "citizen_nodes": list(citizen_nodes),
                "missing_preps": list(missing_preps),
                "validator_count": len(validator_nodes),
                "citizen_count": len(citizen_nodes),
                "missing_preps_count": len(missing_preps),
            }
        }
        pawn.console.log(result)
        return result
