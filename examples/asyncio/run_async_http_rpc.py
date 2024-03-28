#!/usr/bin/env python3
import asyncio

import common
from pawnlib.config.globalconfig import pawnlib_config
from pawnlib.utils import *
from pawnlib.output import *
from pawnlib.asyncio import *
from pawnlib.asyncio import run, fetch_httpx_url
import random
from devtools import debug
from pawnlib.typing.generator import generate_json_rpc, Counter
import sys
from typing import Callable

from itertools import chain


# async def task_func(param=None):
def param_test(target=None, param=1, param2=2):
    print(f"param_test = {target}, {param}, {param2}")


async def task_func(target, **kwargs):
    rnd_int = random.randint(1, 3)
    result = f"async task: random sleep {rnd_int} sec"
    # debug_print(f"[task_func()] param={param}, result='{result}'")
    await asyncio.sleep(rnd_int)
    debug_print(f"[task_func()] target={target}, kwargs={kwargs}, result='{result}'")
    pawnlib_config.append_list(result=result)
    increase_count = pawnlib_config.increase(global_count=1.1)
    decrease_count = pawnlib_config.decrease(global_count=0.1)
    debug_print(f"increase_count={increase_count}, decrease_count={decrease_count}")
    return result


class IterJsonRpc:

    def __init__(self, method="", generator_key="", convert_func: Callable = int, start=1, stop=10, step=1):
        self.method = method
        self.generator_key = generator_key
        self.convert_func = convert_func
        self.start = start
        self.stop = stop
        self.step = step
        self._counter = Counter(start=self.start, stop=self.stop, convert_func=self.convert_func)
        # self.make_rpc()

    def _make_rpc(self, counter=0):
        if counter:
            _counter = counter
        else:
            _counter = self._counter
        import json
        res = generate_json_rpc(
            method=self.method,
            params={self.generator_key: next(_counter)}
        )
        return res

    def __iter__(self):
        return self

    def __next__(self):
        return self._make_rpc()

    # def __next__(self):
    #     if self.start < self.stop:
    #         r = self.start
    #         self.start += self.step
    #         result = self._make_rpc()
    #         return result
    #     else:
    #         raise StopIteration


