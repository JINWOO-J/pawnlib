#!/usr/bin/env python3
import time
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import AsyncIconRpcHelper
import asyncio

async def worker(rpc, task_id):
    async with rpc.semaphore:
        start = time.time()
        await rpc.get_last_blockheight()
        elapsed = time.time() - start
        pawn.console.log(f"Task {task_id} completed in {elapsed:.2f}s | {rpc.concurrency_usage}")


async def main():
    async with AsyncIconRpcHelper(url="https://lisbon.net.solidwallet.io", max_concurrency=2) as rpc:
        tasks = [asyncio.create_task(worker(rpc, i)) for i in range(5)]
        await asyncio.sleep(1)

        # 동시성 4로 상향 조정
        pawn.console.rule("\n=== Adjust concurrency to 4 ===")
        await rpc.adjust_concurrency(4)
        pawn.console.log(f"Current concurrency: {rpc.concurrency_usage}")

        # 추가 5개 작업 실행
        tasks += [asyncio.create_task(worker(rpc, i+5)) for i in range(5)]
        await asyncio.gather(*tasks)

        # 최종 상태 출력
        pawn.console.rule("\n=== Final status ===")
        pawn.console.log(f"Active connections: {rpc.connector._conns}")
        pawn.console.log(f"Semaphore state: {rpc.concurrency_usage}")

if __name__ == "__main__":
    asyncio.run(main())
