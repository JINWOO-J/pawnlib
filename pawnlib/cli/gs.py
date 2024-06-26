#!/usr/bin/env python3
from pawnlib.config import pawn
from pawnlib.output import color_print

try:
    import eth_keys
except Exception as e:
    pawn.console.log("[red]Exception[/red] Required  'eth_keys' module. 'pip3 install eth_keys'")

from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version

from pawnlib.utils.genesis import genesis_generator, create_cid
from pawnlib.utils.in_memory_zip import read_genesis_dict_from_zip
from pawnlib.output import is_file, print_json, open_json
from pawnlib.typing import get_size
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter

__description__ = "Genesis Tool"
__epilog__ = (
    "Usage examples:\n"
    "1. Generate a genesis file from a genesis.json file:\n"
    "     pawns gs gen -i genesis.json -o icon_genesis.zip\n\n"
    "2. Display information about a genesis zip file: \n"
    "     pawns gs info genesis.zip\n\n"
    "\n"
    "Note: \n"
    "  The 'gen' command generates a genesis file based on a provided genesis.json file.\n"
    "  The 'info' command displays information from a given genesis.zip file.\n"
)


def get_parser():
    parser = CustomArgumentParser(
        description='Command Line Interface for Genesis',
        formatter_class=ColoredHelpFormatter,
        epilog=__epilog__
    )
    parser = get_arguments(parser)
    return parser


def get_arguments(parser=None):
    parser.add_argument(
        'command',
        help='gen, info',
        nargs="?",
        choices=['gen', 'info']
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


def print_hex_value(name, value):
    if value:
        pawn.console.log(f"{name} = {value} ({int(value, 16)})")


def get_hex_value(value):
    if value:
        return  f"{value} [bright_black]({int(value, 16)})[/bright_black]"


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

    if not args.command:
        # parser.print_help()
        parser.error("command not found")

    if args.command == "gen":
        genesis_file = f"{args.base_dir}/{args.input_genesis}"
        json_dict = open_json(genesis_file)
        cid = genesis_generator(genesis_json_or_dict=json_dict, base_dir=args.base_dir, genesis_filename=args.output_file)
        pawn.console.log(f"CID = {cid}")

    elif args.command == "info" and is_file(args.genesis_zip_file):
        genesis_json = read_genesis_dict_from_zip(args.genesis_zip_file)
        # print_json(genesis_json)

        cid = create_cid(genesis_json)
        nid = genesis_json.get('nid', "")

        color_print.print_kv("genesis_json", genesis_json)

        color_print.print_kv("FileName", f"{args.genesis_zip_file} ({get_size(args.genesis_zip_file)})")
        color_print.print_kv("cid", get_hex_value(cid))
        color_print.print_kv("nid", get_hex_value(nid))


if __name__ == '__main__':
    main()
