#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils import genesis
from pawnlib.utils import in_memory_zip
from pawnlib.output import is_file, print_json, open_json
from pawnlib.typing import get_size


__description__ = "Genesis Tool"

def get_parser():
    parser = argparse.ArgumentParser(description='Command Line Interface for ICX')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser=None):

    parser.add_argument(
        'command',
        help='gen, info',
        nargs="?"
    )
    parser.add_argument(
        'genesis_zip_file',
        help='genesis zip file name',
        nargs="?"
    )

    parser.add_argument('-i', '--input-genesis', metavar='genesis.json', help=f'genesis.json', default=None)
    parser.add_argument('-b', '--base-dir', metavar='base_dir', help=f'base dir', default=".")
    parser.add_argument('-o', '--output-file', metavar='output filename', help=f'output filename', default="icon_genesis.zip")
    return parser


def main():
    banner = generate_banner(
        app_name="Genesis",
        author="jinwoo",
        description="ICON utility",
        font="graffiti",
        version=_version
    )

    parser = get_parser()
    args, unknown = parser.parse_known_args()
    args.subparser_name = "gs"
    print(banner)
    pawn.console.log(f"args = {args}")

    if args.command == "gen":
        genesis_file = f"{args.base_dir}/{args.input_genesis}"
        json_dict = open_json(genesis_file)
        cid = genesis.genesis_generator(genesis_json_or_dict=json_dict, base_dir=args.base_dir, genesis_filename=args.output_file)
        pawn.console.log(f"CID = {cid}")

    elif args.command == "info" and is_file(args.genesis_zip_file):
            genesis_json = in_memory_zip.read_genesis_dict_from_zip(args.genesis_zip_file)
            print_json(genesis_json)
            cid = genesis.create_cid(genesis_json)
            nid = genesis_json.get('nid')
            pawn.console.log(f"FileName  = {args.genesis_zip_file} ({get_size(args.genesis_zip_file)})")
            pawn.console.log(f"CID       = {cid} ({int(cid, 16)})")
            pawn.console.log(f"NID       = {nid} ({int(nid, 16)})")




if __name__ == '__main__':
    main()
