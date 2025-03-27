import asyncio
import sys
from pawnlib.config import setup_logger


async def shutdown_async_tasks(loop=None, tasks=None, logger=None, exit_on_shutdown=True, verbose=1, exit_code=0):
    """
    Shutdown all pending async tasks and close the loop gracefully.

    Args:
        loop (asyncio.AbstractEventLoop): The event loop to use. If None, the current running loop will be used.
        tasks (List[asyncio.Task]): List of tasks to cancel. If None, all pending tasks in the loop will be cancelled.
        logger (logging.Logger): Logger instance for logging. If None, print will be used as fallback.
        exit_on_shutdown (bool): If True, the system will exit after shutdown.
        verbose (int): The verbosity level for logging output.
        exit_code (int): Exit code to return when exiting the system (default is 0).
    """

    logger = setup_logger(logger, "shutdown_async_tasks", verbose)

    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger("No running event loop found.")
            return

    if tasks is None:
        tasks = [task for task in asyncio.all_tasks(loop) if isinstance(task, asyncio.Task)]

    logger.info(f"Initiating graceful shutdown. Found {len(tasks)} pending task(s) to cancel.")

    if tasks:
        for task in tasks:
            if not task.done() and not task.cancelled():
                task_name = task.get_coro().__name__
                logger.info(f"Cancelling task: {task_name}()")
                task.cancel()

        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                task_name = task.get_coro().__name__
                logger.info(f"Task '{task_name}()' cancelled successfully.")
            except Exception as e:
                task_name = task.get_coro().__name__
                logger.error(f"Error during task '{task_name}' cancellation: {e}")

    logger.info("All tasks cancelled and event loop closed gracefully.")

    if exit_on_shutdown:
        logger.info(f"Exiting the system after graceful shutdown with exit code {exit_code}.")
        sys.exit(exit_code)
