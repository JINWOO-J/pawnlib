import re
from pawnlib.config.globalconfig import pawnlib_config as pawn
import socket
import time
import asyncio
import requests
from typing import Dict, Optional, Union
from concurrent.futures import ThreadPoolExecutor
from timeit import default_timer
from pawnlib.utils import http, timing
from pawnlib.typing import is_valid_ipv4, todaydate, shorten_text, format_network_traffic, format_size
from pawnlib.output import PrintRichTable
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.live import Live
import signal
import threading
import queue

try:
    from bcc import BPF
except ImportError:
    BPF = None

try:
    from typing import Literal, Tuple, List
except ImportError:
    from typing_extensions import Literal, Tuple, List

prev_getaddrinfo = socket.getaddrinfo

class ProcNetMonitor:
    """
    ProcNetMonitor monitors network usage of processes using eBPF.

    :param top_n: The top N processes to display in the table.
    :param refresh_rate: The data refresh rate (refreshes per second).
    :param group_by: How to group processes ("pid" or "name").
    :param unit: The unit for displaying rates (e.g., "Mbps").
    :param protocols: List of protocols to monitor. Defaults to ["tcp", "udp"].
    :param pid_filter: List of PIDs to monitor. Only these PIDs will be tracked.
    :param proc_filter: List of process names to monitor. Only these processes will be tracked.
    :param min_bytes_threshold: Minimum number of bytes to consider for monitoring.
    :param callback: A user-defined function to be called when data is updated.
    :param exit_signal: A string used as the termination signal. When this string is detected,
                        the monitoring process will stop and the program will exit. Default is "EXIT".

    Example:

    .. code-block:: python

        # Example 1: Monitor top 5 processes with TCP and UDP protocols
        def handle_update(data):
            for group, info in data.items():
                print(f"Group: {group}, Sent: {info['bytes_sent']} bytes, Recv: {info['bytes_recv']} bytes")

        monitor = ProcNetMonitor(top_n=5, protocols=["tcp", "udp"], callback=handle_update)
        monitor.run()

        # Example 2: Monitor specific PIDs
        def handle_specific_pids(data):
            for pid, info in data.items():
                print(f"PID: {pid}, Sent: {info['bytes_sent']} bytes, Recv: {info['bytes_recv']} bytes")

        monitor = ProcNetMonitor(pid_filter=[1234, 5678], callback=handle_specific_pids)
        monitor.run()

        # Example 3: Monitor specific process names
        def handle_specific_procs(data):
            for proc, info in data.items():
                print(f"Process: {proc}, Sent: {info['bytes_sent']} bytes, Recv: {info['bytes_recv']} bytes")

        monitor = ProcNetMonitor(proc_filter=["python", "nginx"], callback=handle_specific_procs)
        monitor.run()

        # Example 4: Set a custom refresh rate and exit signal
        def handle_exit(data):
            print("Received data, checking exit condition...")
            if some_condition:
                return 'EXIT'

        monitor = ProcNetMonitor(refresh_rate=1, exit_signal="EXIT", callback=handle_exit)
        monitor.run()

    """

    EVENT_TCP_SEND = 1
    EVENT_TCP_RECV = 2
    EVENT_UDP_SEND = 3
    EVENT_UDP_RECV = 4

    def __init__(self, top_n=10, refresh_rate=2, group_by="pid", unit="Mbps",
                 protocols=None, pid_filter=None, proc_filter=None, min_bytes_threshold=0, callback=None,
                 exit_signal="EXIT"
                 ):
        """
        Initialize the ProcNetMonitor class.

        :param top_n: The top N processes to display in the table.
        :param refresh_rate: The data refresh rate (refreshes per second).
        :param group_by: How to group processes ("pid" or "name").
        :param unit: The unit for displaying rates (e.g., "Mbps").
        :param protocols: List of protocols to monitor. Defaults to ["tcp", "udp"].
        :param pid_filter: List of PIDs to monitor. Only these PIDs will be tracked.
        :param proc_filter: List of process names to monitor. Only these processes will be tracked.
        :param min_bytes_threshold: Minimum number of bytes to consider for monitoring.
        :param callback: A user-defined function to be called when data is updated.
        :param exit_signal: A string used as the termination signal. When this string is detected,
                            the monitoring process will stop and the program will exit. Default is "EXIT".
        """

        if not BPF:
            raise ImportError("'bcc' module is required but not found.")

        self.top_n = top_n
        self.refresh_rate = refresh_rate
        self.group_by = group_by
        self.unit = unit
        self.protocols = protocols or ["tcp", "udp"]
        self.pid_filter = pid_filter  # Monitor specific PIDs only
        self.proc_filter = proc_filter  # Monitor specific process names only
        self.min_bytes_threshold = min_bytes_threshold  # Minimum bytes threshold
        self.callback = callback  # User-defined callback function
        self.exit_signal = exit_signal
        self.is_running = True
        self.process_network = {}
        self.previous_counts = {}
        self.last_update_time = time.time()
        self.bpf = None
        self.console = pawn.console

        self.exit_event = threading.Event()  # Event to signal exit
        self.callback_queue = queue.Queue()  # Queue for callback functions

        # Initialize eBPF
        self._initialize_bcc()
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """
        Set up signal handlers to perform cleanup on script termination.
        """
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _initialize_bcc(self):
        """
        Initialize the eBPF program.
        """
        try:
            self.bpf = BPF(text=self._get_bpf_program())
            if "tcp" in self.protocols:
                self.bpf.attach_kprobe(event="tcp_sendmsg", fn_name="trace_tcp_send")
                self.bpf.attach_kprobe(event="tcp_recvmsg", fn_name="trace_tcp_recv")
            if "udp" in self.protocols:
                self.bpf.attach_kprobe(event="udp_sendmsg", fn_name="trace_udp_send")
                self.bpf.attach_kprobe(event="udp_recvmsg", fn_name="trace_udp_recv")

            self.bpf["events"].open_perf_buffer(self._handle_event)
        except ImportError as e:
            self.console.print(f"[Error] bcc module not found: {e}", style="bold red")
            self.bpf = None
        except Exception as e:
            self.console.print(f"[Error] Failed to initialize BPF: {e}", style="bold red")
            self.bpf = None

    def _get_bpf_program(self):
        """
        Return the eBPF program.
        """
        return """
        #include <uapi/linux/ptrace.h>
        #include <linux/sched.h>
        
        struct sock {};
        struct msghdr {};
    
        #define EVENT_TCP_SEND 1
        #define EVENT_TCP_RECV 2
        #define EVENT_UDP_SEND 3
        #define EVENT_UDP_RECV 4
    
        struct net_data_t {
            u32 pid;
            u64 bytes;
            char comm[TASK_COMM_LEN];
            u32 event_type; // Event type: 1 (TCP Send), 2 (TCP Recv), etc.
        };
    
        BPF_PERF_OUTPUT(events);
    
        int trace_tcp_send(struct pt_regs *ctx, struct sock *sk, struct msghdr *msg, size_t size) {
            struct net_data_t data = {};
            data.pid = bpf_get_current_pid_tgid() >> 32;
            data.bytes = size;
            data.event_type = EVENT_TCP_SEND;
            bpf_get_current_comm(&data.comm, sizeof(data.comm));
            events.perf_submit(ctx, &data, sizeof(data));
            return 0;
        }
    
        int trace_tcp_recv(struct pt_regs *ctx, struct sock *sk, struct msghdr *msg, size_t size) {
            struct net_data_t data = {};
            data.pid = bpf_get_current_pid_tgid() >> 32;
            data.bytes = size;
            data.event_type = EVENT_TCP_RECV;
            bpf_get_current_comm(&data.comm, sizeof(data.comm));
            events.perf_submit(ctx, &data, sizeof(data));
            return 0;
        }
    
        int trace_udp_send(struct pt_regs *ctx, struct sock *sk, struct msghdr *msg, size_t size) {
            struct net_data_t data = {};
            data.pid = bpf_get_current_pid_tgid() >> 32;
            data.bytes = size;
            data.event_type = EVENT_UDP_SEND;
            bpf_get_current_comm(&data.comm, sizeof(data.comm));
            events.perf_submit(ctx, &data, sizeof(data));
            return 0;
        }
    
        int trace_udp_recv(struct pt_regs *ctx, struct sock *sk, struct msghdr *msg, size_t size) {
            struct net_data_t data = {};
            data.pid = bpf_get_current_pid_tgid() >> 32;
            data.bytes = size;
            data.event_type = EVENT_UDP_RECV;
            bpf_get_current_comm(&data.comm, sizeof(data.comm));
            events.perf_submit(ctx, &data, sizeof(data));
            return 0;
        }
        """

    @staticmethod
    def get_process_cmdline(pid):
        """
        Get the command-line arguments of a process by PID.
        """
        try:
            with open(f"/proc/{pid}/cmdline", "r") as f:
                cmdline = f.read().replace("\x00", " ").strip()
            return cmdline
        except Exception as e:
            return f"<Error reading cmdline: {e}>"

    def _handle_event(self, cpu, data, size):
        """
        Handle eBPF events.
        """
        event = self.bpf["events"].event(data)
        bytes_count = event.bytes
        event_type = event.event_type
        proc_name = event.comm.decode().strip()

        if self.group_by == "name":
            group_by = proc_name
        elif self.group_by == "pid":
            group_by = event.pid
        else:
            group_by = event.pid

        # cmdline = self.get_process_cmdline(pid)

        if self.pid_filter and event.pid not in self.pid_filter:
            return
        if self.proc_filter and proc_name not in self.proc_filter:
            return
        if bytes_count < self.min_bytes_threshold:
            return

        if group_by not in self.process_network:
            self.process_network[group_by] = {
                'pid': event.pid,
                'comm': event.comm.decode().strip(),
                # 'cmdline': cmdline,
                'bytes_sent': 0,
                'bytes_recv': 0,
                'tcp_sent': 0,
                'tcp_recv': 0,
                'tcp_sent_rate': 0.0,
                'tcp_recv_rate': 0.0,
                'udp_sent': 0,
                'udp_recv': 0,
                'udp_sent_rate': 0.0,
                'udp_recv_rate': 0.0,
                'send_rate': 0.0,
                'recv_rate': 0.0,
            }

        if event_type == self.EVENT_TCP_SEND:
            self.process_network[group_by]['tcp_sent'] += bytes_count
        elif event_type == self.EVENT_TCP_RECV:
            self.process_network[group_by]['tcp_recv'] += bytes_count
        elif event_type == self.EVENT_UDP_SEND:
            self.process_network[group_by]['udp_sent'] += bytes_count
        elif event_type == self.EVENT_UDP_RECV:
            self.process_network[group_by]['udp_recv'] += bytes_count

        # Bytes sent/received for rate calculations
        if event_type in {self.EVENT_TCP_SEND, self.EVENT_UDP_SEND}:
            self.process_network[group_by]['bytes_sent'] += bytes_count
        elif event_type in {self.EVENT_TCP_RECV, self.EVENT_UDP_RECV}:
            self.process_network[group_by]['bytes_recv'] += bytes_count

        if self.callback:
            # result = self.callback(self.process_network)
            # if result == "EXIT":
            #     self.exit_event.set()
            self.callback_queue.put(self.process_network.copy())

    def _update_rates(self):
        """
        Update transmission rates for each process and protocol.
        Add average rates based on historical data for all protocols.
        """
        current_time = time.time()

        # Initialize history buffer for rate calculations
        if not hasattr(self, 'rate_history'):
            self.rate_history = {
                pid: {
                    proto: {'sent_rate': [], 'recv_rate': []} for proto in self.protocols
                }
                for pid in self.process_network
            }

        for pid, info in self.process_network.items():
            if pid not in self.previous_counts:
                # Initialize `previous_counts` and `rate_history` for a new PID
                self.previous_counts[pid] = {
                    'time': current_time,
                    'bytes_sent': info['bytes_sent'],
                    'bytes_recv': info['bytes_recv'],
                    **{f'{proto}_sent': info.get(f'{proto}_sent', 0) for proto in self.protocols},
                    **{f'{proto}_recv': info.get(f'{proto}_recv', 0) for proto in self.protocols},
                }
                self.rate_history[pid] = {
                    proto: {'sent_rate': [], 'recv_rate': []} for proto in self.protocols
                }
                continue

            prev = self.previous_counts[pid]
            time_diff = current_time - prev['time']

            if time_diff > 0:
                info['send_rate'] = (info['bytes_sent'] - prev['bytes_sent']) / time_diff
                info['recv_rate'] = (info['bytes_recv'] - prev['bytes_recv']) / time_diff

                # Calculate current protocol-specific rates and update history
                for proto in self.protocols:
                    sent_key, recv_key = f'{proto}_sent', f'{proto}_recv'
                    info[f'{proto}_sent_rate'] = (info.get(sent_key, 0) - prev.get(sent_key, 0)) / time_diff
                    info[f'{proto}_recv_rate'] = (info.get(recv_key, 0) - prev.get(recv_key, 0)) / time_diff

                    # Update rate history for the protocol
                    self.rate_history[pid][proto]['sent_rate'].append(info[f'{proto}_sent_rate'])
                    self.rate_history[pid][proto]['recv_rate'].append(info[f'{proto}_recv_rate'])

                    # Limit history size to avoid excessive memory usage
                    max_history_size = 200
                    if len(self.rate_history[pid][proto]['sent_rate']) > max_history_size:
                        self.rate_history[pid][proto]['sent_rate'].pop(0)
                    if len(self.rate_history[pid][proto]['recv_rate']) > max_history_size:
                        self.rate_history[pid][proto]['recv_rate'].pop(0)

                    # Calculate average rates for the protocol
                    info[f'{proto}_avg_sent_rate'] = (
                            sum(self.rate_history[pid][proto]['sent_rate']) / len(self.rate_history[pid][proto]['sent_rate'])
                    )
                    info[f'{proto}_avg_recv_rate'] = (
                            sum(self.rate_history[pid][proto]['recv_rate']) / len(self.rate_history[pid][proto]['recv_rate'])
                    )

            self.previous_counts[pid] = {
                'time': current_time,
                'bytes_sent': info['bytes_sent'],
                'bytes_recv': info['bytes_recv'],
                **{f'{proto}_sent': info.get(f'{proto}_sent', 0) for proto in self.protocols},
                **{f'{proto}_recv': info.get(f'{proto}_recv', 0) for proto in self.protocols},
            }

        self.last_update_time = current_time

    def generate_title(self):
        """
        Dynamically generate the title based on initialized parameters.

        Returns:
            str: Generated title.
        """
        title = f"Process Network Usage ({self.unit} Sent/Recv)"
        title += f", TopN: {self.top_n}"
        title += f", RefreshRate: {self.refresh_rate}s"
        title += f", GroupBy: {self.group_by}"
        if self.pid_filter:
            title += f", PIDFilter: {', '.join(map(str, self.pid_filter))}"
        if self.proc_filter:
            title += f", ProcFilter: {', '.join(map(str, self.proc_filter))}"
        if self.min_bytes_threshold:
            title += f", MinBytesThreshold: {self.min_bytes_threshold} bytes"
        title += f", Protocols: {', '.join(self.protocols)}"
        return title

    def _generate_table(self):
        """
        Generate a Rich table displaying process network usage for specified protocols.
        :return: Rich Table object.
        """

        # table = Table(title=f"Process Network Usage ({self.unit} Sent/Recv), GroupBy: {self.group_by}", expand=True)
        table = Table(title=self.generate_title(), expand=True)
        if self.group_by == "pid":
            table.add_column(f"PID", justify="right", style="cyan")

        table.add_column("Name", style="green")

        table.add_column("Total Sent", justify="right", style="magenta")
        table.add_column("Total Recv", justify="right", style="magenta")

        # Add protocol-specific columns dynamically
        for proto in self.protocols:
            table.add_column(f"{proto.upper()} Sent(AVG)", justify="right", style="yellow")
            table.add_column(f"{proto.upper()} Recv(AVG)", justify="right", style="yellow")

        # Sort processes by the sum of all protocol rates
        sorted_pids = sorted(
            self.process_network.keys(),
            key=lambda pid: sum(
                self.process_network[pid].get(f"{proto}_sent", 0) + self.process_network[pid].get(f"{proto}_recv", 0)
                for proto in self.protocols
            ),
            reverse=True
        )[:self.top_n]

        for pid in sorted_pids:
            info = self.process_network[pid]

            # Basic process details
            row = [
                # str(pid),
                f"{info['comm']}",
                f"{format_size(info['bytes_sent'])}",
                f"{format_size(info['bytes_recv'])}",
            ]

            if self.group_by == "pid":
                row.insert(0, str(pid))

            # Add protocol-specific details
            for proto in self.protocols:
                sent_rate = format_network_traffic(info.get(f'{proto}_sent_rate', 0), unit=self.unit)
                sent_avg_rate = format_network_traffic(info.get(f'{proto}_avg_sent_rate', 0), unit=self.unit, show_unit=False)
                recv_rate = format_network_traffic(info.get(f'{proto}_recv_rate', 0), unit=self.unit)
                avg_recv_rate = format_network_traffic(info.get(f'{proto}_avg_recv_rate', 0), unit=self.unit, show_unit=False)
                row.append(f"{sent_rate} [dim]{sent_avg_rate}[/dim]")
                row.append(f"{recv_rate} [dim]{avg_recv_rate}[/dim]")
            table.add_row(*row)

        return table

    def _process_callbacks(self):
        """
        Process the callback queue.
        """
        while not self.callback_queue.empty():
            data = self.callback_queue.get()
            result = self.callback(data)
            if self.exit_signal and result == self.exit_signal:
                self.is_running = False
                self.exit_event.set()
                break

    # def run(self):
        # """
        # Run the NetworkMonitor (utilize data via callbacks or external logic).
        # """
        # if not self.bpf:
        #     self.console.print("[Error] BPF not initialized. Exiting.", style="bold red")
        #     return
        #
        # self.console.print("Starting NetworkMonitor...", style="bold green")
        # try:
        #     # while not self.exit_event.is_set():
        #     while self.is_running:
        #
        #         self.bpf.perf_buffer_poll(timeout=1000)
        #         self._update_rates()
        #         self._process_callbacks()
        #         time.sleep(1 / self.refresh_rate)
        #
        # except SystemExit:
        #     self.console.print("[bold yellow]Exiting NetworkMonitor...[/bold yellow]")
        #     # self.is_running = False
        # except KeyboardInterrupt:
        #     self.console.print("Stopping NetworkMonitor.", style="bold yellow")
        #
        # finally:
        #     self.is_running = False
        #     self.console.print("[bold red]NetworkMonitor stopped.[/bold red]")

    def run(self):
        """
        ProcNetMonitor를 실행합니다. `is_running`이 `True`인 동안 루프를 계속합니다.
        """
        if not self.bpf:
            self.console.print("[Error] BPF not initialized. Exiting.", style="bold red")
            return

        self.console.print("Starting NetworkMonitor...", style="bold green")
        try:
            while self.is_running:
                self.bpf.perf_buffer_poll(timeout=1000)
                self._update_rates()
                self._process_callbacks()
                time.sleep(1 / self.refresh_rate)
        except SystemExit:
            self.console.print("[bold yellow]Exiting NetworkMonitor...[/bold yellow]")
        except KeyboardInterrupt:
            self.console.print("Stopping NetworkMonitor.", style="bold yellow")
        finally:
            self.is_running = False
            self.console.print("[bold red]NetworkMonitor stopped.[/bold red]")


    def run_live(self):
        """
        Display real-time tables using Rich Live.
        """
        if not self.bpf:
            self.console.print("[Error] BPF not initialized. Exiting.", style="bold red")
            return

        with Live(self._generate_table(), refresh_per_second=self.refresh_rate, console=self.console) as live:
            try:
                while self.is_running:
                    self.bpf.perf_buffer_poll(timeout=1000)
                    self._update_rates()
                    self._process_callbacks()
                    live.update(self._generate_table())
                    time.sleep(1 / self.refresh_rate)
            except KeyboardInterrupt:
                self.console.print("Stopping NetworkMonitor.", style="bold yellow")

    def update_data(self):
        """
        Poll eBPF events and update the process_network data.
        """
        if not self.bpf:
            raise RuntimeError("BPF is not initialized.")

        # eBPF 이벤트 폴링
        self.bpf.perf_buffer_poll(timeout=1000)

        # 네트워크 전송/수신 속도 갱신
        self._update_rates()

    def get_latest_network_data(self, top_n=None):
        """
        Return the latest network usage data, optionally limited to the top N processes.

        Args:
            top_n (int): Number of top processes to return.

        Returns:
            List[Dict[str, Any]]: List of process network usage dictionaries.
        """
        self.update_data()
        return self.get_top_n(top_n or self.top_n)

    def get_top_n(self, n: Optional[int] = None) -> List[Dict[str, Union[int, str, float]]]:
        """
        Retrieve the top N processes by network usage.

        :param n: Number of top processes to retrieve. Defaults to self.top_n.
        :return: List of top N processes sorted by (bytes_sent + bytes_recv).
        """
        n = n or self.top_n
        with threading.Lock():
            sorted_pids = sorted(
                self.process_network.keys(),
                key=lambda pid: self.process_network[pid]['bytes_sent'] + self.process_network[pid]['bytes_recv'],
                reverse=True
            )
            top_pids = sorted_pids[:n]
            top_processes = [self.process_network[pid] for pid in top_pids]
        return top_processes

    def _handle_signal(self, sig, frame):
        """
        Handle signals for cleanup.
        """
        self.console.print(f"\nExiting... signal={sig}, frame={frame}", style="bold red")
        self.is_running = False
        self.exit_event.set()


