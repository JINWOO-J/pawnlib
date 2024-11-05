# -*- coding: utf-8 -*-
import sys
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.output import color_print, get_script_path
from pawnlib.config import pawn
from pawnlib.utils import http
from pawnlib.typing import date_utils, str2bool
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter
from urllib.parse import urlparse

__version__ = "0.0.1"
__description__ = "Connect to the Goloop network with WebSocket to receive blocks."
__epilog__ = (
    "This script allows you to connect to the Goloop network via WebSocket and receive real-time block information.\n\n"
    "Usage examples:\n"
    "  1. Connect to Goloop network via WebSocket:\n"
    "     - Connects to the Goloop network via WebSocket using the specified URL.\n\n"
    "     `pawns websocket http://example.com/ws`\n"

    "  2. Specify the starting block height:\n"
    "     - Specifies the starting block height as 1000.\n\n"
    "     `pawns websocket https://example.com/ws -b 1000`\n"

    "  3. Adjust verbosity level:\n"
    "     - Increases verbosity level for more detailed output.\n\n"
    "     `pawns websocket http://example.com/ws -v`\n\n"

    "For more information and options, use the -h or --help flag."
)


def get_parser():
    parser = CustomArgumentParser(description='Websocket', formatter_class=ColoredHelpFormatter, epilog=__epilog__)
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument('url', help='URL for websocket connection', nargs='?')
    parser.add_argument('-c', '--command', type=str, help='command', default=None, choices=["diff", "transfer", None])
    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level', default=0)
    parser.add_argument('-b', '--blockheight', type=int, help='position of blockheight to start. ', default=0)
    parser.add_argument('-d', '--diff', type=int, help='diff timestamp ', default=3)
    parser.add_argument('-t', '--target', type=str, nargs='+', help='Monitoring target (block|tx)',
                        default=["block", "tx"], choices=["block", "tx"])
    parser.add_argument('--stack-limit', type=int, help='Stack limit count for notify', default=3)
    parser.add_argument('--wait', type=str2bool, help='waiting for response', default=1)
    return parser


def main():
    banner = generate_banner(
        app_name="websocket",
        author="jinwoo",
        description="Connect to Goloop with WebSocket",
        font="graffiti",
        version=_version
    )
    print(banner)
    # pawn_http.disable_ssl_warnings()
    parser = get_parser()
    args, unknown = parser.parse_known_args()
    pawn.console.log(args)

    if not args.url:
        parser.print_help()

    args.try_pass = False
    pawn.set(
        args=args,
        try_pass=False,
        LAST_EXECUTE_POINT=0,
    )

    if not args.url:
        parser.error("The 'url' argument is required.")

    if args.verbose > 2:
        pawn.set(PAWN_DEBUG=True)

    parsed_url = urlparse(http.append_http(args.url))

    websocket_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    websocket_path = parsed_url.path or "/api/v3/icon_dex/block"

    pawn.console.log(f"Url={websocket_url}, Path={websocket_path}")

    network_info = http.NetworkInfo(network_api=websocket_url)
    pawn.console.log(network_info)

    goloop_websocket = http.GoloopWebsocket(
        url=websocket_url,
        blockheight=args.blockheight,
        monitoring_target=args.target,
        verbose=args.verbose,
        sec_thresholds=args.diff,
        network_info=network_info,
        logger=pawn.console
    )
    goloop_websocket.run(api_path=websocket_path)




main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)



if __name__ == "__main__":
    main()
