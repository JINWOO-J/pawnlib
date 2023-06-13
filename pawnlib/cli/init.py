from pawnlib.config import pawnlib_config as pawn
from pawnlib.builder.generator import AppGenerator, generate_banner
from pawnlib.__version__ import __version__ as _version
import argparse

from rich.console import Console
from rich.syntax import Syntax

__description__ = "Python app builder with a template."


def get_parser():
    parser = argparse.ArgumentParser(description=__description__)
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument('--command', help='command', nargs='?', choices=["init"], default="init")
    return parser


def main():
    banner = generate_banner(
        app_name="builder",
        author="jinwoo",
        description="Initialize Python Development Environment",
        font="graffiti",
        version=_version
    )
    print(banner)

    parser = get_parser()
    args, unknown = parser.parse_known_args()

    if args.command == "init":
        generated_file = AppGenerator(app_name="default_app").run()
        console = Console()
        print("Successful file generation")
        with open(generated_file, "rt") as code_file:
            syntax = Syntax(code_file.read(), "python")
        console.print(syntax)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pawn.console.log("[red] KeyboardInterrupt")
