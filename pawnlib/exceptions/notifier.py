import traceback
from pawnlib.utils.notify import send_slack
from pawnlib.config import setup_logger


class ExceptionNotifier:
    def __init__(self, logger=None, slack_status="failed", slack_msg_level="error", slack_icon=":alert:", slack_url=None):
        """
        Initializes the ExceptionNotifier with logging and Slack notification settings.

        :param logger: Logger instance to log the error.
        :param slack_status: Status type for Slack notification (default: 'error').
        :param slack_msg_level: Message level for Slack (default: 'error').
        :param slack_icon: Emoji icon for Slack message (default: ':alert:').
        :param slack_url: The Slack webhook URL. If None, it will use the environment variable.
        """
        self.logger = setup_logger(logger, "ExceptionNotifier", 1)
        self.slack_status = slack_status
        self.slack_msg_level = slack_msg_level
        self.slack_icon = slack_icon
        self.slack_url = slack_url

    def notify(self, e, additional_message=None):
        """
        Logs the exception and sends a notification to Slack with detailed traceback.

        :param e: Exception object.
        :param additional_message: Additional message to send along with the exception details (optional).
        """
        # Log the error with the logger
        self.logger.error(f"Unexpected error: {e}")

        # Capture the full traceback as a string
        tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))

        # Combine additional message with traceback if provided
        title = f"An error occurred: {str(e)}"
        slack_message = f"An error occurred: {str(e)}\n\nTraceback:\n{tb_str}"
        if additional_message:
            slack_message = f"{additional_message}\n\n{slack_message}"

        # Send Slack notification with detailed traceback
        send_slack(
            url=self.slack_url,
            title=title,
            msg_text=slack_message,
            status=self.slack_status,
            msg_level=self.slack_msg_level,
            icon_emoji=self.slack_icon
        )


def notify_exception(e, logger=None, additional_message=None, slack_status="failed", slack_msg_level="error", slack_icon=":alert:", slack_url=None):
    """
    A helper function to quickly notify an exception using the ExceptionNotifier.

    :param e: Exception object.
    :param logger: Logger instance (optional).
    :param additional_message: Additional message to send along with the exception details (optional).
    :param slack_status: Status type for Slack notification (default: 'error').
    :param slack_msg_level: Message level for Slack (default: 'error').
    :param slack_icon: Emoji icon for Slack message (default: ':alert:').
    :param slack_url: Slack webhook URL. If None, it will use the environment variable (optional).
    """
    notifier = ExceptionNotifier(
        logger=logger,
        slack_status=slack_status,
        slack_msg_level=slack_msg_level,
        slack_icon=slack_icon,
        slack_url=slack_url
    )
    notifier.notify(e, additional_message)
