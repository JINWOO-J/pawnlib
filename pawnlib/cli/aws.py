#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn
from pawnlib.output import write_json, syntax_highlight, PrintRichTable
from pawnlib.typing.converter import FlatDict, FlatterDict, flatten_dict

from pawnlib.resource import server

__description__ = 'Get meta information from AWS EC2.'

__epilog__ = (
    "This script retrieves metadata from AWS EC2 instances.\n\n"
    "Usage examples:\n"
    "  1. Retrieve AWS metadata in JSON format:\n"
    "     - Retrieves metadata from the specified IP address (default: 169.254.169.254) and prints it in JSON format.\n\n"    
    "     `pawns aws --metadata-ip 169.254.169.254 --output-format json`\n\n"
    
    "  2. Retrieve AWS metadata in flattened format:\n"
    "     - Retrieves metadata and prints it in a flattened format.\n\n"
    "     `pawns aws --output-format flat`\n\n"
    
    "  3. Specify a custom timeout for the request:\n"
    "     - Sets the timeout for the request to 5 seconds.\n\n"
    "     `pawns aws --timeout 5`\n\n"
    
    "  4. Write AWS metadata to a file:\n"
    "     - Writes the retrieved metadata to a file named 'metadata.json'.\n\n"
    
    "     `pawns aws --output-file metadata.json`\n\n"


    "For more information and options, use the -h or --help flag."
)


def get_parser():
    # pandoc:exclude
    parser = argparse.ArgumentParser(description='AWS', epilog=__epilog__)
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument(
        "--metadata-ip", "-i", type=str,
        help="The IP address for retrieving metadata. Default is 169.254.169.254.",
        default="169.254.169.254"
    )
    parser.add_argument(
        "--timeout", "-t", type=float,
        help="The timeout in seconds for the request. Default is 2 seconds.",
        default=2,
    )
    parser.add_argument(
        "--output-file", "-o", type=str,
        help="The name of the file to write the output to.",
        default="",
    )
    parser.add_argument(
        "--output-format", "-f", type=str, choices=["json", "flat"],
        help="The format of the output. Choose between 'json' or 'flat'. Default is 'json'.",
        default="json"
    )
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

    res = server.get_aws_metadata(meta_ip=args.metadata_ip, timeout=args.timeout)
    if args.output_format == "json":
        print(syntax_highlight(res))
    elif args.output_format == "flat":
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

    if args.output_file:
        write_res = write_json(filename=args.write_filename, data=res)
        pawn.console.log(write_res)

main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
    )

if __name__ == '__main__':
    main()
