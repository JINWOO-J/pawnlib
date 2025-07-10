import os
import re
import requests
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.config import setup_logger, get_logger, LoggerMixinVerbose
from pawnlib.output import color_print
from pawnlib.resource import net
from pawnlib.typing import date_utils, shorten_text, escape_markdown, escape_non_markdown
from pawnlib.utils import http
from pawnlib.utils.network import disable_requests_ssl_warnings

import json
import aiohttp
import asyncio
import time
from pawnlib.typing.constants import StatusType
from typing import Union, Awaitable, TypeVar, Dict, List, Optional, Any
import logging
from rich.table import Table
from datetime import datetime


SlackReturnType = TypeVar('SlackReturnType', bool, Awaitable[bool])
SlackResponseType = TypeVar('SlackResponseType', bool, Dict[str, Any])

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
            disable_requests_ssl_warnings()

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

    def display_all_chat_updates(self):
        """Retrieve all unique chat_ids and their details by getting updates from the Telegram bot API"""

        response = requests.get(f"{self.api_url}/getUpdates", verify=self.verify_ssl)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to retrieve updates: {response.status_code} - {response.text}")

        data = response.json()
        table = Table(title="Telegram Updates")

        # 테이블 열 추가
        table.add_column("Update ID", justify="center", style="cyan")
        table.add_column("Chat ID", justify="center", style="magenta")
        table.add_column("Chat Title", justify="center", style="magenta")
        table.add_column("Type", justify="center", style="magenta")
        table.add_column("From", justify="center", style="green")
        table.add_column("Message", justify="left", style="white")
        table.add_column("Date", justify="center", style="yellow")
        table.add_column("Status", justify="center", style="blue")

        if "result" in data:
            # 날짜 기준으로 정렬
            updates = []
            for update in data["result"]:
                timestamp = None
                if "message" in update:
                    timestamp = update["message"]["date"]
                elif "my_chat_member" in update:
                    timestamp = update["my_chat_member"]["date"]

                if timestamp is not None:
                    updates.append((update, timestamp))

            # 날짜 기준으로 정렬 (내림차순)
            updates.sort(key=lambda x: x[1], reverse=True)

            for update, _ in updates:
                chat_info = self.extract_chat_info(update)
                if chat_info:
                    table.add_row(*chat_info)

        pawn.console.print(table)  # 테이블 출력
        # pawn.console.print(data)


    def extract_chat_info(self, update):
        """Extract chat information from the update."""

        chat_id = None
        chat_title = ""
        chat_type = ""
        from_user = ""
        message_text = ""
        timestamp = ""
        status = ""

        if "message" in update and "chat" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            chat_title = update["message"]["chat"].get("title", "N/A")
            chat_type = update["message"]["chat"].get("type", "N/A")
            from_user = f"{update['message']['from']['first_name']} {update['message']['from'].get('last_name', '')}"
            message_text = update['message'].get('text', '')
            timestamp = datetime.fromtimestamp(update['message']['date']).strftime('%Y-%m-%d %H:%M:%S')

        elif "my_chat_member" in update:
            chat_id = update['my_chat_member']['chat']['id']
            chat_title = update["my_chat_member"]["chat"].get("title", "N/A")
            chat_type = update["my_chat_member"]["chat"].get("type", "N/A")
            from_user = f"{update['my_chat_member']['from']['first_name']} {update['my_chat_member']['from'].get('last_name', '')}"
            status = update['my_chat_member']['new_chat_member']['status']
            timestamp = datetime.fromtimestamp(update['my_chat_member']['date']).strftime('%Y-%m-%d %H:%M:%S')

        if "group_chat_created" in update.get("message", {}):
            status = "Group Chat Created"

        if chat_id is not None:
            return [
                str(update.get('update_id', '')),
                str(chat_id),
                str(chat_title),
                str(chat_type),
                from_user.strip(),
                message_text,
                timestamp,
                status if status else "N/A"
            ]
        return None

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


