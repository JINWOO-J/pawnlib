import os
import re
import requests
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import color_print
from pawnlib.resource import net
from pawnlib.typing import date_utils, shorten_text, escape_markdown, escape_non_markdown
from pawnlib.utils import http, disable_ssl_warnings
import json
import aiohttp
import asyncio
import time


class TelegramBot:
    """
    A class to interact with the Telegram Bot API.

    :param bot_token: Telegram bot token. If not provided, it will be fetched from the 'TELEGRAM_BOT_TOKEN' environment variable.
    :param chat_id: Chat ID to send messages to. If not provided, it will be fetched from the 'TELEGRAM_CHAT_ID' environment variable or determined dynamically.
    :param verify_ssl: Whether to verify the SSL certificate for HTTPS requests. (default: True).
    :param ignore_ssl_warning: Whether to ignore SSL warnings. If True, SSL warnings will be suppressed.
    :param async_mode: Whether to use asynchronous mode. If False, synchronous mode will be used. (default: True)
    :param max_retries: Maximum number of retries for 429 Too Many Requests errors. (default: 5)
    :param retry_delay: Delay in seconds between retries for 429 Too Many Requests errors. (default: 5)

    :raises ValueError: If the bot token is not provided either as an argument or an environment variable.

    Example:

        .. code-block:: python

            bot = TelegramBot(bot_token="your_bot_token", chat_id="your_chat_id", async_mode=False)
            bot.send_message("Hello, world!")
            bot.send_html_message("<b>Hello, world!</b>")
            bot.send_plain_text_message("Just plain text.")
            bot.send_dict_message({"key": "value"})

    """

    def __init__(self, bot_token=None, chat_id=None, verify_ssl=True, ignore_ssl_warning=False, async_mode=False, max_retries=5, retry_delay=5):
        self.bot_token = (bot_token or os.getenv('TELEGRAM_BOT_TOKEN', '')).strip('\'"')
        if not self.bot_token:
            raise ValueError("Telegram bot token is required. Please set it as an argument or in the 'TELEGRAM_BOT_TOKEN' environment variable.")

        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.chat_id = (chat_id or os.getenv('TELEGRAM_CHAT_ID', '')).strip('\'"')
        self.verify_ssl = verify_ssl
        self.async_mode = async_mode
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        if ignore_ssl_warning:
            disable_ssl_warnings()

        if not self.chat_id:
            self.chat_id = self.get_chat_id()

        pawn.console.debug(f"bot_token={self.bot_token}, chat_id={self.chat_id}, async_mode={self.async_mode}")

    @staticmethod
    def escape_markdown(text):
        """
        Escape Markdown special characters for MarkdownV2.

        :param text: The text to escape.
        :return: The escaped text.

        Example:

            .. code-block:: python

                bot = TelegramBot(bot_token="your_bot_token", chat_id="your_chat_id")
                escaped_text = bot.escape_markdown("Hello *world*!")
                print(escaped_text)  # Output: Hello \*world\*!
        """
        # escape_chars = r'_*[]()~`>#+-=|{}.!'
        escape_chars = r'_*`.()-'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

    async def send_multiple_messages_async(self, messages):
        """
        Send multiple messages asynchronously.

        :param messages: A list of messages to send.
        :return: A list of responses from the Telegram API.
        """
        tasks = [self.send_auto_message_async(message) for message in messages]
        return await asyncio.gather(*tasks)

    def send_multiple_messages(self, messages):
        """
        Send multiple messages synchronously.

        :param messages: A list of messages to send.
        :return: A list of responses from the Telegram API.
        """
        if self.async_mode:
            return asyncio.run(self.send_multiple_messages_async(messages))
        else:
            return [self.send_message_sync(message) for message in messages]

    def send_message(self, message, parse_mode="Markdown", disable_web_page_preview=False):
        if self.async_mode:
            # return asyncio.run(self.send_message_async(message, parse_mode, disable_web_page_preview))
            return self.send_message_async(message, parse_mode, disable_web_page_preview)
        else:
            return self.send_message_sync(message, parse_mode, disable_web_page_preview)


    def build_payload(self, message, parse_mode="Markdown", disable_web_page_preview=False, pass_escape=False):
        """
        Build the payload for sending a message.
        """
        _message = self.escape_markdown(message) if parse_mode == "MarkdownV2" and not pass_escape else message
        pawn.console.debug(f"_message -> {_message}")
        payload = {
            "chat_id": self.chat_id,
            "text": _message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }
        return payload

    def send_message_sync(self, message, parse_mode="Markdown", disable_web_page_preview=False, pass_escape=False):
        payload = self.build_payload(message, parse_mode, disable_web_page_preview, pass_escape)

        retries = 0
        while retries < self.max_retries:
            try:
                response = requests.post(f"{self.api_url}/sendMessage", json=payload, verify=self.verify_ssl)
                if response.status_code == 200:
                    return response.json()  # 성공적으로 메시지를 보낸 경우
                elif response.status_code == 429:
                    retries += 1
                    pawn.console.log(f"429 Too Many Requests error. Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    pawn.console.log(f"Failed to send message: {response.status_code} - {response.text}")
                    return None
            except requests.exceptions.RequestException as e:
                pawn.console.log(f"Error sending message: {e}")
                retries += 1
                time.sleep(self.retry_delay)

        pawn.console.log("Maximum number of retries reached. Failed to send message.")
        return None

    async def send_message_async(self, message, parse_mode="MarkdownV2", disable_web_page_preview=False, pass_escape=False):
        payload = self.build_payload(message, parse_mode, disable_web_page_preview, pass_escape)

        retries = 0
        while retries < self.max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{self.api_url}/sendMessage", json=payload, ssl=self.verify_ssl) as response:
                        if response.status == 200:
                            return await response.json()  # 성공적으로 메시지를 보낸 경우
                        elif response.status == 429:
                            retries += 1
                            pawn.console.log(f"429 Too Many Requests error. Retrying in {self.retry_delay} seconds...")
                            await asyncio.sleep(self.retry_delay)
                        else:
                            pawn.console.log(f"Failed to send message: {response.status} - {await response.text()}")
                            return None
            except aiohttp.ClientError as e:
                pawn.console.log(f"Error sending message: {e}")
                retries += 1
                await asyncio.sleep(self.retry_delay)

        pawn.console.log("Maximum number of retries reached. Failed to send message.")
        return None

    def send_html_message(self, message):
        return self.send_message(message, parse_mode="HTML")

    async def send_html_message_async(self, message):
        return await self.send_message_async(message, parse_mode="HTML")

    def send_plain_text_message(self, message, parse_mode="Markdown"):
        return self.send_message(message, parse_mode=parse_mode)

    async def send_plain_text_message_async(self, message, parse_mode="Markdown"):
        return await self.send_message_async(message, parse_mode=parse_mode)

    def send_dict_message(self, message_dict):
        message = json.dumps(message_dict, indent=2)
        return self.send_plain_text_message(message)

    async def send_dict_message_async(self, message_dict):
        message = json.dumps(message_dict, indent=2)
        return await self.send_plain_text_message_async(message)

    def get_chat_id(self):
        """Retrieve chat_id by getting updates from the Telegram bot API"""
        response = requests.get(f"{self.api_url}/getUpdates", verify=self.verify_ssl)
        if response.status_code == 200:
            data = response.json()
            if "result" in data and len(data["result"]) > 0:
                chat_id = data["result"][-1]["message"]["chat"]["id"]
                pawn.console.debug(f"Retrieved chat_id: {chat_id}")
                return chat_id
            else:
                raise ValueError("No messages found in bot updates to retrieve chat_id.")
        else:
            raise ConnectionError(f"Failed to retrieve updates: {response.status_code} - {response.text}")

    def save_chat_id(self, chat_id_file="chat_id.txt"):
        with open(chat_id_file, "w") as file:
            file.write(str(self.chat_id))
        pawn.console.debug(f"chat_id saved to {chat_id_file}")

    def load_chat_id(self, chat_id_file="chat_id.txt"):
        if os.path.exists(chat_id_file):
            with open(chat_id_file, "r") as file:
                self.chat_id = file.read().strip()
            pawn.console.debug(f"Loaded chat_id from {chat_id_file}")
        else:
            pawn.console.debug(f"chat_id file {chat_id_file} not found. Retrieving chat_id using getUpdates...")
            self.chat_id = self.get_chat_id()

    def send_auto_message(self, message):
        if isinstance(message, dict):
            self.send_dict_message(message)
        elif isinstance(message, str):
            if self.is_html(message):
                self.send_html_message(message)
            elif self.is_markdown(message):
                self.send_message(message, parse_mode="Markdown")
            else:
                self.send_plain_text_message(message)
        else:
            raise ValueError("Unsupported message type")

    async def send_auto_message_async(self, message):
        if isinstance(message, dict):
            await self.send_dict_message_async(message)
        elif isinstance(message, str):
            if self.is_html(message):
                await self.send_html_message_async(message)
            elif self.is_markdown(message):
                await self.send_message_async(message, parse_mode="Markdown")
            else:
                await self.send_plain_text_message_async(message)
        else:
            raise ValueError("Unsupported message type")

    def is_html(self, message):
        return bool(re.search(r'<[^>]+>', message))

    def is_markdown(self, message):
        """Check if the string contains MarkdownV2 special characters"""
        # MarkdownV2에서 사용하는 특수 문자를 검사
        markdown_special_chars = r'[_*[\]()~`>#+-=|{}.!]'
        return bool(re.search(f'[{re.escape(markdown_special_chars)}]', message))


def get_level_color(c_level):
    default_color = "5be312"
    return dict(
        info="5be312",
        warn="f2c744",
        warning="f2c744",
        error="f70202",
    ).get(c_level, default_color)


def send_slack(url, msg_text, title=None, send_user_name="CtxBot", msg_level='info'):
    """

    Send to slack message

    :param url: webhook url
    :param msg_text:
    :param title:
    :param send_user_name:
    :param msg_level:
    :return:
    """

    if title:
        msg_title = title
    else:
        msg_title = shorten_text(msg_text, width=50)

    msg_level = msg_level.lower()

    if url is None:
        pawn.error_logger.error("[ERROR] slack webhook url is None")
        return False
    p_color = get_level_color(msg_level)

    payload = {
        # https://app.slack.com/block-kit-builder
        "username": send_user_name,
        "text": msg_title,
        "blocks": [
            {"type": "divider"}
        ],
        "attachments": [
            {
                "color": "#" + p_color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": msg_title
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": f'{"+ [HOST]":^12s} : {net.get_hostname()}, {net.get_public_ip()}'
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": f'{"+ [DATE]":^12s} : {(date_utils.todaydate("log"))}'
                        }
                    },
                    # {
                    #     "type": "section",
                    #     "text": {
                    #         "type": "plain_text",
                    #         "text": f'{"+ [DESC]":^12s} : {msg_text}'
                    #     }
                    # }
                ]
            }
        ]
    }

    def _make_attachment(key=None, value=None):
        if key:
            text = f'💡{key:<12s}: {value}'
        elif not key:
            text = f'{"+ [DESC]":^12s} : {msg_text}'
        else:
            text = ""

        return {
            "type": "section",
            "text": {
                "type": "plain_text",
                "text": text
            },
        }
    _attachments = []
    for attachment in payload["attachments"]:
        if isinstance(msg_text, dict):
            for key, value in msg_text.items():
                if key:
                    attachment['blocks'].append(_make_attachment(key, value))
        elif isinstance(msg_text, list):
            for value_in_list in msg_text:
                if value_in_list:
                    attachment['blocks'].append(_make_attachment(value=value_in_list))
        elif msg_text:
            attachment['blocks'].append(_make_attachment(value=msg_text))
        _attachments.append(attachment)
    payload["attachments"] = _attachments
    try:
        post_result = requests.post(url, json=payload, verify=False, timeout=15)
        if post_result and post_result.status_code == 200 and post_result.text == "ok":
            pawn.app_logger.info("[OK][Slack] Send slack")
            return True
        else:
            pawn.error_logger.error(f"[ERROR][Slack] Got errors, status_code={post_result.status_code}, text={shorten_text(post_result.text, 50)}")
            return False

    except Exception as e:
        pawn.error_logger.error(f"[ERROR][Slack] Got errors -> {e}")
        return False


