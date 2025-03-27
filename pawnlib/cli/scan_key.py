#!/usr/bin/env python3
import os
import asyncio
from aiofiles import open as aio_open

from aiohttp import ClientSession
import aiofiles
import json
from dotenv import load_dotenv, find_dotenv
from pawnlib.config import pawn, setup_logger, setup_app_logger as _setup_app_logger
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.resource.monitor import SSHMonitor
from pawnlib.resource.server import get_interface_ips
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter, get_service_specific_arguments
from typing import List, Dict, Optional, Type, Any
from pawnlib.typing import (
    str2bool,
    sys_exit,
    is_valid_url,
)
from pawnlib.output import print_var, get_script_path, is_file, get_parent_path
from pawnlib.typing.constants import SecretPatternConstants
import re
from pawnlib.utils.http import AsyncGoloopWebsocket, NetworkInfo
from pawnlib.docker.compose import DockerComposeBuilder
from InquirerPy import inquirer
from rich.prompt import Prompt
from pawnlib.resource import SSHLogPathResolver
from pawnlib.utils.notify import send_slack
from pawnlib.exceptions.notifier import notify_exception
import traceback
from pawnlib.input import get_default_arguments
import logging
from typing import List, Dict
from pathlib import Path
import docker
import fnmatch
import tarfile
from io import BytesIO
import tempfile
import platform


IS_DOCKER = str2bool(os.environ.get("IS_DOCKER"))
logger = _setup_app_logger()
# logger = logging.getLogger(__name__)

__description__ = "CLI tool to scan for secret keys and tokens in files or Docker images"
__epilog__ = (
    "\nUsage examples:\n\n"
    "  Scan files: pawns scan_key files --directory ./src --patterns slack_token aws_access_key\n"
    "  Scan Docker: scan_key docker --image my-app:latest --patterns all"
)

def get_parser():
    parser = CustomArgumentParser(
        description='scan_key',
        epilog=__epilog__,
        formatter_class=ColoredHelpFormatter
    )
    parser = get_arguments(parser)
    return parser



def get_arguments(parser=None):

    if not parser:
        parser = CustomArgumentParser()
    subparsers = parser.add_subparsers(dest="mode", help="Scan mode", required=True)
    file_parser = subparsers.add_parser("files", help="Scan files in a directory")
    file_parser.add_argument(
        "--directory", "-d",
        type=str,
        default=".",
        help="Directory to scan (default: current directory)"
    )
    file_parser.add_argument(
        "--patterns", "-p",
        nargs="+",
        default=["all"],
        choices=list(SecretPatternConstants.SECRET_PATTERNS.keys()) + ["all"],
        help="Patterns to scan for (default: all)"
    )

    file_parser.add_argument(
        "--exclude", "-e",
        nargs="+",
        default=["*.pyc"],
        help="File patterns to exclude (e.g., '*.pyc', '*.log')"
    )

    file_parser.add_argument("--max-concurrency", type=int, default=100, help="Max number of files to open simultaneously")


    # 도커 이미지 스캔 모드
    docker_parser = subparsers.add_parser("docker", help="Scan a Docker image")
    docker_parser.add_argument(
        "--image", "-i",
        type=str,
        required=True,
        help="Docker image to scan (e.g., my-app:latest)"
    )
    docker_parser.add_argument(
        "--patterns", "-p",
        nargs="+",
        default=["all"],
        choices=list(SecretPatternConstants.SECRET_PATTERNS.keys()) + ["all"],
        help="Patterns to scan for (default: all)"
    )
    docker_parser.add_argument("--max-concurrency", type=int, default=100, help="Max number of files to open simultaneously")

    return parser


