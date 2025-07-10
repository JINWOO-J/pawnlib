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
    pawn.console.log(pconf()._asdict())
    _private_key_with_argument = PromptWithArgument(
        argument="private_key",
        name="private key",
        default=random_private_key(),
        type="input",
        validate=PrivateKeyValidator(allow_none=True),
        filter=lambda result: result[2:] if result.startswith("0x") else result
    ).prompt()

    pawn.console.log(f"{_private_key_with_argument=}")
    _target_with_argument = PromptWithArgument(
        argument="target",
        # default="2222",
        type="input",
        choices=["1111", "2222"],
    ).fuzzy()

    pawn.console.log(f"{_target_with_argument=}")
    _target2_without_argument = PromptWithArgument(
        name="target",
        type="input",
        choices=[
            {"name": "ssss (1111)", "value": "1111"},
            {"name": "asdasdadsa (2222)", "value": "2222"},
        ],
    ).fuzzy()

    pawn.console.log(f"{_target2_without_argument=}")
    pawn.console.log(pconf())


if __name__ == "__main__":
    run_with_keyboard_interrupt(main)

