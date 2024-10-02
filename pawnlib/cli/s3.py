#!/usr/bin/env python3
import argparse
import sys
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn, pconf
from pawnlib.typing.converter import convert_bytes
from pawnlib.typing.check import sys_exit
from pawnlib.utils.aws import Uploader, Downloader
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter
import importlib.util
import subprocess
import configparser
import requests
import json

__description__ = 'Upload or download directories to/from AWS S3.'

__epilog__ = (
    "This script allows you to upload or download directories to/from an AWS S3 bucket.\n\n"
    "Usage examples:\n\n"

    "  1. Upload a directory to S3:\n\n"
    "     - Uploads the specified directory to the S3 bucket using the provided AWS CLI profile.\n\n"
    "     `pawns upload -d /path/to/directory -p your-aws-profile -b your-s3-bucket`\n\n"

    "  2. Download a directory from S3:\n\n"
    "     - Downloads the specified S3 directory to the local path using the provided AWS CLI profile.\n\n"
    "     `pawns download -d s3-directory -l /local/path -p your-aws-profile -b your-s3-bucket`\n\n"

    "  3. Upload with a suffix appended to file names:\n\n"
    "     - Uploads files with '_backup' appended to their names.\n\n"
    "     `pawns upload -d /path/to/directory -p your-profile -b your-bucket --append-suffix '_backup'`\n\n"

    "  4. Download using an info file:\n\n"
    "     - Downloads files based on the structure specified in the info.json file.\n\n"
    "     `pawns download -p your-profile -b your-bucket --info-file path/to/info.json -l /local/path`\n\n"

    "  5. Upload or download with block height as suffix:\n\n"
    "     - Uploads files with the current block height appended to their names. The block height is obtained from the specified script.\n\n"
    "     `pawns upload -d /path/to/directory -p your-profile -b your-bucket --use-block-height --block-height-script path/to/script.py`\n\n"

    "  6. Execute pre and post commands:\n\n"
    "     - Executes the specified commands before and after the upload or download process.\n\n"
    "     `pawns upload -d /path/to/directory -p your-profile -b your-bucket --pre-cmd 'echo Pre-upload' --post-cmd 'echo Post-upload'`\n\n"

    "  7. Overwrite existing files:\n\n"
    "     - Overwrites existing files in the S3 bucket.\n\n"
    "     `pawns upload -d /path/to/directory -p your-profile -b your-bucket --overwrite`\n\n"

    "  8. Use shorthand commands:\n\n"
    "     - 'up' is shorthand for upload, 'down' for download.\n\n"
    "     `pawns up -d /path/to/directory -p your-profile -b your-bucket`\n\n"
    "     `pawns down -d s3-directory -l /local/path -p your-profile -b your-bucket`\n\n"

    "Note:\n\n"
    "  - The -p/--profile, -b/--bucket, and -d/--directory options are required for most operations.\n"
    "  - The -l/--local-path option specifies the local directory for downloads (default is current directory).\n\n"
    "  - Use the --help flag for a full list of options and their descriptions.\n\n"
)

VALID_COMMANDS = ["upload", "up", "download", "down"]


def get_parser():
    parser = CustomArgumentParser(
        description='AWS S3 Upload/Download',
        formatter_class=ColoredHelpFormatter,
        epilog=__epilog__
    )

    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    # parser.add_argument('command',Fchoices=['upload', 'download'], nargs="?", help='Command: upload or download', default=None)

    parser.add_argument(
        'command',
        help=f'Command to execute ({", ".join(VALID_COMMANDS)})',
        type=str,
        choices=VALID_COMMANDS,
        nargs='?',  # Make this optional if you want to provide a default
        default=None  # Or set a default command if appropriate
    )

    parser.add_argument('-d', '--directory', type=str,  help='Path to the directory to upload or download')
    parser.add_argument('-l', '--local-path', type=str,  help='Path to the local path', default="./")
    parser.add_argument('-p', '--profile', type=str,  help='AWS CLI profile name')
    parser.add_argument('-b', '--bucket', type=str, help='S3 bucket name')
    parser.add_argument(
        '--append-suffix',
        type=str,
        help='Append a suffix to the file or directory names during upload or download'
    )
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files in the S3 bucket or locally')
    parser.add_argument('--info-file', type=str, help='Path to the info.json file containing the upload directory structure')

    parser.add_argument(
        '--use-block-height',
        action='store_true',
        help='Use current block height as suffix'
    )

    parser.add_argument(
        '--block-height-script',
        type=str,
        default='get_current_block_height.py',
        help='Path to the script that gets the current block height'
    )

    parser.add_argument(
        '--pre-cmd',
        type=str,
        help='Command to execute before uploading or downloading'
    )

    parser.add_argument(
        '--post-cmd',
        type=str,
        help='Command to execute after uploading or downloading'
    )
    parser.add_argument('--config-file', type=str, default="config.ini", help="Path to the configuration file")
    parser.add_argument('--webhook', type=str, help='Slack Webhook URL to send logs and errors')

    return parser