def load_environment_settings(args) -> dict:
    """
    Load environment settings from command-line arguments or environment variables,
    prioritizing args if provided, otherwise using environment variables.
    """
    def get_setting(
            attr_name: str,
            env_var: str,
            default: Optional[Any] = None,
            value_type: Type = str,
            is_list: bool = False
    ) -> Any:
        """Helper function to get setting value from args or env."""

        # Check if the argument was provided via the command line
        value = getattr(args, attr_name, None)

        # If priority is 'args' and the argument is explicitly provided (including 0), use it
        if args.priority == 'args' and value is not None and value != 0:
            pawn.console.debug(f"Using command-line argument for '{attr_name}': {value}")
            return value

        # Check the environment variable if command-line argument is not provided or default
        env_value = os.environ.get(env_var, None)

        if env_value is not None:
            if is_list:
                pawn.console.debug(f"<is_list> Using environment variable for '{attr_name}': {env_value}")
                return [item.strip() for item in env_value.split(",") if item.strip()]
            elif value_type == bool:
                pawn.console.debug(f"Using environment variable for '{attr_name}': {env_value}")
                return str2bool(env_value)
            elif value_type == int:
                try:
                    env_value_int = int(env_value)
                    pawn.console.debug(f"Using environment variable for '{attr_name}': {env_value_int}")
                    return env_value_int
                except ValueError:
                    pawn.console.debug(f"[WARN] Invalid int value for environment variable '{env_var}', using default: {default}")
                    return default
            else:
                pawn.console.debug(f"Using environment variable for '{attr_name}': {env_value}")
                return env_value

        # If neither is provided, use the default value
        pawn.console.debug(f"Using default value for '{attr_name}': {default}")
        return default

    settings: dict = {
        'endpoint_url': get_setting('endpoint_url', 'ENDPOINT_URL', default="", value_type=str),
        'ignore_data_types': get_setting('ignore_data_types', 'IGNORE_DATA_TYPES', default=['base'], is_list=True),
        'check_tx_result_enabled': get_setting('check_tx_result_enabled', 'CHECK_TX_RESULT_ENABLED', default=True, value_type=bool),
        'address_filter': get_setting('address_filter', 'ADDRESS_FILTER', default=[], is_list=True),
        'log_type': get_setting('log_type', 'LOG_TYPE', default='console', value_type=str),
        'file': get_setting('file', 'FILE', default=None, is_list=True),
        'slack_webhook_url': get_setting('slack_webhook_url', 'SLACK_WEBHOOK_URL', default=None, value_type=str),
        'send_slack': get_setting('send_slack', 'SEND_SLACK', default=True, value_type=bool),
        'max_transaction_attempts': get_setting('max_transaction_attempts', 'MAX_TRANSACTION_ATTEMPTS', default=10, value_type=int),
        'verbose': get_setting('verbose', 'VERBOSE', default=1, value_type=int),
        'network_name': get_setting('network_name', 'NETWORK_NAME', default="", value_type=str),
        'bps_interval': get_setting('bps_interval', 'BPS_INTERVAL', default=0, value_type=int),
        'skip_until': get_setting('skip_until', 'SKIP_UNTIL', default=0, value_type=int),
        'base_dir': get_setting('base_dir', 'BASE_DIR', default="./", value_type=str),
        # 'state_cache_file': os.environ.get('STATE_CACHE_FILE', args.state_cache_file),
        'check_interval': get_setting('check_interval', 'CHECK_INTERVAL', default=10, value_type=str),
        'ignore_decimal': get_setting('ignore_decimal', 'IGNORE_DECIMAL', default=False, value_type=bool),
    }
    return settings


def setup_app_logger(log_type: str = 'console', verbose: int = 0, app_name: str = ""):
    """Sets up the logger based on the selected type (console or file)."""
    log_time_format = '%Y-%m-%d %H:%M:%S.%f'

    if log_type == 'file':
        stdout_value =str2bool( not IS_DOCKER and (verbose > 1))
        # pawn.console.log(f"stdout_value={stdout_value}")
        pawn.set(
            PAWN_LOGGER=dict(
                log_level="INFO",
                stdout_level="INFO",
                # stdout=verbose > 1,
                stdout=stdout_value,
                log_format="[%(asctime)s] %(levelname)s::" "%(filename)s/%(funcName)s(%(lineno)d) %(message)s",
                std_log_format="%(message)s",
                use_hook_exception=True,
                use_clean_text_filter=True,
            ),
            PAWN_TIME_FORMAT=log_time_format,
            PAWN_CONSOLE=dict(
                redirect=True,
                record=True
            ),
            app_name=app_name,
            data={}
        )
        pawn.console.log(pawn.to_dict())
        _logger = pawn.app_logger
    else:
        _logger = pawn.console  # Use pawn's built-in console logger

    return setup_logger(_logger, f"Monitoring {app_name}", verbose)



