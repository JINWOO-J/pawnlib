import requests
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import color_print
from pawnlib.resource import net
from pawnlib.typing import date_utils
from pawnlib.utils import http


def get_level_color(c_level):
    default_color = "5be312"
    return dict(
        info="5be312",
        warn="f2c744",
        warning="f2c744",
        error="f70202",
    ).get(c_level, default_color)


# def exception_handler(exception_type, exception, traceback):
#     # import inspect
#     # import traceback as traceback_module
#     # from devtools import debug
#     # debug(traceback_module.extract_stack()[:-3])
#     exception_string = f"[Exception] {exception_type.__name__}: {exception}, {traceback.tb_frame}"
#     cprint(f"{exception_string}", "red")
#     error_logger.error(f"{exception_string}")


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
        msg_title = msg_text
    msg_level = msg_level.lower()

    if url is None:
        color_print.cprint("[ERROR] slack webhook url is None", "red")
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
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": f'Job Title : {msg_title}'
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
                            "text": f'{"+ [DATE]":^12s} : {(date_utils.todaydate("time"))}'
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": f'{"+ [DESC]":^12s} : {msg_text}'
                        }
                    }
                ]
            }
        ]
    }
    try:
        post_result = requests.post(url, json=payload, verify=False, timeout=15)
        if post_result and post_result.status_code == 200 and post_result.text == "ok":
            pawn.app_logger.info(f"[OK][Slack] Send slack")
            return True
        else:
            pawn.error_logger.error(f"[ERROR][Slack] Got errors, status_code={post_result.status_code}, text={post_result.text}")
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

