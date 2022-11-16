#!/usr/bin/env python3
import common
from pawnlib.typing.converter import FlatDict, MedianFinder, StackList
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn
import argparse


def get_parser():
    parser = argparse.ArgumentParser(description='Vault Cli')
    parser.add_argument("--debug", "-d", action="store_true", default=False, required=False, )
    parser.add_argument('--file', type=argparse.FileType('r'), default=None)
    return parser

pawn.console.log(pawn)
parser = get_parser()
args = parser.parse_args()

pawn.set(
    ALL="AAA",
    value=args,
    args=args
)

conf = pawn.conf()
pawn.console.log(pawn.__dict__)
pawn.console.log(conf.args)
# pawn.console.log(conf.ALL)
pawn.console.log(conf.args.file.readlines())

