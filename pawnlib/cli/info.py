#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf
import os
from pawnlib.typing import str2bool, StackList, remove_tags, dict_to_line
from pawnlib.output import write_json, get_color_by_threshold
from rich.tree import Tree
from pawnlib.resource import (
    get_interface_ips,
    get_public_ip,
    get_hostname,
    get_platform_info,
    get_rlimit_nofile,
    get_mem_info,
    get_location,
    get_location_with_ip_api,
    DiskUsage
)

from pawnlib.resource.server import get_uptime, get_swap_usage, get_load_average

__description__ = "This command displays server resource information."

__epilog__ = (
    "This tool provides a detailed overview of your server's system and network resources.\n\n"
    "Usage examples:\n"
    "  1. Display all resource information in verbose mode:\n"
    "     - Displays detailed information about system and network resources.\n\n"
    "     `pawns info -v`\n"


    "  2. Run in quiet mode without displaying any output:\n"
    "     - Executes the script without showing any output, useful for logging purposes.\n\n"
    "     `pawns info -q`\n"
    

    "  3. Specify a custom base directory and configuration file:\n"
    "     - Uses the specified base directory and configuration file for operations.\n\n"
    "     `pawns info -b /path/to/base/dir --config-file my_config.ini`\n"
    

    "  4. Write output to a specified file in quiet mode without displaying any output:\n"
    "     - Writes the collected resource information to 'output.json'.\n\n"
    "    `pawns info -q --output-file output.json`\n\n"


    "For more detailed command usage and options, refer to the help documentation by running 'pawns info --help'."
)


def get_parser():
    parser = argparse.ArgumentParser(description='monitor')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    # parser.add_argument('url', help='url', type=str, nargs='?', default="")
    parser.add_argument('-c', '--config-file', type=str, help='config', default="config.ini")
    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level (default: %(default)s)', default=1)
    parser.add_argument('-q', '--quiet', action='count', help='Quiet mode. Dont show any messages. (default: %(default)s)', default=0)
    parser.add_argument('-b', '--base-dir', type=str, help='base dir for httping (default: %(default)s)', default=os.getcwd())
    parser.add_argument('-d', '--debug',  action='count', help='base dir for httping (default: %(default)s)', default=0)
    parser.add_argument('--ip-api-provider', type=str, help='API provider to fetch public IP information (e.g., ip-api.com, another-api.com)', default="ip-api.com")
    # parser.add_argument( "-o", "--output-file", type=str, help="The name of the file to write the output to.", default="", )
    parser.add_argument(
        '-w', '--write-file',
        type=str,
        nargs='?',
        const='resource_info.json',
        help='Write the output to a file. Default file is "resource_info.json". If a filename is provided, it will be used instead.',
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
        "disk": {},
    }


    system_tree = Tree("[bold]🖥️  System Information[/bold]")
    system_tree.add(f"Hostname:  {get_hostname()}")
    for k, v in get_platform_info().items():
        system_tree.add(f"{k.title()}: {v}")
        result['system'][k] = v

    result['system']['mem_total'] = get_mem_info().get('mem_total')
    system_tree.add(f"Memory: {result['system']['mem_total']} GB")

    result['system']["resource_limit"] = get_rlimit_nofile(detail=bool(args.debug))

    # system_tree.add(f"Resource limit: {result['system']['resource_limit']}")
    resource_tree = system_tree.add(f"Resource limit")
    for k, v in result['system']['resource_limit'].items():
        resource_tree.add(f"{k.title()}: {v}")

    system_tree.add(f"Swap Usage : {get_swap_usage()}")
    system_tree.add(f"CPU Load : {get_load_average()}")
    system_tree.add(f"Uptime: {get_uptime()}")

    print_unless_quiet_mode(system_tree)
    print_unless_quiet_mode("")

    network_tree = Tree("[bold]🛜 Network Interface[/bold]")

    if args.ip_api_provider == "ip-api.com":
        public_ip_info = get_location_with_ip_api()
        if  public_ip_info.get('status'):
            del public_ip_info['status']
        result['network']['public_ip'] = {"ip":  public_ip_info.get('query')}
        public_ip_tree = network_tree.add(f"[bold] Public IP[/bold]: {result['network']['public_ip']['ip']}")

        if result['network']['public_ip']:
            result['network']['public_ip'].update(public_ip_info)
            public_ip_tree.add(f"[bold] Region : {public_ip_info.get('countryCode')}, {public_ip_info.get('regionName')}, {public_ip_info.get('city')}, "
                               f"{public_ip_info.get('country')}, Timezone={public_ip_info.get('timezone')}")
            public_ip_tree.add(f"[bold] ASN : {public_ip_info.get('as')}, ISP: {public_ip_info.get('isp')}, ORG: {public_ip_info.get('org')}")

    else:
        result['network']['public_ip'] = {"ip":  get_public_ip()}
        public_ip_tree= network_tree.add(f"[bold] Public IP[/bold]: {result['network']['public_ip']['ip']}")

        if result['network']['public_ip']:
            _location = get_location(result['network']['public_ip']['ip'])
            if _location:
                result['network']['public_ip'].update(_location)
                public_ip_tree.add(f"[bold] Region : {_location.get('region')}, Timezone={_location.get('timezone')}")
                public_ip_tree.add(f"[bold] ASN : {dict_to_line(_location.get('asn'), end_separator=', ')}")

    local_tree = network_tree.add("[bold] Local IP[/bold]")
    interface_list = get_interface_ips(ignore_interfaces=['lo0', 'lo'], detail=True)

    if interface_list:
        longest_length = max(len(item[0]) for item in interface_list)

        for interface, ipaddr in interface_list:
            subnet_str = f" / {ipaddr.get('subnet')}" if ipaddr.get('subnet') else ""
            gateway_str = f", G/W: {ipaddr.get('gateway')}" if ipaddr.get('gateway') else ""
            formatted_ipaddr = f"{ipaddr.get('ip'):<10}{subnet_str}{gateway_str}"

            result['network'][interface] = ipaddr
            if "gateway" in ipaddr:
                interface = f"[bold blue][on #050B27]{interface:<{longest_length}} [/bold blue]"
                formatted_ipaddr = f"{formatted_ipaddr}[/on #050B27]"
            local_tree.add(f"[bold]{interface:<{longest_length+1}}[/bold]: {formatted_ipaddr}")
        print_unless_quiet_mode(network_tree)
        print_unless_quiet_mode("")

    disk_usage = DiskUsage()
    disk_usage_result = disk_usage.get_disk_usage("all", unit="auto")
    result['disk'] = disk_usage_result

    disk_tree = Tree("[bold]💾 Disk Usage[/bold]")
    for mount_point, usage in disk_usage_result.items():
        color,  percent = get_color_by_threshold(usage['percent'], return_tuple=True)
        color_unit = f"[grey74]{usage['unit']}[/grey74]"
        usage_line = f"[{color}]{usage['used']:>7}[/{color}] {color_unit}[{color}] / {usage['total']:>7}[/{color}] {color_unit} [{color}]({percent}%)[/{color}] "
        disk_tree.add(f"[bold blue]{mount_point:<11}[/bold blue][dim]{usage['device']}[/dim]: {usage_line}")

    print_unless_quiet_mode(disk_tree)

    if args.write_file:
        write_res = write_json(filename=args.write_file, data=result)
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

