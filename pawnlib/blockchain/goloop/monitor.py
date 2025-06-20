
from pawnlib.metrics.tracker import TPSCalculator, SyncSpeedTracker, BlockDifferenceTracker, calculate_reset_percentage, calculate_pruning_percentage
from pawnlib.utils.http import AsyncIconRpcHelper, append_http
from pawnlib.typing.date_utils import format_seconds_to_hhmmss, second_to_dayhhmm
from pawnlib.config import pawn, LoggerMixinVerbose
from pawnlib.config import pawn
import time
from pawnlib.config import LoggerMixinVerbose
from typing import Optional, List

import asyncio


class NodeStatsMonitor(LoggerMixinVerbose):
    """
    Monitors a Goloop node by periodically polling its status and computing statistics.
    """
    def __init__(
        self,
        network_api: str,
        compare_api: str,
        helper: Optional[AsyncIconRpcHelper] = None,
        interval: int = 2,
        history_size: int = 100,
        log_interval: int = 20,
        logger=None,
    ):
        """
        Initialize the NodeStatsMonitor.

        :param network_api: RPC URL of the target node to monitor.
        :param compare_api: RPC URL of the node to compare against.
        :param helper: Optional AsyncIconRpcHelper instance for RPC calls. If None, a default helper is created.
        :param interval: Polling interval in seconds between data fetches.
        :param history_size: Number of entries to retain for TPS, block diff, and sync speed calculations.
        :param log_interval: Number of polls between full static information logs.
        :param logger: Optional logger instance. If None, a default logger is initialized.
        """
        self.network_api = network_api
        self.compare_api = compare_api
        self.helper = helper or AsyncIconRpcHelper(logger=pawn.console, timeout=2, return_with_time=True, retries=1)

        self.interval = interval
        self.log_interval = log_interval
        self.init_logger(logger=logger, verbose=1)

        self.tps_calculator = TPSCalculator(history_size=history_size, variable_time=True)
        self.block_tracker = BlockDifferenceTracker(history_size=history_size)
        self.sync_speed_tracker = SyncSpeedTracker(history_size=history_size)

    async def _fetch_data(self) -> dict:
        """
        Asynchronously fetch chain information from the target and comparison nodes.

        :return: A dict with 'target_node' and 'external_node' keys, each containing the fetched data
                 along with elapsed time or error details.
        """
        try:
            target_node, target_node_time = await self.helper.fetch(
                url=f"{self.network_api}/admin/chain", return_first=True
            )

            target_node = (
                {"elapsed": target_node_time, **target_node}
                if isinstance(target_node, dict)
                else {"elapsed": target_node_time, "error": "Invalid target node response"}
            )

        except Exception as e:
            target_node = {"error": f"Failed to fetch target node data: {e}"}

        if self.compare_api:
            try:
                external_height, external_node_time = await self.helper.get_last_blockheight(url=self.compare_api)

                external_node = {
                    "elapsed": external_node_time,
                    "height": external_height,
                } if external_height else {
                    "elapsed": external_node_time,
                    "error": "Failed to fetch external node block height"
                }

            except Exception as e:
                external_node = {"error": f"Failed to fetch external node data: {e}"}
        else:
            external_node = {}

        return {"target_node": target_node, "external_node": external_node}

    def _process_stats(self, data: dict) -> dict:
        """
        Compute statistical metrics based on fetched node data.

        :param data: Dictionary containing 'target_node' and 'external_node' data entries.
        :return: A dict with calculated metrics including:
                 - height: Current block height
                 - tps: Transactions per second (current)
                 - avg_tps: Average transactions per second
                 - tx_count: Number of transactions in the last interval
                 - diff: Block height difference to external node
                 - state: Node state
                 - last_error: Last error message from the node
                 - cid, nid, channel: Node identifiers
                 - sync_time: Estimated time to sync (if applicable)
        """
        target_node = data.get('target_node', {})
        external_node = data.get('external_node', {})


        current_height = target_node.get('height')

        if not isinstance(current_height, int):
            raise ValueError(f"Invalid 'height' received from {self.network_api}")

        current_time = time.time()
        self.sync_speed_tracker.update(current_height, current_time)

        external_height = external_node.get("height", 0)
        block_difference = external_height - current_height if external_height > 0 else 0
        self.block_tracker.add_difference(block_difference)

        current_tps, average_tps = self.tps_calculator.calculate_tps(current_height, current_time)

        stats = {
            "height": current_height,
            "tps": current_tps,
            "avg_tps": average_tps,
            "tx_count": self.tps_calculator.last_n_tx(),
            "diff": block_difference,
            "state": target_node.get('state'),
            "last_error": target_node.get('lastError'),
            "cid": target_node.get('cid'),
            "nid": target_node.get('nid'),
            "channel": target_node.get('channel'),
        }

        avg_speed = self.sync_speed_tracker.get_average_sync_speed()
        if block_difference > 1 and avg_speed > 0:
            estimated_seconds = block_difference / avg_speed
            stats["sync_time"] = second_to_dayhhmm(estimated_seconds)

        return stats

    def _format_log_message(self, stats: dict) -> str:
        """
        Format computed statistics into a human-readable log message.

        :param stats: Dictionary of computed metrics from _process_stats.
        :return: Formatted log string, with static info prepended at configured intervals.
        """
        dynamic_parts = [
            f"Height: {stats['height']}",
            f"TPS: {stats['tps']:.2f} (Avg: {stats['avg_tps']:.2f})",
            f"TX Count: {stats['tx_count']:.2f}",
            f"Diff: {stats['diff']}",
        ]
        if stats.get("sync_time"):
            dynamic_parts.append(f"Sync Time: {stats['sync_time']}")


        if stats['state'] != "started" or stats['last_error']:
            state_msg = f"State: {stats['state']} | lastError: {stats['last_error']}"
            if "reset" in stats['state']:
                _state = calculate_reset_percentage(stats['state'])
                state = f"reset {_state.get('reset_percentage')}%"

            elif "pruning" in stats['stats']:
                _state = calculate_pruning_percentage(stats['state'])
                # state = f"reset {_state.get('reset_percentage')}%"
                state_msg = f"Progress  {_state.get('progress')}% ({_state.get('resolve_progress_percentage')}%) | "

            dynamic_parts.append(f"[red]{state_msg}[/red]")
        log_message = " | ".join(dynamic_parts)

        if (self.tps_calculator.call_count % self.log_interval) == 1:
            static_parts = [
                f"{self.network_api}",
                f"channel: {stats.get('channel', 'N/A')}",
                f"cid: {stats.get('cid', 'N/A')}",
                f"nid: {stats.get('nid', 'N/A')}"
            ]
            static_log_message = ", ".join(static_parts)
            return f"[bold blue]{static_log_message}[/bold blue]\n{log_message}"

        return log_message

    async def run(self):
        """
        Start the monitoring loop.

        Continuously fetches node data, processes statistics, logs the output,
        and sleeps for the configured interval.
        """
        self.logger.info(f"Starting node monitor for {self.network_api}...")
        while True:
            try:
                start_time = time.time()
                raw_data = await self._fetch_data()

                processed_stats = self._process_stats(raw_data)
                log_message = self._format_log_message(processed_stats)
                self.logger.info(log_message)

                elapsed_time = time.time() - start_time
                sleep_time = self.interval - elapsed_time
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            except Exception as e:
                self.logger.error(f"An error occurred in monitor loop: {e}", exc_info=pawn.debug)
                await asyncio.sleep(self.interval)