def send_slack_token(title=None, message=None, token=None, channel_name=None, send_user="python_app", msg_level="info"):
    if title:
        msg_title = title
    else:
        msg_title = message

    p_color = get_level_color(msg_level)

    attachments = [
        {
            # "pretext": f"[{send_user}] {title}",
            "title": str(title).capitalize(),
            # "text": f"{converter.todaydate('ms')}  {message}",
            # "mrkdwn_in": ["pretext"]
        },
        {
            "color": "#" + p_color,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": f'Title : {msg_title}'
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": f'{"+ [HOST]":^12s} : {net.get_hostname()}, {net.get_public_ip()}'
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": f'{"+ [DATE]":^12s} : {(date_utils.todaydate("log"))}'
                    }
                },
            ],
            # "mrkdwn_in": ["blocks"],
        }
    ]
    if isinstance(message, dict):
        if attachments[-1].get("blocks"):
            for message_k, message_v in message.items():
                attachments[-1]['blocks'].append(
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": f"+ [{message_k:<12s}]: {message_v}"
                        }
                    }
                )
    else:
        attachments[-1]['blocks'].append(
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": f"{'+ [DESC]':^12s} : {message}"
                }
            }
        )

    payload = {
        "channel": channel_name,
        "attachments": attachments
    }
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        res = http.jequest(url='https://slack.com/api/chat.postMessage', method="post", payload=payload, headers=headers)

        if res and res.get('status_code') == 200 and res['json']['ok'] == True:
            pawn.app_logger.info(f"[OK][Slack] Send slack with token")
            return True
        else:
            pawn.error_logger.error(f"[ERROR][Slack] Got errors, status_code={res.get('status_code')}, text={res.get('text')}")
            return False

    except Exception as e:
        pawn.error_logger.error(f"[ERROR][Slack] Got errors -> {e}")
        return False

