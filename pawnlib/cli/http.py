#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf, one_time_run
from pawnlib.typing import str2bool, StackList, ErrorCounter,  is_json, is_valid_url, sys_exit, Null, remove_tags, FlatDict
from pawnlib.utils.http import CallHttp, disable_ssl_warnings, ALLOW_OPERATOR
from pawnlib.utils import ThreadPoolRunner, send_slack
from pawnlib.output import bcolors, print_json, is_file
from dataclasses import dataclass, field
from pawnlib.input import ColoredHelpFormatter
import copy
import os
import json
from typing import List, Dict, Union, Type, get_type_hints, Any
import re
import time

script_name = "pawns"

__description__ = 'This is a tool to measure RTT on HTTP/S requests.'

http_config_example = """
    # The configuration options are provided below. You can customize these settings in the 'http_config.ini' file.
    
    [default]
    success = status_code==200 
    slack_url = 
    interval = 3
    method = get
    ; data = sdsd
    data = {"sdsd": "sd222sd"}
    
    [post]
    url = http://httpbin.org/post
    method = post
    
    [http_200_ok]
    url = http://httpbin.org/status/200
    success = status_code==200
    
    [http_300_ok_and_2ms_time]
    url = http://httpbin.org/status/400
    success = ['status_code==300', 'response_time<0.02']
        
    [http_400_ok]
    url = http://httpbin.org/status/400
    success = ["status_code==400"]
    """

__epilog__ = (
    f"This script provides various options to check the HTTP status of URLs. \n\n"
    f"Usage examples:\n"
    f"  1. Basic usage:  \n\t`{script_name} http https://example.com`\n\n"
    f"  2. Verbose mode: \n\t`{script_name} http https://example.com -v`\n\n"
    f"  3. Using custom headers and POST method: \n\t`{script_name} http https://example.com -m POST --headers '{{\"Content-Type\": \"application/json\"}}' --data '{{\"param\": \"value\"}}'` \n\n"
    f"  4. Ignoring SSL verification and setting a custom timeout: \n\t`{script_name} http https://example.com --ignore-ssl True --timeout 5`\n\n"
    f"  5. Checking with specific success criteria and logical operator: \n\t`{script_name} http https://example.com --success 'status_code==200' 'response_time<2' --logical-operator and`\n\n"
    f"  6. Running with a custom config file and interval: \n\t`{script_name} http https://example.com -c http_config.ini -i 3`\n"
    f"  7. Setting maximum workers and stack limit: \n\t{script_name} http https://example.com -w 5 --stack-limit 10\n\n"
    f"  8. Dry run without actual HTTP request: \n\t{script_name} http https://example.com --dry-run\n\n"
    f"  9. Sending notifications to a Slack URL on failure: \n\t{script_name} http https://example.com --slack-url 'https://hooks.slack.com/services/...'\n\n\n"

    f" 10. Checking blockheight increase: \n\t`{script_name} http http://test-node-01:26657/status --blockheight-key \"result.sync_info.latest_block_height\" -i 5`\n\n"

    "Note:  \n"
    "   .. line-block:: \n\n"
    
    f"\n{http_config_example}\n\n\n"
    
    f"For more details, use the -h or --help flag."
)

class SuccessCriteria:
    @staticmethod
    def from_string(criteria_string: str) -> List[str]:
        return re.split(r'\s+(?=[a-zA-Z_]+)', criteria_string)


@dataclass
class AppConfig:
    url: str = ""
    config_file: str = "config.ini"
    verbose: int = 1
    quiet: int = 0
    interval: float = 1.0
    # method: str = "GET"
    method: str = ""
    timeout: float = 10.0
    base_dir: str = field(default_factory=lambda: os.getcwd())
    # success: List[str] = field(default_factory=lambda: ["status_code==200"])
    success: List[str] = field(default_factory=lambda: [])
    # success: List = []
    logical_operator: str = "and"
    ignore_ssl: bool = True

    data: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    workers: int = 10
    stack_limit: int = 5

    section_name: str = "default"
    total_count: int = 0
    error_stack_count: int = 0
    fail_count: int = 0
    response_time: List[int] = field(default_factory=lambda: StackList())

    dynamic_increase_stack_limit: bool = True
    slack_url: str = ""
    # blockheight_key: str = ""
    blockheight_key: Union[str, None] = None
    blockheight_stack: List[int] = field(default_factory=lambda: StackList())


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help()
        sys_exit(message, 2)


