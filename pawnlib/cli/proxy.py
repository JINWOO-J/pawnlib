#!/usr/bin/env python3
import socket
import select
import time
import sys
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import remove_http
from pawnlib.typing.check import is_int, is_valid_ipv4


def get_parser():
    parser = argparse.ArgumentParser(description='Proxy Reflector')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument("--listen", "-l", type=str, help="Listen  IPaddr:port", default="0.0.0.0:8080")
    parser.add_argument("--forward", "-f", type=str, help="Forward IPaddr:port", default=None, required=True)
    parser.add_argument("--buffer-size", type=int, help="buffer size for socket", default=4096)
    parser.add_argument("--delay", type=float, help="buffer delay for socket", default=0.0001)
    parser.add_argument("--timeout", '-t', type=float, help="timeout for socket", default=3)
    return parser


class Forward:
    def __init__(self):
        self._forwarder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port, timeout=10):
        try:
            self._forwarder.connect((host, port))
            self._forwarder.settimeout(timeout)
            return self._forwarder
        except Exception as e:
            pawn.console.log(f"[red][Forward ERROR] Connect to {host}:{port} {e}")
            return False


class EchoWebServer:
    input_list = []
    channel = {}

    def __init__(self, l_host, l_port, f_host, f_port, buffer_size, delay):
        self.data = None
        self.s = None

        self.l_host = l_host
        self.l_port = l_port
        self.f_host = f_host
        self.f_port = f_port

        self.buffer_size = buffer_size
        self.delay = delay

        self._validate()
        self._listen_server()

    def _listen_server(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.l_host, self.l_port))
        self.server.listen(200)

    def _validate(self):
        for ipaddr in [self.l_host, self.f_host]:
            if not is_valid_ipv4(ipaddr):
                # pawn.console.print(f"[bold red]Invalid IP address - {ipaddr}, {is_valid_ipv4(ipaddr)}")
                raise ValueError(f"Invalid IP address - '{ipaddr}'")

    def main_loop(self):
        self.input_list.append(self.server)
        while True:
            time.sleep(self.delay)
            ss = select.select
            input_ready, output_ready, except_ready = ss(self.input_list, [], [])
            for self.s in input_ready:
                if self.s == self.server:
                    self.on_accept()
                    break
                try:
                    self.data = self.s.recv(self.buffer_size)
                except Exception as e:
                    pawn.console.log(f"[red bold] {e}")

                if len(self.data) == 0:
                    self.on_close()
                    break
                else:
                    self.on_recv()

    def on_accept(self):
        pawn.console.log("[bold red] on_accept")
        forward = Forward().start(self.f_host, self.f_port)
        clientsock, client_addr = self.server.accept()
        client_ip, client_port = client_addr
        if forward:
            pawn.console.log(f"{client_ip}:{client_port} has connected")
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
        else:
            pawn.console.log(f"Can't establish connection with remote server. "
                             f"Closing connection with client side: {client_ip}:{client_port}")
            clientsock.close()

    def on_close(self):
        pawn.console.log(f"{self._return_ip_port(self.s.getpeername())}", "has disconnected")
        # remove objects from input_list
        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        # close the connection with client
        self.channel[out].close()  # equivalent to do self.s.close()
        # close the connection with remote server
        self.channel[self.s].close()
        # delete both objects from channel dict
        del self.channel[out]
        del self.channel[self.s]

    def on_recv(self):
        data = self.data
        lines = data.decode('UTF-8')
        if "\r\n" in lines:
            data_arr = lines.split('\r\n')
            if data_arr and data_arr[0].startswith("HTTP"):
                pawn.console.log(f"[bold blue]Response from {self.f_host}:{self.f_port}")
            else:
                pawn.console.log(f"[bold blue]Request from {self.l_host}:{self.l_port}")
            pawn.console.rule(f"[bold blue] ", align="right")
            for line in data_arr:
                pawn.console.print(line)
        # print("\n")
        pawn.console.rule(style="spring_green2")
        self.channel[self.s].send(data)

    @staticmethod
    def _return_ip_port(data):
        if data and len(data) > 1:
            return "{}:{}".format(*data)


def parse_ip_port(data):
    def _return_port(port=None):
        if port and not is_int(port):
            raise ValueError(f"Invalid port -> {port}")
        return int(port)

    data = remove_http(data)
    if ":" in data:
        ip_addr, port = data.split(":")
        return ip_addr, _return_port(port)
    return "0.0.0.0", _return_port(data)


def main():

    banner = generate_banner(
        app_name="proxy reflector",
        author="jinwoo",
        description="proxy reflector",
        font="graffiti",
        version=_version
    )
    print(banner)

    parser = get_parser()
    args, unknown = parser.parse_known_args()

    pawn.console.log(f"args = {args}")

    listen_ip_addr, listen_port = parse_ip_port(args.listen)
    forward_ip_addr, forward_port = parse_ip_port(args.forward)

    pawn.console.log(f"Listen {listen_ip_addr}:{listen_port} => Forward {forward_ip_addr}:{forward_port}")

    server = EchoWebServer(
        l_host=listen_ip_addr,
        l_port=listen_port,
        f_host=forward_ip_addr,
        f_port=forward_port,
        buffer_size=args.buffer_size,
        delay=args.delay
    )
    try:
        server.main_loop()
    except KeyboardInterrupt:
        print("Ctrl C - Stopping server")
        sys.exit(1)


if __name__ == '__main__':
    main()
