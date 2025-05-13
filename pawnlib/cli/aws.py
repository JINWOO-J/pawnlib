#!/usr/bin/env python3

import asyncio
import json
import argparse
from rich.console import Console
from rich.table import Table
import os
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn
from pawnlib.output import write_json, syntax_highlight, PrintRichTable
from pawnlib.typing.converter import FlatDict, FlatterDict, flatten_dict
from pawnlib.resource import server, aws
from datetime import datetime
import aioboto3

__description__ = 'Get meta information from AWS EC2 and manage Route53 hosted zones.'

__epilog__ = (
    "This script retrieves metadata from AWS EC2 instances and manages Route53 hosted zones.\n\n"
    "Usage examples:\n"
    "  1. Retrieve AWS metadata in JSON format:\n"
    "     - Retrieves metadata from the specified IP address (default: 169.254.169.254) and prints it in JSON format.\n\n"
    "     `pawns aws --metadata-ip 169.254.169.254 --output-format json`\n\n"
    "  2. Retrieve AWS metadata in flattened format:\n"
    "     - Retrieves metadata and prints it in a flattened format.\n\n"
    "     `pawns aws --output-format flat`\n\n"
    "  3. Specify a custom timeout for the request:\n"
    "     - Sets the timeout for the request to 5 seconds.\n\n"
    "     `pawns aws --timeout 5`\n\n"
    "  4. Write AWS metadata to a file:\n"
    "     - Writes the retrieved metadata to a file named 'metadata.json'.\n\n"
    "     `pawns aws --output-file metadata.json`\n\n"
    "  5. Backup a Route53 hosted zone:\n"
    "     - Backs up a specific hosted zone to a JSON file.\n\n"
    "     `pawns aws route53 backup /hostedzone/Z123456789 backup.json`\n\n"
    "  6. Backup all Route53 hosted zones:\n"
    "     - Backs up all hosted zones to a timestamped directory.\n\n"
    "     `pawns aws route53 backup all`\n\n"
    "  7. Restore a Route53 hosted zone:\n"
    "     - Restores a hosted zone from a backup file.\n\n"
    "     `pawns aws route53 restore backup.json example.com`\n\n"
    "  8. List Route53 hosted zones:\n"
    "     - Displays information about all hosted zones.\n\n"
    "     `pawns aws route53 ls`\n\n"
    "For more information and options, use the -h or --help flag."
)

