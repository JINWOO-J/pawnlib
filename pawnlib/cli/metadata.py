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
    },
    'KAKAO': {
        'meta_url': 'http://169.254.169.254/latest/meta-data/',
        'headers': {'X-aws-ec2-metadata-token': 'required'},
        'detect_url': 'http://169.254.169.254/latest/meta-data/',
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


def detect_cloud_provider(timeout=2.0):
    """
    Automatically detects the cloud provider based on metadata service.

    Parameters:
        timeout (float): Timeout for HTTP requests in seconds

    Returns:
        str: Name of the detected cloud provider (AWS, GCP, OCI, KAKAO)
    """
    for provider, info in CLOUD_PROVIDERS.items():
        try:
            response = requests.get(
                info['detect_url'],
                headers=info['headers'],
                timeout=timeout
            )
            if response.status_code == 200:
                # Distinguish between AWS and Kakao Cloud using server header
                if provider in ['AWS', 'KAKAO']:
                    server_header = response.headers.get('Server', '')
                    detected_provider = 'AWS' if 'EC2ws' in server_header else 'KAKAO'
                    pawn.console.log(f"Detected cloud provider: {detected_provider}")
                    return detected_provider

                pawn.console.log(f"Detected cloud provider: {provider}")
                return provider
        except requests.exceptions.RequestException as e:
            pawn.console.debug(f"Failed to detect {provider}: {e}")
            continue

    pawn.console.log("Could not detect cloud provider. Exiting.")
    sys.exit(1)


def get_metadata(provider, meta_ip, timeout):
    """
    Retrieves metadata specific to the detected cloud provider.

    Parameters:
        provider (str): The name of the cloud provider.
        meta_ip (str): The IP address of the metadata service.
        timeout (float): Timeout for the HTTP request in seconds.

    Returns:
        dict: The collected metadata from the cloud provider.

    Example:

        .. code-block:: python

            provider = "AWS"
            meta_ip = "169.254.169.254"
            timeout = 2.0

            metadata = get_metadata(provider, meta_ip, timeout)
            print(metadata)  # Output: Metadata dictionary for AWS, GCP, or OCI
    """
    metadata_handlers = {
        'AWS': server.get_aws_metadata,
        'GCP': server.get_gcp_metadata,
        'OCI': server.get_oci_metadata,
        'KAKAO': server.get_kakao_metadata
    }

    handler = metadata_handlers.get(provider)
    if not handler:
        pawn.console.log(f"Unsupported cloud provider. - {provider}")
        sys.exit(1)

    return handler(meta_ip=meta_ip, timeout=timeout)


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
        provider = detect_cloud_provider(timeout=args.timeout)

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
