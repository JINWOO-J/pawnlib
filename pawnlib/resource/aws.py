import asyncio
import json
import os
from datetime import datetime
import aioboto3

from rich.table import Table
from pawnlib.config import pawn
from pawnlib.output import print_var
import boto3


def get_boto3_session(profile_name=None):
    """boto3.Session을 생성하고 자격 증명을 로깅합니다."""
    if profile_name:
        pawn.console.log(f"Using AWS profile: {profile_name}")
        session = boto3.Session(profile_name=profile_name)
    else:
        if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
            pawn.console.log("Using AWS Environment Variables")
        else:
            pawn.console.log("Using default AWS settings (e.g., IAM role)")
        session = boto3.Session()
    
    credentials = session.get_credentials()
    if credentials:
        pawn.console.debug(f"Profile: {profile_name}, Access Key ID: {credentials.access_key}, Region: {session.region_name}")
    else:
        pawn.console.debug("No credentials found.")
    return session


def log_aws_credentials(aws_access_key_id=None, aws_secret_access_key=None, aws_session_token=None, region_name=None):
        """현재 사용 중인 AWS 자격 증명을 확인하고 로깅."""
        # aioboto3.Session에서 boto3.Session 생성
        boto_session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=region_name
        )
        credentials = boto_session.get_credentials()

        if credentials:
            pawn.console.debug(f"현재 사용 중인 Access Key ID: {credentials.access_key}")
            if credentials.token:
                pawn.console.debug("AWS_SESSION_TOKEN이 설정되어 있습니다.")
        else:
            pawn.console.debug("자격 증명을 찾을 수 없습니다.")


class Route53Manager:
    def __init__(self, profile_name=None, debug=False):
        """Route53Manager 초기화. AWS 프로파일을 설정합니다."""


        if profile_name:
            self.session = aioboto3.Session(profile_name=profile_name)
        else:
            pawn.console.log(f"Using AWS Environment Variables")
            self.session = aioboto3.Session()

        if debug or pawn.get('DEBUG'):
            get_boto3_session(profile_name=profile_name)    


        # self.boto_session = get_boto3_session(profile_name=profile_name)
        
        # credentials = self.boto_session.get_credentials()
        # self.session = aioboto3.Session(
        #     aws_access_key_id=credentials.access_key,
        #     aws_secret_access_key=credentials.secret_key,
        #     aws_session_token=credentials.token,
        #     region_name=self.boto_session.region_name
        # )
                

    def _client(self):
        return self.session.client('route53')

    async def backup_zone(self, zone_id, backup_file):
        """단일 호스팅 영역을 백업합니다."""
        async with self._client() as route53:
            zone = await route53.get_hosted_zone(Id=zone_id)
            zone = zone['HostedZone']
            records = await route53.list_resource_record_sets(HostedZoneId=zone_id)
            records = records['ResourceRecordSets']
            
            backup_data = {
                'HostedZone': zone,
                'ResourceRecordSets': records
            }
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=4)
            print(f"Route53 호스팅 영역이 {backup_file}에 백업되었습니다.")

    async def backup_all_zones(self):
        """모든 호스팅 영역을 백업합니다."""
        zones = await self.get_zones()
        base_directory = f"route53_backups/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        os.makedirs(base_directory, exist_ok=True)
        tasks = [
            self.backup_zone(zone['Id'], f"{base_directory}/{zone['Name'].replace('.', '_')}.json")
            for zone in zones
        ]
        await asyncio.gather(*tasks)

    async def restore_zone(self, backup_file, new_zone_name):
        """백업 파일에서 호스팅 영역을 복원합니다."""
        async with self._client() as route53:
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
            new_zone_id = new_zone['HostedZone']['Id']
            
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
            print(f"새 Route53 호스팅 영역이 생성되었습니다. ID: {new_zone_id}")

    async def get_zones(self):
        """모든 호스팅 영역 목록을 반환합니다."""
        async with self._client() as route53:
            zones = await route53.list_hosted_zones()
            return zones['HostedZones']

    async def get_zone_details_async(self, zone):
        """호스팅 영역의 레코드 세트를 비동기로 조회합니다."""
        async with self._client() as route53:
            records = await route53.list_resource_record_sets(HostedZoneId=zone['Id'])
            return zone, records['ResourceRecordSets']

    async def get_zones_with_details(self):
        """호스팅 영역과 그에 대한 세부 정보를 비동기로 가져와 가공합니다."""
        zones = await self.get_zones()
        tasks = [self.get_zone_details_async(zone) for zone in zones]
        results = await asyncio.gather(*tasks)
        
        zones_data = []
        for zone, records in results:
            record_types = {'A': 0, 'CNAME': 0, 'MX': 0}
            health_check_count = 0
            for record in records:
                if record['Type'] in record_types:
                    record_types[record['Type']] += 1
                if 'HealthCheckId' in record:
                    health_check_count += 1
            
            zone_data = {
                'Name': zone['Name'],
                'Id': zone['Id'],
                'Comment': zone.get('Config', {}).get('Comment', 'N/A'),
                'RecordCount': len(records),
                'ARecords': record_types['A'],
                'CNAMERecords': record_types['CNAME'],
                'MXRecords': record_types['MX'],
                'HealthChecks': health_check_count,
                'PrivateZone': zone.get('Config', {}).get('PrivateZone', False),
                'CreatedTime': zone.get('CreatedTime', 'N/A')
            }
            zones_data.append(zone_data)
        
        return zones_data

    async def list_zones(self):
        """호스팅 영역 정보를 표로 출력합니다."""
        zones_data = await self.get_zones_with_details()
        
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
        
        for zone in zones_data:
            table.add_row(
                zone['Name'],
                zone['Id'],
                zone['Comment'],
                str(zone['RecordCount']),
                str(zone['ARecords']),
                str(zone['CNAMERecords']),
                str(zone['MXRecords']),
                str(zone['HealthChecks']),
                str(zone['PrivateZone']),
                str(zone['CreatedTime'])
            )
        
        pawn.console.print(table)