class OverrideDNS:
    """

    Change the Domain Name using socket

    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.OverrideDNS(domain=domain, ipaddr=ipaddr).set()

    """
    _dns_cache = {}

    def __init__(self, domain="", ipaddr="", port=80):
        self._dns_cache[domain] = ipaddr
        self.prv_getaddrinfo = prev_getaddrinfo

    def new_getaddrinfo(self, *args):
        if args[0] in self._dns_cache:
            if pawn.verbose:
                print("Forcing FQDN: {} to IP: {}".format(args[0], self._dns_cache[args[0]]))
            return self.prv_getaddrinfo(self._dns_cache[args[0]], *args[1:])
        else:
            return self.prv_getaddrinfo(*args)

    def set(self):
        socket.getaddrinfo = self.new_getaddrinfo

    def unset(self):
        socket.getaddrinfo = self.prv_getaddrinfo


def get_public_ip(use_cache=False):
    """
    The get_public_ip function returns the public IP address of the machine it is called on.

    :param use_cache: Whether to use the cached public IP if available
    :type use_cache: bool

    :return: The public ip address of the server


    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.get_public_ip()

            net.get_public_ip(use_cache=True)

    """
    try:
        if use_cache and pawn.get('CACHED_PUBLIC_IP'):
            return pawn.get('CACHED_PUBLIC_IP')

        public_ip = http.jequest("http://checkip.amazonaws.com", timeout=2).get('text', "").strip()

        if is_valid_ipv4(public_ip):

            if use_cache:
                pawn.set(CACHED_PUBLIC_IP=public_ip)
            return public_ip
        else:
            pawn.error_logger.error(f"An error occurred while fetching Public IP address. Invalid IPv4 address - '{public_ip}'")
            pawn.console.debug(f"An error occurred while fetching Public IP address. Invalid IPv4 address - '{public_ip}'")

    except Exception as e:
        pawn.error_logger.error(f"An error occurred while fetching Public IP address - {e}")
        pawn.console.debug(f"An error occurred while fetching Public IP address - {e}")

    return ""


