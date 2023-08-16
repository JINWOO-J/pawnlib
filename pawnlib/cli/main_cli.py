from pawnlib.config import pawnlib_config as pawn
from pawnlib.output import get_real_path, classdump
import argparse

from glob import glob
import os
import sys
import importlib
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.utils.operate_handler import run_with_keyboard_interrupt
from pawnlib.typing.check import sys_exit


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
    pawn.console.debug(f"load a {module_name}")
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


def get_sys_argv():
    if len(sys.argv) > 1:
        return sys.argv[1]
    return ""


def load_cli_module(commands=None, module_name=""):
    pawn.console.debug(f"Add parser => {module_name}")
    module = importlib.import_module(f"pawnlib.cli.{module_name}")
    description = getattr(module, "__description__", f"{module_name} module")
    _parser = commands.add_parser(module_name, help=f'{description}')
    module.get_arguments(_parser)


def get_args():
    parser = argparse.ArgumentParser(
        usage=generate_banner(app_name="PAWNS", version=_version, author="jinwoo", font="graffiti"),
        formatter_class=argparse.RawTextHelpFormatter
    )
    commands = parser.add_subparsers(title='sub-module')
    pawn.console.debug(f"sys_argv={get_sys_argv()}, modules={get_submodule_names()}")
    if get_sys_argv() and  get_sys_argv() in get_submodule_names():
        load_cli_module(commands, get_sys_argv())
    else:
        for module_name in get_submodule_names():
            try:
                load_cli_module(commands, module_name)
            except Exception as e:
                pawn.console.debug(f"[red] An error occurred while loading the module [/red] - {e}")

    args, command = parse_args(parser, commands)
    return args, command, parser


def cleanup_args():
    if len(sys.argv) > 2 and "-" not in sys.argv[2]:
        pawn.console.debug(f"Remove argument -> {sys.argv[1]}")
        del sys.argv[1]


def main():
    pawn.console.debug("Starting main_cli wrapper")
    args, command, parser = None, None, None
    try:
        pawn.console.debug(f"<before> {sys.argv}")
        args, command, parser = get_args()
        # pawn.console.debug(f"<after> parser {args}, {command}, {parser}")
        cleanup_args()
        # pawn.console.debug(f"<after> {sys.argv}")
    except Exception as e:
        pawn.console.debug(f"[red]Exception while parsing an argument = {e}")
        # sys_exit("Stopped CLI")
    pawn.console.debug(f"args={args}, command={command}, parser={parser}")

    if command:
        pawn.console.debug(f"command = {command}, PAWN_DEBUG={pawn.get('PAWN_DEBUG')}")
        try:
            # run_with_keyboard_interrupt(run_module, command)
            run_module(command)
        except KeyboardInterrupt:
            pawn.console.log("[red]KeyboardInterrupt")
        except Exception as e:
            if pawn.get('PAWN_DEBUG'):
                pawn.console.print_exception(show_locals=pawn.get("PAWN_DEBUG", False), width=160)
            else:
                pawn.console.log(f"[red]Exception -- {e}")
    else:
        if parser:
            parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    run_with_keyboard_interrupt(main)
    # main()

