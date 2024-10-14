from pawnlib.output.file import Tail
from pawnlib.utils.notify import send_slack
from datetime import datetime, timedelta
from pawnlib.typing.constants import const
import re

class SSHMonitor:
    def __init__(self, log_file_path, slack_webhook_url, alert_interval=60, allow_duplicates=True):
        self.log_file_path = log_file_path
        self.slack_webhook_url = slack_webhook_url
        self.alert_interval = alert_interval
        self.last_alert_time = {}
        self.allow_duplicates = allow_duplicates
        self.ip_attempts = {}  # Dictionary to track attempts per IP address

    def extract_ip(self, line):
        """Extracts IP address from the log line."""
        match = re.search(const.PATTERN_IP_ADDRESS, line)

        return match.group(0) if match else None

    def increment_attempts(self, ip, status):
        """Increments the failed or success count for a given IP address."""
        if ip not in self.ip_attempts:
            self.ip_attempts[ip] = {"failed": 0, "success": 0}
        self.ip_attempts[ip][status] += 1
        return self.ip_attempts[ip][status]

    def should_alert(self, key):
        """Prevents duplicate alerts within the defined interval unless allow_duplicates is True."""
        if self.allow_duplicates:
            return True
        now = datetime.now()
        if key not in self.last_alert_time or (now - self.last_alert_time[key]).seconds > self.alert_interval:
            self.last_alert_time[key] = now
            return True
        return False

    async def create_alert_message(self, line, status):
        """Creates and sends a Slack alert with emoji in the title."""
        # emoji = "✅" if "Accepted" in line else "🚨"

        ip = self.extract_ip(line)

        attempt_count = self.increment_attempts(ip, status)
        title = f"SSH login {'failed' if 'Failed' in line else 'successful'}"
        # message = f"{line.strip()} (IP: {ip}, Attempt #{attempt_count})"

        message = {"Info": line.strip(), "Source IP": f"{ip} , Attempt #{attempt_count}"}

        # title = f"SSH login {'failed' if 'Failed' in line else 'successful'}"
        # message = f" {line.strip()}"
        return await send_slack(
            url=self.slack_webhook_url,
            msg_text=message,
            # title=f"{emoji} SSH Alert",
            title=title,
            status=status,
            async_mode=True
        )

    async def process_line(self, line):
        """Processes a log line and sends alerts if needed."""
        if "Failed" in line and self.should_alert("failed"):
            await self.create_alert_message(line, status="failed")
        elif "Accepted" in line and self.should_alert("success"):
            await self.create_alert_message(line, status="success")

    async def monitor_ssh(self):
        """Asynchronous SSH log monitoring."""
        async def event_handler(line):
            await self.process_line(line)

        filters = ["Failed", "Accepted"]
        tail = Tail(self.log_file_path, filters, event_handler, async_mode=True)
        await tail.follow_async()
