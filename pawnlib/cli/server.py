#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf
import os
from pawnlib.typing import str2bool, StackList, remove_tags, dict_to_line
from pawnlib.output import write_json, print_grid, print_var
from rich.tree import Tree

from pawnlib.resource import DiskPerformanceTester

__description__ = "This command is used to check and verify the server’s resources."

__epilog__ = (
    "This tool is intended for checking and validating server resources.\n\n"
    "Usage examples:\n"
    "  1. Measure disk performance:\n"
    "     pawns server disk --file-path /path/to/testfile --file-size-mb 1024 --iterations 5 --block-size-kb 1024 --num-threads 1 --io-pattern sequential\n"
    "     - Measures write and read speed for a test file with specified parameters.\n\n"
    "For more detailed command usage and options, refer to the help documentation by running 'pawns server --help'."
)


def get_parser():
    parser = argparse.ArgumentParser(description='server')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument('command', help='command', type=str, nargs='?', default="")
    parser.add_argument('-c', '--config-file', type=str, help='config', default="config.ini")
    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level (default: %(default)s)', default=1)
    parser.add_argument('-q', '--quiet', action='count', help='Quiet mode. Dont show any messages. (default: %(default)s)', default=0)
    parser.add_argument('-b', '--base-dir', type=str, help='base dir for httping (default: %(default)s)', default=os.getcwd())
    parser.add_argument('--file-path', type=str, default='testfile', help='Path to the test file')
    parser.add_argument('--file-size-mb', type=int, default=1024, help='Size of the test file in MB')
    parser.add_argument('--iterations', type=int, default=5, help='Number of iterations for testing')
    parser.add_argument('--block-size-kb', type=int, default=1024, help='Block size in KB')
    parser.add_argument('-n', '--num-threads', type=int, default=1, help='Number of parallel threads')
    parser.add_argument('--io-pattern', type=str, choices=['sequential', 'random'], default='sequential', help='I/O pattern: sequential or random')
    return parser


def print_banner():
    if not pconf().args.quiet:
        banner = generate_banner(
            app_name=pconf().app_name,
            author="jinwoo",
            description=f"{__description__} \n"
                        f" - base_dir    : {pconf().args.base_dir} \n" 
                        f" - logs_dir    : {pconf().args.base_dir}/logs \n",
            font="graffiti",
            version=_version
        )
        print(banner)


def print_unless_quiet_mode(message=""):
    if not pconf().args.quiet:
        pawn.console.print(message)


def main():
    app_name = 'Server Checker'
    parser = get_parser()
    args, unknown = parser.parse_known_args()
    config_file = args.config_file

    is_hide_line_number = args.verbose > 2
    stdout = not args.quiet

    pawn.set(
        app_name=app_name,
        PAWN_CONFIG_FILE=config_file,
        PAWN_PATH=args.base_dir,
        PAWN_CONSOLE=dict(
            redirect=True,
            record=True,
            log_path=is_hide_line_number, # hide line number on the right side
        ),
        args=args,
        try_pass=False,
        last_execute_point=0,
        data={},
        fail_count=0,
        total_count=0,
    )

    if args.verbose > 2:
        pawn.set(
            PAWN_LOGGER=dict(
                log_level="DEBUG",
                stdout_level="DEBUG",
            )
        )
    print_grid(args.__dict__, title="Arguments", key_prefix="--")

    if args.command == "disk":
        tester = DiskPerformanceTester(
            file_path=args.file_path,
            file_size_mb=args.file_size_mb,
            iterations=args.iterations,
            block_size_kb=args.block_size_kb,
            num_threads=args.num_threads,
            io_pattern=args.io_pattern,
            debug=args.verbose > 1
        )
        tester.console.log(f'Measuring write and read speed for {args.file_size_mb}MB with {args.block_size_kb}KB block size, {args.iterations} iterations, {args.num_threads} threads, {args.io_pattern} I/O pattern...')
        tester.run_parallel_tests()
    else:
        parser.error(f"'{args.command}' command not found")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        pawn.console.log(e)

