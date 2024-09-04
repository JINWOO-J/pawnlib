#!/usr/bin/env python3
import common
import os
from pawnlib.utils.notify import TelegramBot

# bot_token을 명시적으로 제공하지 않으면 환경변수에서 가져옴
bot = TelegramBot()

# 기본 Markdown 메시지 전송
bot.send_message("1. Hello, *World*! This is a Telegram message with _Markdown_ formatting.")

# HTML 포맷 메시지 전송
bot.send_html_message("2. Hello, <b>World</b>! This is a Telegram message with <i>HTML</i> formatting.")

# Plain text 메시지 전송
bot.send_plain_text_message("3. Hello, World! This is a plain text message.")

# chat_id 저장
bot.save_chat_id()

# 나중에 chat_id를 파일에서 로드
bot.load_chat_id()

bot.send_auto_message("[HTML] Hello, <b>World</b>! This is a Telegram message with <i>HTML</i> formatting.")
bot.send_auto_message({"DICT key": "value", "foo": "bar"})
bot.send_auto_message("Plain Hello, World! This is a plain text message.")

