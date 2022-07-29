from pawnlib.builder.generator import AppGenerator, generate_banner
from pawnlib.__version__ import __version__ as _version
import argparse

from rich.console import Console
from rich.syntax import Syntax


def get_parser():
    parser = argparse.ArgumentParser(description='pawns client for goloop')
    parser.add_argument('command', help='command', choices=["init"])
    # parser.add_argument('-c', '--command', type=str, help=f'command', default=None, choices=["start", "stop", "restart", None])
    return parser


def main():
    banner = generate_banner(
        app_name="pawns",
        author="jinwoo",
        description="Initialize Python Development Environment",
        font="graffiti",
        version=_version
    )
    print(banner)

    parser = get_parser()
    args = parser.parse_args()

    if args.command == "init":
        generated_file = AppGenerator(app_name="default_app").run()
        console = Console()
        print("Successful file generation")
        with open(generated_file, "rt") as code_file:
            syntax = Syntax(code_file.read(), "python")
        console.print(syntax)


if __name__ == "__main__":
    main()

