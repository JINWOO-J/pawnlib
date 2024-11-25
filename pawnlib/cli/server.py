#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf
import os
from pawnlib.typing import str2bool, StackList, remove_tags, dict_to_line, flatten, sys_exit
from pawnlib.output import write_json, print_grid, print_var, get_color_by_threshold
from rich.tree import Tree
from copy import deepcopy
from rich.table import Table
from rich.panel import Panel

from pawnlib.resource.server import DiskPerformanceTester, FileSystemTester, get_platform_info, DiskUsage, get_cpu_load, get_iowait

__description__ = "This command is used to measure server performance and verify specifications."

__epilog__ = (
    "This tool is intended for checking and validating server resources.\n\n"
    "Usage examples:\n"
    "  1. Measure disk performance:\n\n"
    "     - Measures write and read speed for a test file with specified parameters.\n\n"
    "     `pawns server disk --file-path /path/to/testfile --file-size-mb 1024 --iterations 5 --block-size-kb 1024 --num-threads 1 --io-pattern sequential`\n"
    "  2. Measure filesystem performance:\n\n"
    "     -  Measure the filesystem performance 5 times with 2,000 files.\n\n"
    "     `pawns server fs server fs -i 5 --count 2000` \n\n"
    "For more detailed command usage and options, refer to the help documentation by running 'pawns server --help'."
)

VALID_COMMANDS = ["disk", "fs", "all"]


def get_parser():
    parser = argparse.ArgumentParser(description='server')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument(
        'command',
        help=f'Command to execute ({", ".join(VALID_COMMANDS)})',
        type=str,
        choices=VALID_COMMANDS,
        nargs='?',  # Make this optional if you want to provide a default
        default=None  # Or set a default command if appropriate
    )
    parser.add_argument('-c', '--config-file', type=str, help='config', default="config.ini")
    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level (default: %(default)s)', default=1)
    parser.add_argument('-q', '--quiet', action='count', help='Quiet mode. Dont show any messages. (default: %(default)s)', default=0)
    parser.add_argument('-b', '--base-dir', type=str, help='base dir for httping (default: %(default)s)', default=os.getcwd())
    parser.add_argument('--file-path', type=str, default='testfile', help='Path to the test file')
    parser.add_argument('--file-size-mb', type=int, default=1024, help='Size of the test file in MB')
    parser.add_argument('-i', '--iterations', type=int, default=5, help='Number of iterations for testing')
    parser.add_argument('--block-size-kb', type=int, default=1024, help='Block size in KB')
    parser.add_argument('-n', '--num-threads', type=int, default=1, help='Number of parallel threads')
    parser.add_argument('--count', type=int, default=1000, help='Number of file')
    parser.add_argument('--io-pattern', type=str, choices=['sequential', 'random'], default='sequential', help='I/O pattern: sequential or random')
    parser.add_argument(
        '-w', '--write-file',
        type=str,
        nargs='?',
        const='performance_test.json',
        help='Write the output to a file. Default file is "performance_test.json". If a filename is provided, it will be used instead.',
        default=None
    )
    return parser


def print_banner():
    if not pconf().args.quiet:
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


def find_all_arguments(parser):
    args = {}
    for action in parser._actions:
        if action.option_strings:  # Positional arguments have an empty option_strings list
            args[action.dest] = action.option_strings
    return args


def create_argument_dict(namespace, all_arguments):
    namespace_copy = deepcopy(namespace.__dict__)
    combined_args_dict = {}
    for arg_dest, arg_value in namespace_copy.items():
        if arg_dest in all_arguments:
            combined_arg_names = ", ".join(all_arguments[arg_dest])
            combined_args_dict[combined_arg_names] = arg_value
    return combined_args_dict


def print_unless_quiet_mode(message=""):
    if not pconf().args.quiet:
        pawn.console.print(message)


def run_disk_performance_test(args):
    disk_tester = DiskPerformanceTester(
        file_path=args.file_path,
        file_size_mb=args.file_size_mb,
        iterations=args.iterations,
        block_size_kb=args.block_size_kb,
        num_threads=args.num_threads,
        io_pattern=args.io_pattern,
        verbose=args.verbose > 1,
    )
    disk_tester.console.log(f'Measuring write and read speed for {args.file_size_mb}MB with {args.block_size_kb}KB block size, {args.iterations} iterations, {args.num_threads} threads, {args.io_pattern} I/O pattern...')
    test_results = disk_tester.run_parallel_tests()
    test_results["resource_usages"] = get_cpu_load()
    disk_tester.print_summary()

    return test_results


def run_filesystem_performance_test(args):
    fs_tester = FileSystemTester(
        test_dir=args.file_path,
        file_count=args.count,
        file_size=args.file_size_mb,
        iterations=args.iterations,
        verbose=args.verbose > 1
    )
    test_results = fs_tester.run_tests()
    test_results["resource_usages"] = get_cpu_load()
    return test_results