class SlackNotifier(LoggerMixinVerbose):
    """
    Class for sending Slack messages. Provides both synchronous and asynchronous methods.

    :param webhook_url: Slack webhook URL. If not provided, it will be fetched from the environment variable 'SLACK_WEBHOOK_URL'.
    :param username: Username to display in Slack.
    :param icon_emoji: Emoji to use as the icon for the message.
    :param retries: Number of retry attempts in case of failure.
    :param retry_delay: Time to wait between retries (in seconds).
    """

    def __init__(
        self,
        webhook_url: str = None,
        username: str = "PawnBot",
        icon_emoji: str = ":robot_face:",
        retries: int = 3,
        retry_delay: int = 2,
        verbose: int = 1,
        logger: logging.Logger = None,
    ):
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL', '')
        self.username = username
        self.icon_emoji = icon_emoji
        self.retries = retries
        self.retry_delay = retry_delay
        self.init_logger(logger, verbose)

        if not self.webhook_url:
            self.logger.error("Slack webhook URL is not set. Please set the 'webhook_url' parameter or the 'SLACK_WEBHOOK_URL' environment variable.")

    def _get_level_color(self, level: str = "") -> str:
        """Return color code according to the message level."""
        color_mapping = {
            "info": "5be312",
            "warn": "f2c744",
            "warning": "f2c744",
            "error": "ff0000",
            "trace": "1e90ff",
            "critical": "ff00ff",
            "debug": "a9a9a9",
            "success": "5be312",
            "failed": "ff0000",
            "in_progress": "f2c744",
            "complete": "5be312",
            "paused": "f2c744",
            "running": "f2c744",
        }

        level = level.lower() if level else ""
        return color_mapping.get(level, "5be312")

    def _get_status_emoji(self, status: Union[str, StatusType]) -> str:
        """Return emoji according to the status."""
        status_emojis = {
            'success': '✅',  # 성공
            'failed': '🚨',  # 실패
            'warning': '⚠️',  # 경고
            'info': 'ℹ️',  # 정보
            'critical': '❗',  # 중대한 문제
            'in_progress': '⏳',  # 진행 중
            'complete': '🏁',  # 완료
            'paused': '⏸️',  # 일시 중지
            'running': '🏃',  # 실행
            'error': '🔴',  # 에러
            'retrying': '🔄',  # 재시도 중
            'changed': '♻️',  # 변경
            'stopped': '🛑',  # 중단
            'queued': '⌛',  # 대기 중
            'canceled': '❌',  # 작업 취소
            'approved': '👍',  # 승인
            'rejected': '👎',  # 거절
            'scheduled': '🗓️',  # 스케줄된 작업
            'maintenance': '🛠️',  # 유지보수
            'update': '⬆️',  # 업데이트
            'unknown': '❓'
        }
        return status_emojis.get(str(status).lower(), '')

    def create_message_payload(
        self,
        message: Union[str, Dict, List],
        title: str = "",
        text: str = "",
        msg_level: str = "info",
        status: Union[str, StatusType] = None,
        simple_mode: bool = False,
        footer: str = "",
        timestamp_format: str = None,
        max_text_length: int = 1000
    ) -> Dict[str, Any]:
        """Create message payload."""

        emoji = self._get_status_emoji(status) if status else ""
        color = self._get_level_color(msg_level)
        title_text = f"{emoji} {title}" if emoji and title else title

        # Date/time formatting
        current_timestamp = int(time.time())
        formatted_time = ""
        if timestamp_format:
            from datetime import datetime
            formatted_time = datetime.now().strftime(timestamp_format)

        # Set default payload
        payload = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
        }

        # Simple mode
        if simple_mode:
            msg_content = message if isinstance(message, str) else json.dumps(message, indent=2)
            if len(msg_content) > max_text_length:
                msg_content = f"{msg_content[:max_text_length]}..."

            payload["text"] = f"{title_text}\n{msg_content}"
            return payload

        # Normal mode
        attachments = [{
            "color": f"#{color}",
            "title": title_text,
            "ts": current_timestamp,
            "text": text or "",
        }]

        # Process message content
        if isinstance(message, dict):
            fields = []
            for key, value in message.items():
                fields.append({
                    "title": str(key),
                    "value": str(value) if value is not None else "N/A",
                    "short": True
                })
            attachments[0]["fields"] = fields
        elif isinstance(message, list):
            # if text:
            #     attachments[0]["fallback"] = text
            # else:
            text_content = "\n".join([str(item) for item in message])
            attachments[0]["text"] = text_content
        else:
            attachments[0]["text"] = str(message)

        # Add timestamp format
        if formatted_time:
            attachments[0]["footer"] = f"{footer} | {formatted_time}" if footer else formatted_time
        elif footer:
            attachments[0]["footer"] = f"{footer} | sent from {net.get_hostname()}"

        payload["attachments"] = attachments
        return payload

    def send(
        self,
        message: Union[str, Dict, List],
        title: str = "",
        msg_level: str = "info",
        status: Union[str, StatusType] = None,
        simple_mode: bool = False,
        footer: str = "",
        timestamp_format: str = None,
        text: str = "",
    ) -> bool:
        """
        Synchronously send a Slack message.

        :param message: The message to send (string, dictionary, list)
        :param title: Message title
        :param msg_level: Message severity level (info, warn, error, critical, etc.)
        :param status: Status type or string for dynamic emoji and message formatting.
        :param simple_mode: If True, send a simplified message without additional info.
        :param footer: Footer text to display at the bottom of the message.
        :param timestamp_format: Time display format (e.g. "%Y-%m-%d %H:%M:%S")
        :return: Boolean indicating success or failure.
        """
        if not self.webhook_url:
            self.logger.error("SlackNotifier: Webhook URL is not set.")
            return False

        payload = self.create_message_payload(
            message=message,
            title=title,
            msg_level=msg_level,
            status=status,
            simple_mode=simple_mode,
            footer=footer,
            timestamp_format=timestamp_format,
            text=text,
        )

        # Retry logic
        for attempt in range(self.retries):
            try:
                response = requests.post(self.webhook_url, json=payload, timeout=10)
                if response.status_code == 200 and response.text == "ok":
                    pawn.app_logger.info("SlackNotifier: Message sent successfully")
                    return True
                else:
                    pawn.error_logger.error(f"SlackNotifier: Response error. Status code: {response.status_code}, response: {response.text}")
            except Exception as e:
                pawn.error_logger.error(f"SlackNotifier: Exception occurred: {str(e)}")

            # If not the last attempt, wait and retry
            if attempt < self.retries - 1:
                self.logger.info(f"SlackNotifier: Retrying... ({attempt + 1}/{self.retries})")
                time.sleep(self.retry_delay)

        return False

    async def send_async(
        self,
        message: Union[str, Dict, List],
        title: str = "",
        msg_level: str = "info",
        status: Union[str, StatusType] = None,
        simple_mode: bool = False,
        footer: str = "",
        timestamp_format: str = None,
        text: str = "",
    ) -> bool:
        """
        Asynchronously send a Slack message.

        :param message: The message to send (string, dictionary, list)
        :param title: Message title
        :param msg_level: Message severity level (info, warn, error, critical, etc.)
        :param status: Status type or string for dynamic emoji and message formatting.
        :param simple_mode: If True, send a simplified message without additional info.
        :param footer: Footer text to display at the bottom of the message.
        :param timestamp_format: Time display format (e.g. "%Y-%m-%d %H:%:M:%S")
        :return: Boolean indicating success or failure.
        """
        if not self.webhook_url:
            pawn.error_logger.error("SlackNotifier: Webhook URL is not set.")
            return False

        payload = self.create_message_payload(
            message=message,
            title=title,
            msg_level=msg_level,
            status=status,
            simple_mode=simple_mode,
            footer=footer,
            timestamp_format=timestamp_format,
            text=text,
        )

        # Asynchronous retry logic
        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            response_text = await response.text()
                            if response_text == "ok":
                                pawn.app_logger.info("SlackNotifier: Asynchronous message sent successfully")
                                return True
                        pawn.error_logger.error(f"SlackNotifier: Response error. Status code: {response.status}, response: {await response.text()}")
            except Exception as e:
                pawn.error_logger.error(f"SlackNotifier: Exception occurred during asynchronous send: {str(e)}")

            # If not the last attempt, wait and retry
            if attempt < self.retries - 1:
                pawn.app_logger.info(f"SlackNotifier: Retrying... ({attempt + 1}/{self.retries})")
                await asyncio.sleep(self.retry_delay)

        return False

    def send_batch(self, messages: List[Dict]) -> List[bool]:
        """
        Send multiple messages in batch (synchronous)

        :param messages: List of messages to send [{"message": "content", "title": "title", ...}, ...]
        :return: List of results for each message
        """
        results = []
        for msg_data in messages:
            result = self.send(**msg_data)
            results.append(result)
        return results

    async def send_batch_async(self, messages: List[Dict]) -> List[bool]:
        """
        Send multiple messages in batch (asynchronous)

        :param messages: List of messages to send [{"message": "content", "title": "title", ...}, ...]
        :return: List of results for each message
        """
        tasks = [self.send_async(**msg_data) for msg_data in messages]
        return await asyncio.gather(*tasks)

    def send_error(self, error: Exception, additional_info: Dict = None, title: str = "Error occurred"):
        """
        Send error information

        :param error: The exception object that occurred
        :param additional_info: Additional information dictionary
        :param title: Message title
        :return: Boolean indicating success or failure
        """
        import traceback
        error_type = type(error).__name__
        error_message = str(error)
        error_traceback = traceback.format_exc()

        message = {
            "Error Type": error_type,
            "Error Message": error_message,
            "Stack Trace": f"```{error_traceback[:800]}```" if len(error_traceback) > 800 else f"```{error_traceback}```"
        }

        if additional_info:
            for key, value in additional_info.items():
                message[key] = value

        return self.send(
            message=message,
            title=title,
            msg_level="error",
            status="failed"
        )

    async def send_error_async(self, error: Exception, additional_info: Dict = None, title: str = "Error occurred"):
        """
        Send error information asynchronously

        :param error: The exception object that occurred
        :param additional_info: Additional information dictionary
        :param title: Message title
        :return: Boolean indicating success or failure
        """
        import traceback
        error_type = type(error).__name__
        error_message = str(error)
        error_traceback = traceback.format_exc()

        message = {
            "Error Type": error_type,
            "Error Message": error_message,
            "Stack Trace": f"```{error_traceback[:800]}```" if len(error_traceback) > 800 else f"```{error_traceback}```"
        }

        if additional_info:
            for key, value in additional_info.items():
                message[key] = value

        return await self.send_async(
            message=message,
            title=title,
            msg_level="error",
            status="failed"
        )


