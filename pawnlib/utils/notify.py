import requests


def get_level_color(c_level):
    default_color = "5be312"
    return dict(
        info="5be312",
        warn="f2c744",
        warning="f2c744",
        error="f70202",
    ).get(c_level, default_color)


def slack_wh_send(self, text):
    payload = {"text": text}
    if self.config.get('SLACK_WH_URL'):
        requests.post(self.config['SLACK_WH_URL'], json=payload, verify=False)


# def exception_handler(exception_type, exception, traceback):
#     # import inspect
#     # import traceback as traceback_module
#     # from devtools import debug
#     # debug(traceback_module.extract_stack()[:-3])
#     exception_string = f"[Exception] {exception_type.__name__}: {exception}, {traceback.tb_frame}"
#     cprint(f"{exception_string}", "red")
#     error_logger.error(f"{exception_string}")


def send_slack(url, msg_text, title=None, send_user_name="CtxBot", msg_level='info'):
    if title:
        msg_title = title
    else:
        msg_title = msg_text
    msg_level = msg_level.lower()

    if url is None:
        cprint("[ERROR] slack webhook url is None", "red")
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
                            "text": f'{"+ [HOST]":^12s} : {socket.gethostname()}, {jmon_lib.get_public_ipaddr()}'
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": f'{"+ [DATE]":^12s} : {(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])}'
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
            app_logger.info(f"[OK][Slack] Send slack")
            return True
        else:
            error_logger.error(f"[ERROR][Slack] Got errors, status_code={post_result.status_code}, text={post_result.text}")
            return False

    except Exception as e:
        error_logger.error(f"[ERROR][Slack] Got errors -> {e}")
        return False
