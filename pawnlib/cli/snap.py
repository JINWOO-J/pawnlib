#!/usr/bin/env python3
import os
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf, setup_app_logger, ConfigHandler
from pawnlib.utils import execute_command_batch
from pawnlib.typing import StackList,load_env_with_defaults, mask_string, todaydate
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter, ask_yes_no
from pawnlib.output.file_indexing import FileIndexer
from pawnlib.output import write_json
from rich.table import Table
import asyncio

logger = setup_app_logger()

__description__ = "A CLI tool for managing and validating snapshot files efficiently."


__epilog__ = (
    "Usage Examples:",
    "---------------",
    "1. **Check Snapshots**:",
    "   pawns snap check --dir ./snapshots --verbose",
    "",
    "2. **Index Snapshots**:",
    "   pawns snap index --dir ./snapshots --output-path ./index --verbose",
    "",
    "3. **Run Tasks**:",
    "   pawns snap run --config-file config.ini --verbose",
    "",
    "Key Features:",
    "-------------",
    "- **Snapshot Management**: Upload, index, and validate snapshot files with ease.",
    "- **Task Automation**: Define and execute tasks using a configuration file.",
    "- **Customizable Options**: Specify directories, output paths, and methods for validation.",
    "- **Detailed Logging**: Leverage verbosity levels for comprehensive debug information.",
    "",
    "Options:",
    "--------",
    "- `command`        The action to perform. Choices are `check`, `index`, or `run`.",
    "- `--dir`          Directory containing snapshot files (default: `./data`).",
    "- `--output-path`  Directory to store the indexed files (default: `./`).",
    "- `--verbose`      Increase verbosity for detailed logs.",
    "- `--quiet`        Suppress output for minimal logs.",
    "",
    "Get Started:",
    "------------",
    "Run `pawns snap --help` for detailed usage instructions and examples."
)


def get_parser():
    parser = CustomArgumentParser(
        description='snap',
        epilog=__epilog__,
        formatter_class=ColoredHelpFormatter,
        fromfile_prefix_chars='@'
    )
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument('command', help='Action: "check", "index", "run".', choices=['check', 'index', 'run'], type=str, nargs='?', default=None)
    parser.add_argument('-b', '--base-dir', type=str, help='base dir for httping (default: %(default)s)', default=None)
    parser.add_argument('-d', '--dir', help='Snapshot files directory (default: ./data)', default=None)
    parser.add_argument('-o', '--output-path', help='Directory for indexed files (default: ./)', default=None)
    parser.add_argument('-p', '--prefix', help='Prefix (e.g., http://PREFIX/)', default=None)
    parser.add_argument('-m', '--check-method', help='Validation method.', choices=['hash', 'size'], default=None)
    parser.add_argument('--exclude-files', action='append', help='Files to exclude (default: ["restore"])', default=None)
    parser.add_argument('-v', '--verbose', action='count', help='Increase verbosity.', default=0)
    parser.add_argument('-q', '--quiet', action='count', help='Suppress output.', default=0)
    parser.add_argument('-c', '--checksum-file', help='Checksum file name (default: checksum.json)', default=None)
    parser.add_argument('-n', '--network-name', help='Network name for metadata.', default=None)
    parser.add_argument('-s', '--store-metadata', action='store_true', help='Store metadata.', default=False)
    parser.add_argument('--backup-type', type=str, help='Type of backup to create (default: full).', default=None)
    parser.add_argument('-f', '--force', action="store_true", help='Force execution of tasks, ignoring warnings.', default=None)
    return parser


def print_banner():
    banner = generate_banner(
        app_name=pconf().app_name,
        author="jinwoo",
        description=f"{__description__} \n"
                    f" - base_dir    : {pconf().args.base_dir} \n" 
                    f" - logs_dir    : {pconf().args.base_dir}/logs \n",
        font="graffiti",
        version=_version
    )
    print(banner)


def read_tasks_from_config():
    # config = configparser.ConfigParser()
    # config.read(config_file)
    config = pconf().PAWN_CONFIG.as_dict()
    pawn.console.log(config)
    tasks = []
    for section in config.keys():
        task = {}
        if section and "task" in str(section).lower():
            for key, value in config[section].items():
                # Convert values if necessary
                task[key] = convert_value(value)
            tasks.append(task)
    return tasks


def convert_value(value):
    if value.lower() in ('true', 'yes', 'on'):
        return True
    elif value.lower() in ('false', 'no', 'off'):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    return value


