#!/usr/bin/env python3
import argparse
import os
import sys
import importlib.util
import subprocess
import configparser
import requests
import json
import logging
from pawnlib.config import pawnlib_config as pawn, pconf, setup_app_logger, change_log_level, change_propagate_setting
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.typing import convert_bytes, const
from pawnlib.typing.check import sys_exit
from pawnlib.utils.aws import Uploader, Downloader, S3Lister
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter
from pawnlib.typing.defines import load_env_with_defaults
from pawnlib.output import file
from pawnlib.utils.http import append_s3

logger = setup_app_logger(simple_format="detailed", propagate_scope="pawnlib")

__description__ = 'Upload or download directories to/from AWS S3.'

__epilog__ = (
    "This script allows you to upload or download directories to/from an AWS S3 bucket using simplified commands.\n\n"
    "Usage examples:\n\n"
    "  1. Sync a local directory to S3:\n\n"
    "     `pawns s3 sync ./data s3://your-bucket/sync/data`\n\n"
    "  2. Sync from S3 to a local directory:\n\n"
    "     `pawns s3 sync s3://your-bucket/sync/data ./data`\n\n"
    "  3. Copy a file or directory:\n\n"
    "     `pawns s3 cp ./file.txt s3://your-bucket/path/file.txt`\n\n"
    "     `pawns s3 cp s3://your-bucket/path/file.txt ./file.txt`\n\n"
    "  4. List objects in an S3 bucket:\n\n"
    "     `pawns s3 ls s3://your-bucket/path/`\n\n"
    "  5. Remove objects from an S3 bucket:\n\n"
    "     `pawns s3 rm s3://your-bucket/path/ --recursive`\n\n"
    "Note:\n\n"
    "  - Use the --help flag for a full list of options and their descriptions.\n\n"
)

VALID_COMMANDS = ["sync", "cp", "ls", "rm", "info"]


def get_parser():
    parser = CustomArgumentParser(
        description='AWS S3 Utility',
        formatter_class=ColoredHelpFormatter,
        epilog=__epilog__
    )
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument('--profile', type=str, help='AWS CLI profile name')
    parser.add_argument('--max-workers', type=int, help='Max workers', default=10)
    parser.add_argument('-v', '--verbose', action='count', help='Verbose mode', default=1)
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode. Overrides verbosity to 0.')
    parser.add_argument('--config-file', type=str, default="config.ini", help="Path to the configuration file")

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Sub-commands')

    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Synchronize directories')
    sync_parser.add_argument('source', type=str, help='Source path (local or S3)')
    sync_parser.add_argument('destination', type=str, help='Destination path (local or S3)')
    sync_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files')
    sync_parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    sync_parser.add_argument('--delete', action='store_true', help='Delete files not in source')
    sync_parser.add_argument('--recursive', action='store_true', help='Recursive copy (default for directories)')

    # Copy command
    cp_parser = subparsers.add_parser('cp', help='Copy files or directories')
    cp_parser.add_argument('source', type=str, help='Source path (local or S3)')
    cp_parser.add_argument('destination', type=str, help='Destination path (local or S3)')
    cp_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files')
    cp_parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    cp_parser.add_argument('--recursive', action='store_true', help='Recursive copy (default for directories)')

    # List command
    ls_parser = subparsers.add_parser('ls', help='List S3 bucket or prefix')
    ls_parser.add_argument('path', type=str, help='S3 path to list', nargs='?')
    ls_parser.add_argument('--recursive', action='store_true', help='List recursively')
    ls_parser.add_argument('--include-size', action='store_true', help='Include size in the output')
    # Remove command
    rm_parser = subparsers.add_parser('rm', help='Remove objects from S3')
    rm_parser.add_argument('path', type=str, help='S3 path to remove')
    rm_parser.add_argument('--recursive', action='store_true', help='Remove recursively')
    rm_parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    rm_parser.add_argument('--pattern', type=str, help='Pattern to match objects')

    # Info command
    info_parser = subparsers.add_parser('info', help='Show S3 bucket info')

    return parser

def parse_s3_path(path):
    if path.startswith('s3://'):
        bucket, key = path[5:].split('/', 1) if '/' in path[5:] else (path[5:], '')
        return bucket, key.lstrip('/')  # Remove leading slash from key
    return None, path.lstrip('/')  # Remove leading slash from local path


def load_config(config_file="config.ini"):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config["DEFAULT"] if "DEFAULT" in config else {}


def apply_config_defaults(args, config):
    """Apply defaults from config.ini, overridden by command-line args."""
    for key, value in vars(args).items():
        if not value and key in config:
            setattr(args, key, config[key])


