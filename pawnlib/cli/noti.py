#!/usr/bin/env python3
import os
import sys
import asyncio

from pawnlib.config import pawn, setup_logger, setup_app_logger as _setup_app_logger, create_app_logger
from pawnlib.builder.generator import generate_banner
from pawnlib.__version__ import __version__ as _version
from pawnlib.input.prompt import CustomArgumentParser, ColoredHelpFormatter
from pawnlib.config.settings_config import SettingDefinition, load_environment_settings, BaseSettingsConfig, AppConfig
from pawnlib.utils.notify import send_slack, TelegramBot
from dataclasses import dataclass
from pawnlib.typing import shorten_text, random_token_address,  str2bool, is_float, sys_exit
from pawnlib.output import print_var
from pawnlib.config import pawn, LoggerFactory
from pawnlib.utils.log import print_logger_configurations


IS_DOCKER = str2bool(os.environ.get("IS_DOCKER"))

__description__ = "Notify Tool"
__epilog__ = (
    "\nUsage examples:\n\n"
    "1. Send a Telegram message:\n"
    "     `pawns telegram send --message 'Hello!'`\n\n"
    "2. List Telegram chat updates:\n"
    "     `pawns telegram ls`\n\n"
    "3. Send a Slack message:\n"
    "     `pawns slack send --message 'Hello!'`\n\n"
    "Note:\n"
    "  Use `--help` with any command for details, e.g., `pawns telegram --help`.\n"
)


def get_parser():
    parser = CustomArgumentParser(
        description='Command Line Interface for Notify',
        formatter_class=ColoredHelpFormatter,
        epilog=__epilog__,
        add_help=False
    )
    parser = get_arguments(parser)
    return parser


def add_common_arguments(parser):
    """Add common arguments to parsers."""
    parser.add_argument('-v', '--verbose', action='count', default=1, help='Increase verbosity level. Use -v, -vv, -vvv, etc.')
    parser.add_argument('--message', type=str, required=False, help='Message to send')
    parser.add_argument('--priority', choices=['env', 'args'], default='env' if IS_DOCKER else 'args',
        help='Specify whether to prioritize environment variables ("env") or command-line arguments ("args"). Default is "args".'
    )
    return parser


@dataclass
class SettingsConfig(BaseSettingsConfig):
    slack_webhook_url: SettingDefinition = SettingDefinition('SLACK_WEBHOOK_URL', default=None, value_type=str)
    telegram_bot_token: SettingDefinition = SettingDefinition('TELEGRAM_BOT_TOKEN', default=None, value_type=str)
    telegram_chat_id: SettingDefinition = SettingDefinition('TELEGRAM_CHAT_ID', default=None, value_type=str)

    message: SettingDefinition = SettingDefinition('MESSAGE', default=None, value_type=str)    
    priority: SettingDefinition = SettingDefinition('PRIORITY', default='env' if IS_DOCKER else 'args', value_type=str)
    verbose: SettingDefinition = SettingDefinition('VERBOSE', default=1, value_type=int)
    

def get_arguments(parser=None):    
    if not parser:
        parser = CustomArgumentParser(
            description='Command Line Interface for ICON Maximizer',
            formatter_class=ColoredHelpFormatter,
            epilog=__epilog__,
            add_help=True,
        )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    common_parser = CustomArgumentParser(add_help=False)
    add_common_arguments(common_parser)
    
    telegram_parser = subparsers.add_parser("telegram", help="Send Telegram message", parents=[common_parser], add_help=True)
    telegram_parser.add_argument('--telegram-bot-token', type=str, required=False, help='telegram bot token')    
    telegram_parser.add_argument('--telegram-chat-id', type=str, required=False, help='telegram chat id')
    telegram_parser.add_argument('action', choices=['send', 'ls'], nargs='?', default='ls', help='Action to perform with Telegram')
    slack_parser = subparsers.add_parser("slack", help="Send Slack message", parents=[common_parser], add_help=True)    
    slack_parser.add_argument('--slack-webhook-url', type=str, required=False, help='slack webhook url')    
    return parser


def main():
    banner = generate_banner(
        app_name=__description__,
        author="jinwoo",
        description="ICON utils",
        font="graffiti",
        version=_version
    )

    pawn.set(PAWN_LINE=False)

    parser = get_parser()
    args, unknown = parser.parse_known_args()
    print(banner)

    args_index = 2 if len(sys.argv) > 1 and sys.argv[1] == 'noti' else 1

    if len(sys.argv) <= args_index:
        parser.print_help()
        sys_exit("No command specified", 0)

    args = parser.parse_args(sys.argv[args_index:])
    pawn.console.log(f"args = {args}")

    settings = load_environment_settings(args, SettingsConfig)
    
    logger = create_app_logger(        
        app_name="icon_tools",
        propagate=False, verbose=settings.get('verbose')
    )

    if settings.get('verbose') > 2:
        LoggerFactory.set_global_log_level(verbose=settings.get('verbose'))

    config = AppConfig(logger=logger, **settings)
    print_var(config)

    if args.command == 'telegram':
        bot = TelegramBot(
            bot_token=args.telegram_bot_token,
            chat_id=args.telegram_chat_id,
            verify_ssl=False,
            ignore_ssl_warning=True,
        )
        if args.action == 'ls':
            bot.display_all_chat_updates()
            bot.get_chat_id()
        elif args.action == 'send':        
            bot.send_message(args.message)
        
    elif args.command == 'slack':
        bot = send_slack(
            url=config.slack_webhook_url,
            title=args.message,            
            msg_text=args.message,            
            status="info",
            simple_mode=True,
            async_mode=False,
            footer="Pawnlib"
        )
        pawn.console.log(f"Send Slack message = {bot}")
    else:
        parser.print_help()
        sys_exit("No command specified", 0)


if __name__ == '__main__':
    main()
