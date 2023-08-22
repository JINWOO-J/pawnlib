#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn
from pawnlib.output import write_json, syntax_highlight, PrintRichTable
from pawnlib.typing.converter import FlatDict, FlatterDict, flatten_dict

from pawnlib.resource import server

__description__ = 'Get meta information from AWS EC2.'


def get_parser():
    parser = argparse.ArgumentParser(description='AWS')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument("--meta-ip", "-i", type=str, help="IP address for retrieving Metadata", default="169.254.169.254")
    parser.add_argument("--timeout", '-t', type=float, help="timeout for request", default=2)
    parser.add_argument("--write-filename", '-w', type=str, help="write filename", default="")
    parser.add_argument("--print-type", '-p', type=str, help="print type", choices=["json", "flat"], default="json")


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
    if args.print_type == "json":
        print(syntax_highlight(res))
    elif args.print_type == "flat":
        PrintRichTable(
            title="AWS Metadata",
            data=flatten_dict(res),
            columns_options=dict(
                value=dict(
                    justify="left",
                )
            )
        )

    # PrintRichTable(title="AWS Metadata", data=flatten_dict(res))

    if args.write_filename:
        write_res = write_json(filename=args.write_filename, data=res)
        pawn.console.log(write_res)


if __name__ == '__main__':
    main()
