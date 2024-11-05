#!/usr/bin/env python3
import common
import os
from pawnlib.utils.notify import send_slack
from pawnlib.config.globalconfig import pawn, pconf, set_debug_logger
from pawnlib.typing.constants import StatusType
import asyncio

SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', None)

if not SLACK_WEBHOOK_URL:
    pawn.console.log("[red] Requires SLACK_WH_URL environment variable")
    exit()


pawn.set(
    PAWN_LOGGER=dict(
        stdout=True,
    ),
)

pawn.console.log(pconf())

msg_text = {
    "message1": "messagesdsds",
    "message2": "messagesdsds",
    "message3": None,
    "message4": "",
    "message5": 0,
    "message6": False,
}

res = send_slack(
    url=SLACK_WEBHOOK_URL,
    msg_text=msg_text,
    title="Slack test",
    icon_emoji=":webhook:",
    # icon_emoji=":robot_face:",
)

async def send_async_slack_message():
    message = "This is an async test message!"
    # Use the send_slack function with async_mode=True
    result = await send_slack(
        url=SLACK_WEBHOOK_URL,
        msg_text=message,
        title="Async Slack Notification",
        send_user_name="AsyncBot",
        msg_level="info",
        retries=3,
        async_mode=True
    )
    if result:
        print("send_async_slack_message() Message sent successfully!")
    else:
        print("send_async_slack_message() Failed to send message.")

# Run the async function
asyncio.run(send_async_slack_message())

send_slack(SLACK_WEBHOOK_URL, "The process completed successfully", title="Process Status", msg_level="info", status="success")
send_slack(SLACK_WEBHOOK_URL, msg_text, title="Process Status", msg_level="info", status="success")
send_slack(SLACK_WEBHOOK_URL, "The process completed successfully", title="Process Status", msg_level="info", status=StatusType.SUCCESS)
send_slack(SLACK_WEBHOOK_URL, "The process failed due to an unexpected error", title="Process Status", msg_level="error", status="failed")
send_slack(SLACK_WEBHOOK_URL, "The disk space is running low", title="System Warning", msg_level="warning", status="warning")
send_slack(SLACK_WEBHOOK_URL, "The process is currently running", title="Process Status", msg_level="info", status="in_progress")
send_slack(SLACK_WEBHOOK_URL, "The task has been completed", title="Task Status", msg_level="info", status="complete")

send_slack(SLACK_WEBHOOK_URL, "The process completed successfully", title="Process Status", msg_level="info", status=StatusType.SUCCESS)


send_slack(SLACK_WEBHOOK_URL, "Task completed successfully", title="Task Status", msg_level="info", status=StatusType.SUCCESS, simple_mode=True)


# 잘못된 Slack Webhook URL로 설정
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/INVALID_URL"

# send_slack 호출
send_slack(SLACK_WEBHOOK_URL, "This is a test message for retry logic.", title="Test Retry", msg_level="info", retries=3, status="info")