def convert_type(value, to_type):
    """주어진 값을 to_type 타입으로 변환합니다."""
    if to_type == bool:
        return str2bool(value)  # 이전에 정의한 str2bool 함수 사용
    elif to_type == list or to_type == List:
        if not isinstance(value, list):
            value = [value]
        return json.loads(value)
    elif to_type == dict or to_type == Dict:
        return json.loads(value)
    else:
        return to_type(value)


def convert_value(value: Any, target_type: Type) -> Any:
    if isinstance(value, str):
        value = value.replace("'", "\"")

    if hasattr(target_type, '__origin__'):
        if target_type.__origin__ == list:
            return _convert_to_list(value, target_type.__args__[0])
        elif target_type.__origin__ == dict:
            return _convert_to_dict(value, *target_type.__args__)
        else:
            return value  # 기타 제네릭 타입에 대한 처리

    # 기본 타입 (예: int, str)에 대한 처리
    elif isinstance(value, str) or not isinstance(value, target_type):
        return target_type(value)
    else:
        return value  # 이미 올바른 타입일 경우


def _convert_to_list(value: Any, item_type: Type) -> list:
    if isinstance(value, str):
        try:
            parsed_list = json.loads(value)
        except json.JSONDecodeError:
            parsed_list = re.split(r'\s+(?=[a-zA-Z_]+)', value)
    else:
        parsed_list = [value] if not isinstance(value, list) else value

    return [convert_value(item, item_type) for item in parsed_list]


def _convert_to_dict(value: Any, key_type: Type, value_type: Type) -> dict:
    if isinstance(value, str):
        try:
            parsed_dict = json.loads(value)
        except json.JSONDecodeError:
            return {}
    elif isinstance(value, dict):
        parsed_dict = value
    else:
        return {}

    return {convert_value(k, key_type): convert_value(v, value_type) for k, v in parsed_dict.items()}


def get_parser():

    parser = CustomArgumentParser(
        description='httping',
        epilog=__epilog__,
        formatter_class=ColoredHelpFormatter
    )
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument('url', help='URL to be checked', type=str, nargs='?', default="")

    parser.add_argument('-c', '--config-file', type=str, help='Path to the configuration file. Defaults to "config.ini".', default="config.ini")
    parser.add_argument('-v', '--verbose', action='count', help='Enables verbose mode. Higher values increase verbosity level. Default is 1.', default=1)

    parser.add_argument('-q', '--quiet', action='count', help='Enables quiet mode. Suppresses all messages. Default is 0.', default=0)
    parser.add_argument('-i', '--interval', type=float, help='Interval time in seconds between checks. Default is 1 second.', default=1)
    parser.add_argument('-m', '--method', type=lambda s: s.upper(), help='HTTP method to use (e.g., GET, POST). Default is "GET".', default="GET")
    parser.add_argument('-t', '--timeout', type=float, help='Timeout in seconds for each HTTP request. Default is 10 seconds.', default=10)
    parser.add_argument('-b', '--base-dir', type=str, help='Base directory for httping operations. Default is the current working directory.', default=os.getcwd())
    parser.add_argument('--success', nargs='+', help='Criteria for success. Can specify multiple criteria. Default is ["status_code==200"].', default=['status_code==200'])
    parser.add_argument('--logical-operator',
                        type=str,
                        help='Logical operator for evaluating success criteria. Choices are "and", "or". Default is "and".',
                        choices=["and", "or"],
                        default="and"
                        )
    parser.add_argument('--ignore-ssl', type=str2bool, help='Ignores SSL certificate validation if set to True. Default is True.', default=True)
    parser.add_argument('-d', '--data', type=json.loads, help="Data to be sent in the HTTP request body. Expected in JSON format. Default is an empty dictionary.", default={})
    parser.add_argument('--headers', type=json.loads, help="HTTP headers to be sent with the request. Expected in JSON format. Default is an empty dictionary.", default={})
    parser.add_argument('-w', '--workers', type=int, help="Maximum number of worker processes. Default is 10.", default=10)
    parser.add_argument('--stack-limit', type=int, help="Error stack limit. Default is 5.", default=5)
    parser.add_argument('--dynamic-increase-stack-limit', type=str2bool, help="Dynamically increases the error stack limit if set to True. Default is True.", default=1)
    parser.add_argument('--slack-url', type=str, help="URL for sending notifications to Slack. Optional.", default="")
    parser.add_argument('--log-level', type=lambda s: s.upper(), help="Log level.", default="info")

    parser.add_argument('-bk', '--blockheight-key', type=str, help="JSON key to extract the blockheight information, e.g., 'result.sync_info.latest_block_height'. "
                                                            "The script will check if the blockheight at this path is increasing.", default="")
    parser.add_argument('--dry-run', action='store_true', help="Executes a dry run without making actual HTTP requests. Default is False.", default=False)
    return parser