def merge_environment_settings(args):
    """
    Merge environment settings with command-line arguments based on the selected priority.
    """
    dotenv_path = f"{pawn.get_path()}/.env"
    if not is_file(dotenv_path):
        pawn.console.log(".env file not found")
    else:
        pawn.console.log(f".env file found at '{dotenv_path}'")
        load_dotenv(dotenv_path=dotenv_path)

    parser = get_parser()
    default_args = get_default_arguments(parser)
    env_settings = load_environment_settings(args)
    args_dict = vars(args)
    # settings = env_settings.copy()  # Start with environment settings
    _settings = {}

    # Determine which to prioritize: env or args
    if args.priority == 'env':
        for key, value in args_dict.items():
            # pawn.console.log(f"{key} = {value}")
            if env_settings.get(key) is None:
                _value = value
            else:
                _value = env_settings.get(key, value)

            # _settings[key] = env_settings.get(key, value)
            _settings[key] = _value
    else:
        # Command-line arguments take priority
        for key, args_value in args_dict.items():
            default_value = default_args.get(key)
            env_value = env_settings.get(key, args_value)

            if args_value != default_value:
                _value = args_value
            else:
                _value = env_value
            _settings[key] = _value
    return _settings


# def scan_files(directory: str, patterns: List[str], exclude_patterns: List[str]) -> Dict[str, List[Dict]]:
#     results = {}
#     dir_path = Path(directory)
#
#     if not dir_path.exists():
#         logger.error(f"Directory '{directory}' does not exist.")
#         return results
#     logger.info(f"Start scanning files in '{directory}' with exclude patterns: {', '.join(exclude_patterns)}")
#
#     for file_path in dir_path.rglob("*"):
#         if file_path.is_file():
#             # 상대 경로를 기준으로 제외 패턴 체크
#             relative_path = file_path.relative_to(dir_path).as_posix()
#             exclude_match = any(fnmatch.fnmatch(relative_path, pattern) for pattern in exclude_patterns)
#             if exclude_match:
#                 logger.debug(f"Skipping excluded path: {file_path}")
#                 continue
#             try:
#                 with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
#                     content = f.read()
#                     for pattern_name in patterns:
#                         pattern = SecretPatternConstants.get_pattern(pattern_name)
#                         matches = re.findall(pattern, content)
#                         if matches:
#                             if str(file_path) not in results:
#                                 results[str(file_path)] = []
#                             for match in matches:
#                                 results[str(file_path)].append({
#                                     "type": pattern_name,
#                                     "match": match,
#                                     "description": SecretPatternConstants.get_description(pattern_name)
#                                 })
#             except Exception as e:
#                 logger.warning(f"Failed to read {file_path}: {e}")
#     return results

SEM = asyncio.Semaphore(100)  # 동시에 최대 100개만 열기

async def scan_file(file_path: Path, patterns: list, concurrency=asyncio.Semaphore) -> list:
    """단일 파일을 스캔하는 코루틴"""
    results = []
    async with concurrency:  # 이 블록 안에서만 동시에 열 수 있는 파일 개수가 100개 이내로 제한됨
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = await f.read()
                for pattern in patterns:
                    # 단순 예시: 정규식으로 매칭
                    matches = re.findall(pattern, content)
                    for match in matches:
                        results.append({
                            "file_path": str(file_path),
                            "pattern": pattern,
                            "match": match
                        })
        except Exception as e:
            # 필요 시 로깅 처리
            logger.exception(f"Failed to read {file_path}: {e}")
    return results