def get_level_color(c_level: str = "") -> str:
    color_mapping = {
        "info": "5be312",
        "warn": "f2c744",
        "warning": "f2c744",
        "error": "ff0000",
        "trace": "1e90ff",
        "critical": "ff00ff",
        "debug": "a9a9a9",
        "success": "5be312",
        "failed": "ff0000",
        "in_progress": "f2c744",
        "complete": "5be312",
        "paused": "f2c744",
        "running": "f2c744",
    }

    c_level = c_level.lower() if c_level else ""
    return color_mapping.get(c_level, "5be312")  # 기본 색상


def get_status_emoji(status: Union[str, StatusType]) -> str:
    """
    Return appropriate emoji based on the status.

    :param status: The status (success, failed, warning, etc.)
    :return: Emoji string corresponding to the status
    """
    # status_emojis = {
    #     'success': ':white_check_mark:',  # 성공
    #     'failed': ':x:',  # 실패
    #     'warning': ':warning:',  # 경고
    #     'info': ':information_source:',  # 정보
    #     'critical': ':bangbang:',  # 중대한 문제
    #     'in_progress': ':hourglass_flowing_sand:',  # 진행 중
    #     'complete': ':checkered_flag:',  # 완료
    #     'paused': ':pause_button:',  # 일시 중지
    #     'running': ':runner:',  # 실행 중
    #     'error': ':red_circle:',  # 에러
    #     'retrying': ':repeat:',  # 재시도 중
    #     'stopped': ':stop_sign:',  # 중단
    #     'queued': ':hourglass:',  # 대기 중
    # }
    status_emojis = {
        'success': '✅',  # 성공
        'failed': '🚨',  # 실패
        'warning': '⚠️',  # 경고
        'info': 'ℹ️',  # 정보
        'critical': '❗',  # 중대한 문제
        'in_progress': '⏳',  # 진행 중
        'complete': '🏁',  # 완료
        'paused': '⏸️',  # 일시 중지
        'running': '🏃',  # 실행
        'error': '🔴',  # 에러
        'retrying': '🔄',  # 재시도 중
        'stopped': '🛑',  # 중단
        'queued': '⌛',  # 대기 중
        'canceled': '❌',  # 작업 취소
        'approved': '👍',  # 승인
        'rejected': '👎',  # 거절
        'scheduled': '🗓️',  # 스케줄된 작업
        'maintenance': '🛠️',  # 유지보수
        'update': '⬆️',  # 업데이트
        'unknown': '❓'
    }
    return status_emojis.get(status, '')  # 기본값은 알 수 없는 상태 이모지


