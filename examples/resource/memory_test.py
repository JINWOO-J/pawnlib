#!/usr/bin/env python3
from datetime import time

import common
from pawnlib.resource import net
from pawnlib.config import pawn
import psutil
import time

def increase_memory(size_in_gb):
    # 지정된 크기(GB)의 메모리를 증가시키기 위해 리스트를 사용
    arr = []
    for _ in range(size_in_gb * 1024):  # 각 배열이 약 1MB 크기
        arr.append(bytearray(1024 * 1024))  # 1MB의 바이트 배열 생성
    return arr

def check_memory_usage():
    # 현재 시스템의 메모리 사용량을 출력합니다.
    mem = psutil.virtual_memory()
    print(f"Total: {mem.total / (1024 ** 3):.2f} GB")
    print(f"Available: {mem.available / (1024 ** 3):.2f} GB")
    print(f"Used: {mem.used / (1024 ** 3):.2f} GB")
    print(f"Percent: {mem.percent}%")

if __name__ == "__main__":
    print("메모리 사용량 증가 전:")
    check_memory_usage()

    # 메모리 증가
    arr = increase_memory(2)  # 2GB 메모리 증가

    # 잠시 대기하여 OS가 메모리를 업데이트할 시간을 줍니다.
    time.sleep(5)

    print("\n메모리 사용량 증가 후:")
    check_memory_usage()