async def check_port(port, host="localhost"):
    loop = asyncio.get_event_loop()
    try:
        await loop.create_connection(lambda: asyncio.Protocol(), host, port)
        pawn.console.debug(f"Port {port} is open.")
        return port, True
    except:
        return port, False


async def find_open_ports(start_port=9000, end_port=9999, port_list=None, host="localhost"):

    log_message = "Checking for open ports... "
    if port_list:
        tasks = port_list
        log_message += f"from port_list = {port_list}"
        # pawn.console.log(f"Checking for open ports... Found: {port_list}")
    else:
        tasks = [check_port(port, host) for port in range(start_port, end_port + 1)]
        log_message += f"from port_list = ({start_port} ~ {end_port})"

    results = await asyncio.gather(*tasks)
    open_ports = [port for port, is_open in results if is_open]
    pawn.console.log(f"{log_message}, Found: {open_ports}")
    return open_ports


from collections import deque

def calculate_tps(heights, times, sleep_duration=1):
    if len(heights) < 2:
        return 0, 0
        # 최근 TPS 및 평균 TPS 계산
    recent_tx_count = heights[-1] - heights[-2]
    avg_tx_count = heights[-1] - heights[0]

    recent_tps = recent_tx_count / sleep_duration if sleep_duration > 0 else 0
    avg_tps = avg_tx_count / (times[-1] - times[0]) if (times[-1] - times[0]) > 0 else 0

    return recent_tps, avg_tps, recent_tx_count