class GetBlock:

    def __init__(self,
                 start=1,
                 stop=23,
                 url="",
                 max_at_once=10,
                 max_per_second=10,
                 max_request_size=10,
                 max_keepalive_connections=100,
                 max_connections=100
                 ):
        self.start = start
        self.stop = stop
        self.url = url

        self.max_at_once = max_at_once
        self.max_per_second = max_per_second

        self.max_request_size = max_request_size
        self.max_keepalive_connections = max_keepalive_connections
        self.max_connections = max_connections
        self.now_count = 0
        limits = httpx.Limits(max_keepalive_connections=max_keepalive_connections, max_connections=max_connections)
        self.httpx_client = httpx.AsyncClient(timeout=5, limits=limits)

        self._status = None
        self.progress = None
        self._task = None
        self._index = 0

    def _call_httpx(self, requests):
        async_http = run.AsyncHttp(debug=False, status=True, urls=requests, max_at_once=10, max_per_second=10)
        pawn.console.log(f"[red] tasks={async_http.get_tasks()}, {requests}")
        res = async_http.run()
        # yield requests
        # yield async_http
        pawn.console.log(f"{res}")
        # yield res

    async def async_run(self):
        results = await asyncio.gather(
            *[self.generate_rpc()], return_exceptions=True)
        pawn.console.log(results)

    async def request_httpx(self, data):
        json_rpc = generate_json_rpc(method="icx_getBlockByHeight", params={"height": hex(data)})
        request = httpx.Request("POST", self.url, data=json_rpc)
        res = await self.httpx_client.send(request)
        self._index += 1
        if res.status_code == 200:
            _result_height = res.json()['result']['height']
            _result_hash = res.json()['result']['block_hash']
            # pawn.console.log(f"height: {data} ({hex(data)}) _result={_result_height}, {_result_hash}")
            return f"[{self._index}] height: {data} ({hex(data)}) _result={_result_height}, {_result_hash}"
        else:
            pawn.console.log(f"[red]height: {data} ({hex(data)}), {res}")
            return f"[{self._index}] height: {data} ({hex(data)}), {res}"

    async def generate_rpc(self):

        json_rpc_payloads = IterJsonRpc(method="icx_getBlockByHeight", generator_key="height", convert_func=hex, start=self.start, stop=self.stop)
        payload_list = []
        for json_rpc in json_rpc_payloads:

            payload_list.append(
                {
                    "url": self.url,
                    # "url": "https://httpbin.org/post",

                    "kwargs": {
                        "data": json_rpc,
                        "method": "post",
                    }
                }
            )
            # pawn.console.log(f"{self.url} / {json_rpc}")
            request = httpx.Request("POST", self.url, data=json_rpc)
            res = await self.httpx_client.send(request)
            pawn.console.log(res)

            # res = await fetch_httpx_url(
            #
            # )
            # pawn.console.log(res.text)
            # if self.now_count % self.max_request_size == 0:
            #     pawn.console.log(f"{self.now_count}")
            #     # self._call_httpx(payload_list)
            #
            #     res = await fetch_httpx_url(self.url, data=json_rpc, method="post" )
            #     pawn.console.log(res.text)
            print(self.now_count)
            self.now_count += 1

        return self.now_count

    def run(self):

        with ProgressTime() as self.progress:
            self._task = self.progress.add_task("[red]Downloading...", total=self.stop-self.start)
            while not self.progress.finished:
                # progress.advance(task1)
                result = asyncio.run(self._runner())


        # with pawn.console.status("Start Calling") as self._status:
        #     result = asyncio.run(self._runner())
        # asyncio.run(self.async_run())

    async def _runner(self, status=None):
        async with aiometer.amap(
                async_fn=self.request_httpx,
                args=range(self.start, self.stop),
                max_at_once=self.max_at_once,
                max_per_second=self.max_per_second,
                _include_index=True,
        ) as amap_results:

            async for _index, _result in amap_results:
                # print(_result)
                # self._status.update(_result)
                #
                self.progress.update(self._task, advance=1, description=_result)
            pawn.console.print("END")


def main():
    GetBlock(
        url="http://20.20.1.242:9800/api/v3",
        stop=100,
        max_connections=300,
        max_at_once=200,
        max_per_second=200,
        max_keepalive_connections=300
    ).run()

    exit()

    max_json_count = 10
    json_rpc_batch = IterJsonRpc(method="icx_getBlockByHeight", generator_key="height", convert_func=hex, start=1, stop=20)

    sys.getsizeof(json_rpc_batch)
    pawn.console.log(sys.getsizeof(json_rpc_batch))

    # json_rpc_list = [json_rpc for json_rpc in json_rpc_batch]
    # pawn.console.log(json_rpc_list)
    request_urls = []
    for json_rpc in json_rpc_batch:
        request_urls.append(
            {
                "url": "http://20.20.1.242:9000/api/v3",
                # "url": "https://httpbin.org/post",

                "kwargs": {
                    "data": json_rpc,
                    "method": "post",
                }
            }
        )

    pawn.console.log(request_urls)
    async_http = run.AsyncHttp(debug=False, status=True, urls=request_urls, max_at_once=10, max_per_second=10)
    pawn.console.log(f"[red] tasks={async_http.get_tasks()}")
    res = async_http.run()
    print(res)


    exit()
    # dump(get_file_path(filename="sdsd"), debug=False)

    async_tasks = AsyncTasks(
        max_at_once=50,
        max_per_second=50,
        debug=True,
        status=True,
    )

    # pawnlib_config.set(result=[])

    target_list = [f"target_{i}" for i in range(1, 10)]
    dump(async_tasks.__dict__)

    async_tasks.generate_tasks(
        target_list=target_list,
        function=task_func,
        kwargs={"param": "sssd"}
        # **{"param": "sssd"}
    )
    async_tasks_result = async_tasks.run()
    debug(async_tasks_result)

    print("Global variable")
    debug(pawnlib_config.get("result"))
    debug(pawnlib_config.get("global_count"))


if __name__ == "__main__":
    main()
