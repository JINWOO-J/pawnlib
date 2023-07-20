#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn

icx = 0.001


def get_parser():
    parser = argparse.ArgumentParser(description='Command Line Interface for ICX')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser=None):

    parser.add_argument(
        'command',
        help='account, icx_sendTransaction, icx_sendTransaction_v3, get_transactionResult, icx_getBalance, icx_getTotalSupply')
    parser.add_argument('--url', metavar='url', help=f'loopchain baseurl. default: None', default=None)
    parser.add_argument('--from', metavar='address', dest='from_addr', help=f'from address. default: None', default=None)
    parser.add_argument('--to', metavar='address', dest="to_addr", help=f'to address. default: None', default=None)
    parser.add_argument('--address', metavar='address', help=f'icx address. default: None', default=None)
    parser.add_argument('--txhash', metavar='txhash', help='txhash')
    parser.add_argument('--icx', metavar='amount', type=float, help=f'icx amount to transfer. unit: icx. ex) 1.0. default:{icx}', default=icx)
    parser.add_argument('--fee', metavar='amount', type=float, help='transfer fee. default: 0.01', default=0.001)
    parser.add_argument('--pk', metavar='private_key', help=f'hex string. default: None', default=None)
    parser.add_argument('--debug', action='store_true', help=f'debug mode. True/False')
    parser.add_argument('-n', '--number', metavar='number', type=int, help=f'try number. default: 1', default=1)
    parser.add_argument('--nid', metavar='nid', type=str, help=f'network id default: 0x1', default="0x1")
    parser.add_argument('-c', '--config', metavar='config', help=f'config name')
    parser.add_argument('-k', '--keystore-name', metavar='key_store', help=f'keystore file name')
    parser.add_argument('-p', '--password', metavar='password', help=f'keystore file password')
    parser.add_argument('-t', '--timeout', metavar='timeout', type=float, help=f'timeout')
    parser.add_argument('-w', '--worker', metavar='worker',type=int,  help=f'worker')
    parser.add_argument('-i', '--increase', metavar='increase_count',type=int,  help=f'increase count number')
    parser.add_argument('--increase-count', metavar='increase_count', type=int,  help=f'increase count number', default=1)
    parser.add_argument('-r', '--rnd_icx', metavar='rnd_icx', help=f'rnd_icx', default="no")
    return parser


def main():
    banner = generate_banner(
        app_name="ICON",
        author="jinwoo",
        description="ICON utils",
        font="graffiti",
        version=_version
    )

    parser = get_parser()
    args, unknown = parser.parse_known_args()
    print(banner)
    pawn.console.log(f"args = {args}")


if __name__ == '__main__':
    main()
