#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn, pconf
from pawnlib.utils import disable_ssl_warnings

from pawnlib.resource import net

disable_ssl_warnings()
NONE_STRING = "__NOT_DEFINED_VALUE__"
PLATFORM_LIST = ["icon", "havah"]


def get_parser():
    parser = argparse.ArgumentParser(description='RPC')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument(
        'command',
        help='check',
        nargs='?'
    )
    parser.add_argument('-d', '--debug', action='store_true', help='debug mode. True/False')
    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level', default=0)
    return parser


def print_banner():
    banner = generate_banner(
        app_name="NET",
        author=f"jinwoo",
        description="Network checker",
        font="graffiti",
        version=_version
    )
    print(banner)


def initialize_arguments():
    parser = get_parser()
    args, unknown = parser.parse_known_args()
    args.subparser_name = "net"
    pawn.set(
        PAWN_DEBUG=args.debug,
        data=dict(
            args=args
        )
    )
    print_banner()
    return args


def main():
    args = initialize_arguments()
    disable_ssl_warnings()

    ff_region = net.FindFastestRegion(verbose=args.verbose)
    ff_region.run()
    ff_region.print_results()


if __name__ == '__main__':
    main()