class FindFastestRegion:
    def __init__(self, verbose=True, aws_regions=None):
        self.results = []
        self.verbose = verbose
        if aws_regions:
            self.aws_regions = aws_regions
        else:
            self.aws_regions = {
                "Seoul": "ap-northeast-2",
                "Tokyo": "ap-northeast-1",
                "Virginia": "us-east-1",
                "Hongkong": "ap-east-1",
                "Singapore": "ap-southeast-1",
                "Mumbai": "ap-south-1",
                "Frankfurt": "eu-central-1",
                "Ohio": "us-east-2",
                "California": "us-west-1",
                "US-West": "us-west-2",
                "Ceentral":"ca-central-1",
                "Ireland": "eu-west-1",
                "London": "eu-west-2",
                "Sydney": "ap-southeast-2",
                "São Paulo": "sa-east-1",
                "Beijing": "cn-north-1",
            }

    def run(self):
        self.results = []
        loop = asyncio.get_event_loop()
        future = asyncio.ensure_future(self.find_fastest_region())
        loop.run_until_complete(future)
        self.sorted_results()
        return self.results

    async def find_fastest_region(self):
        tasks = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            loop = asyncio.get_event_loop()
            for region_name, region_code in self.aws_regions.items():
                url = f'https://s3.{region_code}.amazonaws.com/ping?x=%s' % todaydate("ms")
                tasks.append(loop.run_in_executor(executor, self.get_time, *(url, region_name)))
            await asyncio.gather(*tasks)

    def get_time(self, url, name="NULL"):
        start_time = default_timer()
        try:
            response = requests.get(f'{url}', timeout=3)
            response_text = response.text
            response_time = round(response.elapsed.total_seconds(), 3)
            status_code = response.status_code
        except:
            response_time = None
            response_text = None
            status_code = 999
        elapsed = round(default_timer() - start_time, 3)

        data = {
            "region": name,
            "time": response_time,
            "run_time": elapsed,
            "url": shorten_text(url, 50),
            # "text": response_text,
            "status_code": status_code
        }
        if data.get('time') and data.get("run_time") and data.get("status_code") == 200:
            self.results.append(data)
            if self.verbose:
                print(data)
        return data

    def sorted_results(self, key="run_time"):
        self.results = sorted(self.results, key=(lambda x: x.get(key)), reverse=False)

    def print_results(self):
        PrintRichTable(title="fast_region", data=self.results)
        pawn.console.log(f"Fastest Region={self.results[0]['region']}, time={self.results[0]['run_time']} sec")


