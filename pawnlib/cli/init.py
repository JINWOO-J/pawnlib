from pawnlib.config import pawnlib_config as pawn
from pawnlib.builder.generator import AppGenerator, generate_banner
from pawnlib.__version__ import __version__ as _version
import argparse

from rich.console import Console
from rich.syntax import Syntax


__description_shorten__ = "Advanced Python application builder"
__description__ = f"{__description_shorten__}: \nEasily initialize your Python development environment with customizable templates and best practices."
__epilog__ = (
    "This script provides advanced features for building Python applications. \n\n"
    "The script will generate a new application with default settings and print the generated code to the console.\n"
    "Make sure to adjust the generated code according to your project's needs.\n\n"
    "Usage examples:\n"
    "  1. Initialize a new Python application with default settings:\n\n"
    f"     `$ pawns init`\n\n"    
    "For more details on available commands and options, use the `-h` or `--help` flag.\n"
    "For additional support and documentation, visit the project repository or consult the documentation."
)

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
        description=__description_shorten__,
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


main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pawn.console.log("[red] KeyboardInterrupt")
