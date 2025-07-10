#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config
from pawnlib.utils import *
from pawnlib.output import *
from pawnlib.asyncio import *
import random
from devtools import debug
import sys


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


def main():
    dump(get_file_path(filename="sdsd"), debug=False)

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
