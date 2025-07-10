#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawn, pconf
from pawnlib.output import dump, classdump
from pawnlib.input.prompt import PromptWithArgument, PrivateKeyValidator
from pawnlib.typing.generator import random_private_key
import argparse
from pawnlib.utils.operate_handler import run_with_keyboard_interrupt

def get_args_parser():
    parser = argparse.ArgumentParser(description='Test')
    parser.add_argument('--target', required=False, default="")
    parser.add_argument('--private-key', required=False, default="")
    return parser.parse_args()



def main():
    args = get_args_parser()
    pawn.console.log(pconf())
    pawn.set(
        args=args,
        data=dict(
            args=args
        )
    )
    _checkbox = PromptWithArgument(
        name="target",
        argument="target",
        type="input",
        choices=[
            {"name": "first item (1111)", "value": "1111"},
            {"name": "second item (2222)", "value": "2222"},
        ],
    ).checkbox()

    pawn.console.log(f"{_checkbox=}")
    pawn.console.log(pconf())


if __name__ == "__main__":
    run_with_keyboard_interrupt(main)