def create_slack_payload(
        msg_text: Union[str, dict, list],
        title: str,
        send_user_name: str,
        msg_level: str,
        status: Union[str, StatusType],
        simple_mode: bool,
        icon_emoji: str = "",
        max_value_length: int = 100,
        footer: str = "",
        text: str = ""
) -> dict:
    """
    Create the payload for sending a message to Slack.

    :param msg_text: The main message text, can be a string, dict, or list.
    :type msg_text: Union[str, dict, list]
    :param title: Title of the message.
    :type title: str
    :param send_user_name: The username to display in Slack.
    :type send_user_name: str
    :param msg_level: Severity level of the message (info, warning, error, critical).
    :type msg_level: str
    :param status: Status type or string for dynamic emoji and message formatting.
    :type status: Union[str, StatusType]
    :param simple_mode: If True, send a simplified message without additional info.
    :type simple_mode: bool
    :param icon_emoji: Optional emoji to display as the icon for the message.
    :type icon_emoji: str
    :param max_value_length: Maximum length for any single value.
    :type max_value_length: int
    :param footer: Footer text to display at the bottom of the message.
    :type footer: str
    :param text: Optional text to display in Slack
    :type text: str
    :return: Dictionary containing the Slack message payload.
    :rtype: dict
    """
    def truncate_text(text: str, max_length: int) -> str:
        """Truncate text if it exceeds the maximum length."""
        _text = str(text)
        return _text if len(_text) <= max_length else _text[:max_length - 3] + "..."

    emoji = get_status_emoji(status)
    msg_title = title if title else shorten_text(msg_text, width=50)
    p_color = get_level_color(msg_level)
    _msg_title = f"{emoji} {msg_title}" if status else msg_title

    category_emoji = "▪️"
    payload = {
        "username": send_user_name,
        "text": _msg_title,
        "icon_emoji": icon_emoji if icon_emoji else ":robot_face:",
        "blocks": [{"type": "divider"}],
        "attachments": [{
            "color": f"#{p_color}",
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": _msg_title}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f'{category_emoji}{"*Host*":^12s} : {net.get_hostname()}, {net.get_public_ip(use_cache=True)}'}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f'{category_emoji}{"*Date*":^12s} : {date_utils.todaydate("log")}'}}]
        }]
    }

    if footer:
        formatted_message = format_slack_message(
            title=f"{emoji} {title}" if emoji else title,
            msg_text=msg_text,
            msg_level=msg_level,
            status=status,
            icon_emoji=":rocket:",
            footer=footer or "Additional info",
            text=text
        )
        # from pawnlib.output import print_var
        # print_var(formatted_message)
        return formatted_message

    elif simple_mode:
        return {"username": send_user_name, "text": f"{msg_title}\n{msg_text}", "attachments": []}

    def _make_attachment(key=None, value=None):
        if key == "Info":
            text = f'{category_emoji}{"Info":^12s} : {truncate_text(value, max_value_length)}'
        elif key:
            text = f'💡{key:^12s}: {truncate_text(value, max_value_length)}'
        elif not key:
            text = f'{category_emoji}{"Info":^12s} : {truncate_text(msg_text, max_value_length)}'
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
                    attachment['blocks'].append(_make_attachment(key, truncate_text(value, max_value_length)))
        elif isinstance(msg_text, list):
            for value_in_list in msg_text:
                if value_in_list:
                    attachment['blocks'].append(_make_attachment(value=value_in_list))
        elif msg_text:
            attachment['blocks'].append(_make_attachment(value=truncate_text(msg_text, max_value_length)))
        _attachments.append(attachment)
    payload["attachments"] = _attachments
    return payload


