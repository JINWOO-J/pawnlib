#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf
import os
from pawnlib.typing import str2bool, StackList, remove_tags, dict_to_line
from pawnlib.output import write_json
from rich.tree import Tree
from pawnlib.resource import get_interface_ips, get_public_ip, get_hostname, get_platform_info, get_rlimit_nofile, get_mem_info, get_location

__description__ = "This command displays server resource information."

__epilog__ = (
    "This tool provides a detailed overview of your server's system and network resources.\n\n"
    "Usage examples:\n"
    "  1. Display all resource information in verbose mode:\n"
    "     pawns info -v\n"
    "     - Displays detailed information about system and network resources.\n\n"

    "  2. Run in quiet mode without displaying any output:\n"
    "     pawns info -q\n"
    "     - Executes the script without showing any output, useful for logging purposes.\n\n"

    "  3. Specify a custom base directory and configuration file:\n"
    "     pawns info -b /path/to/base/dir --config-file my_config.ini\n"
    "     - Uses the specified base directory and configuration file for operations.\n\n"

    "  4. Write output to a specified file in quiet mode without displaying any output:\n"
    "     pawns info -q --output-file output.json\n"
    "     - Writes the collected resource information to 'output.json'.\n\n"

    "For more detailed command usage and options, refer to the help documentation by running 'pawns info --help'."
)


def get_parser():
    parser = argparse.ArgumentParser(description='monitor')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument('url', help='url', type=str, nargs='?', default="")
    parser.add_argument('-c', '--config-file', type=str, help='config', default="config.ini")
    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level (default: %(default)s)', default=1)
    parser.add_argument('-q', '--quiet', action='count', help='Quiet mode. Dont show any messages. (default: %(default)s)', default=0)
    parser.add_argument('-b', '--base-dir', type=str, help='base dir for httping (default: %(default)s)', default=os.getcwd())
    parser.add_argument("--output-file", "-o", type=str, help="The name of the file to write the output to.", default="", )
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


def print_unless_quiet_mode(message=""):
    if not pconf().args.quiet:
        pawn.console.print(message)


def main():
    app_name = 'Resource Information'
    parser = get_parser()
    args, unknown = parser.parse_known_args()
    config_file = args.config_file

    pawn.console.debug(args)
    is_hide_line_number = args.verbose > 2
    stdout = not args.quiet

    pawn.set(
        PAWN_CONFIG_FILE=config_file,
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
            )
        )
    print_banner()

    result = {
        "system": {},
        "network": {},
    }

    system_tree = Tree("[bold]🖥️  System Information[/bold]")
    system_tree.add(f"Hostname:  {get_hostname()}")
    for k, v in get_platform_info().items():
        system_tree.add(f"{k.title()}: {v}")
        result['system'][k] = v

    result['system']['mem_total'] = get_mem_info().get('mem_total')
    system_tree.add(f"Memory: {result['system']['mem_total']} GB")

    result['system']["resource_limit"] = get_rlimit_nofile()
    system_tree.add(f"Resource limit: {result['system']['resource_limit']}")

    print_unless_quiet_mode(system_tree)
    print_unless_quiet_mode("")

    network_tree = Tree("[bold]🛜 Network Interface[/bold]")
    result['network']['public_ip'] = get_public_ip()
    public_ip_tree= network_tree.add(f"[bold] Public IP[/bold]: {result['network']['public_ip']}")

    if result['network']['public_ip']:
        _location = get_location(result['network']['public_ip'])
        if _location:
            public_ip_tree.add(f"[bold] Region : {_location.get('region')}, Timezone={_location.get('timezone')}")
            public_ip_tree.add(f"[bold] ASN : {dict_to_line(_location.get('asn'), end_separator=', ')}")

    local_tree = network_tree.add("[bold] Local IP[/bold]")

    interface_list = get_interface_ips(ignore_interfaces=['lo0', 'lo'])

    if interface_list:
        longest_length = max(len(item[0]) for item in interface_list)

        for interface, ipaddr in get_interface_ips(ignore_interfaces=['lo0', 'lo']):
            result['network'][interface] = ipaddr
            if "G/W" in ipaddr:
                interface = f"[bold blue][on #050B27]{interface:<{longest_length}} [/bold blue]"
                ipaddr = f"{ipaddr}[/on #050B27]"
            local_tree.add(f"[bold]{interface:<{longest_length+1}}[/bold]: {ipaddr}")
        print_unless_quiet_mode(network_tree)

        if args.output_file:
            write_res = write_json(filename=args.output_file, data=result)
            pawn.console.log(write_res)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        pawn.console.log(e)