def send_slack_message(webhook_url, message):
    """Send a message to a Slack channel via webhook."""
    if webhook_url:
        try:
            response = requests.post(
                webhook_url,
                data=json.dumps({'text': message}),
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code != 200:
                print(f"Failed to send message to Slack: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"Exception occurred while sending message to Slack: {str(e)}")


def load_block_height_module(script_path, webhook_url=None):
    """Load the block height module or raise an error if it fails."""
    try:
        spec = importlib.util.spec_from_file_location("block_height_module", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        error_message = f"Error loading block height module from {script_path}: {str(e)}"
        pawn.console.log(f"[red]{error_message}")
        send_slack_message(webhook_url, error_message)
        sys_exit(error_message)


def execute_command(command):
    pawn.console.log(f"Execute Command : {command}")
    try:
        subprocess.run(command, shell=True, check=True)
        pawn.console.log(f"Successfully executed command: {command}")
    except subprocess.CalledProcessError as e:
        pawn.console.log(f"Error executing command: {command}\n{e}")


def validate_required_args(args):
    """Validate that required arguments are provided."""
    missing_args = []

    if not args.directory:
        missing_args.append('-d/--directory')
    if not args.profile:
        missing_args.append('-p/--profile')
    if not args.bucket:
        missing_args.append('-b/--bucket')

    # if missing_args:
    #     sys_exit(f"Error: The following arguments are required: {', '.join(missing_args)}\n")
    return missing_args


def load_config(config_file="config.ini"):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config["DEFAULT"]

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

    parser = get_parser()
    args, unknown = parser.parse_known_args()

    config = load_config(args.config_file)
    apply_config_defaults(args, config)
    pawn.console.log(f"args = {args}")

    if not args.command:
        parser.print_help()
        sys_exit(f"\nError: A valid command is required. Please choose from ({', '.join(VALID_COMMANDS)}).\n")

    missing_args = validate_required_args(args)
    if missing_args:
        parser.print_help()
        sys_exit(f"Error: The following arguments are required: {', '.join(missing_args)}\n")

    if args.use_block_height:
        try:
            block_height_module = load_block_height_module(args.block_height_script)
            height = block_height_module.get_current_block_height()
            if height:
                args.append_suffix = f"_height_{height}"
            else:
                pawn.console.log("Failed to get block height. Proceeding without suffix.")
                args.append_suffix = None
        except Exception as e:
            send_slack_message(args.webhook, f"Error loading or executing block height script: {e}")
            sys_exit(f"Error loading or executing block height script: {e}")

            args.append_suffix = None

    if args.pre_cmd:
        execute_command(args.pre_cmd)

    if args.command in ['upload', 'up']:
        uploader = Uploader(
            profile_name=args.profile,
            bucket_name=args.bucket,
            overwrite=args.overwrite,
            info_file=args.info_file
        )
        uploader.upload_directory(args.directory, append_suffix=args.append_suffix)
        pawn.console.log(f"Total Uploaded Size={convert_bytes(uploader.total_uploaded_size)}")

    elif args.command in ['download', 'down']:
        downloader = Downloader(profile_name=args.profile, bucket_name=args.bucket, overwrite=args.overwrite)

        if args.info_file:
            # downloader.download_from_info(args.info_file, args.overwrite)
            downloader.download_from_info(
                s3_info_key=args.info_file,
                local_path=args.local_path,
                overwrite=args.overwrite
            )
        else:
            downloader.download_directory(s3_directory=args.directory, local_path=args.local_path, overwrite=args.overwrite)
        # downloader = Downloader(profile_name=args.profile, bucket_name=args.bucket, overwrite=args.overwrite)
        # downloader.download_directory(args.directory)
        # pawn.console.log(f"Total Downloaded Size={convert_bytes(downloader.total_downloaded_size)}")

    if args.post_cmd:
        execute_command(args.post_cmd)

main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':
    main()
