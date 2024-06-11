# -*- coding: utf-8 -*-
import sys
import json
import argparse
from pawnlib.typing import generate_number_list, Counter
from pawnlib.config.globalconfig import ConfigSectionMap, pawnlib_config as pawn
from pawnlib.output import open_file, check_file_overwrite, write_file, is_file, dump
from pawnlib.asyncio import AsyncTasks
from pawnlib.typing import str2bool, flatten_list
from pawnlib.docker import AsyncDocker, run_container, run_dyn_container
from InquirerPy import prompt

from rich.prompt import Confirm, FloatPrompt, Prompt, PromptBase
from rich.syntax import Syntax

from jinja2 import Template
from pathlib import Path
from importlib.machinery import SourceFileLoader
import os
import configparser


EXEC_PATH = os.getcwd()


def get_parser():
    parser = argparse.ArgumentParser(
        description='Command Line Interface for docker',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument(
        'command',
        # choices=['init', 'run', 'create', 'create_or_replace', 'delete', 'start', 'stop'],
        choices=['init', 'run', 'delete', 'start', 'stop', "ls"],
        help='')
    parser.add_argument('-s', '--unixsocket', metavar='unixsocket', help='unix domain socket path (default: /var/run/docker.sock)',
                        default="/var/run/docker.sock")
    parser.add_argument('-d', '--debug', action='store_true', help='debug mode. ', default=False)
    parser.add_argument('-c', '--count', metavar="container count", type=int, help='container count (default: 30)', default=30)
    parser.add_argument('--max-at-once', metavar="max_at_once count", type=int, help='max_at_once count (default: 30)', default=30)
    parser.add_argument('--max-per-second', metavar="max_per_second count", type=int, help='max_per_second count (default: 50)', default=50)
    parser.add_argument('-n', '--name', metavar="container name", type=str, help='container prefix name ', default=None)
    parser.add_argument('-i', '--image', metavar="image name", type=str, help='docker image name ', default=None)

    # parser.add_argument('-f', '--file', type=argparse.FileType('r'), help="container source code")
    parser.add_argument('-f', '--file', type=str, help="import the container source code", default=None)
    parser.add_argument('--force', action='store_true', help="run force mode without confirm", default=False)

    parser.add_argument('--config', type=str, help="import the config file", default=f'{EXEC_PATH}/config.ini')
    # parser.add_argument('-t', '--target', type=str, help="target", default=None)
    parser.add_argument('-t', '--target', nargs='+', help="target", default=None)
    parser.add_argument('-log', '--show-container-log', type=str2bool, help="show last container log (default: False)", default=False)

    return parser


def initialize(args):
    pawn.set(PAWN_CONFIG_FILE=args.config)
    pawn.console.debug(f"os.cwd => {EXEC_PATH}")
    pwn = pawn.conf()
    pawn_config = pawn.to_dict().get('PAWN_CONFIG')

    default_image = {
        "docker_planet": "jinwoo/planet",
        "docker_echo": "jmalloc/echo-server"
    }
    if args.command == "init":
        pawn.console.log("Generate the sample files for docker container")
        template_dir = f"{os.path.dirname(__file__)}/templates"

        template_question = [
            {
                'type': 'list',
                'name': 'category',
                'message': 'What do you want to template?',
                'choices': [tmpl_file.replace(".tmpl", "") for tmpl_file in os.listdir(template_dir) if tmpl_file.endswith('.tmpl')],
            },
            {
                'type': 'input',
                'name': 'target_list',
                'message': 'What\'s the target(access_code) list?',
                # 'default': "[]"
                'default': lambda x: f'Counter(start=10000, stop=10000+args.count, convert_func=str)' if "docker_echo" in x['category'] else "[]"
            },
            {
                'type': 'input',
                'name': 'filename',
                'message': 'What\'s the filename?',
                'default': lambda x: x['category']
            },
            {
                'type': 'input',
                'name': 'image',
                'message': 'What\'s your image name?',
                'default': lambda x: default_image.get(x['category'])
            },
            {
                'type': 'input',
                'name': 'container_name',
                'message': 'What\'s your container name?',
                'default': lambda x: x['category']
            },
        ]

        answers = prompt(template_question)
        template_file = f"{template_dir}/{answers['category']}.tmpl"
        template = open_file(f"{template_file}")

        templated_dict = Template(template).render(
            **answers
        )

        syntax = Syntax(templated_dict, "python")
        pawn.console.rule(answers['category'])
        pawn.console.print(syntax)
        pawn.console.rule("")

        check_file_overwrite(filename=f"{answers['category']}.py")
        write_file(filename=f"{answers['category']}.py", data=templated_dict, permit="660")

        check_file_overwrite(filename=args.config)
        config = configparser.ConfigParser()
        config['default'] = {
            "image": answers['image'],
            "name": answers['container_name'],
            "file": f"{EXEC_PATH}/{answers['filename']}.py",
            "target": answers['target_list'],
        }
        with open(args.config, 'w') as configfile:
            config.write(configfile)

    if pawn_config:
        pawn.console.debug(f"Found config file => '{pwn.PAWN_CONFIG_FILE}'")
        pawn.console.log(f"config=")
        pawn.console.log(pawn_config)

        if not args.image:
            args.image = pawn_config['default']['image']

        if not args.name:
            args.name = pawn_config['default']['name']

        # if not args.target and pawn_config['default'].get('target_list'):
        if not args.target:
            args.target = pawn_config['default'].get('target')

        if not args.file:
            args.file = pawn_config['default'].get('file')

    if args.image and ":" not in args.image:
        args.image = f"{args.image}:latest"

    pawn.set(args=args)

    if args.file and is_file(args.file):
        _file = Path(args.file)
        module_name = _file.stem
        # module_name = args.file.replace(".py", "")
        # pawn.console.debug(f"module_name={module_name}, file={args.file}")
        args.module = SourceFileLoader(module_name, args.file).load_module()
        pawn.console.log(f"[bold]Load module from '{module_name}'")
        pawn.console.debug(f"from {args.module}")
    return args


def _run_async_task(args=None, function=None, target_list=[]):
    if function:
        _function = function
    else:
        _function = args.module.main

    async_tasks = AsyncTasks(args=args, max_at_once=args.max_at_once, max_per_second=args.max_per_second)
    async_tasks.generate_tasks(
        target_list=target_list,
        function=_function,
        **{"args": args, "_config": pawn.conf()}
    )
    async_tasks.run()


def _download_image_if_not_exist(args=None, docker=None):
    if args.image:
        if docker.find_image(image=args.image):
            pawn.console.debug(f"[green][OK] Find Docker Image: {args.image}")
        else:
            pawn.console.log(f"[yellow]Pulling Image: {args.image}")
            docker.pull_image(args.image)
    else:
        pawn.console.log(f"[red] Image argument not found - {args.image}")


def _remove_needless_string(string=None, needless=[]):
    for target_string in needless:
        if string.find(target_string)!= -1:
            string = string.replace(target_string, "")
    return string


def _remove_needless_list(string_list=None, needless=[]):
    result = []
    for string in string_list:
        result.append(_remove_needless_string(string=string, needless=needless))
    return result


def _flatten_string_list(string_list=None):
    result = []
    for string in string_list:
        if string.find("[") != -1 and string.find("]") != -1:
            result.append(eval(f"{string}"))
        else:
            result.append(string)
    return flatten_list(result)


def _convert_string_to_list(string_list, args):
    if isinstance(string_list, str):
        if "[" in string_list and "]" in string_list:
            try:
                string_list = json.loads(string_list)
            except ValueError:
                pawn.console.debug(f"[red] error json load = {string_list}, {type(string_list)}")
        target_list = eval(f"{string_list}")
    elif isinstance(string_list, list):
        target_list = _flatten_string_list(string_list)
    else:
        target_list = string_list
    target_list = _remove_needless_list(target_list, needless=[",", "[", " ", "]"])

    return target_list


def _make_target_list(args=None):
    if args.target:
        target_list = _convert_string_to_list(args.target, args)
    else:
        target_list = _convert_string_to_list(args.module.target_list, args)

    return target_list


def main():
    parser = get_parser()
    args, unknown = parser.parse_known_args()
    args = initialize(args)
    pawn.console.debug(f"args={args}, unknown={unknown}")
    try:
        if args.module:
            pawn.console.debug(f"module={args.module}")
    except Exception as e:
        pawn.console.log(f"[red]Cannot load module - {e}")
        raise ValueError("Did you initialize or Did you installed the \"aiodocker\"? ( pawns docker init )")

    with AsyncDocker(
            client_options=dict(
                url=f"unix://{args.unixsocket}"
            ),
            max_at_once=args.max_at_once,
            max_per_second=args.max_per_second,
            count=args.count,
            container_name=args.name
    ) as docker:
        _download_image_if_not_exist(args, docker)
        target_list = _make_target_list(args)

        if not args.force:
            if args.command == "run":
                pawn.console.log(f"Target={target_list}, Target length={len(target_list)}")
            Confirm.ask(f"Are you sure to {args.command.upper()}?", default=True)

        if args.command == 'run':
            _run_async_task(args=args, target_list=target_list)

        elif args.command == "create":
            async_tasks = AsyncTasks(args=args, max_at_once=args.max_at_once, max_per_second=args.max_per_second)
            async_tasks.generate_tasks(
                target_list=Counter(start=10000, stop=10000+args.count, convert_func=str),
                function=run_container,
                **{"args": args}
            )
            async_tasks.run()
        else:
            docker.control_container(method=args.command, filters={"Names": f"{args.name}.*"}, all=True)


if __name__ == "__main__":
    main()
