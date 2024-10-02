#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawn, pconf
from pawnlib.output import dump, classdump
from pawnlib.input.prompt import PromptWithArgument, PrivateKeyValidator, json_input_prompt
from pawnlib.typing.generator import random_private_key
import argparse
from pawnlib.utils.operate_handler import run_with_keyboard_interrupt

def get_args_parser():
    parser = argparse.ArgumentParser(description='Test')
    parser.add_argument('--target', required=False, default="")
    parser.add_argument('--private-key', required=False, default="")
    return parser.parse_args()



def main():
    default_json = {
        "ssssss": "sdsdsdsds",
        "11": "sdsdsdsds",
        "22": "sdsdsdsds",
    }
    json_input_prompt(default_json)


if __name__ == "__main__":
    run_with_keyboard_interrupt(main)

