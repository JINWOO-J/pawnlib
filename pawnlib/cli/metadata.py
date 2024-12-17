#!/usr/bin/env python3
import argparse
import requests
import logging
import sys
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawnlib_config as pawn
from pawnlib.output import write_json, syntax_highlight, PrintRichTable
from pawnlib.typing.converter import FlatDict, FlatterDict, flatten_dict

from pawnlib.resource import server

__description__ = 'Get meta information from Cloud Providers (AWS, GCP, OCI).'

__epilog__ = (
    "This script retrieves metadata from AWS, GCP, or OCI instances.\n\n"
    "Usage examples:\n"
    "  1. Retrieve metadata in JSON format (auto-detect cloud provider):\n"
    "     `pawns metadata --output-format json`\n\n"

    "  2. Retrieve metadata in flattened format:\n"
    "     `pawns metadata --output-format flat`\n\n"

    "  3. Specify a custom timeout for the request:\n"
    "     `pawns metadata --timeout 5`\n\n"

    "  4. Write metadata to a file:\n"
    "     `pawns metadata --output-file metadata.json`\n\n"

    "For more information and options, use the -h or --help flag."
)


CLOUD_PROVIDERS = {
    'AWS': {
        'meta_url': 'http://169.254.169.254/latest/meta-data/',
        'headers': {},
        'detect_url': 'http://169.254.169.254/latest/meta-data/',
    },
    'GCP': {
        'meta_url': 'http://metadata.google.internal/computeMetadata/v1/',
        'headers': {'Metadata-Flavor': 'Google'},
        'detect_url': 'http://metadata.google.internal/computeMetadata/v1/',
    },
    'OCI': {
        'meta_url': 'http://169.254.169.254/opc/v1/',
        'headers': {'Authorization': 'Bearer Oracle'},
        # OCI는 루트 URL로는 감지가 불가능하므로 특정 경로를 사용
        'detect_url': 'http://169.254.169.254/opc/v1/instance/id',
    }
}


def get_parser():
    parser = argparse.ArgumentParser(description=__description__, epilog=__epilog__)
    parser = get_arguments(parser)
    return parser

def get_arguments(parser):
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
    parser.add_argument(
        "--provider", "-p", type=str,
        help="Choose provider.",
        default=""
    )
    return parser

def detect_cloud_provider(meta_ip, timeout):
    """
    클라우드 제공업체를 자동으로 감지합니다.

    Parameters:
        meta_ip (str): 메타데이터 서비스의 IP 주소.
        timeout (float): HTTP 요청의 타임아웃 (초).

    Returns:
        str: 감지된 클라우드 제공업체의 이름(AWS, GCP, OCI). 감지되지 않으면 'Unknown'.
    """
    for provider, info in CLOUD_PROVIDERS.items():
        try:
            response = requests.get(
                info['detect_url'],
                headers=info['headers'],
                timeout=timeout
            )
            if response.status_code == 200:
                pawn.console.log(f"Detected cloud provider: {provider}")
                return provider
        except requests.exceptions.RequestException as e:
            pawn.console.debug(f"Could not detect {provider}: {e}")
            continue
    pawn.console.log("Could not detect cloud provider. Exiting.")
    sys.exit(1)

def get_metadata(provider, meta_ip, timeout):
    """
    클라우드 제공업체별로 메타데이터를 가져옵니다.

    Parameters:
        provider (str): 클라우드 제공업체의 이름.
        meta_ip (str): 메타데이터 서비스의 IP 주소.
        timeout (float): HTTP 요청의 타임아웃 (초).

    Returns:
        dict: 수집된 메타데이터.
    """
    if provider == 'AWS':
        return server.get_aws_metadata(meta_ip=meta_ip, timeout=timeout)
    elif provider == 'GCP':
        return server.get_gcp_metadata(meta_ip=meta_ip, timeout=timeout)
    elif provider == 'OCI':
        return server.get_oci_metadata(meta_ip=meta_ip, timeout=timeout)
    else:
        pawn.console.log(f"Unsupported cloud provider. - {provider}")
        sys.exit(1)

def main():
    banner = generate_banner(
        app_name="Cloud Metadata",
        author="jinwoo",
        description="Get metadata from Cloud Providers (AWS, GCP, OCI)",
        font="graffiti",
        version=_version
    )
    print(banner)

    parser = get_parser()
    args, unknown = parser.parse_known_args()

    pawn.console.log(f"args = {args}")

    if args.provider:
        provider = args.provider.upper()
    else:
        provider = detect_cloud_provider(meta_ip=args.metadata_ip, timeout=args.timeout)

    res = get_metadata(provider=provider, meta_ip=args.metadata_ip, timeout=args.timeout)

    if args.output_format == "json":
        print(syntax_highlight(res))
    elif args.output_format == "flat":
        PrintRichTable(
            title=f"{provider} Metadata",
            data=flatten_dict(res),
            columns_options=dict(
                value=dict(
                    justify="left",
                )
            )
        )

    if args.output_file:
        write_res = write_json(filename=args.output_file, data=res)
        pawn.console.log(write_res)

main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':
    main()