class ChainMonitor(LoggerMixinVerbose):
    """
    Monitors the status of ICON chain nodes by periodically checking their RPC endpoints.
    It can scan for open ports or monitor a fixed list of ports,
    calculate TPS (Transactions Per Second), and log node states.
    """
    def __init__(
        self,
        host: str = "localhost",
        ports: Optional[List[int]] = None,
        sleep_duration: float = 2.0,        refresh_interval: float = 30.0,
        logger=None,
    ):
        """
        Initializes the ChainMonitor.

        :param host: The RPC host address (e.g., "localhost" or "127.0.0.1").
        :type host: str
        :param ports: An optional list of fixed ports to monitor. If None, the monitor will periodically scan for open ports on the host.
        :type ports: Optional[List[int]]
        :param sleep_duration: The time in seconds to wait between each monitoring loop iteration.
        :type sleep_duration: float
        :param refresh_interval: The interval in seconds at which to re-scan for open ports (if `ports` is None).
        :type refresh_interval: float
        :param logger: An optional logger object for outputting logs (e.g., `pawn.console`). If None, a default logger will be initialized.
        :type logger: Any, optional

        Example:

            .. code-block:: python

                import asyncio
                from pawnlib.utils import pawn # Assuming pawnlib is available
                from collections import deque # Required for deques

                # Example 1: Monitor localhost on dynamically found ports every 5 seconds
                monitor1 = ChainMonitor(host="127.0.0.1", sleep_duration=5.0, logger=pawn.console)
                # asyncio.run(monitor1.run()) # To run the monitor

                # Example 2: Monitor specific ports with a shorter refresh interval
                monitor2 = ChainMonitor(
                    host="my_node_ip",
                    ports=[9000, 9002],
                    sleep_duration=1.0,
                    refresh_interval=10.0,
                    logger=pawn.console
                )
                # asyncio.run(monitor2.run()) # To run the monitor
        """
        self.host = host
        self.ports = ports
        self.sleep_duration = sleep_duration
        self.refresh_interval = refresh_interval
        self.init_logger(logger=logger, verbose=1)

        # Internal state
        self.open_ports: list[int] = []
        """List of currently identified open RPC ports."""
        self.last_refresh = 0.0
        """Timestamp of the last port refresh."""
        self.block_heights: dict[int, deque[int]] = {}
        """A dictionary mapping port numbers to deques of historical block heights."""
        self.block_times: dict[int, deque[float]] = {}
        """A dictionary mapping port numbers to deques of timestamps corresponding to block heights."""
        self.failures: dict[int, int] = {}
        """A dictionary mapping port numbers to the count of consecutive failed RPC calls."""

        # API base URL
        self.api_url = append_http(host)

    @staticmethod
    def calculate_tps(heights: list[int], times: list[float], sleep_duration: float):
        """
        Calculates recent and average TPS (Transactions Per Second) based on block heights and timestamps.

        :param heights: A list of block heights.
        :type heights: list[int]
        :param times: A list of timestamps corresponding to each block height.
        :type times: list[float]
        :param sleep_duration: The `sleep_duration` between fetching new block heights, used for recent TPS calculation.
        :type sleep_duration: float
        :returns: A tuple containing (recent_tps, avg_tps, recent_tx_count).
        :rtype: tuple[float, float, int]

        Example:

            .. code-block:: python

                # Assume heights and times are collected over time
                sample_heights = [1000, 1010, 1025, 1030]
                sample_times = [0.0, 1.0, 2.0, 3.0] # 1 second intervals

                recent_tps, avg_tps, recent_tx = ChainMonitor.calculate_tps(
                    sample_heights,
                    sample_times,
                    sleep_duration=1.0 # Assuming 1-second sleep
                )
                # recent_tps will be (1030 - 1025) / 1.0 = 5.0
                # avg_tps will be (1030 - 1000) / 3.0 = 10.0
                # recent_tx will be 5
        """
        if len(heights) < 2:
            return 0.0, 0.0, 0
        recent_tx = heights[-1] - heights[-2]
        avg_tx = heights[-1] - heights[0]
        recent_tps = recent_tx / sleep_duration if sleep_duration > 0 else 0.0
        total_time = times[-1] - times[0]
        avg_tps = avg_tx / total_time if total_time > 0 else 0.0
        return recent_tps, avg_tps, recent_tx

    async def _refresh_ports(self):
        """
        Periodically scans for open ports and updates the internal state dictionaries.
        If `self.ports` is provided during initialization, it uses that fixed list;
        otherwise, it dynamically finds open ports.
        """
        now = asyncio.get_event_loop().time()
        if now - self.last_refresh < self.refresh_interval:
            return
        self.last_refresh = now

        new_ports = self.ports or await find_open_ports(host=self.host)
        # add
        for p in new_ports:
            if p not in self.open_ports:
                self.open_ports.append(p)
                self.block_heights[p] = deque(maxlen=60)
                self.block_times[p] = deque(maxlen=60)
                self.failures[p] = 0
        # remove
        for p in list(self.open_ports):
            if p not in new_ports:
                self.open_ports.remove(p)
                self.block_heights.pop(p, None)
                self.block_times.pop(p, None)
                self.failures.pop(p, None)

    async def _fetch_states(self, rpc_helper):
        """
        Asynchronously fetches the current chain state from all currently open RPC ports.

        :param rpc_helper: An instance of `AsyncIconRpcHelper` used for making asynchronous RPC calls.
        :type rpc_helper: AsyncIconRpcHelper
        :returns: A list of results, where each result is the raw response from the `/admin/chain` endpoint
                  or an error indicator if the call failed.
        :rtype: list
        """
        tasks = [
            rpc_helper.fetch(
                url=f"{self.api_url}:{port}/admin/chain",
                return_first=True
            )
            for port in self.open_ports
        ]
        return await asyncio.gather(*tasks)

    def _process_result(self, port: int, result, current_time: float):
        """
        Processes the result of an individual RPC call for a given port and logs the status.

        It updates block height/time histories, calculates TPS, and determines logging output
        based on the success or failure of the RPC call and calculated metrics.

        :param port: The port number for which the result is being processed.
        :type port: int
        :param result: The raw result received from the RPC call (expected to be a dictionary on success).
        :type result: Any
        :param current_time: The current timestamp when the result was obtained.
        :type current_time: float
        """
        status = "no result"
        nid = height = state = None
        recent_tps = avg_tps = recent_tx = 0

        if isinstance(result, dict):
            status = "ok"
            nid = result.get("nid", "N/A")
            height = result.get("height", 0)
            state = result.get("state", "")

            if "reset" in state:
                pct = calculate_reset_percentage(state).get("reset_percentage")
                state = f"reset {pct}%"
            elif "pruning" in state:
                data = calculate_pruning_percentage(state)
                state = f"Progress {data.get('progress')}% ({data.get('resolve_progress_percentage')}%) |"
            self.block_heights[port].append(height)
            self.block_times[port].append(current_time)

            if len(self.block_heights[port]) >= 2:
                recent_tps, avg_tps, recent_tx = self.calculate_tps(
                    list(self.block_heights[port]),
                    list(self.block_times[port]),
                    self.sleep_duration
                )
                self.failures[port] = 0
            else:
                status = "initializing"

        else:
            self.failures[port] += 1
            if self.failures[port] >= 3:
                status = "warn"

        if status != "ok":
            color = "[red]"
        elif avg_tps == 0 and recent_tps == 0:
            color = "[red]"
        elif avg_tps > 1:
            color = "[yellow]"
        else:
            color = "[dim]"

        try:
            if status == "ok":
                self.logger.info(
                    f"{color}Port {port}: Status={status:<3}, "
                    f"Height={height:,}, nid={nid}, TPS(avg)={avg_tps:5.2f}, "
                    f"[dim]TPS(recent)={recent_tps:5.2f}[/dim], TX Cnt={recent_tx:<3}, {state or ''}"
                )
            else:
                self.logger.info(f"{color}Port {port}: Status={status}, result={result}")
        except Exception as e:
            self.logger.info(f"Error logging port={port}: {e}")

    async def run(self):
        """
        Executes the main monitoring loop indefinitely.

        It initializes the list of open ports, then continuously refreshes the port list
        (if not fixed), fetches chain states, processes the results, and logs the status.
        The loop pauses for `self.sleep_duration` seconds between iterations.

        Example:

            .. code-block:: python

                import asyncio
                from pawnlib.utils import pawn

                monitor = ChainMonitor(host="127.0.0.1", ports=[9000, 9001], sleep_duration=1.0, logger=pawn.console)
                # To run the monitor:
                # asyncio.run(monitor.run())
        """
        if self.ports:
            self.open_ports = self.ports.copy()
        else:
            self.open_ports = await find_open_ports(host=self.host)
        if not self.open_ports:
            self.logger.info("No open ports found. Exiting.")
            return

        for p in self.open_ports:
            self.block_heights[p] = deque(maxlen=60)
            self.block_times[p] = deque(maxlen=60)
            self.failures[p] = 0

        async with AsyncIconRpcHelper(
            logger=self.logger,
            timeout=2,
            return_with_time=False,
            retries=1
        ) as rpc_helper:
            while True:
                now = asyncio.get_event_loop().time()
                await self._refresh_ports()

                results = await self._fetch_states(rpc_helper)

                # 결과 처리
                for port, res in zip(self.open_ports, results):
                    self._process_result(port, res, now)

                self.logger.debug(f"Active Ports: "
                                  f"{sum(1 for r in results if isinstance(r, dict))}/"
                                  f"{len(self.open_ports)}")
                await asyncio.sleep(self.sleep_duration)
