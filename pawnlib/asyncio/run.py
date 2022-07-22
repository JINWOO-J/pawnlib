from functools import wraps, partial
import asyncio
import aiometer
from pawnlib.output import *


class AsyncTasks:
    def __init__(self, max_at_once=10, max_per_second=10, debug=False, **kwargs):
        self.tasks = []
        self.max_at_once = max_at_once
        self.max_per_second = max_per_second
        self.debug = debug
        self._debug_print(self)

        self.get_list_function = None

        self.async_partial_target_func = None
        self.async_partial_task_func = None

    def generate_tasks(self, target_list=None, function=None, **kwargs):

        self._debug_print(f"{target_list}, {type(target_list)}")
        if kwargs.get('kwargs'):
            kwargs = kwargs['kwargs']

        if target_list is None:
            target_list = []

        for target in target_list:
            self._debug_print(f"target={target}, function={function}, kwargs={kwargs}")
            self.tasks.append(partial(function, target, **kwargs))

    def run(self):
        return asyncio.run(self._runner())

    async def _runner(self):
        result = []
        if len(self.tasks) > 0:
            result = await aiometer.run_all(self.tasks, max_at_once=self.max_at_once, max_per_second=self.max_per_second)
        else:
            print("ERROR: tasks is null")
        return result

    def _debug_print(self, *args, **kwargs):
        if self.debug:
            debug_print(*args, **kwargs)


# def async_partial(f, *args, **kwargs):
#     print(f"1. {f}, {args}, {kwargs}")
#     async def f2(*args2):
#         print(f"2. {args}, {args2}")
#
#         if asyncio.iscoroutinefunction(f):
#             result = await f(*args, *args2)
#             print(f"2. {args}, {args2} result={result}")
#         return result
#
#     return f2


def async_partial(async_fn, *args, **kwargs):
    async def wrapped():
        result = None
        if asyncio.iscoroutinefunction(async_fn):
            result = await async_fn(*args, **kwargs)
        else:
            debug_print(f"{async_fn} is not coroutine", "red")
        return result
    return wrapped


def run_in_async_loop(f):
    @wraps(f)
    async def wrapped(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, f(*args, **kwargs))
    return wrapped
