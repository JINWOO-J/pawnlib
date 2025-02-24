#!/usr/bin/env python3
import argparse
import os
import re
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import setup_app_logger
from pawnlib.utils.operate_handler import execute_command
import yaml
import json


logger = setup_app_logger()
__description__ = 'Convert terraform output to structured data and optionally to YAML.'
__epilog__ = (
    "Usage examples:\n"
    "  1. Convert terraform output to structured JSON/YAML:\n"
    "     `pawns tf output`\n\n"
    "  2. Save the output to a file:\n"
    "     `pawns tf output -o output.yaml`\n"
)

def get_parser():
    parser = argparse.ArgumentParser(description=__description__, epilog=__epilog__)
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument(
        'command',
        help="Specify the command to execute. Available options: ['output']",
        choices=['output'],
        nargs="?"
    )
    parser.add_argument("--cwd", "-c", type=str, help="Directory to run terraform command.", default=os.getcwd())
    parser.add_argument("--output-file", "-o", type=str, help="Output file path.", default="")
    parser.add_argument("--ansible", "-a",
                        action='store_true', default=False,
                        help='Enable Ansible hosts file generation [default: False]')
    return parser


def generate_ansible_hosts(data):
    """
    Generate Ansible hosts inventory from processed data
    :param data: Processed Terraform output data
    :return: Formatted Ansible hosts content
    """
    hosts_content = []
    for tag, instances in data.items():
        hosts_content.append(f"[{tag}]")
        for instance in instances:
            if isinstance(instance, dict) and instance.get("IPADDR"):
                ipaddress = instance.get("IPADDR")
            else:
                ipaddress = instance

            hosts_content.append(ipaddress)
        hosts_content.append("")
    return '\n'.join(hosts_content)


def run_terraform_command(cwd):
    """
    Execute the Terraform output command and return its JSON output as a dictionary.

    :param cwd: Directory to run the Terraform command.
    :return: Parsed JSON dictionary of Terraform output.
    """
    result = execute_command("terraform output -json", cwd=cwd)
    stdout = result.get('stdout', '')

    stdout = ''.join(stdout)

    if stdout:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Terraform output JSON: {e}")
    return {}


def clean_json_data(obj, remove_sensitive=True, flatten_value=True):
    """
    Recursively clean the JSON data by removing 'sensitive' and flattening 'value'.
    """
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            if remove_sensitive and k == "sensitive":
                continue
            if flatten_value and k == "value" and not isinstance(v, dict):
                return clean_json_data(v)
            cleaned[k] = clean_json_data(v, remove_sensitive, flatten_value)
        return cleaned
    elif isinstance(obj, list):
        return [clean_json_data(item, remove_sensitive, flatten_value) for item in obj]
    return obj


def augment_with_zone_and_tags(data):
    """
    Add zone and tag metadata to the processed data.

    :param data: Input dictionary.
    :return: Updated dictionary with zone and tag metadata.
    """
    zone_data = {}
    tag_data = {}

    instances = data.get("instance_info", {}).get("value", {})
    for instance, details in instances.items():
        zone = details.get("zone")
        name = details.get("name")
        public_ip = details.get("public_ip")

        if zone:
            zone_data.setdefault(zone, []).append({"Name": name, "IPADDR": public_ip})

        for tag in details.get("tags", []):
            tag_data.setdefault(tag, []).append({"Name": name, "IPADDR": public_ip, "Zone": zone})

    data["zones"] = zone_data
    data["tags"] = tag_data
    return data


def remove_unnecessary_keys(data, keys_to_remove):
    """
    Remove specified keys from the data.

    :param data: Input dictionary.
    :param keys_to_remove: List of keys to remove.
    :return: Cleaned dictionary.
    """
    if isinstance(data, dict):
        return {k: remove_unnecessary_keys(v, keys_to_remove) for k, v in data.items() if k not in keys_to_remove}
    elif isinstance(data, list):
        return [remove_unnecessary_keys(item, keys_to_remove) for item in data]
    return data


def restructure_data(data, keys_to_move):
    """
    Move specified keys to the root of the dictionary.

    :param data: Original dictionary.
    :param keys_to_move: List of keys to move.
    :return: Restructured dictionary.
    """
    for key in keys_to_move:
        if key in data:
            value = data.pop(key)
            if isinstance(value, dict):
                data.update(value)
            else:
                data[key] = value
    return data


def convert_to_yaml_format(data):
    """
    Convert the given dictionary to a YAML-formatted string with spacing.

    :param data: Input dictionary.
    :return: YAML-formatted string.
    """
    yaml_output = yaml.dump(data, default_flow_style=False, sort_keys=False)
    yaml_output = re.sub(r'(\n)([^\s-])', r'\n\n\2', yaml_output)
    yaml_output = yaml_output.lstrip('\n')
    return yaml_output


def main():
    banner = generate_banner(
        app_name="Terraform Helper",
        author="jinwoo",
        description=__description__,
        font="graffiti",
        version=_version
    )
    print(banner)

    parser = get_parser()
    args, unknown = parser.parse_known_args()
    logger.info(f"args = {args}")
    logger.info(f"Processing Terraform data from directory: {args.cwd}")

    terraform_data = run_terraform_command(cwd=args.cwd)
    if not terraform_data:
        logger.error("Failed to retrieve Terraform output. Exiting.")
        return

    cleaned_data = clean_json_data(terraform_data)
    augmented_data = augment_with_zone_and_tags(cleaned_data)
    processed_data = remove_unnecessary_keys(augmented_data, ['instance_info', 'private_ips', 'lb_ips'])
    final_data = restructure_data(processed_data, ['zones', 'tags'])

    if args.ansible:
        output_content = generate_ansible_hosts(final_data)
        output_type_prefix_msg = "🔧 Ansible Hosts \n"
    else:
        output_content = convert_to_yaml_format(final_data)
        output_type_prefix_msg = "📄 YAML Output \n"

    logger.info(f"{output_type_prefix_msg}{output_content}".replace('[', '\['))

    if args.output_file and output_content:
        with open(args.output_file, 'w') as file:
            file.write(output_content)
        logger.info(f"🎯Output saved to {args.output_file}")


main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':
    main()