class AsyncPortScanner:
    """
    Asynchronous Port Scanner class.

    :param ip_range: Tuple of start and end IP addresses to scan.
    :param port_range: Tuple of start and end ports to scan. Default is all ports (0, 65535).
    :param max_concurrency: Maximum number of concurrent scans. Default is 30.

    Example:

        .. code-block:: python

            scanner = AsyncPortScanner(("192.168.0.1", "192.168.0.255"), (1, 1024), 50)
            asyncio.run(scanner.scan_all())
    """

    def __init__(self, ip_range: Tuple[str, str], port_range: Tuple[int, int] = (0, 65535),
                 max_concurrency: int = 30, timeout=1, ping_timeout=0.05, fast_scan_ports: List[int] = [22, 80, 443], batch_size=50000):
        self.start_ip, self.end_ip = ip_range
        self.start_port, self.end_port = port_range
        self.scan_results = {}
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.timeout = timeout
        self.ping_timeout = ping_timeout
        self.fast_scan_ports = fast_scan_ports
        self.batch_size = batch_size

    async def ping_host(self, ip: str) -> bool:
        common_ports = [22, 80, 443]
        for port in common_ports:
            try:
                await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=self.ping_timeout)
                return ip  # 연결 성공, 호스트가 살아 있음
            except Exception:
                continue  # 해당 포트에 대한 연결 실패, 다음 포트 시도
        return False  # 모든 시도 실패, 호스트가 닫혀 있음

    async def try_ping_host(self, ip: str, progress: Progress, task_id: int):
        progress.advance(task_id)
        for port in self.fast_scan_ports:
            try:
                await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=self.timeout)
                if progress is not None and task_id is not None:
                    progress.advance(task_id)  # 성공적으로 핑을 완료하면 진행 상황을 업데이트합니다.
                return ip
            except (asyncio.TimeoutError, Exception):
                continue  # 해당 포트에서 연결 실패, 다음 포트로 계속 시도합니다.
        return False

    async def scan_all(self, fast_scan: bool = False):
        if fast_scan:
            tasks = [self.check_and_scan_host(ip) for ip in self._generate_ips()]
        else:
            tasks = [
                self.wrap_scan(ip, port)
                for ip in self._generate_ips()
                for port in range(self.start_port, self.end_port + 1)
            ]
        await asyncio.gather(*tasks)

    async def check_and_scan_host(self, ip):
        if await self.ping_host(ip):
            print(f"{ip} is up, scanning ports...")
            tasks = [self.wrap_scan(ip, port) for port in range(self.start_port, self.end_port + 1)]
            await asyncio.gather(*tasks)
        else:
            print(f"{ip} is down, skipping...")

    async def scan_port(self, ip: str, port: int) ->(str, int, bool):
        async with (self.semaphore):
            pawn.console.debug(f"Scanning {ip}:{port} - Acquired semaphore, timeout={self.timeout}")
            try:
                await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=self.timeout)
                pawn.console.debug(f"Connection successful: {ip}:{port}")
                return ip, port, True
            except asyncio.TimeoutError:
                pawn.console.debug(f"Timeout: {ip}:{port}")
                return ip, port, False
            except Exception as e:
                if "Too many" in str(e):
                    pawn.console.log(f"Error scanning -> [red]{e}[/red]")
                else:
                    pawn.console.debug(f"Error scanning {ip}:{port} - {e}")
                return ip, port, False
            # finally:
            #     pawn.console.log(f"Releasing semaphore: {ip}:{port}")

    def calculate_scan_range(self):
        start_ip_int = self.ip_to_int(self.start_ip)
        end_ip_int = self.ip_to_int(self.end_ip)
        total_ips = end_ip_int - start_ip_int + 1
        total_ports = self.end_port - self.start_port + 1
        total_tasks = total_ips * total_ports
        return start_ip_int, end_ip_int, total_tasks

    async def scan(self, fast_scan: bool = False, progress: Progress = None):
        tasks = []
        ips_to_scan = await self.get_ips_to_scan(fast_scan, progress)
        if fast_scan:
            if ips_to_scan:
                pawn.console.log(f"<FAST SCAN> Alive IPs: {ips_to_scan}")
            else:
                pawn.console.log(f"<FAST SCAN> [red]No open servers found on ports {self.fast_scan_ports}.[/red]")

        total_ports = self.end_port - self.start_port + 1
        total_tasks = len(ips_to_scan) * total_ports
        fast_scan_string = "FastScan" if fast_scan else ""
        task_id = progress.add_task(f"[cyan]Scanning {fast_scan_string}...", total=total_tasks)
        if fast_scan:
            pawn.console.log(f"Alive IP: {ips_to_scan}")

        for ip in ips_to_scan:
            for port in range(self.start_port, self.end_port + 1):
                task = self.wrap_scan(ip, port, progress, task_id)
                tasks.append(task)
                if len(tasks) >= self.batch_size:
                    await asyncio.gather(*tasks)
                    tasks.clear()

        if tasks:
            await asyncio.gather(*tasks)

    async def get_ips_to_scan(self, fast_scan: bool, progress: Progress) -> List[str]:
        ips = self._generate_ips()
        if not fast_scan:
            return ips

        task_id = progress.add_task("Checking IPs...", total=len(ips))
        ping_tasks = [self.try_ping_host(ip, progress, task_id) for ip in ips]

        results = await asyncio.gather(*ping_tasks)
        alive_ips = [result for result in results if result]
        return alive_ips

    async def wrap_scan(self, ip, port, progress, task_id):
        async with self.semaphore:
            result = await self.scan_port(ip, port)
            progress.update(task_id, advance=1)
            self._process_results(result)
            return result

    def _generate_ips(self) -> List[str]:
        start_int = self.ip_to_int(self.start_ip)
        end_int = self.ip_to_int(self.end_ip)
        return [self.int_to_ip(ip_int) for ip_int in range(start_int, end_int + 1)]

    @staticmethod
    def ip_to_int(ip: str) -> int:
        return sum([int(octet) << (8 * i) for i, octet in enumerate(reversed(ip.split('.')))])

    @staticmethod
    def int_to_ip(ip_int: int) -> str:
        return '.'.join(str((ip_int >> (8 * i)) & 0xFF) for i in reversed(range(4)))

    def _process_results(self, results: List[Tuple[str, int, bool]]):
        if isinstance(results, tuple):
            results = [results]
        for ip, port, is_open in results:
            if ip not in self.scan_results:
                self.scan_results[ip] = {"open": [], "closed": []}

            if is_open:
                self.scan_results[ip]["open"].append(port)
            else:
                self.scan_results[ip]["closed"].append(port)

    def get_results(self):
        return self.scan_results

    def print_scan_results(self, view="all"):
        for ipaddr, result in self.scan_results.items():
            parsed_data = ""
            for is_open, port in result.items():
                if view == "all" or view == is_open and port:
                    # pawn.console.print(f"\t \[{is_open}] {port}")
                    parsed_data = f"\t \[{is_open}] {port}"
                    # is_data = True

            if parsed_data:
                pawn.console.print(ipaddr)
                pawn.console.print(parsed_data)

    def run_scan(self, fast_scan: bool = False):
        with Progress(
                TextColumn("[bold blue]{task.description}", justify="right"),
                BarColumn(bar_width=None),
                TextColumn("{task.completed}/{task.total} • [progress.percentage]{task.percentage:>3.0f}%"),
                "•",
                TimeRemainingColumn(),
                transient=True  # Hide the progress bar when done
        ) as progress:
            # asyncio.get_event_loop().run_until_complete(self.scan(progress))
            asyncio.get_event_loop().run_until_complete(self.scan(fast_scan, progress))


