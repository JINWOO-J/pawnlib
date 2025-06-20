#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn, pconf
from pawnlib.typing.check import sys_exit
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter
from pawnlib.docker.compose import DockerComposeBuilder

__description__ = 'An interactive Docker Compose builder for creating and managing services.'
__epilog__ = (
    "This tool helps to build a Docker Compose file interactively. You can add multiple services, configure ports, "
    "environment variables, and volumes.\n\n"
    "Usage examples:\n"
    "  1. Create a Docker Compose file:\n"
    "     - This will start the interactive wizard to create a docker-compose.yml file.\n\n"
    "     `pawns compose  init` \n"


)

VALID_COMMANDS = ["init"]

def non_empty_validator(value):
    if value.strip() == "":
        raise ValueError("Input cannot be empty")
    return value.strip()


def get_parser():
    parser = CustomArgumentParser(
        description='Docker Compose File Creation Wizard',
        formatter_class=ColoredHelpFormatter,
        epilog=__epilog__
    )

    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument(
        'command',
        help=f'Command to execute ({", ".join(VALID_COMMANDS)})',
        type=str,
        choices=VALID_COMMANDS,
        nargs='?',  # Make this optional if you want to provide a default
        default="init"  # Or set a default command if appropriate
    )
    parser.add_argument('-d', '--directory', type=str,  help='Path to the directory to upload or download')
    parser.add_argument('-f', '--compose-file', type=str,  help='docker-compose file name', default="docker-compose.yml")
    return parser


def main():
    banner = generate_banner(
        app_name="compose builder",
        author="jinwoo",
        description="Docker Compose File Creation Wizard",
        font="graffiti",
        version=_version
    )
    print(banner)

    parser = get_parser()
    args, unknown = parser.parse_known_args()

    pawn.console.log(f"args = {args}")

    if not args.command:
        parser.print_help()
        sys_exit(f"\nError: A valid command is required. Please choose from ({', '.join(VALID_COMMANDS)}).\n")

    builder = DockerComposeBuilder(compose_file=args.compose_file)

    if args.command == "init":
        builder.create_docker_compose()
        builder.save_docker_compose()

main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':
    main()
