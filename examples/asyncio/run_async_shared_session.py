#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config
import asyncio
import aiohttp
import logging
from pawnlib.config import LoggerMixinVerbose, create_app_logger
from pawnlib.utils.http import AsyncIconRpcHelper

# 로깅 설정
# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger("AsyncIconRpcHelperTestTTT")
# logger.info("start")
logger = create_app_logger(verbose=3)


class AsyncIconRpcHelperTest(LoggerMixinVerbose):
    def __init__(self, url="http://20.20.1.20:9000", max_concurrent=1, timeout=5):
        self.init_logger(logger=logger, verbose=2)
        self.url = url
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.loop = asyncio.get_event_loop()
        self.session = None
        self.logger.info(f"Test initialized with max_concurrent={max_concurrent}, {self.logger}")

    async def initialize_session(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=self.max_concurrent),
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                loop=self.loop
            )
            self.logger.debug(f"[TEST SESSION INIT] Created session with loop: {self.loop}")

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.debug("[TEST SESSION CLOSED] Session closed")

    async def test_single_request(self):
        await self.initialize_session()
        try:
            async with AsyncIconRpcHelper(
                    url=self.url,
                    logger=self.logger,
                    session=self.session,
                    timeout=self.timeout,
                    retries=1,
                    max_concurrency=self.max_concurrent,
                    loop=self.loop
            ) as rpc_helper:
                self.logger.debug(f"[TEST] Starting single request with loop: {rpc_helper.loop}")
                response = await rpc_helper.fetch("/admin/chain", return_first=True)
                self.logger.info(f"[TEST SINGLE RESPONSE] {response}")
        finally:
            await self.close_session()

    async def test_multiple_requests(self, num_requests=5):
        await self.initialize_session()
        try:
            async with AsyncIconRpcHelper(
                    url=self.url,
                    logger=self.logger,
                    session=self.session,
                    timeout=self.timeout,
                    retries=1,
                    max_concurrency=self.max_concurrent,
                    loop=self.loop,
            ) as rpc_helper:
                self.logger.debug(f"[TEST] Starting {num_requests} concurrent requests with loop: {rpc_helper.loop}")
                tasks = [rpc_helper.fetch("/admin/chain", return_first=True) for _ in range(num_requests)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    self.logger.info(f"[TEST MULTI RESPONSE {i}] {result}")
        finally:
            await self.close_session()

async def run_tests():
    # 테스트 1: max_concurrent=1로 단일 요청
    tester = AsyncIconRpcHelperTest(max_concurrent=1)
    await tester.test_single_request()

    # 테스트 2: max_concurrent=5로 다중 요청
    tester = AsyncIconRpcHelperTest(max_concurrent=5)
    await tester.test_multiple_requests(num_requests=5)

if __name__ == "__main__":
    asyncio.run(run_tests())
