#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn
from pawnlib.output import write_json
from pawnlib.resource import server
import pyfiglet

__description__ = 'Command to test the banner.'
__epilog__ = (
    "This script generates text banners using various fonts.\n\n"
    
    "Usage examples:\n"
    
    "    1. Generate a banner with default font:\n"
    "        `$ pawns banner --text \"Hello World\"`\n\n"
    "    2. List all available fonts and generate banners:\n"
    "        `$ pawns banner --text \"Sample Text\"`\n\n"
    
    "For more information, visit the project repository or consult the documentation."
)

def get_parser():
    parser = argparse.ArgumentParser(description='BANNER')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument("--text",  type=str, help="IP address for retrieving Metadata", default="defaul text")
    return parser


def main():
    banner = generate_banner(
        app_name="banner",
        author="jinwoo",
        description="get the aws metadata",
        font="graffiti",
        version=_version
    )
    print(banner)

    parser = get_parser()
    args, unknown = parser.parse_known_args()

    pawn.console.log(f"args = {args}")
    font_list = pyfiglet.FigletFont.getFonts()

    for font in font_list:
        pawn.console.print(font)
        print(generate_banner(args.text, font=font, version=font))


main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':
    main()