def check_url_process(config):
    if not config.url:
        return
    if one_time_run() and config.slack_url:
        res = _send_slack(url=config.slack_url, title=f"Starting HTTPING - {config.section_name}", msg_text=config.__dict__)

    check_url = CallHttp(
        url=config.url,
        method=config.method,
        timeout=config.timeout * 1000,
        payload=config.data,
        headers=config.headers,
        success_criteria=config.success,
        success_operator=config.logical_operator,
        ignore_ssl=config.ignore_ssl,
    ).run()
    config.total_count += 1

    parsed_response = ""

    if config.verbose == 0:
        check_url.response.text = ""

    response_time = check_url.response.elapsed

    config.response_time.push(response_time)
    avg_response_time = f"{int(config.response_time.mean())}"
    max_response_time = f"{int(config.response_time.max())}"
    min_response_time = f"{int(config.response_time.min())}"
    status_code = check_url.response.status_code

    if config.fail_count > 0:
        count_msg = f'CER:{config.error_stack_count}/[red]ER:{config.fail_count}[/red]/SQ:{config.total_count}'
    else:
        count_msg = f'CER:{config.error_stack_count}/ER:{config.fail_count}/SQ:{config.total_count}'

    if config.blockheight_key and isinstance(check_url.response.json, (dict, list)):
        flat_json = FlatDict(check_url.response.json)
        blockheight_key = config.blockheight_key
        last_blockheight = flat_json.get(blockheight_key)

        if last_blockheight is not None:
            last_blockheight = int(last_blockheight)
            check_block_result = config.blockheight_stack.check_and_push(last_blockheight)

            if not check_block_result:
                handle_failure_on_check_url(config, f"Blockheight '{blockheight_key}' did not increase => {last_blockheight}", check_url)

            parsed_response = f"{blockheight_key.split('.')[-1]}={last_blockheight}, "
        else:
            handle_failure_on_check_url(config, f"Blockheight key '{blockheight_key}' not found in JSON response", check_url)
    # else:
    #     handle_failure_on_check_url(config, f"Invalid blockheight key or JSON response structure, "
    #                                         f"blockheight_key={config.blockheight_key} "
    #                                         f"response={type(check_url.response.json)}", check_url)

    # message = f"<{count_msg}> name={args.section_name}, url={args.url}, {parsed_response}" \

    if len(pconf().tasks) > 1:
        _name_string = f"name={config.section_name}, "
    else:
        _name_string = ""

    message = f"<{count_msg}> {_name_string}url='{config.url}', {parsed_response}" \
              f"status={status_code}, {response_time:>4}ms " \
              f"(avg: {avg_response_time}, max: {max_response_time}, min: {min_response_time})"

    if pconf().args.verbose > 0:
        if status_code != 999:
            if pconf().args.verbose > 2:
                detail = f" 📄[i]{check_url.response}, criteria: {config.success}, operator: {config.logical_operator}[/i]"
            else:
                detail = ""
            message = f"{message}{detail}"
        else:
            message = f"{message} 😞 "

    if check_url.is_success():
        pawn.app_logger.info(remove_tags(f"[ OK ] {message}"))
        print_response_if_verbose(check_url)
    else:
        handle_failure_on_check_url(config, message, check_url)
        print_response_if_verbose(check_url)

    if config.interval and not pconf().args.dry_run:
        time.sleep(config.interval)