def display_tasks(tasks):
    all_keys = set()
    for task in tasks:
        if isinstance(task, dict):
            all_keys.update(task.keys())
        else:
            all_keys.add('cmd')

    color_mapping = {
        'cmd': 'green',
        'cwd': 'blue',
        'text': 'yellow',
        'use_spinner': 'cyan',
        'retries': 'magenta',
    }

    default_color = 'white'
    table = Table(title="Loded Tasks from Configuration", show_lines=True, expand=True)
    table.add_column("Task Number", justify="center", style="bold cyan", no_wrap=True)
    sorted_keys = sorted(all_keys)
    for key in sorted_keys:
        color = color_mapping.get(key, default_color)
        table.add_column(key.capitalize(), style=color, overflow='fold')

    for idx, task in enumerate(tasks, 1):
        row = [str(idx)]
        if isinstance(task, dict):
            for key in sorted_keys:
                value = str(task.get(key, ""))
                row.append(value)
        else:
            for key in sorted_keys:
                value = task if key == 'cmd' else ""
                row.append(value)
        table.add_row(*row)
    pawn.console.print(table)


def generate_network_info_meta(network_name="", prefix_url="", backup_type="full" ):
    network_info = {
        "network_name": network_name,
        "index_url": f'{prefix_url}/file_list.txt?version={todaydate("md")}',
        "checksum_url": f'{prefix_url}/checksum.json?version={todaydate("md")}',
        "updated_time": todaydate("ms")
    }
    pawn.console.log(write_json(filename=f"{network_name}.json", data=network_info))


def run_tasks(config_handler: ConfigHandler = None):
    tasks = config_handler.get_all_sections("task").values()
    if not tasks:
        raise ValueError(f"There are no tasks in the config.ini file. {tasks}")
    display_tasks(tasks)
    if not config_handler.get('force'):
        answer = ask_yes_no("Do you want to execute these tasks?", default=True)
        if answer:
            pawn.console.print("✅ [bold green]You chose to proceed![/bold green]")
        else:
            pawn.console.print("❌ [bold red]Operation aborted by the user.[/bold red]")

    slack_web_hook_url = pconf().PAWN_CONFIG.default.SLACK_WEBHOOK_URL
    execute_default_kwargs = {
        "use_spinner": True,
        "check_output": False
    }
    execute_command_batch(
        # tasks=[
        #     {"cmd": "docker-compose down", "cwd": "logs", "text": "Listing directory contents"},
        #     {"cmd": "sleep 20", "cwd": "logs", "text": "Sleep 10 sec"},
        #     "sleep 5",
        #     "invalid"
        # ],
        tasks=tasks,
        slack_url=slack_web_hook_url,
        default_kwargs=execute_default_kwargs,
        function_registry=globals()
    )


def main():
    app_name = 'snap'
    parser = get_parser()
    args, unknown = parser.parse_known_args()

    is_hide_line_number = args.verbose > 2
    stdout = not args.quiet

    pawn.set(
        # PAWN_CONFIG_FILE=config_file,
        PAWN_PATH=args.base_dir,
        PAWN_CONSOLE=dict(
            redirect=True,
            record=True,
            log_path=is_hide_line_number, # hide line number on the right side
        ),
        app_name=app_name,
        args=args,
        try_pass=False,
        last_execute_point=0,
        data={
            "response_time": StackList(),
        },
        fail_count=0,
        total_count=0,

    )
    if args.verbose > 2:
        pawn.set(
            PAWN_LOGGER=dict(
                log_level="DEBUG",
                stdout_level="DEBUG",
                # log_path=f"{args.base_dir}/logs",
                stdout=stdout,
                use_hook_exception=True,
                show_path=False, #hide line numbers
            ),
        )
    print_banner()
    pawn.console.log(args)

    pawn.console.log(f"checksum_file={args.checksum_file}")
    load_env_with_defaults()
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    pawn.console.log(mask_string(slack_webhook_url, show_chars=10, align="side"))

    code_defaults = {
        'base_dir': os.getcwd(),
        'dir': './data',
        'output_path': './',
        'check_method': 'hash',
        'exclude_files': ['restore'],
        'verbose': 0,
        'quiet': 0,
        'checksum_file': 'checksum.json',
        'store_metadata': False,
        'backup_type': 'full',
        'force': False,
        # Add other defaults as needed
    }

    config_handler = ConfigHandler(config_file='config.ini', args=args, env_prefix="PAWN_", section_pattern="task", defaults=code_defaults)
    config_handler.print_config()
    config_args = config_handler.as_namespace()

    file_indexer = FileIndexer(
        base_dir=config_args.dir,
        output_dir=config_args.output_path,
        debug=config_args.verbose > 0,
        check_method=config_args.check_method,
        prefix=config_args.prefix,
        checksum_filename=config_args.checksum_file,
        exclude_files=config_args.exclude_files,
    )

    pawn.set(file_indexer=file_indexer)

    if args.command == "index":
        run_indexing()

    elif args.command == "check":
        asyncio.run(file_indexer.check())

    elif args.command == "run":
        run_tasks(config_handler)

def run_indexing():
    file_indexer = pawn.get('file_indexer')
    asyncio.run(file_indexer.run())

def run_generating_metadata():
    file_indexer = pawn.get('file_indexer')
    asyncio.run(file_indexer.check())

main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)


if __name__ == '__main__':

    try:
        main()
    except Exception as e:
        pawn.console.log(e)

