#!/usr/bin/env python3
import socket
import select
import time
import sys
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import remove_http, ALLOWS_HTTP_METHOD
from pawnlib.typing import str2bool, is_int, is_valid_ipv4, detect_encoding
from collections import OrderedDict
import re
import ssl

__description__ = "A Proxy Reflector Tool"
__epilog__ = (
    "This script acts as a proxy reflector, forwarding traffic between a listening address and a forwarding address.\n\n"
    "Usage examples:\n"
    "  1. To start proxying with default settings (listening on 0.0.0.0:8080):\n\n"
    "     - This forwards traffic from the default listening address to the specified forward address.\n\n"
    "     `pawns proxy --forward ip_address:port`\n"
    "  2. To specify a listening address and port:\n\n"
    "     - Listens on 127.0.0.1:9090 and forwards traffic to the specified forward address.\n\n"
    "     `pawns proxy --listen 127.0.0.1:9090 --forward ip_address:port`\n"
    "  3. To adjust buffer size and delay for socket operations:\n\n"
    "     - Uses a buffer size of 5120 bytes and a delay of 0.001 seconds for socket operations.\n\n"
    "     `pawns proxy --listen ip_address:port --forward ip_address:port --buffer-size 5120 --delay 0.001`\n"
    "  4. To set a timeout for the proxy connections:\n"
    "     - Sets a timeout of 5 seconds for the proxy connections.\n\n"
    "     `pawns proxy --listen ip_address:port --forward ip_address:port --timeout 5`\n\n"
    "For more detailed information on command options, use the -h or --help flag."
)


def get_parser():
    parser = argparse.ArgumentParser(description='Proxy Reflector')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument("--listen", "-l", type=str, help="Listen  ip_address:port", default="0.0.0.0:8080")
    parser.add_argument("--forward", "-f", type=str, help="Forward ip_address:port", default=None, required=True)
    parser.add_argument("--buffer-size", type=int, help="buffer size for socket", default=4096)
    parser.add_argument("--delay", type=float, help="buffer delay for socket", default=0.0001)
    parser.add_argument("--timeout", '-t', type=float, help="timeout for socket", default=3)
    return parser


class Forward:
    def __init__(self):
        self._forwarder = None
        self._secure_forwarder = None

    def start(self, host, port, is_ssl=False, hostname="", timeout=10):
        self._forwarder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._forwarder.connect((host, port))
            self._forwarder.settimeout(timeout)

            if is_ssl:
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                self._secure_forwarder = context.wrap_socket(self._forwarder, server_hostname=hostname)
                return self._secure_forwarder

            return self._forwarder

        except Exception as e:
            pawn.console.log(f"[red][Forward ERROR] Connect to {host}:{port} {e}")
            return False


