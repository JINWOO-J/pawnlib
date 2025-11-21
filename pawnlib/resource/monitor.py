from pawnlib.output.file import Tail, is_file
from pawnlib.utils.notify import send_slack
from datetime import datetime
from pawnlib.typing.constants import const
import re
import platform
import subprocess
from typing import List, Union, Optional
from pawnlib.config import setup_logger


class SSHMonitor:
    def __init__(self,
                 log_file_path: Union[str, List[str]],
                 slack_webhook_url: Optional[str] = None,
                 alert_interval: int = 60,
                 allow_duplicates: bool = True,
                 logger=None,
                 verbose: int = 0,
                 os_type: Optional[str] = None
                 ):
        self.log_file_path = log_file_path if isinstance(log_file_path, list) else [log_file_path]
        self.slack_webhook_url = slack_webhook_url
        self.alert_interval = alert_interval
        self.last_alert_time = {}
        self.allow_duplicates = allow_duplicates
        self.logger = setup_logger(logger, "SSHMonitor", verbose)
        self.verbose = verbose
        self.ip_attempts = {}  # Dictionary to track attempts per IP address
        
        # 운영체제 타입 자동 감지 또는 수동 설정
        self.os_type = os_type or self._detect_os_type()
        
        # 운영체제별 로그 패턴 정의
        self._setup_log_patterns()
        
        self.logger.info(f"Starting SSHMonitor with {self.log_file_path}, OS type: {self.os_type}")

    def _detect_os_type(self):
        """운영체제 타입을 자동으로 감지합니다."""
        system = platform.system().lower()
        if system == "linux":
            # /etc/os-release 파일을 확인하여 배포판 구분
            try:
                with open("/etc/os-release", "r") as f:
                    content = f.read().lower()
                    if "ubuntu" in content:
                        return "ubuntu"
                    elif "centos" in content or "rhel" in content:
                        return "centos"
            except FileNotFoundError:
                pass
            
            # systemd 사용 여부로 판단
            try:
                result = subprocess.run(["systemctl", "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return "ubuntu"  # systemd 기반은 Ubuntu로 가정
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
                
        return "centos"  # 기본값

    def _setup_log_patterns(self):
        """운영체제별 로그 패턴을 설정합니다."""
        if self.os_type == "ubuntu":
            self.failed_patterns = [
                "authentication failure",
                "Failed password",
                "Invalid user",
                "Connection closed by authenticating user",
                "Disconnected from authenticating user"
            ]
            self.success_patterns = [
                "Accepted password",
                "Accepted publickey",
                "New session",
                "session opened"
            ]
            self.filters = self.failed_patterns + self.success_patterns + ["systemd-logind"]
        else:  # centos 또는 기타
            self.failed_patterns = [
                "Failed",
                "Invalid",
                "authentication failure"
            ]
            self.success_patterns = [
                "Accepted"
            ]
            self.filters = ["Failed", "Accepted", "Invalid"]

    def extract_ip(self, line):
        """로그 라인에서 IP 주소를 추출합니다."""
        match = re.search(const.PATTERN_IP_ADDRESS_IN_LOG, line)
        return match.group(0) if match else None

    def extract_user(self, line):
        """로그 라인에서 사용자명을 추출합니다."""
        if self.os_type == "ubuntu":
            # Ubuntu systemd-logind 패턴: "New session c56 of user ubuntu"
            user_match = re.search(r"of user (\w+)", line)
            if user_match:
                return user_match.group(1)
        
        # 공통 SSH 로그 패턴들
        patterns = [
            r"for (\w+) from",  # "Failed password for user from IP"
            r"for invalid user (\w+) from",  # "Failed password for invalid user admin from IP"
            r"user=(\w+)",  # "authentication failure ... user=root"
            r"user (\w+)",  # "Accepted password for user ubuntu"
        ]
        
        for pattern in patterns:
            user_match = re.search(pattern, line)
            if user_match:
                return user_match.group(1)
                
        return "unknown"

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

    def _is_failed_login(self, line):
        """로그인 실패 패턴을 확인합니다."""
        return any(pattern in line for pattern in self.failed_patterns)

    def _is_successful_login(self, line):
        """로그인 성공 패턴을 확인합니다."""
        return any(pattern in line for pattern in self.success_patterns)

    async def create_alert_message(self, line, status):
        """Slack 알림 메시지를 생성하고 전송합니다."""
        ip = self.extract_ip(line)
        user = self.extract_user(line)
        
        # IP가 없는 경우 (Ubuntu systemd-logind 로그 등) 사용자 기반으로 추적
        tracking_key = ip if ip else user
        attempt_count = self.increment_attempts(tracking_key, status)
        
        # 운영체제별 제목 생성
        if status == "failed":
            title = f"SSH 로그인 실패 ({self.os_type.upper()})"
        else:
            title = f"SSH 로그인 성공 ({self.os_type.upper()})"
        
        # 메시지 구성
        message_info = {
            "Info": line.strip(),
            "OS Type": self.os_type.upper(),
            "User": user,
            "Attempt Count": f"#{attempt_count}"
        }
        
        if ip:
            message_info["Source IP"] = ip
        
        self.logger.info(f"{title}, {message_info}")

        if self.slack_webhook_url:
            return await send_slack(
                url=self.slack_webhook_url,
                msg_text=message_info,
                send_user_name="SSH Monitor",
                icon_emoji=":alert:",
                title=title,
                status=status,
                async_mode=True
            )

    # async def process_line(self, line):
    #     """Processes a log line and sends alerts if needed."""
    #     if "Failed" in line and self.should_alert("failed"):
    #         await self.create_alert_message(line, status="failed")
    #     elif "Invalid" in line and self.should_alert("failed"):
    #         await self.create_alert_message(line, status="failed")
    #     elif "Accepted" in line and self.should_alert("success"):
    #         await self.create_alert_message(line, status="success")
    async def process_line(self, line):
        """로그 라인을 처리하고 필요시 알림을 전송합니다."""
        if self._is_failed_login(line) and self.should_alert("failed"):
            await self.create_alert_message(line, status="failed")
        elif self._is_successful_login(line) and self.should_alert("success"):
            await self.create_alert_message(line, status="success")

    #
    # async def monitor_file(self, log_file):
    #     """Asynchronous monitoring of a single log file."""
    #     async def event_handler(line):
    #         await self.process_line(line)
    #
    #     filters = ["Failed", "Accepted"]
    #     if not is_file(log_file):
    #         raise ValueError(f"Log file '{log_file}' not found. Please check the file path and ensure the file exists.")
    #     tail = Tail(log_file, filters, event_handler, async_mode=True, logger=self.logger, verbose=self.verbose)
    #     await tail.follow_async()
    #
    # async def monitor_ssh(self):
    #     """Asynchronous SSH log monitoring for multiple files."""
    #     tasks = [self.monitor_file(log_file) for log_file in self.log_file_path]
    #     await asyncio.gather(*tasks)

    async def monitor_ssh(self):
        """비동기 SSH 로그 모니터링을 수행합니다."""
        async def event_handler(line):
            await self.process_line(line)

        # 파일 존재 확인
        for _file in self.log_file_path:
            if not is_file(_file):
                raise ValueError(f"Log file '{_file}' not found. Please check the file path and ensure the file exists.")

        self.logger.info(f"Monitoring {self.os_type.upper()} logs with filters: {self.filters}")
        
        tail = Tail(self.log_file_path, self.filters, event_handler, async_mode=True, logger=self.logger, verbose=self.verbose)
        await tail.follow_async()