async def send_slack_async(
        url: str,
        payload: dict,
        retries: int
) -> bool:
    """
    Asynchronous Slack message sender with retry logic.

    :param url: Slack webhook URL.
    :type url: str
    :param payload: The payload to send to Slack.
    :type payload: dict
    :param retries: Number of retry attempts in case of failure.
    :type retries: int

    :return: Boolean indicating success or failure.
    :rtype: bool
    """
    async with aiohttp.ClientSession() as session:
        for attempt in range(retries):
            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        pawn.app_logger.info("[OK][Slack] Slack message sent successfully.")
                        return True
                    else:
                        pawn.error_logger.error(f"[ERROR][Slack] Error in response. Status: {response.status}")
            except Exception as e:
                pawn.error_logger.error(f"[ERROR][Slack] Exception occurred: {str(e)}")
            pawn.error_logger.info(f"[INFO][Slack] Retrying... ({attempt + 1}/{retries})")
            await asyncio.sleep(2)
    return False


def send_slack_sync(
        url: str,
        payload: dict,
        retries: int
) -> bool:
    """
    Synchronous Slack message sender with retry logic.

    :param url: Slack webhook URL.
    :type url: str
    :param payload: The payload to send to Slack.
    :type payload: dict
    :param retries: Number of retry attempts in case of failure.
    :type retries: int

    :return: Boolean indicating success or failure.
    :rtype: bool
    """
    for attempt in range(retries):
        try:
            post_result = requests.post(url, json=payload, timeout=15)
            if post_result.status_code == 200 and post_result.text == "ok":
                logging.info("[OK][Slack] Slack message sent successfully.")
                return True
            else:
                logging.error(f"[ERROR][Slack] Error in response. Status: {post_result.status_code}, Response: {shorten_text(post_result.text, 50)}")
        except Exception as e:
            logging.error(f"[ERROR][Slack] Exception occurred: {str(e)}")
        logging.info(f"[INFO][Slack] Retrying... ({attempt + 1}/{retries})")
        time.sleep(2)
    return False


