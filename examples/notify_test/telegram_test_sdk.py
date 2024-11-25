#!/usr/bin/env python3
from telegram import Bot
from telegram.parsemode import ParseMode
import os

# 봇 토큰과 채팅 ID (텔레그램에서 발급받은 토큰과 대화 상대방의 chat_id)
TOKEN =os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 텔레그램 봇 인스턴스 생성
bot = Bot(token=TOKEN)

# MarkdownV2 형식의 메시지
message = """
[Click here](https://www.example.com)
*This is bold text*
_This is italic text_
`This is inline code`

[Click here](https://www.example.com)

\- Item 1
\- Item 2

Special characters must be escaped: \* \_ $begin:math:display$ $end:math:display$ $begin:math:text$ $end:math:text$ \~ \` \> \# \+ \- \= \| \{ \} \. \!

"""

# 메시지 보내기
bot.send_message(
    chat_id=CHAT_ID,
    text=message,
    parse_mode=ParseMode.MARKDOWN_V2
)