class EchoWebServer:
    input_list = []
    channel = {}

    def __init__(self, listen, forward, buffer_size, delay):
        self.data = None
        self.s = None

        self.listen = listen
        self.forward = forward

        self.l_host = None
        self.l_port = None
        self.f_host = None
        self.f_port = None

        self.is_ssl = False

        self.buffer_size = buffer_size
        self.delay = delay

        self._parse_ip_port()
        self._validate()
        self._listen_server()

        self._http_headers = {}
        self._ongoing_response = True

        self._request = {}

    def _parse_ip_port(self):
        _parsed_listen = parse_ip_port(self.listen)
        self.l_host = _parsed_listen.get('ip_or_domain')
        self.l_port = _parsed_listen.get('port')
        _parsed_forward = parse_ip_port(self.forward)
        self.f_host = _parsed_forward.get('ip_or_domain')
        self.f_port = _parsed_forward.get('port')
        self.f_hostname = _parsed_forward.get('hostname', '')
        self.is_ssl = _parsed_forward.get('is_ssl', '')
        pawn.console.debug(f"forward={_parsed_forward}")
        pawn.console.log(f"Listen {self.l_host}:{self.l_port} => Forward {self.f_hostname}({self.f_host}:{self.f_port})")

    def _listen_server(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((self.l_host, self.l_port))
            self.server.listen(200)
            pawn.console.log(f"Server started on {self.l_host}:{self.l_port}")
        except Exception as e:
            pawn.console.log(f"Error starting server: {e}")
            raise

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
                    pawn.console.log(f"[red bold] {e} data={self.data}")
                if len(self.data) == 0:
                    self.on_close()
                    break
                else:
                    self.on_recv()

    def _parse_headers(self):
        self._http_headers = {}
        lines = self._decode_data()
        if lines and "\r\n" in lines:
            lines_arr = lines.split('\r\n')
            if len(lines_arr) >= 1:
                for line in lines_arr[1:]:
                    if line and ":" in line:
                        header_kv = line.split(":")
                        header_key = header_kv[0]
                        header_value = header_kv[1]
                        self._http_headers[header_key.strip()] = header_value.strip()

    def _decode_data(self, default_encode="utf8"):
        lines = ""
        try:
            encoding = detect_encoding(self.data, default_encode=default_encode)
            pawn.console.debug(f"encoding={encoding}")
            lines = self.data.decode(encoding, "ignore")
        except Exception as e:
            pawn.console.log(f"[red] [Exception] {e} data={self.data}")

        return lines

    def _get_decoded_data_lines(self, delimiter="\r\n") -> list:
        lines = self._decode_data()
        data_arr = lines.split(delimiter)
        return data_arr

    def _inject_headers(self, headers={}):
        self._parse_headers()
        lines = self._decode_data()
        # if lines and self.f_hostname and self._http_headers.get('Host'):
        if lines and self.f_hostname and self._http_headers.get('Host'):

            request_line, _headers = lines.split('\r\n', 1)
            if not request_line.startswith('HTTP'):
                pawn.console.log("START injection")
                headers_list =_headers.split('\r\n')[:-2]  # exclude the last two elements as they are empty
                headers_dict = OrderedDict((header.split(':')[0], ':'.join(header.split(':')[1:]).strip()) for header in headers_list)

                for header_k, header_v in headers.items():
                    if header_k and header_v:
                        headers_dict[header_k] = header_v
                headers_string = '\r\n'.join(f'{k}: {v}' for k, v in headers_dict.items())
                # Add the request line and the final two '\r\n' back in
                headers = f'{request_line}\r\n{headers_string}\r\n\r\n'
                self.data = headers.encode()

    def _parse_response(self):
        pawn.console.log(f"raw_data = {self.data}")
        lines = self._decode_data()
        pawn.console.log(f"lines={lines}")
        if lines:
            _request_line, _headers_body = lines.split('\r\n', 1)
            _headers, _body = _headers_body.split('\r\n\r\n')
            pawn.console.log(f"request_line={_request_line}")
            pawn.console.log(f"headers={_headers}")
            pawn.console.log(f"body={_body}")

    def parse_http_request(self):
        headers = {}
        # Split the request into lines
        request = self._decode_data()
        lines, body = request.split("\r\n\r\n")
        _headers = lines.split('\r\n')
        if _headers:
            self._request = {}
            # The first line contains the request method, path, and protocol version
            method, path, protocol = _headers[0].split(' ')
            # Parse the headers
            for header in _headers[1:]:
                if header and ": " in header:
                    key, value = header.split(': ')
                    if key and value:
                        headers[key.strip()] = value.strip()

            self._request = {
                'method': method,
                'path': path,
                'protocol': protocol,
                'headers': headers,
                'body': body
            }

    def parse_http_response(self):
        pawn.console.log(self.data)

    def convert_to_request_raw(self):
        _raw = ""
        if self._request:
            _raw = f"{self._request.get('method')} {self._request.get('path')} {self._request.get('protocol')}\r\n"
            if self._request.get('headers'):
                for k, v in self._request['headers'].items():
                    _raw += f"{k}: {v}\r\n"
            _raw += f"\r\n{self._request.get('body')}"
        self.data = _raw.encode()

    def modify_http_request_headers(self, headers={}):
        if self._request and self._request.get('headers') and headers:
            for k, v in headers.items():
                self._request['headers'][k] = v
                pawn.console.debug(f"[yellow] modified header => {k}: {v}")
            self.convert_to_request_raw()

    def on_accept(self):
        try:
            forward = Forward().start(self.f_host, self.f_port, is_ssl=self.is_ssl, hostname=self.f_hostname)
            pawn.console.log(f"[bold red]on_accept [/bold red] forward={forward}")
            clientsock, client_addr = self.server.accept()
            client_ip, client_port = client_addr
            if forward:
                pawn.console.rule(f"{client_ip}:{client_port} has connected", style="spring_green2", align="left")

                self.input_list.append(clientsock)
                self.input_list.append(forward)
                self.channel[clientsock] = forward
                self.channel[forward] = clientsock
            else:
                pawn.console.log(f"Can't establish connection with remote server. "
                                 f"Closing connection with client side: {client_ip}:{client_port}")
                clientsock.close()
        except Exception as e:
            pawn.console.log(f"Error handling connection: {e}")
            raise

    def on_close(self):
        try:
            self._ongoing_response = False
            # pawn.console.log(f"{self._return_ip_port(self.s.getpeername())}", "has disconnected")
            pawn.console.rule(f"{self._return_ip_port(self.s.getpeername())} has disconnected", style="spring_green2", align="right")

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
        except Exception as e:
            pawn.console.log(f"Error closing connection: {e}")
            raise

    @staticmethod
    def _is_http_method(data):
        for method in ALLOWS_HTTP_METHOD:
            if data.startswith(method.upper()):
                return True
        return False

    def on_recv(self):
        lines = self._decode_data()
        if lines and "\r\n" in lines:
            data_arr = self._get_decoded_data_lines()

            if data_arr and data_arr[0].startswith("HTTP"):
                if self.f_hostname:
                    _forward_host = f"{self.f_hostname}({self.f_host})"
                else:
                    _forward_host = f"{self.f_host}"
                pawn.console.log(f"[bold blue]Response from {_forward_host}:{self.f_port}")
                pawn.console.rule(f"[bold blue] ", align="right")

            elif data_arr and self._is_http_method(data_arr[0]):
                pawn.console.log(f"[bold blue]Request from {self.l_host}:{self.l_port}")
                pawn.console.debug(f"[green] request-> {self.data}")
                self.parse_http_request()
                self.modify_http_request_headers(headers={'Host': self.f_hostname})
                pawn.console.debug(f"[bold blue] {self.data}")
                data_arr = self._get_decoded_data_lines()

            elif self._ongoing_response:
                pawn.console.log(f"[green] request-> {self.data}")
                pawn.console.log(f"[bold blue]Request from {self.l_host}:{self.l_port}")
                pawn.console.rule(f"[bold blue] ", align="right")
                self._ongoing_response = False

            for line in data_arr:
                pawn.console.print(line)

        self.channel[self.s].send(self.data)

    @staticmethod
    def _return_ip_port(data):
        if data and len(data) > 1:
            return "{}:{}".format(*data)


def resolve_domain_to_ip(domain):
    try:
        ip = socket.gethostbyname(domain)
        return ip
    except socket.gaierror:
        return None


def is_valid_ip(ip):
    # Regular expression pattern for IP address validation
    pattern = r'^((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))$'

    # Match IP address using regex
    match = re.match(pattern, ip)
    return match is not None


def parse_ip_port(input_str):
    # Regular expression pattern to match IP address, domain name, and port
    pattern = r'(?:(?:http|https)://)?(?:([\w_-]+(?:\.[\w_-]+)*|\d{1,3}(?:\.\d{1,3}){3}))(?::(\d+))?(?:/|$)'
    match = re.search(pattern, input_str)

    if match:
        ip_or_domain = match.group(1)
        port = match.group(2)

        return dict(
            ip_or_domain=resolve_domain_to_ip(ip_or_domain),
            port=int(port) if port else 443 if 'https' in input_str else 80,
            hostname=ip_or_domain if not is_valid_ip(ip_or_domain) else "",
            is_ssl=True if input_str.startswith("https://") else False
        )
    return {}


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

    if not args.forward:
        parser.error("forward not found")


    pawn.console.log(f"args = {args}")

    server = EchoWebServer(
        listen=args.listen,
        forward=args.forward,
        buffer_size=args.buffer_size,
        delay=args.delay,
    )
    try:
        server.main_loop()
    except KeyboardInterrupt:
        print("Ctrl C - Stopping server")
        sys.exit(1)


main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':
    main()