def get_local_ip():
    """

    Get the local IP address

    :return:

    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.get_local_ip()

    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ipaddr = s.getsockname()[0]
    except Exception:
        ipaddr = '127.0.0.1'
    finally:
        s.close()

    if is_valid_ipv4(ipaddr):
        return ipaddr
    else:
        pawn.error_logger.error("An error occurred while fetching Local IP address. Invalid IPv4 address")
        pawn.console.debug("An error occurred while fetching Local IP address. Invalid IPv4 address")
    return ""


def get_hostname():
    """

    Get the local hostname

    :return:

    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.get_hostname()

    """
    return socket.gethostname()


def extract_host_port(host):
    """
    The extract_host_port function extracts the host and port from a string.

    :param host: Extract the hostname from the url
    :return: A tuple of the host and port number

    Example:

    .. code-block:: python

        from pawnlib.resource import net
        net.extract_host_port("http://127.0.0.1:8000")

    """
    http_regex = '^((?P<proto>https?)(://))?(?P<host>[^:/ ]+).?(?P<port>[0-9]*).*'

    regex_res = re.search(http_regex, host)
    port = 0
    if regex_res:
        if regex_res.group('port'):
            port = int(regex_res.group('port'))
        else:
            if regex_res.group('proto'):
                if regex_res.group('proto') == "http":
                    port = 80
                elif regex_res.group('proto') == "https":
                    port = 443
            else:
                port = 80
        host = regex_res.group('host')
        pawn.console.debug(f"[Regex] host={host}, port={port}, {regex_res.groupdict()}")

    return host, port


def check_port(host: str = "", port: int = 0, timeout: float = 3.0, protocol: Literal["tcp", "udp"] = "tcp") -> bool:
    """
    Returns boolean with checks if the port is open

    :param host: ipaddress os hostname
    :param port: destination port number
    :param timeout: timeout sec
    :param protocol: type of protocol
    :return: boolean

    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.check_port()

    """

    if not host:
        raise ValueError(f"Host must be specified. inputs: host={host}")

    if protocol not in ["tcp", "udp"]:
        raise ValueError(f"Invalid protocol specified. Only 'tcp' and 'udp' are supported. inputs: {protocol}")

    if not port:
        host, port = extract_host_port(host)
        pawn.console.debug(f"[red] Parsed from host -> host={host}, port={port}")

    port = int(port)
    pawn.console.debug(f"host={host}, port={port} ({type(port).__name__}), protocol={protocol}, timeout={timeout}")

    socket_protocol = socket.SOCK_STREAM if protocol == "tcp" else socket.SOCK_DGRAM

    # if timeout:
    #     socket.setdefaulttimeout(float(timeout))  # seconds (float)

    with socket.socket(socket.AF_INET, socket_protocol) as sock:
        host = http.remove_http(host)
        sock.settimeout(timeout)  # Set timeout directly on the socket
        try:
            result = sock.connect_ex((host, port))
        except Exception as e:
            pawn.console.debug(f"[FAIL] {e}")
            pawn.error_logger.error(f"[FAIL] {e}")
            return False

    if result == 0:
        pawn.console.debug(f"[OK] Opened port -> {host}:{port}")
        return True
    else:
        pawn.error_logger.error(f"[FAIL] Closed port -> {host}:{port}")
    return False


def listen_socket(host, port):
    """
    Create a socket object and bind it to the host and port provided.
    Listen for incoming connections on that socket, with a maximum of 5 connections in the queue.

    :param host: str - hostname of the machine where the server is running
    :param port: int - port number that the server will listen on
    :return: socket - a socket object

    Example:
        .. code-block:: python

            # create a socket object and bind it to localhost and port 8080
            sock = listen_socket("localhost", 8080)

            # listen for incoming connections
            conn, addr = sock.accept()

    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(5)
    return sock


