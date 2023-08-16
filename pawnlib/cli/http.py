#!/usr/bin/env python3
import argparse
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.config import pawn, pconf
import json
import copy
from pawnlib.typing import str2bool, StackList, is_json, is_valid_url, sys_exit, Null
from pawnlib.utils.http import CallHttp, disable_ssl_warnings
from pawnlib.utils import ThreadPoolRunner, send_slack
from pawnlib.output import get_script_path, dump, debug_print, print_var
from pawnlib.typing import remove_tags
import os

__description__ = 'This is a tool to measure RTT on HTTP/S requests.'


def get_parser():
    parser = argparse.ArgumentParser(description='httping')
    parser = get_arguments(parser)
    return parser


def get_arguments(parser):
    parser.add_argument('url', help='url', type=str, nargs='?', default="")
    parser.add_argument('-c', '--config-file', type=str, help='config', default="config.ini")
    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level (default: %(default)s)', default=1)
    parser.add_argument('-q', '--quiet', action='count', help='Quiet mode. Dont show any messages. (default: %(default)s)', default=0)
    parser.add_argument('-i', '--interval', type=float, help='interval sleep time seconds. (default: %(default)s)', default=1)
    parser.add_argument('-m', '--method', type=lambda s : s.upper(), help='method. (default: %(default)s)', default="get")
    parser.add_argument('-t', '--timeout', type=float, help='timeout seconds (default: %(default)s)', default=10)
    parser.add_argument('-b', '--base-dir', type=str, help='base dir for httping (default: %(default)s)', default=os.getcwd())
    parser.add_argument('--success', nargs='+', help='success criteria. (default: %(default)s)', default=['status_code==200'])
    parser.add_argument('--logical-operator',
                        type=str,
                        help='logical operator for checking success condition (default: %(default)s)',
                        choices=["and", "or"],
                        default="and"
                        )
    parser.add_argument('--ignore-ssl', type=str2bool, help='ignore ssl certificate (default: %(default)s)', default=True)
    parser.add_argument('-d', '--data', type=json.loads, help="data parameter", default={})
    parser.add_argument('--headers', type=json.loads, help="header parameter", default={})
    parser.add_argument('-w', '--workers', type=int, help="max worker process (default: %(default)s)", default=10)
    parser.add_argument('--stack-limit', type=int, help="error stack limit (default: %(default)s)", default=3)
    parser.add_argument('--dynamic-increase-stack-limit', type=str2bool, help="error stack limit (default: %(default)s)", default=1)
    parser.add_argument('--slack-url', type=str, help="Slack URL", default="")
    return parser


def check_url_process(args):
    if not args.url:
        return

    check_url = CallHttp(
        url=args.url,
        method=args.method,
        timeout=args.timeout * 1000,
        data=args.data,
        headers=args.headers,
        success_criteria=args.success,
        success_operator=args.logical_operator,
        ignore_ssl=args.ignore_ssl,
    ).run()
    args.total_count += 1

    if args.verbose == 0:
        check_url.response.text = ""

    response_time = check_url.response.elapsed
    args.response_time.push(response_time)
    avg_response_time = f"{int(args.response_time.mean())}"
    max_response_time = f"{int(args.response_time.max())}"
    min_response_time = f"{int(args.response_time.min())}"
    status_code = check_url.response.status_code

    if args.fail_count > 0:
        count_msg = f'CER:{args.error_stack_count}/[red]ER:{args.fail_count}[/red]/SQ:{args.total_count}'
    else:
        count_msg = f'CER:{args.error_stack_count}/ER:{args.fail_count}/SQ:{args.total_count}'

    message = f"<{count_msg}> name={args.section_name}, url={args.url}, " \
              f"status={status_code}, {response_time:>4}ms " \
              f"(avg: {avg_response_time}, max: {max_response_time}, min: {min_response_time})"

    if args.verbose > 0:
        if status_code != 999:
            if args.verbose > 2:
                detail = f" 📄[i]{check_url.response}, criteria: {args.success}, operator: {args.logical_operator}[/i]"
            else:
                detail = ""
            message = f"{message}{detail}"
        else:
            message = f"{message} 😞 "

    if check_url.is_success():
        pawn.app_logger.info(remove_tags(f"[ OK ] {message}"))
    else:
        handle_failure_on_check_url(args, message, check_url)


