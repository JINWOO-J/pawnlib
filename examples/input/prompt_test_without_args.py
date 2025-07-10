#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawn, pconf, Null
from pawnlib.output import dump, classdump
from pawnlib.input.prompt import PromptWithArgument, PrivateKeyValidator
from pawnlib.typing.generator import random_private_key
import argparse
from pawnlib.utils.operate_handler import run_with_keyboard_interrupt


def main():
    _private_key = PromptWithArgument(
        name="private key",
        default=random_private_key(),
        type="input",
        validate=PrivateKeyValidator(allow_none=True),
        filter=lambda result: result[2:] if result.startswith("0x") else result,
    ).prompt()

    pawn.console.log(_private_key)


if __name__ == "__main__":
    run_with_keyboard_interrupt(main)

