import requests
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import color_print
from pawnlib.resource import net
from pawnlib.typing import date_utils, shorten_text
from pawnlib.utils import http


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

