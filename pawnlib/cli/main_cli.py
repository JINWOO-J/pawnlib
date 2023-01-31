from pawnlib.config import pawnlib_config as pawn
from pawnlib.output import get_real_path
import argparse

from glob import glob
import os
import sys
import importlib
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.utils.operate_handler import run_with_keyboard_interrupt


def load_submodule_parsers(parent_module, parser, help=None):
    if help is None:
        help = parent_module.__name__ + " modules"
    modules = glob(os.path.join(parent_module.__path__, "*.py"))
    subparsers = parser.add_subparsers(help=help)
    for module_file in modules:
        module_name = os.path.basename(module_file)[:-3]
        if module == "__init__":
            continue
        module = importlib.import_module(module_name, package=parent_module.__name__)
        if "define_arguments" not in module.__dict__:
            raise ImportError(parent_module.__name__ + " submodule '" + module_name + "' does not have required 'define_arguments' function.")
        parser = subparsers.add_parser(module_name)
        module.define_arguments(parser)


def load_all_submodule():
    for module_file in get_submodule_names():
        module_name = module_file
        pawn.console.log(module_name)
        run_module(module_name)


def get_module_name(name):
    return os.path.basename(name)[:-3]


def get_submodule_names():
    module_list = glob(os.path.join(get_real_path(__file__), "*.py"))
    main_cli_name = get_module_name(__file__)
    exclude_module_names = ["__init__", main_cli_name]
    modules = []
    for module_file in module_list:
        module_name = get_module_name(module_file)
        if module_name not in exclude_module_names:
            modules.append(module_name)
    return modules


def run_module(module_name=None):
    module = importlib.import_module(f"pawnlib.cli.{module_name}")
    module.main()
    pawn.console.log(f"load a {module_name}")
    return module


def remove_argument(parser, arg):
    for action in parser._actions:
        opts = action.option_strings
        if (opts and opts[0] == arg) or action.dest == arg:
            parser._remove_action(action)
            pawn.console.log("ok remove")
            break

    for action in parser._action_groups:
        for group_action in action._group_actions:
            if group_action.dest == arg:
                action._group_actions.remove(group_action)
                pawn.console.log("ok remove")
                return


def parse_args(parser, commands):
    split_argv = [[]]
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = None
    for c in sys.argv[1:]:
        if c in commands.choices:
            split_argv.append([c])
        else:
            split_argv[-1].append(c)
    args = argparse.Namespace()
    for c in commands.choices:
        setattr(args, c, None)
    parser.parse_args(split_argv[0], namespace=args)  # Without command
    for argv in split_argv[1:]:  # Commands
        n = argparse.Namespace()
        setattr(args, argv[0], n)
        parser.parse_args(argv, namespace=n)
    return args, command


def get_args():
    parser = argparse.ArgumentParser(
        usage=generate_banner(app_name="PAWNS", version=_version, author="jinwoo", font="graffiti"),
        formatter_class=argparse.RawTextHelpFormatter)

    commands = parser.add_subparsers(title='sub-module')
    for module_name in get_submodule_names():
        _parser = commands.add_parser(module_name, help=f'{module_name} module')
        module = importlib.import_module(f"pawnlib.cli.{module_name}")
        module.get_arguments(_parser)

    args, command = parse_args(parser, commands)
    return args, command, parser


def main():
    pawn.console.log(f"main_cli wrapper")
    args, command, parser = get_args()
    pawn.console.log(f"args = {args}, command = {command}")
    if command:
        run_with_keyboard_interrupt(run_module, command)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    run_with_keyboard_interrupt(main)