def print_response_if_verbose(check_url):
    if (pconf().args.verbose > 3 or pconf().args.dry_run)  and hasattr(check_url, "response"):
        check_url.response.json = FlatDict(check_url.response.json).as_dict()
        check_url.print_http_response()


def handle_failure_on_check_url(args, message, check_url):
    args.fail_count += 1
    args.error_stack_count += 1

    if args.error_stack_count >= args.stack_limit:
        pawn.error_logger.error(remove_tags(f"[FAIL][OVERFLOW]{args.error_stack_count}/{args.stack_limit} "
                                            f"Error Stack Count: {args.error_stack_count}, SEND_SLACK"))
        args.error_stack_count = 0

        if args.dynamic_increase_stack_limit:
            args.stack_limit = args.stack_limit ** 2
            _send_slack(url=args.slack_url, title=f"Error: {message} from {args.url}", msg_text=args.__dict__)

    pawn.error_logger.error(remove_tags(f"[FAIL] {message}, Error={check_url.response}"))


def set_default_counter(section_name="default"):
    args = copy.deepcopy(pconf().args)
    args.section_name = section_name
    args.response_time = StackList()
    args.blockheight_stack = StackList()
    args.error_stack_count = 0
    args.total_count = 0
    args.fail_count = 0
    return args


def apply_config_values(config_instance, section_name, section_value):
    """섹션 값들을 AppConfig 인스턴스에 적용합니다."""
    type_hints = get_type_hints(AppConfig)

    if section_name:
        setattr(config_instance, "section_name", section_name)

    for conf_key, conf_value in section_value.items():
        if conf_key in type_hints:
            # 필드 타입에 맞게 값을 변환
            converted_value = convert_value(conf_value, type_hints[conf_key])
            pawn.console.debug(f"conf_value={conf_value}, type_hints={type_hints[conf_key]}, converted_value={converted_value}")
            pawn.console.debug(f"Update argument from {config_instance}, <{section_name}> {conf_key}={conf_value} <ignore args={getattr(pconf().args, conf_key, None)}>")
            setattr(config_instance, conf_key, converted_value)
    return config_instance


def load_and_verify_config():
    pconfig = pconf().PAWN_CONFIG
    config_file = pconf().PAWN_CONFIG_FILE
    pconf_dict = pconfig.as_dict()

    if is_file(config_file):
        pawn.console.log(f"Found config file={config_file}")
        if not pconf_dict:
            sys_exit("Invalid config file. Exiting...")

    return pconf_dict


def generate_task_from_config():
    tasks = []
    pconf_dict = load_and_verify_config()
    if pconf_dict:
        for section_name, section_value in pconf_dict.items():
            config_instance = AppConfig()
            pawn.console.debug(f"section_name={section_name}, value={section_value}")
            # args = set_default_counter(section_name)
            _config_instance = apply_config_values(config_instance, section_name, section_value)
            if _config_instance.url and _config_instance.url != "http":
                tasks.append(_config_instance)

            if section_name == "default":
                pawn.set(default_config=_config_instance)

    if not tasks:
        tasks = [set_default_counter()]

    tasks = fill_default_config_values(tasks)

    validate_task_exit_on_failure(tasks)
    return tasks

