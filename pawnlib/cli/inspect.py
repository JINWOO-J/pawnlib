#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf, one_time_run
from pawnlib.typing import str2bool, StackList
from pawnlib.utils.http import CallHttp, disable_ssl_warnings,HttpInspect, CheckSSL, parse_auth, parse_headers, append_scheme
from pawnlib.input import ColoredHelpFormatter
from pawnlib.input.prompt import CustomArgumentParser
from urllib.parse import urlparse
from pawnlib.utils.operate_handler import Spinner

import os
import json
import sys
from typing import Set, Optional

COMMANDS = {"dns", "http", "ssl", "all"}
ROOT_COMMANDS = {"inspect"}
SCRIPT_NAME = "pawns inspect"

__description__ = 'This is a tool to inspect the URL.'

__epilog__ = f"""
Examples:
  Basic URL inspection (default: all)
    {SCRIPT_NAME} https://example.com

  DNS record inspection only
    {SCRIPT_NAME} dns https://example.com

  SSL certificate check only
    {SCRIPT_NAME} ssl https://example.com

  HTTP request inspection only
    {SCRIPT_NAME} http https://example.com

  Verbose HTTP inspection
    {SCRIPT_NAME} http https://example.com -v

  POST request with headers and JSON body
    {SCRIPT_NAME} http https://example.com -m POST \\
        --headers '{{"Content-Type": "application/json"}}' \\
        --data '{{"param": "value"}}'

"""


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


def get_parser():

    parser = CustomArgumentParser(
        description='inspect',
        epilog=__epilog__,
        formatter_class=ColoredHelpFormatter, 
        add_help=False
    )
    parser = get_arguments(parser)
    return parser


def preprocess_argv(argv: list[str]) -> list[str]:
    if not argv:
        return argv

    if argv[0] in ROOT_COMMANDS:
        if len(argv) == 1:
            return [argv[0], "all"]

        if argv[1] not in COMMANDS and not argv[1].startswith("-"):
            return [argv[0], "all", *argv[1:]]

        return argv

    if argv[0] not in COMMANDS and not argv[0].startswith("-"):
        return ["all", *argv]

    return argv


def add_common_arguments(parser):
    """Add common arguments to both SSH and Wallet parsers."""
    parser.add_argument('url', help='URL to be checked', type=str, nargs='?', default="")
    
    parser.add_argument('--auth', help="Authentication (e.g., 'username:password' or 'token')")
    parser.add_argument('--full-body', action='store_true', help="Display full response body")
    parser.add_argument('--output', help="Save response to a file")
    parser.add_argument('--secure', action='store_true', help="Enable SSL verification")
    
    parser.add_argument('-v', '--verbose', action='count', help='Enables verbose mode. Higher values increase verbosity level. Default is 1.', default=1)

    parser.add_argument('-q', '--quiet', action='count', help='Enables quiet mode. Suppresses all messages. Default is 0.', default=0)
    parser.add_argument('-i', '--interval', type=float, help='Interval time in seconds between checks. Default is 1 second.', default=1)
    parser.add_argument('-m', '--method', type=lambda s: s.upper(), help='HTTP method to use (e.g., GET, POST). Default is "GET".', default="GET")
    parser.add_argument('-t', '--timeout', type=float, help='Timeout in seconds for each HTTP request. Default is 10 seconds.', default=10)
    parser.add_argument('-b', '--base-dir', type=str, help='Base directory for httping operations. Default is the current working directory.', default=os.getcwd())

    parser.add_argument('--ignore-ssl', type=str2bool, help='Ignores SSL certificate validation if set to True. Default is True.', default=True)
    parser.add_argument('-d', '--data', type=json.loads, help="Data to be sent in the HTTP request body. Expected in JSON format. Default is an empty dictionary.", default={})
    parser.add_argument('--headers', type=json.loads, help="HTTP headers to be sent with the request. Expected in JSON format. Default is an empty dictionary.", default={})
    parser.add_argument('--sni', type=str, help="SNI hostname to be used for the SSL handshake. Default is the hostname of the URL.", default="")    
    parser.add_argument('--dry-run', action='store_true', help="Executes a dry run without making actual HTTP requests. Default is False.", default=False)
    parser.add_argument('-l', '--max-response-length', type=int, help="Maximum length of the response text to display. Default is 700.", default=300)
    parser.add_argument('--dns','--dns-server', type=str, help="DNS server to use. Default is None.", default=None)


    return parser