def send_slack(
        url: str = "",
        msg_text: Union[str, dict, list] = "",
        title: str = "",
        text: str = "",
        send_user_name: str = "CtxBot",
        msg_level: str = 'info',
        retries: int = 1,
        status: Union[str, StatusType] = 'ℹ️',
        simple_mode: bool = False,
        async_mode: bool = False,
        icon_emoji: str = "",
        footer: str = ""
) -> SlackReturnType:
    """
    Send a message to Slack with optional retry logic and dynamic emoji based on status.

    :param url: Slack webhook URL (fetched from env `SLACK_WEBHOOK_URL` if not provided)
    :type url: str
    :param msg_text: The main message to send
    :type msg_text: Union[str, dict, list]
    :param title: Optional title for the message
    :type title: str
    :param text: Optional text to display in Slack
    :type text: str
    :param send_user_name: Username to display in Slack
    :type send_user_name: str
    :param msg_level: Message severity level (info, warning, error, critical)
    :type msg_level: str
    :param retries: Number of retries in case of failure
    :type retries: int
    :param status: Either a string or StatusType enum value to use a different format with emojis
    :type status: Union[str, StatusType]
    :param simple_mode: If True, send a simple message without extra info like host or date
    :type simple_mode: bool
    :param async_mode: If True, sends the message asynchronously
    :type async_mode: bool
    :param icon_emoji: Optional emoji to display as the icon for the message.
    :type icon_emoji: str
    :param footer: Footer text to display at the bottom of the message.
    :type footer: str
    :return: Boolean indicating success or failure
    :rtype: bool

    Example:

        .. code-block:: python

            from pawnlib.utils.notify import send_slack

            # Send a message with status using StatusType enum
            send_slack(SLACK_WEBHOOK_URL, "The process completed successfully",
                       title="Process Status", msg_level="info", status=StatusType.SUCCESS)

            # Send a message with status using string
            send_slack(SLACK_WEBHOOK_URL, "The process completed successfully",
                       title="Process Status", msg_level="info", status="success")

            # Send an error message
            send_slack(SLACK_WEBHOOK_URL, "The process failed due to an unexpected error",
                       title="Process Status", msg_level="error", status="failed")

            # Send a warning message
            send_slack(SLACK_WEBHOOK_URL, "The disk space is running low",
                       title="System Warning", msg_level="warning", status="warning")

            # Send a message for an in-progress task
            send_slack(SLACK_WEBHOOK_URL, "The process is currently running",
                       title="Process Status", msg_level="info", status="in_progress")

            # Send a message for task completion
            send_slack(SLACK_WEBHOOK_URL, "The task has been completed",
                       title="Task Status", msg_level="info", status="complete")
    """
    logger = setup_logger(None, "send_slack")

    if not url:
        url = os.getenv('SLACK_WEBHOOK_URL', url)
        if url:
            logger.debug("Using SLACK_WEBHOOK_URL from environment variables.")
        else:
            logger.error("Required SLACK_WEBHOOK_URL")
            if async_mode:
                future = asyncio.Future()
                future.set_result(False)
                return future
            else:
                return False

    payload = create_slack_payload(
        msg_text=msg_text,
        title=title,
        send_user_name=send_user_name,
        msg_level=msg_level,
        status=status,
        simple_mode=simple_mode,
        icon_emoji=icon_emoji,
        footer=footer,
        text=text
    )

    if async_mode:
        return send_slack_async(url, payload, retries)
    else:
        return send_slack_sync(url, payload, retries)


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