def wait_for_port_open(host: str = "", port: int = 0, timeout: float = 3.0, protocol: Literal["tcp", "udp"] = "tcp", sleep: float =1) -> bool:
    """

    Wait for a port to open. Useful when writing scripts which need to wait for a server to be available.

    :param host: hostname or ipaddress
    :param port: port
    :param timeout: timeout seconds (float)
    :param protocol: tcp or udp
    :param sleep: sleep fime seconds (float)
    :return:

    Example:

        .. code-block:: python

            from pawnlib.resource import net
            net.wait_for_port_open("127.0.0.1", port)

            ## ⠏  Wait for port open 127.0.0.1:9900 ... 6


    """
    message = f"[bold green] Wait for port open[/bold green] {host}:{port} ........."
    count = 0
    with pawn.console.status(message) as status:
        while True:
            if check_port(host, port, timeout, protocol):
                status.stop()
                pawn.console.debug(f"[OK] Activate port -> {host}:{port}")
                pawn.app_logger.info(f"[OK] Activate port -> {host}:{port}")
                return True
            status.update(f"{message}[cyan] {count}[/cyan]")
            count += 1
            time.sleep(sleep)


def get_location(ipaddress=""):
    try:
        response = requests.get(
        f"https://ipinfo.io/widget/demo/{ipaddress}",
            headers={
                'referer': 'https://ipinfo.io/',
                'content-type': 'application/json',
            },
            timeout=2,
        )
        return response.json().get('data')
    except Exception as e:
        pawn.console.debug(f"Error getting location - {e}")
        return {}


def get_location_with_ip_api():
    try:
        response = requests.get(
            f"http://ip-api.com/json",
            headers={
                'content-type': 'application/json',
            },
            timeout=2,
        )
        return response.json()
    except Exception as e:
        pawn.console.debug(f"Error getting location - {e}")
        return {}




