#!/usr/bin/env python3
import common
import os
import asyncio
from pawnlib.utils.notify import TelegramBot
from pawnlib.typing.converter import escape_markdown, escape_non_markdown
from pawnlib.typing import const
from telegram.parsemode import ParseMode

message_list = (
    "[HTML] Hello, <b>World</b>! This is a Telegram message with <i>HTML</i> formatting.",
    {"DICT key": "value", "foo": "bar"},
    "Plain Hello, World! This is a plain text message.",
    # "🔥[Main] JJJJJ([hx0b0](https://aaa.com)) *fail:* `175612` → `175624`"
)

markdown_message = """
*This is bold text*
_This is italic text_
`This is inline code`


- Item 1
- Item 2
🔥[Main] JJJJJ([hx0b0](https://aaa.com)) *fail:* `175612` → `175624`

 

"""
special_characters = "Special characters must be escaped: * _ [ ] ( $end:math:text$ ~ ` > #+-=| { }. !"

async def send_telegram_special_char():
    a_bot = TelegramBot(verify_ssl=False, ignore_ssl_warning=True, async_mode=True)
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    tasks = []
    for idx, escape_char in enumerate(escape_chars):
        print(f"[{idx}] Preparing to send: {escape_char}")
        tasks.append(a_bot.send_auto_message_async(f"[{idx}] {escape_char}"))  # 비동기 작업 추가
    await asyncio.gather(*tasks)


async_bot = TelegramBot(verify_ssl=False, ignore_ssl_warning=True, async_mode=True)
async_bot.send_multiple_messages(message_list)

bot = TelegramBot(verify_ssl=False, ignore_ssl_warning=True, async_mode=False)
# 기본 Markdown 메시지 전송
# bot.send_auto_message("1. Hello, *World*! This is a Telegram message with _Markdown_ formatting.")
bot.send_message_sync(
    # message="1. Hello, *World*! This is a Telegram message with _Markdown_ formatting.",
    message=markdown_message,
    parse_mode="Markdown",
    # parse_mode=ParseMode.MARKDOWN_V2,
    # pass_escape=False
)

bot.send_message_sync(markdown_message, parse_mode="Markdown", pass_escape=True)
bot.send_auto_message(markdown_message)

# HTML 포맷 메시지 전송
bot.send_html_message("2. Hello, <b>World</b>! This is a Telegram message with <i>HTML</i> formatting.")

# Plain text 메시지 전송
bot.send_plain_text_message("3. Hello, World! This is a plain text message.")

# chat_id 저장
bot.save_chat_id()

# 나중에 chat_id를 파일에서 로드
bot.load_chat_id()

for message in message_list:
    bot.send_auto_message(f"[SYNC] {message}")

async_bot = TelegramBot(verify_ssl=False, ignore_ssl_warning=True, async_mode=True)
async_bot.send_multiple_messages(message_list)

# asyncio.run(send_telegram_special_char())