def format_slack_message(title: str="", msg_text: str="", msg_level: str="info",
                         status: str="", icon_emoji: str="", footer: str="", text: str="") -> dict:
    p_color = get_level_color(msg_level)
    if isinstance(msg_text, dict):
        fields = []
        for key, value in msg_text.items():
            fields.append({
                "title": key,
                "value": str(value) if value is not None else "N/A",
                "short": True
            })
    else:
        fields = []  # msg_text가 string일 때 fields는 필요 없음
        msg_text = str(msg_text)

    return {
        "attachments": [
            {
                "fallback": title,
                "color": f"#{p_color}",
                "title": title,
                "text": text or msg_text,
                "footer": f"{footer} run and sent from {net.get_hostname()}",
                "ts": int(time.time()),
                "icon_emoji": icon_emoji,
                "fields": fields
            }
        ]
    }

async def send_slack_notification(title: str, msg_text: str, level="info", icon_emoji="", footer="Pawnlib"):
    formatted_message = format_slack_message(
        title=title,
        msg_text=msg_text,
        status=level,
        icon_emoji=icon_emoji or ":rocket:",
        footer=footer
    )
    slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL', "")
    async with aiohttp.ClientSession() as session:
        async with session.post(slack_webhook_url, json=formatted_message) as response:
            if response.status != 200:
                pawn.console.log(f"[red]Failed to send Slack notification: {response.status}[/red]")
