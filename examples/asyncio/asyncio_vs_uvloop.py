import asyncio
import time
import uvloop

async def dummy_task(delay):
    await asyncio.sleep(delay)

async def run_tasks(loop, num_tasks=1000):
    tasks = [dummy_task(0.001) for _ in range(num_tasks)]
    start_time = time.time()
    await asyncio.gather(*tasks)
    end_time = time.time()
    print(f"Tasks completed in {end_time - start_time:.4f} seconds using {loop}.")

def compare_loops(num_tasks=1000):
    # asyncio 기본 이벤트 루프 사용
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    asyncio.run(run_tasks('asyncio', num_tasks))

    # uvloop 사용
    uvloop.install()
    asyncio.run(run_tasks('uvloop', num_tasks))

if __name__ == "__main__":
    compare_loops(100000)
