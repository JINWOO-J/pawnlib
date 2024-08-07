#!/usr/bin/env python3
import common
import os
from pawnlib.utils.notify import send_slack
from pawnlib.config.globalconfig import pawn, pconf, set_debug_logger

send_wh_url = os.getenv('SLACK_WH_URL', None)

if not send_wh_url:
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
    url=send_wh_url,
    msg_text=msg_text,
    title="Slack test"
)


# send_slack(
#     url=send_wh_url,
#     msg_text="plain text",
#     title="Slack test"
# )
#
#
#