async def scan_file(file_path: Path, patterns: List[str]) -> List[Dict]:
    """파일을 비동기적으로 스캔하여 민감한 패턴을 탐지."""
    results = []
    try:
        async with aio_open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = await f.read()
            for pattern_name in patterns:
                pattern = SecretPatternConstants.get_pattern(pattern_name)
                matches = re.findall(pattern, content)
                for match in matches:
                    results.append({
                        "type": pattern_name,
                        "match": match,
                        "description": SecretPatternConstants.get_description(pattern_name)
                    })
    except Exception as e:
        logger.exception(f"Failed to read {file_path}: {e}")
    return results

# async def scan_file(file_path: Path, patterns: List[str]) -> List[Dict]:
#     results = []
#     try:
#         async with aio_open(file_path, "r", encoding="utf-8", errors="ignore") as f:
#             content = await f.read()
#             for pattern_name in patterns:
#                 pattern = SecretPatternConstants.get_pattern(pattern_name)
#                 matches = re.findall(pattern, content)
#                 for match in matches:
#                     results.append({
#                         "file_path": file_path,
#                         "type": pattern_name,
#                         "match": match,
#                         "description": SecretPatternConstants.get_description(pattern_name)
#                     })
#     except Exception as e:
#         logger.exception(f"Failed to read {file_path}: {e}")
#     return results

async def scan_files(directory: str, patterns: List[str], exclude_patterns: List[str], concurrency: int) -> Dict[str, List[Dict]]:
    results = {}
    dir_path = Path(directory)
    if not dir_path.exists():
        logger.error(f"Directory '{directory}' does not exist.")
        return results

    semaphore = asyncio.Semaphore(concurrency)

    tasks = []
    for file_path in dir_path.rglob("*"):
        if file_path.is_file() and not any(fnmatch.fnmatch(file_path.relative_to(dir_path).as_posix(), p) for p in exclude_patterns):
            tasks.append(scan_file(file_path, patterns, semaphore))

    scan_results = await asyncio.gather(*tasks)
    for result in scan_results:
        if result:
            results[str(result[0]["file_path"])] = result
    return results



def get_docker_client():
    """도커 클라이언트를 생성하며, MacOS와 Linux 환경을 고려."""
    # 환경 변수 확인
    docker_host = os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock")
    if docker_host:
        logger.info(f"Using DOCKER_HOST from environment: {docker_host}")
        return docker.DockerClient(base_url=docker_host)

    # MacOS와 Linux 구분
    system = platform.system()
    socket_options = []

    if system == "Darwin":  # MacOS
        socket_options.append(f"unix://{os.path.expanduser('~/.docker/run/docker.sock')}")
        socket_options.append("unix:///var/run/docker.sock")
        socket_options.append("tcp://127.0.0.1:2375")
    else:  # Linux 등
        socket_options = ["unix:///var/run/docker.sock", "tcp://127.0.0.1:2375"]

    for url in socket_options:
        try:
            client = docker.DockerClient(base_url=url)
            client.ping()  # 연결 테스트
            logger.info(f"Connected to Docker daemon via {url}")
            return client
        except (docker.errors.DockerException, FileNotFoundError) as e:
            logger.warning(f"Failed to connect via {url}: {e}")
    raise Exception("Could not connect to Docker daemon. Ensure Docker is running and accessible.")