def handle_failure_on_check_url(args, message, check_url):
    args.fail_count += 1
    args.error_stack_count += 1

    if args.error_stack_count >= args.stack_limit:
        pawn.error_logger.error(remove_tags(f"[FAIL][OVERFLOW]{args.error_stack_count}/{args.stack_limit} "
                                            f"Error Stack Count: {args.error_stack_count}, SEND_SLACK"))
        args.error_stack_count = 0

        if args.dynamic_increase_stack_limit:
            args.stack_limit = args.stack_limit ** 2
            _send_slack(url=args.slack_url, title=f"Error {args.url}", msg_text=args.__dict__)

    pawn.error_logger.error(remove_tags(f"[FAIL] {message}, Error={check_url.response}"))


def set_default_counter(section_name="default"):
    args = copy.deepcopy(pconf().args)
    args.section_name = section_name
    args.response_time = StackList()
    args.error_stack_count = 0
    args.total_count = 0
    args.fail_count = 0
    return args


def generate_task_from_config():
    tasks = []
    pconfig = pconf().PAWN_CONFIG
    config_file = pconf().PAWN_CONFIG_FILE
    pconf_dict = pconfig.as_dict()
    if pconf_dict:
        pawn.console.log(f"Found config file={config_file}")
        for section_name, section_value in pconf_dict.items():
            pawn.console.debug(f"section_name={section_name}, value={section_value}")
            args = set_default_counter(section_name)

            for conf_key, conf_value in section_value.items():
                if getattr(args, conf_key, "__NOT_DEFINED__") != "__NOT_DEFINED__":
                    if is_json(conf_value):
                        conf_value = json.loads(conf_value)
                    if section_name == "default":
                        setattr(pconf().args, conf_key, conf_value)
                    pawn.console.debug(f"Update argument from {config_file}, <{section_name}> {conf_key}={conf_value} <ignore args={getattr(args, conf_key, None)}>")
                    setattr(args, conf_key, conf_value)

            pawn.console.debug(args)
            if args.url != "http":
                tasks.append(args)

    if not tasks:
        args = set_default_counter()
        tasks = [args]

    validate_task_exit_on_failure(tasks)
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
        if is_valid_url(task.url):
            is_least_one_url = True
        else:
            pawn.console.log(f"Invalid url: name={task.section_name}, url={task.url}")

    if not is_least_one_url:
        sys_exit("Requires at least one valid URL. The URL argument must be in the first position.")


def main():
    app_name = 'httping'
    parser = get_parser()
    args, unknown = parser.parse_known_args()
    config_file = args.config_file

    is_hide_line_number = args.verbose > 1
    stdout = not args.quiet

    pawn.set(
        PAWN_CONFIG_FILE=config_file,
        PAWN_PATH=args.base_dir,
        PAWN_LOGGER=dict(
            log_level="INFO",
            stdout_level="INFO",
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

    if args.ignore_ssl:
        disable_ssl_warnings()
    tasks = generate_task_from_config()
    # if args.slack_url:
    #     res = _send_slack(url=args.slack_url, msg_text=tasks)
    #     pawn.console.log(res)
    # _send_slack(url=args.slack_url, title=f"Error HTTPING {args.url}", msg_text=args.__dict__)
    # pawn.console.log(f"console_options={pawn.console_options}")
    # exit()
    pawn.console.log(f"Start httping ... url_count={len(tasks)}")
    pawn.console.log("If you want to see more logs, use the [yellow]-v[/yellow] option")
    pawn.console.log(tasks)

    ThreadPoolRunner(
        func=check_url_process,
        tasks=tasks,
        max_workers=args.workers,
        verbose=args.verbose,
        sleep=args.interval
    ).forever_run()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        pawn.console.log(e)

