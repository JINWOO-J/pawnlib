#!/usr/bin/env python3
# requirements: scapy (`pip install scapy`) — root 권한으로 실행하세요.
from scapy.all import sniff, TCP, IP, Raw
import datetime
import re
import argparse

METHODS = ("GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS")

def parse_http_request(payload: bytes):
    """
    HTTP 요청 페이로드에서
      method, uri, headers(dict)
    를 리턴합니다. 요청이 아니면 None.
    """
    try:
        text = payload.decode('utf-8', errors='replace')
    except (UnicodeDecodeError, AttributeError) as e:
        # 로깅 추가로 디버깅 개선
        print(f"패킷 디코딩 실패: {e}")
        return None

    lines = text.split("\r\n")
    # 1) 요청 라인 매칭
    m = re.match(rf'^({"|".join(METHODS)}) (.*?) HTTP/1\.[01]$', lines[0])
    if not m:
        return None

    method, uri = m.group(1), m.group(2)
    hdrs = {}
    for line in lines[1:]:
        if line == "":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            hdrs[k.strip()] = v.strip()
    return method, uri, hdrs

def on_packet(pkt):
    # 1) TCP, Raw, dst port 80 (request only)
    if not (pkt.haslayer(TCP) and pkt.haslayer(Raw)):
        return
    tcp = pkt[TCP]
    if tcp.dport != 80:
        return

    parsed = parse_http_request(pkt[Raw].load)
    if not parsed:
        return
    method, uri, hdrs = parsed

    # 2) ELB-HealthChecker UA 제외
    ua = hdrs.get("User-Agent", "")
    if "ELB-HealthChecker/2.0" in ua:
        return

    # 3) 필요한 필드 출력
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    src_ip = pkt[IP].src
    direction = ">"
    host = hdrs.get("Host", "")

    # TAB 구분으로 timestamp, source-ip, direction, method, host, uri, user-agent
    print(f"{ts}\t{src_ip}\t{direction}\t{method}\t{host}\t{uri}\t{ua}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live HTTP request sniffer (Scapy)")
    parser.add_argument("-i","--iface", default="any", help="Interface to sniff (default: any)")
    parser.add_argument("-p","--port", type=int, default=80, help="TCP port (default: 80)")
    args = parser.parse_args()

    # BPF 필터로 tcp port 지정
    bpf = f"tcp port {args.port}"
    print(f"** Sniffing HTTP requests on {args.iface}, port {args.port} (ctrl-C to stop) **")
    sniff(iface=args.iface, filter=bpf, prn=on_packet, store=False)