def display_system_info(system_info):
    tree = Tree("[bold blue]🖥️ System Information[/bold blue]")

    for key, value in system_info.items():
        if key == "disk_usages":
            disk_usages_tree = tree.add("[bold green]💾 Disk Usages[/bold green]")
            for mount_point, usage in value.items():
                # disk_usages_tree.add(
                #     f"{mount_point}: [yellow]Total[/yellow]: {usage['total']} {usage['unit']}, "
                #     f"[red]Used[/red]: {usage['used']} {usage['unit']}, [green]Free[/green]: {usage['free']} {usage['unit']}, "
                #     f"[magenta]Percent Used[/magenta]: {usage['percent']}%"
                # )
                color,  percent = get_color_by_threshold(usage['percent'], return_tuple=True)
                usage_line = f"[{color}]{usage['used']:>7} / {usage['total']:>7} {usage['unit']} ({percent}%) [/{color}]"
                disk_usages_tree.add(f"{mount_point:>10} : {usage_line}")

        elif key == "arguments":
            pass
            # arguments_tree = tree.add("[bold cyan]⚙️ Arguments[/bold cyan]")
            # for arg, arg_value in value.items():
            #     arguments_tree.add(f"{arg}: {arg_value}")
        else:
            tree.add(f"{key.replace('_', ' ').title()}: {value}")

    pawn.console.print(Panel(tree, title="🖥️ [bold blue]System Information[/bold blue]"))


def display_performance_results(disk_performance_result=None, filesystem_performance_result=None):
    tree = Tree("[bold blue]📊 Performance Results[/bold blue]")

    if disk_performance_result:
        disk_perf_tree = tree.add("[bold yellow]💽 Disk Performance[/bold yellow]")
        disk_perf_tree.add(f"Write Speeds (MB/s): {disk_performance_result['write_speeds']}")
        disk_perf_tree.add(f"Average Write Speed (MB/s): {disk_performance_result['average_write_speed']}")
        disk_perf_tree.add(f"Read Speeds (MB/s): {disk_performance_result['read_speeds']}")
        disk_perf_tree.add(f"Average Read Speed (MB/s): {disk_performance_result['average_read_speed']}")

        resource_usages_tree = disk_perf_tree.add("[bold magenta]🔧 Resource Usages[/bold magenta]")
        for period, load in disk_performance_result['resource_usages'].items():
            resource_usages_tree.add(f"{period}: {load}")

    if filesystem_performance_result:
        fs_perf_tree = tree.add("[bold green]🗄️ Filesystem Performance[/bold green]")
        for key, value in filesystem_performance_result.items():
            if key != "resource_usages":
                fs_perf_tree.add(f"{key.replace('_', ' ').title()}: {value}")

        fs_resource_usages_tree = fs_perf_tree.add("[bold magenta]🔧 Resource Usages[/bold magenta]")
        for period, load in filesystem_performance_result['resource_usages'].items():
            fs_resource_usages_tree.add(f"{period}: {load}")

    if tree:
        pawn.console.print(Panel(tree, title="📊 [bold blue]Performance Results[/bold blue]"))


def main():
    app_name = 'Server Checker'
    parser = get_parser()
    command_definitions = {
        "disk": {
            "functions": [run_disk_performance_test],
            "result_keys": ["disk_performance_result"],
        },
        "fs": {
            "functions": [run_filesystem_performance_test],
            "result_keys": ["filesystem_performance_result"],
        },
        "all": {
            "functions": [run_disk_performance_test, run_filesystem_performance_test],
            "result_keys": ["disk_performance_result", "filesystem_performance_result"],
        }
    }

    args, unknown = parser.parse_known_args()
    config_file = args.config_file

    is_hide_line_number = args.verbose > 2
    stdout = not args.quiet

    pawn.set(
        app_name=app_name,
        PAWN_CONFIG_FILE=config_file,
        PAWN_PATH=args.base_dir,
        PAWN_CONSOLE=dict(
            redirect=True,
            record=True,
            log_path=is_hide_line_number, # hide line number on the right side
        ),
        args=args,
        try_pass=False,
        last_execute_point=0,
        data={},
        fail_count=0,
        total_count=0,
        PAWN_LINE=False,
    )

    if args.verbose > 2:
        pawn.set(
            PAWN_LINE=True,
            PAWN_LOGGER=dict(
                log_level="DEBUG",
                stdout_level="DEBUG",
            )
        )

    print_banner()

    all_args = find_all_arguments(parser)
    argument_dict = create_argument_dict(args, all_args)

    print_grid(argument_dict, title="Arguments", key_prefix="", key_ratio=2)

    test_results = {
        "system_info": get_platform_info(
            **dict(
                disk_usages=DiskUsage().get_disk_usage('all'),
                arguments=argument_dict
            )
        ),
    }

    if not args.command:
        parser.print_help()
        sys_exit(f"\nError: A valid command is required. Please choose from ({', '.join(VALID_COMMANDS)}).\n")

    # Execute the functions and store the results based on the command
    if args.command in command_definitions:
        command_info = command_definitions[args.command]
        for func, result_key in zip(command_info["functions"], command_info["result_keys"]):
            test_results[result_key] = func(args)
    else:
        parser.error(f"'{args.command}' is not a valid command.")

    # Display all information
    display_system_info(test_results['system_info'])
    display_performance_results(test_results.get('disk_performance_result'), test_results.get('filesystem_performance_result'))

    if args.write_file:
        write_res = write_json(filename=args.write_file, data=test_results)
        pawn.console.log(write_res)


main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        pawn.console.log(e)