async def scan_docker_image(image_name: str, patterns: List[str], concurrency: int) -> Dict[str, List[Dict]]:
    results = {}
    client = docker.from_env()

    try:
        client.images.get(image_name)  # 이미지 존재 확인
        logger.info(f"Starting scan for Docker image: {image_name}")

        container = client.containers.run(image_name, "sleep 3600", detach=True)
        try:
            # 스캔할 경로 목록
            paths_to_scan = ["/etc", "/usr", "/var"]  # 필요하다면 "/app" 등 추가

            semaphore = asyncio.Semaphore(concurrency)
            all_tasks = []

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                for path in paths_to_scan:
                    try:
                        # tar 아카이브 추출
                        tar_stream, _ = container.get_archive(path)
                        tar_content = b"".join(tar_stream)

                        # tarfile 열기
                        with tarfile.open(fileobj=BytesIO(tar_content)) as tar:
                            tar.extractall(path=temp_path)

                            # tar 안의 모든 파일 멤버를 순회
                            for member in tar.getmembers():
                                if member.isfile():
                                    extracted_file = temp_path / member.name
                                    if extracted_file.exists():
                                        # 파일 스캔을 위한 코루틴 태스크를 만들고 예약
                                        all_tasks.append(scan_file(extracted_file, patterns, semaphore))
                    except Exception as e:
                        logger.warning(f"Failed to scan '{path}' in {image_name}: {e}")

                # 모든 파일 스캔 태스크를 병렬 실행
                scan_results = await asyncio.gather(*all_tasks, return_exceptions=True)
                for file_result in scan_results:
                    if isinstance(file_result, Exception):
                        continue
                    if file_result:
                        # file_result는 하나의 파일에 대한 매칭 결과 리스트
                        # 각 item에 file_path, pattern, match 등이 들어있음
                        for item in file_result:
                            # docker_path를 굳이 만들려면,
                            # 어떤 경로에서 추출된 파일인지 추적해야 함
                            # 여기선 간단히 로컬 경로(extracted_file) 사용
                            # 필요하면 "path + '/' + member.name" 로 구성
                            fp = item["file_path"]
                            if fp not in results:
                                results[fp] = []
                            results[fp].append(item)
        finally:
            container.stop()
            container.remove()
            logger.info(f"Cleaned up container for {image_name}")
    except docker.errors.ImageNotFound:
        logger.error(f"Image '{image_name}' not found.")
    except Exception as e:
        logger.error(f"Error scanning Docker image '{image_name}': {e}")

    return results


def print_results(results: Dict[str, List[Dict]]):
    if not results:
        logger.info("No secrets found.")
        return

    for location, secrets in results.items():
        logger.info(f"\nLocation: {location}")
        for secret in secrets:
            logger.info(f"- Type: {secret['type']}  | Location: {location}")
            logger.info(f"  Match: {secret['match']}")
            logger.info(f"  Description: {secret['description']}")


def initialize_logger(settings):
    """Set up the logger based on the command and its log type."""
    app_name = f"{settings.get('command')}_watcher"
    pawn.console.log(app_name)
    # return setup_app_logger(log_type=settings.get('log_type'), verbose=settings.get('verbose'), app_name=app_name)
    _setup_app_logger(log_type=settings.get('log_type'), verbose=settings.get('verbose'), app_name=app_name)

    return logging.getLogger(__name__)


def main():
    banner = generate_banner(
        app_name="Monitoring",
        author="jinwoo",
        description="Monitor SSH logs and run the Async Goloop Websocket Client",
        font="ogre",
        version=f"{_version}, IS_DOCKER={IS_DOCKER}"
    )

    parser = get_parser()
    args = parser.parse_args()

    print(banner)
    pawn.console.log(f"Parsed arguments: {args}")

    # settings = merge_environment_settings(args)

    if IS_DOCKER:
        pawn.console.rule("RUN IN DOCKER")

    patterns = args.patterns
    if "all" in patterns:
        patterns = list(SecretPatternConstants.SECRET_PATTERNS.keys())

    logger.info(f"Scanning with patterns: {', '.join(patterns)}")

    # 모드에 따른 스캔 실행
    if args.mode == "files":
        # results = scan_files(args.directory, patterns, args.exclude)
        results = asyncio.run(scan_files(args.directory, patterns, args.exclude, args.max_concurrency))
    elif args.mode == "docker":
        # results = scan_docker_image(args.image, patterns)
        results = asyncio.run(scan_docker_image(args.image, patterns, args.max_concurrency))
    else:
        parser.error(f"Unknown mode: {args.mode}")

    # 결과 출력
    print_results(results)

main.__doc__ = (
    f"{__description__}\n{__epilog__}"
)


if __name__ == '__main__':
    main()