def fill_default_config_values(tasks):
    if not pconf().default_config.__dict__:

        if not pconf().args.method:
            pconf().args.method = "GET"

    ignore_keys = ["log_level", "dry_run"]

    for args_key, args_value in pconf().args.__dict__.items():

        if args_key not in ignore_keys and args_value:
            _default_value = getattr(pconf().default_config, args_key, None)

            if not _default_value:
                pawn.console.debug(f"Change default value '{args_key}' => {args_value}")
                setattr(pconf().default_config, args_key, args_value)
            elif getattr(pconf().default_config, args_key) != args_value:
                pawn.console.debug(f"Priority args {_default_value} => {args_value}")
                setattr(pconf().default_config, args_key, args_value)


    for config in tasks:
        for _default_key, _default_value  in  pconf().default_config.__dict__.items():
            if not getattr(config, _default_key):
                setattr(config, _default_key, _default_value)
    return tasks


def _send_slack(url, msg_text, title=None, send_user_name=None, msg_level='info'):
    if not send_user_name:
        send_user_name = pconf().app_name

    if url:
        pawn.console.log("Send slack")
        return send_slack(
            url=url,
            msg_text=msg_text,
            title=title,
            send_user_name=send_user_name,
            msg_level=msg_level
        )


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


def validate_task_exit_on_failure(tasks):
    if not tasks:
        sys_exit("Task not found")
    is_least_one_url = False
    for task in tasks:
        # if is_valid_url(task.url, strict=False) and task.url != "http":
        if task.url and task.url != "http":
            is_least_one_url = True
        else:
            pawn.console.log(f"Invalid url: name={task.section_name}, url={task.url}")

    if not is_least_one_url:
        pconf().args_parser.error("Requires at least one valid URL. The URL argument must be in the first position.")


def main():
    app_name = 'httping'
    parser = get_parser()
    args, unknown = parser.parse_known_args()
    pawn.console.debug(f"args={args}, unknown={unknown}")
    config_file = args.config_file

    is_hide_line_number = args.verbose > 1
    stdout = not args.quiet

    pawn.set(
        PAWN_CONFIG_FILE=config_file,
        PAWN_PATH=args.base_dir,
        PAWN_LOGGER=dict(
            log_level=args.log_level,
            stdout_level=args.log_level,
            log_path=f"{args.base_dir}/logs",
            stdout=stdout,
            use_hook_exception=True,
            show_path=False, #hide line numbers
        ),
        PAWN_CONSOLE=dict(
            redirect=True,
            record=True,
            log_path=is_hide_line_number, # hide line number on the right side
        ),
        args_parser=parser,
        app_name=app_name,
        args=args,
        try_pass=False,
        last_execute_point=0,
        data={
            "response_time": StackList(),
        },
        fail_count=0,
        total_count=0,
        default_config={},

    )
    if args.verbose > 2:
        pawn.set(
            PAWN_LOGGER=dict(
                log_level="DEBUG",
                stdout_level="DEBUG",
            )
        )
    print_banner()

    if args.ignore_ssl:
        disable_ssl_warnings()
    tasks = generate_task_from_config()
    pawn.set(tasks=tasks)

    # if args.slack_url:
    #     res = _send_slack(url=args.slack_url, title="Starting HTTPING", msg_text=tasks)
    #     pawn.console.log(res)
    # _send_slack(url=args.slack_url, title=f"Error HTTPING {args.url}", msg_text=args.__dict__)
    # pawn.console.log(f"console_options={pawn.console_options}")
    # exit()
    pawn.console.log(f"Start httping ... url_count={len(tasks)}")
    pawn.console.log("If you want to see more logs, use the [yellow]-v[/yellow] option")
    pawn.console.log(f"tasks={tasks}")

    # pawn.console.log(tasks)
    if args.dry_run:
        for task in tasks:
            check_url_process(task)
    else:
        runner = ThreadPoolRunner(
            func=check_url_process,
            tasks=tasks,
            max_workers=args.workers,
            verbose=args.verbose,
            sleep=args.interval
        )
        runner.forever_run()

        # try:
        #     runner.forever_run()
        # except KeyboardInterrupt:
        #     runner.stop()
        #     print("Runner stopped.")

main.__doc__ = (
    f"{__description__} \n"
    f"{__epilog__}"
)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        pawn.console.log(e)