def get_arguments(parser):
    # Code to set the default option to "all"
    argv = preprocess_argv(sys.argv[1:])
    sys.argv = [sys.argv[0]] + argv

    common_parser = CustomArgumentParser(add_help=False)
    add_common_arguments(common_parser)

    subparsers = parser.add_subparsers(dest='command', help='Sub-commands')
    subparsers.add_parser('dns', parents=[common_parser], help='Inspect the DNS records')
    subparsers.add_parser('http', parents=[common_parser], help='Inspect the HTTP request')
    subparsers.add_parser('ssl', parents=[common_parser], help='Inspect the SSL certificate')
    subparsers.add_parser('all', parents=[common_parser], help='Inspect all')
    return parser


def handle_inspect(args) -> int:
    """
    Run DNS / HTTP / SSL inspections based on `args.command`.
    Returns UNIX‑style exit code (0 = success).
    """

    EXIT_OK          = 0
    EXIT_DNS_FAIL    = 10
    EXIT_HTTP_FAIL   = 11
    EXIT_SSL_FAIL    = 12

    if args.command in ("dns", "http", "ssl"):
        needs: Set[str] = {args.command}
    else:
        needs = {"dns", "http", "ssl"}

    domain  = urlparse(args.url).netloc or urlparse(args.url).path
    auth    = parse_auth(args.auth)       if args.auth   else None
    headers = parse_headers(args.headers) if args.headers else {}
    client: Optional[HttpInspect] = None

    
    sni_hostname = args.sni or headers.get("Host") or domain
    
    if "Host" not in headers:
        headers["Host"] = sni_hostname

    pawn.console.log(f"needs={needs}")

    if needs & {"dns", "http"}:    
        client = HttpInspect(
            url     = args.url,
            method  = args.method,
            headers = headers,
            auth    = auth,
            verify  = not args.ignore_ssl,
            data    = args.data,                
            max_response_length = args.max_response_length,
            timeout = args.timeout,
            output  = args.output,
            dns_server = args.dns,
            debug = args.verbose > 2,
        )
        if not client.get_ip_address():
            return EXIT_DNS_FAIL

        if "dns" in needs:
            with pawn.console.status("[bold cyan]Resolving domain and fetching DNS records..."):
                pawn.console.log("[cyan]🔍 Displaying DNS records...")                
                client.display_dns_records()

    if "ssl" in needs:
        if not args.url.startswith('https://'):
            pawn.console.log("[yellow]⚠️  SSL check is not supported for HTTPS URLs.")
        else:
            with pawn.console.status("[bold cyan]Checking SSL certificate..."):
                try:
                    CheckSSL(domain, timeout=args.timeout, sni_hostname=sni_hostname).display()
                except Exception as exc:
                    pawn.console.log(f"[red]❌ SSL check failed: {exc}")
                    return EXIT_SSL_FAIL

    if "http" in needs:
        if args.dry_run:
            pawn.console.log("[yellow]⚠️ Dry-run enabled. Skipping HTTP request.")
        else:
            with pawn.console.status("[bold cyan]Making HTTP request..."):
                if not client.make_http_request():
                    return EXIT_HTTP_FAIL

            pawn.console.log("[green]✅ HTTP request completed. Displaying results...")
            client.display_results()

    return EXIT_OK


def main():
    app_name = 'httping'
    parser = get_parser()
    args, unknown = parser.parse_known_args()
    pawn.console.debug(f"args={args}, unknown={unknown}")
    

    is_hide_line_number = args.verbose > 1
    stdout = not args.quiet

    pawn.set(
        PAWN_PATH=args.base_dir,
        PAWN_LOGGER=dict(            
            log_path=f"{args.base_dir}/logs",
            stdout=stdout,
            use_hook_exception=True,
            show_path=False, #hide line numbers
        ),
        PAWN_CONSOLE=dict(
            redirect=True,
            record=True,
            log_path=is_hide_line_number, # hide line number on the right side
        ),
        args_parser=parser,
        app_name=app_name,
        args=args,
        try_pass=False,
        last_execute_point=0,
        data={
            "response_time": StackList(),
        },
        fail_count=0,
        total_count=0,
        default_config={},

    )
    if args.verbose > 2:
        pawn.set(
            PAWN_LOGGER=dict(
                log_level="DEBUG",
                stdout_level="DEBUG",
            )
        )

    print_banner()
    pawn.console.log(f"args={args}")

    if not args.url:
        parser.print_help()
        sys.exit(2)

    if args.ignore_ssl:                
        disable_ssl_warnings()

    handle_inspect(args)


main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        pawn.console.log(e)