def main():
    banner = generate_banner(
        app_name="AWS S3 Utility",
        author="jinwoo",
        description="Upload or download directories to/from AWS S3",
        font="graffiti",
        version=_version
    )
    print(banner)

    load_env_with_defaults(force_reload=True)

    parser = get_parser()
    args = parser.parse_args()

    pawn.console.log(args)

    if args.quiet:
        args.verbose = 0

    if args.verbose > 2:
        change_propagate_setting(propagate=True, propagate_scope="all")

    config = load_config(args.config_file)
    apply_config_defaults(args, config)
    # pawn.console.log(f"args = {args}")

    if not args.command:
        parser.print_help()
        sys_exit(f"\nError: A valid command is required. Please choose from ({', '.join(VALID_COMMANDS)}).\n")

    log_level = const.get_level_name(args.verbose)
    change_log_level(log_level)
    logger.info(f"Start Log Level={log_level}")

    if args.command == 'sync' or args.command == 'cp':
        source_bucket, source_key = parse_s3_path(args.source)
        dest_bucket, dest_key = parse_s3_path(args.destination)

        if dest_key == ".":
            dest_key = os.path.basename(source_key)

        pawn.console.log(f"source_bucket={source_bucket}, source_key={source_key}")
        pawn.console.log(f"dest_bucket={dest_bucket}, dest_key={dest_key}")

        # Determine operation type
        if source_bucket and not dest_bucket:
            operation = 'download'
        elif not source_bucket and dest_bucket:
            operation = 'upload'
        else:
            sys_exit("Both source and destination cannot be S3 paths or local paths.")

        if operation == 'upload':
            uploader = Uploader(
                profile_name=args.profile,
                bucket_name=dest_bucket,
                overwrite=args.overwrite,
                confirm_upload=False,
                keep_path=False,
                use_dynamic_config=False,
                dry_run=args.dry_run,
                verbose=args.verbose
            )
            uploader.print_config()

            path_info = file.check_path(args.source)
            if path_info == "directory":
                uploader.upload_directory(args.source, s3_prefix=dest_key,  max_workers=args.max_workers)
            elif path_info == "file":
                pawn.console.log("File upload")
                uploader.upload_file(args.source,  s3_prefix=dest_key)
            else:
                raise ValueError(f"{args.source} not found.")

            pawn.console.log(f"Total Uploaded Size={convert_bytes(uploader.total_uploaded_size)}")

        elif operation == 'download':
            downloader = Downloader(
                profile_name=args.profile,
                bucket_name=source_bucket,
                overwrite=args.overwrite,
                dry_run=args.dry_run
            )
            downloader.print_config()

            if downloader.is_s3_file(source_key):
                pawn.console.rule("Object is File")
                downloader.download_file(s3_key=source_key, local_path=dest_key, overwrite=args.overwrite)
            else:
                pawn.console.rule("Object is Directory")
                downloader.download_directory(s3_directory=source_key, local_path=args.destination, overwrite=args.overwrite)

    elif args.command == 'ls':
        if args.path:
            bucket, prefix = parse_s3_path(args.path)
            if not bucket:
                sys_exit("Please provide a valid S3 path to list.")
            pawn.console.rule("[bold green]Bucket Contents: {bucket}[/bold green]")
            s3_lister = S3Lister(profile_name=args.profile, bucket_name=bucket, verbose=args.verbose)
            s3_lister.print_config()
            s3_lister.ls(prefix=prefix, recursive=args.recursive)
        else:
            from rich.table import Table
            pawn.console.rule("[bold cyan]Available Buckets[/bold cyan]")
            
            s3_lister = S3Lister(profile_name=args.profile, verbose=args.verbose)
            s3_lister.print_config()

            buckets = s3_lister.list_buckets(include_size=args.include_size)
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Index", justify="right")
            table.add_column("Bucket Name")
            if args.include_size:
                table.add_column("Size")

            for idx, bucket in enumerate(buckets, start=1):
                
                if args.include_size:
                    table.add_row(str(idx), bucket["Name"], convert_bytes(bucket["Size"]))
                else:
                    table.add_row(str(idx), bucket["Name"])

            pawn.console.print(table)

    elif args.command == 'rm':
        bucket, key = parse_s3_path(args.path)
        if not bucket:
            sys_exit("Please provide a valid S3 path to remove.")
        uploader = Uploader(
            profile_name=args.profile,
            bucket_name=bucket,
            # overwrite=args.overwrite,
            confirm_upload=False,
            keep_path=True
        )
        uploader.print_config()
        uploader.delete_objects(pattern=args.pattern, max_workers=args.max_workers)

    elif args.command == 'info':
        s3_lister = S3Lister(profile_name=args.profile, verbose=args.verbose)
        s3_lister.debug_info()

    else:
        parser.print_help()
        sys_exit(f"\nError: Invalid command '{args.command}'. Please choose from ({', '.join(VALID_COMMANDS)}).\n")


main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':
    main()
