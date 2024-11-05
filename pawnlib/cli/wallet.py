#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__
from pawnlib.output.color_print import *
from pawnlib.config import pawnlib_config as pawn, pconf
try:
    from pawnlib.utils import icx_signer
    icx_signer_loaded = True
except ImportError:
    icx_signer_loaded = False
    pass
from pawnlib.utils.operate_handler import run_with_keyboard_interrupt
from pawnlib.input import PromptWithArgument

__description__ = "A tool for managing ICON wallets. It supports creating new wallets and loading existing ones."

__epilog__ = (
    "This command-line interface offers various options for interacting with ICON wallets. "
    "You can easily create a new wallet or load an existing one using a private key or a keystore file.\n\n"

    "Usage examples:\n"
    "  1. Create a new wallet:\n\n"
    "     - This command creates a new wallet and outputs the keystore file and address.\n\n"
    "     `pawns wallet create`\n"


    "  2. Load an existing wallet using a private key:\n\n"
    "     - Loads a wallet from the provided private key.\n\n"
    "     `pawns wallet load --private-key YOUR_PRIVATE_KEY`\n"
    

    "  3. Load an existing wallet from a keystore file:\n\n"
    "     - Loads a wallet from a keystore file with the provided password.\n\n"
    "     `pawns wallet load --keystore /path/to/keystore --password YOUR_PASSWORD`\n"
    

    "Options:\n"
    "  - Use '--debug' to enable debug mode for more detailed logs.\n"
    "  - Use '--no-store' with the 'create' command to avoid saving the wallet keystore file.\n\n"

    "For more detailed information on command options, use the -h or --help flag."
)


if not icx_signer_loaded:
    pawn.console.log("[red]Required packages - coincurve, eth_keyfile ")


def get_parser():
    parser = argparse.ArgumentParser(description='ICON')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument(
        'sub_command',
        help='Specifies the action to perform. Options: "create" to generate a new wallet, "load" to load an existing wallet.',
        choices=["create", "load"],
        nargs='?'
    )
    parser.add_argument('-pk', '--private-key', metavar='PRIVATE_KEY',
                        help='Specifies a private key in hexadecimal format. Used with the "load" sub-command to load a wallet from its private key.',
                        default=None)
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enables debug mode, providing more detailed output for troubleshooting.',
                        default=False)
    parser.add_argument('-k', '--keystore', metavar='KEYSTORE',
                        help='Specifies the path to a keystore file or the keystore content directly. Required for loading a wallet from a keystore.',
                        required=False)
    parser.add_argument('-p', '--password', metavar='PASSWORD',
                        help='The password for decrypting the keystore file. Required when loading a wallet from a keystore.',
                        required=False)
    parser.add_argument('-l', '--load-type', metavar='LOAD_TYPE',
                        help='Determines how the keystore information is provided: "file" for keystore file path, "text" for keystore content as text.',
                        choices=["file", "text"], required=False)
    parser.add_argument('-ns', '--no-store', action='store_true',
                        help='Prevents the new wallet\'s keystore from being saved to a file when creating a wallet. Useful for temporary wallets.',
                        default=False)
    parser.add_argument('--base-dir', metavar='BASE_DIR',
                        help='Sets the base directory for storing keystore files. Defaults to the current working directory.',
                        default=os.getcwd())

    return parser


def private_key_validator(private_key):
    if icx_signer.is_private_key(private_key) or private_key == "":
        return True
    return "Invalid private key "


def least_length_validator(text, length=1):
    if len(text) >= length or text != "":
        return True
    return f"Must be at least {length} word(s) "


def main():
    icx_signer.compressed = False
    banner = generate_banner(
        app_name="WALLET",
        author="jinwoo",
        description="Wallet tools",
        font="graffiti",
        version=f"pawnlib {__version__}"
    )
    print(banner)
    parser = get_parser()
    args, unknown = parser.parse_known_args()

    if args.sub_command == "wallet":
        args.sub_command = ""

    args.subparser_name = "wallet"
    pawn.set(
        PAWN_DEBUG=args.debug,
        data=dict(
            args=args
        )
    )

    if args.sub_command:
        _sub_command = args.sub_command
    else:
        _sub_command = ""

    args.debug and pawn.console.log(f"args = {args}")

    pawn.console.log(f"{_sub_command} wallet".title())
    args.sub_command = PromptWithArgument(
        message="What do you want to do?",
        choices=
        [
            {"name": "Load wallet", "value": "load"},
            {"name": "Create wallet", "value": "create"},
        ],
        instruction="",
        max_height="40%",
        default="",
        argument="sub_command",
        verbose=0,
    ).fuzzy()
    wallet_cli = icx_signer.WalletCli(args=pconf().data.args)

    if args.sub_command == "load":
        wallet_cli.load()

    elif args.sub_command == "create":
        is_store_file = not args.no_store
        wallet_cli.create(is_store_file=is_store_file)


main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':
    main()
