# Ubuntu SSH 모니터링 지원

Pawnlib의 SSH 모니터링 기능이 Ubuntu 시스템을 지원하도록 개선되었습니다.

## 주요 개선사항

### 1. 운영체제 자동 감지
- CentOS/RHEL과 Ubuntu를 자동으로 감지
- `/etc/os-release` 파일과 systemd 존재 여부로 판단
- 수동 설정도 가능

### 2. Ubuntu 전용 로그 패턴 지원
- **systemd-logind 로그**: `New session c56 of user ubuntu`
- **SSH 인증 실패**: `authentication failure`, `Failed password`, `Invalid user`
- **SSH 인증 성공**: `Accepted password`, `Accepted publickey`, `New session`

### 3. 향상된 사용자명 추출
- Ubuntu systemd-logind: `of user username` 패턴
- SSH 로그: `for username from`, `for invalid user username from`
- PAM 로그: `user=username` 패턴

## 사용 방법

### CLI 사용
```bash
# 자동 감지 (기본값)
pawns mon ssh -f /var/log/auth.log

# Ubuntu로 명시적 설정
pawns mon ssh -f /var/log/auth.log --os-type ubuntu

# CentOS로 명시적 설정  
pawns mon ssh -f /var/log/secure --os-type centos
```

### 프로그래밍 방식 사용
```python
from pawnlib.resource.monitor import SSHMonitor

# 자동 감지
monitor = SSHMonitor("/var/log/auth.log")

# Ubuntu로 명시적 설정
monitor = SSHMonitor("/var/log/auth.log", os_type="ubuntu")

# 비동기 모니터링 시작
await monitor.monitor_ssh()
```

### 환경변수 설정
```bash
# Docker 환경에서 OS 타입 설정
export OS_TYPE=ubuntu
pawns mon ssh --priority env
```

## 지원하는 로그 패턴

### Ubuntu 패턴
- **실패**: `authentication failure`, `Failed password`, `Invalid user`
- **성공**: `Accepted password`, `Accepted publickey`, `New session`, `session opened`
- **필터**: systemd-logind 로그도 포함

### CentOS 패턴 (기존)
- **실패**: `Failed`, `Invalid`, `authentication failure`
- **성공**: `Accepted`

## 테스트 예제

제공된 테스트 파일을 실행하여 기능을 확인할 수 있습니다:

```bash
PYTHONPATH=. python examples/ssh_monitor_ubuntu_test.py
```

## 로그 샘플

### Ubuntu systemd-logind 로그
```
2025-10-24T17:18:56.842381+00:00 server systemd-logind[695]: New session c56 of user ubuntu.
2025-10-24T17:18:56.855864+00:00 server systemd-logind[695]: Session c56 logged out.
```

### Ubuntu SSH 로그
```
Oct 24 17:20:01 server sshd[12345]: Failed password for invalid user admin from 192.168.1.100
Oct 24 17:20:05 server sshd[12346]: Accepted password for ubuntu from 192.168.1.101
Oct 24 17:20:10 server sshd[12347]: authentication failure; user=root rhost=192.168.1.102
```

이제 Ubuntu와 CentOS 모두에서 안정적인 SSH 로그 모니터링이 가능합니다!