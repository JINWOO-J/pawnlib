#!/usr/bin/env python3
"""
Ubuntu SSH 모니터링 테스트 예제

이 예제는 Ubuntu 시스템에서 SSH 로그 모니터링을 테스트합니다.
"""

import asyncio
import tempfile
import os
from pawnlib.resource.monitor import SSHMonitor

async def test_ubuntu_ssh_monitor():
    """Ubuntu SSH 모니터 테스트"""
    
    # 테스트용 임시 로그 파일 생성
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        test_log_file = f.name
        
        # Ubuntu systemd-logind 로그 샘플 작성
        sample_logs = [
            "2025-10-24T17:18:56.714834+00:00 aws-kr-v1-backend01 systemd-logind[695]: Removed session c55.",
            "2025-10-24T17:18:56.842381+00:00 aws-kr-v1-backend01 systemd-logind[695]: New session c56 of user ubuntu.",
            "2025-10-24T17:18:56.855864+00:00 aws-kr-v1-backend01 systemd-logind[695]: Session c56 logged out. Waiting for processes to exit.",
            "2025-10-24T17:18:56.861857+00:00 aws-kr-v1-backend01 systemd-logind[695]: Removed session c56.",
            "Oct 24 17:20:01 server sshd[12345]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2",
            "Oct 24 17:20:05 server sshd[12346]: Accepted password for ubuntu from 192.168.1.101 port 22 ssh2",
            "Oct 24 17:20:10 server sshd[12347]: authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=192.168.1.102 user=root"
        ]
        
        for log in sample_logs:
            f.write(log + '\n')
    
    try:
        print("Ubuntu SSH 모니터 테스트 시작...")
        
        # Ubuntu 모니터 생성 (os_type을 명시적으로 ubuntu로 설정)
        monitor = SSHMonitor(
            log_file_path=test_log_file,
            slack_webhook_url=None,  # 테스트이므로 Slack 비활성화
            alert_interval=1,
            allow_duplicates=True,
            verbose=1,
            os_type="ubuntu"
        )
        
        print(f"감지된 OS 타입: {monitor.os_type}")
        print(f"실패 패턴: {monitor.failed_patterns}")
        print(f"성공 패턴: {monitor.success_patterns}")
        print(f"필터: {monitor.filters}")
        
        # 각 로그 라인을 수동으로 처리하여 테스트
        with open(test_log_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    print(f"\n--- 로그 라인 {line_num} 처리 ---")
                    print(f"로그: {line}")
                    
                    # IP 및 사용자 추출 테스트
                    ip = monitor.extract_ip(line)
                    user = monitor.extract_user(line)
                    print(f"추출된 IP: {ip}")
                    print(f"추출된 사용자: {user}")
                    
                    # 패턴 매칭 테스트
                    is_failed = monitor._is_failed_login(line)
                    is_success = monitor._is_successful_login(line)
                    print(f"실패 패턴 매칭: {is_failed}")
                    print(f"성공 패턴 매칭: {is_success}")
                    
                    # 실제 처리
                    if is_failed or is_success:
                        await monitor.process_line(line)
        
        print("\n=== 테스트 완료 ===")
        print(f"IP별 시도 횟수: {monitor.ip_attempts}")
        
    finally:
        # 임시 파일 정리
        os.unlink(test_log_file)

def test_os_detection():
    """운영체제 감지 테스트"""
    print("=== 운영체제 감지 테스트 ===")
    
    # 자동 감지 테스트
    monitor_auto = SSHMonitor("/tmp/test.log")
    print(f"자동 감지된 OS: {monitor_auto.os_type}")
    
    # 수동 설정 테스트
    monitor_ubuntu = SSHMonitor("/tmp/test.log", os_type="ubuntu")
    print(f"Ubuntu 설정: {monitor_ubuntu.os_type}")
    
    monitor_centos = SSHMonitor("/tmp/test.log", os_type="centos")
    print(f"CentOS 설정: {monitor_centos.os_type}")

if __name__ == "__main__":
    print("SSH Monitor Ubuntu 지원 테스트")
    print("=" * 50)
    
    # OS 감지 테스트
    test_os_detection()
    
    print("\n" + "=" * 50)
    
    # Ubuntu 모니터링 테스트
    asyncio.run(test_ubuntu_ssh_monitor())