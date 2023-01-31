#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn
from pawnlib.output import write_json
from pawnlib.resource import server


def get_parser():
    parser = argparse.ArgumentParser(description='AWS')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument("--meta-ip", "-i", type=str, help="IP address for retrieving Metadata", default="169.254.169.254")
    parser.add_argument("--timeout", '-t', type=float, help="timeout for request", default=2)
    parser.add_argument("--write-filename", '-w', type=str, help="write filename", default="")

    return parser


def main():
    banner = generate_banner(
        app_name="aws metadata",
        author="jinwoo",
        description="get the aws metadata",
        font="graffiti",
        version=_version
    )
    print(banner)

    parser = get_parser()
    args, unknown = parser.parse_known_args()

    pawn.console.log(f"args = {args}")

    res = server.get_aws_metadata(meta_ip=args.meta_ip, timeout=args.timeout)
    pawn.console.log(res)

    if args.write_filename:
        write_json(filename=args.write_filename, data=res)


if __name__ == '__main__':
    main()