def json_serializable(obj):
    """datetime 객체를 JSON 직렬화 가능하도록 변환합니다."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

async def backup_route53_zone_async(session, zone_id, backup_file):
    """Route53 호스팅 영역의 레코드 세트를 비동기로 백업하여 JSON 파일로 저장합니다."""
    async with session.client('route53') as route53:
        zone = await route53.get_hosted_zone(Id=zone_id)
        zone = zone['HostedZone']
        records = await route53.list_resource_record_sets(HostedZoneId=zone_id)
        records = records['ResourceRecordSets']
        
        backup_data = {
            'HostedZone': zone,
            'ResourceRecordSets': records
        }
        
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=4, default=json_serializable)
        pawn.console.log(f"Route53 호스팅 영역이 {backup_file}에 백업되었습니다.")

async def restore_route53_zone_async(session, backup_file, new_zone_name):
    """백업 파일을 읽어 새로운 Route53 호스팅 영역을 비동기로 생성하고 레코드 세트를 복원합니다."""
    async with session.client('route53') as route53:
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        new_zone = await route53.create_hosted_zone(
            Name=new_zone_name,
            CallerReference=f"{new_zone_name}-{datetime.now().isoformat()}",
            HostedZoneConfig={
                'Comment': backup_data['HostedZone'].get('Config', {}).get('Comment', ''),
                'PrivateZone': backup_data['HostedZone'].get('Config', {}).get('PrivateZone', False)
            }
        )
        new_zone = new_zone['HostedZone']
        new_zone_id = new_zone['Id']
        
        for record in backup_data['ResourceRecordSets']:
            if record['Type'] not in ['SOA', 'NS']:
                await route53.change_resource_record_sets(
                    HostedZoneId=new_zone_id,
                    ChangeBatch={
                        'Changes': [{
                            'Action': 'CREATE',
                            'ResourceRecordSet': record
                        }]
                    }
                )
        
        pawn.console.log(f"새 Route53 호스팅 영역이 생성되었습니다. ID: {new_zone_id}")

async def get_route53_info_async(session):
    """현재 계정의 Route53 호스팅 영역 정보를 비동기로 반환합니다."""
    async with session.client('route53') as route53:
        zones = await route53.list_hosted_zones()
        return zones['HostedZones']

async def print_ls_route53_info_async(profile_name=None):
    """현재 Route53 호스팅 영역 정보를 Rich 표로 비동기로 출력합니다."""
    session = aioboto3.Session(profile_name=profile_name)
    async with session.client('route53') as route53:
        zones = await route53.list_hosted_zones()
        zones = zones['HostedZones']
        
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Zone Name", style="dim")
        table.add_column("Zone ID")
        table.add_column("Comment")
        table.add_column("Record Count")
        table.add_column("A Records")
        table.add_column("CNAME Records")
        table.add_column("MX Records")
        table.add_column("Health Checks")
        table.add_column("Private Zone")
        table.add_column("Created Time")
        
        tasks = [get_zone_details_async(route53, zone) for zone in zones]
        results = await asyncio.gather(*tasks)
        
        for zone, records in results:
            record_types = {'A': 0, 'CNAME': 0, 'MX': 0}
            health_check_count = 0
            for record in records:
                if record['Type'] in record_types:
                    record_types[record['Type']] += 1
                if 'HealthCheckId' in record:
                    health_check_count += 1
            
            table.add_row(
                zone['Name'],
                zone['Id'],
                zone.get('Config', {}).get('Comment', 'N/A'),
                str(len(records)),
                str(record_types['A']),
                str(record_types['CNAME']),
                str(record_types['MX']),
                str(health_check_count),
                str(zone.get('Config', {}).get('PrivateZone', False)),
                str(zone.get('CreatedTime', 'N/A'))
            )
        
        console.print(table)

async def get_zone_details_async(route53, zone):
    """호스팅 영역의 레코드 세트를 비동기로 조회합니다."""
    records = await route53.list_resource_record_sets(HostedZoneId=zone['Id'])
    return zone, records['ResourceRecordSets']

def get_parser():
    parser = argparse.ArgumentParser(description=__description__, epilog=__epilog__)
    parser = get_arguments(parser)
    return parser

def get_arguments(parser):
    # EC2 Metadata 관련 인자
    parser.add_argument(
        "--metadata-ip", "-i", type=str,
        help="The IP address for retrieving metadata. Default is 169.254.169.254.",
        default="169.254.169.254"
    )
    parser.add_argument(
        "--timeout", "-t", type=float,
        help="The timeout in seconds for the request. Default is 2 seconds.",
        default=2,
    )
    parser.add_argument(
        "--output-file", "-o", type=str,
        help="The name of the file to write the output to.",
        default="",
    )
    parser.add_argument(
        "--output-format", "-f", type=str, choices=["json", "flat"],
        help="The format of the output. Choose between 'json' or 'flat'. Default is 'json'.",
        default="json"
    )
    
    # Route53 관련 서브커맨드
    subparsers = parser.add_subparsers(dest='subcommand', help="Subcommands: route53")
    
    route53_parser = subparsers.add_parser('route53', help="Route53 management commands")
    route53_subparsers = route53_parser.add_subparsers(dest='command', help="Route53 commands: backup, restore, ls")
    
    backup_parser = route53_subparsers.add_parser('backup', help="Route53 hosted zone backup")
    backup_parser.add_argument('zone_id', help="Hosted zone ID to backup or 'all' for all zones")
    backup_parser.add_argument('backup_file', nargs='?', help="Backup file name (JSON format)", default="default_backup.json")
    backup_parser.add_argument('--profile', help="AWS profile to use (optional)", default=None)
    
    restore_parser = route53_subparsers.add_parser('restore', help="Restore Route53 hosted zone from backup")
    restore_parser.add_argument('backup_file', help="Backup file name (JSON format)")
    restore_parser.add_argument('new_zone_name', help="Name of the new hosted zone")
    restore_parser.add_argument('--profile', help="AWS profile to use (optional)", default=None)
    
    ls_parser = route53_subparsers.add_parser('ls', help="List Route53 hosted zones")
    ls_parser.add_argument('--profile', help="AWS profile to use (optional)", default=None)
    
    return parser

def main():
    banner = generate_banner(
        app_name="aws metadata & route53",
        author="jinwoo",
        description="get aws metadata and manage route53",
        font="graffiti",
        version=_version
    )
    print(banner)

    parser = get_parser()
    args, unknown = parser.parse_known_args()

    pawn.console.log(f"args = {args}")

    if args.subcommand == 'route53':
        # Route53Manager 인스턴스 생성
        manager = aws.Route53Manager(profile_name=args.profile)
        
        if args.command == 'backup':
            if args.zone_id == "all":
                asyncio.run(manager.backup_all_zones())
            else:
                asyncio.run(manager.backup_zone(args.zone_id, args.backup_file))
        elif args.command == 'restore':
            asyncio.run(manager.restore_zone(args.backup_file, args.new_zone_name))
        elif args.command == 'ls':
            asyncio.run(manager.list_zones())
    else:
        # EC2 Metadata 처리
        res = server.get_aws_metadata(meta_ip=args.metadata_ip, timeout=args.timeout)
        if args.output_format == "json":
            print(syntax_highlight(res))
        elif args.output_format == "flat":
            PrintRichTable(
                title="AWS Metadata",
                data=flatten_dict(res),
                columns_options=dict(
                    value=dict(
                        justify="left",
                    )
                )
            )
        
        if args.output_file:
            write_res = write_json(filename=args.output_file, data=res)
            pawn.console.log(f"Output written to {write_res}")


main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == "__main__":
    main()