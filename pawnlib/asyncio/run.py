from functools import wraps, partial
import asyncio
import aiometer
from aiometer._impl import utils
from pawnlib.output import debug_print, classdump
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import ALLOWS_HTTP_METHOD
import httpx


class AsyncTasks:
    def __init__(self,
                 max_at_once: int = 10,
                 max_per_second: int = 10,
                 title: str = "Working on async tasks ...",
                 debug: bool = False,
                 status: bool = False,
                 **kwargs):
        """
        This Class is to run asyncio using aiometer.

        :param max_at_once: Limit maximum number of concurrently running tasks.
        :param max_per_second: Limit request rate to not overload the server.
        :param title: Title of the tasks
        :param status: Status of the tasks
        :param debug: Whether to use debug
        :param kwargs:

        Example:

            .. code-block:: python

                async_tasks = AsyncTasks(max_at_once=10, max_per_second=10)
                async_tasks.generate_tasks(
                    target_list=range(1, 100) ,
                    function=run_container,
                    **{"args": args}
                ).run()


        """
        self.tasks = []
        self.max_at_once = max_at_once
        self.max_per_second = max_per_second
        self.debug = debug
        self._debug_print(self)

        self.get_list_function = None

        self.async_partial_target_func = None
        self.async_partial_task_func = None
        self.status_console = None

        self._title = title
        self._view_status = status
        self._function_name = ""

    def get_tasks(self):
        return self.tasks

    def generate_tasks(self, target_list=None, function=None, **kwargs):
        """
        This function generates the async tasks list

        :param target_list: List of targets for asynchronous execution
        :param function: Name of the function to execute
        :param kwargs:
        :return:
        """
        if function and getattr(function, "__qualname__"):
            self._function_name = function.__qualname__
        else:
            raise ValueError(f"{function} is not function")

        self._debug_print(f"{target_list}, {type(target_list)}")
        if kwargs.get('kwargs'):
            kwargs = kwargs['kwargs']
        else:
            kwargs = {}

        if target_list is None:
            target_list = []

        for target in target_list:
            self._debug_print(f"target={target}, function={self._function_name}(), kwargs={kwargs}, task_len={len(self.tasks)}")
            self.tasks.append(partial(function, target, **kwargs))

    def run(self):
        """
        This function executes an asynchronous operation.

        :return:
        """

        if self._view_status:
            with pawn.console.status(self._title) as status:
                result = asyncio.run(self._runner(status))
        else:
            result = asyncio.run(self._runner())

        return result

    async def _runner(self, status=None):
        result = {}
        tasks_length = len(self.tasks)

        if tasks_length > 0:
            async with aiometer.amap(
                    async_fn=lambda fn: fn(),
                    args=self.tasks,
                    max_at_once=self.max_at_once,
                    max_per_second=self.max_per_second,
                    _include_index=True,
            ) as amap_results:
                async for _index, _result in amap_results:
                    result[_index] = _result
                    if status and self._view_status:
                        status.update(f"{self._title} <{self._function_name}> [{_index}/{tasks_length}] {_result}")
        else:
            pawn.console.log(f"ERROR: tasks is null = {self.tasks}")
        return utils.list_from_indexed_dict(result)

    def _debug_print(self, *args, **kwargs):
        if self.debug:
            debug_print(*args, **kwargs)


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


class AsyncHttp(AsyncTasks):
    """
    This class is a subclass of AsyncTasks and is used to handle asynchronous HTTP requests.

    Attributes:
        max_at_once (int): Maximum number of tasks to run at once.
        max_per_second (int): Maximum number of tasks to start per second.
        title (str): Title for the progress bar.
        debug (bool): If True, print debug information.
        status (bool): If True, print status information.
        urls (list): List of URLs to fetch.
    """

    def __init__(self,
                 max_at_once: int = 10,
                 max_per_second: int = 10,
                 title="Working on async tasks ...",
                 debug: bool = False,
                 status: bool = False,
                 urls: list = None,
                 **kwargs):
        if urls is None:
            urls = []
        super().__init__(max_at_once, max_per_second, title, debug, status, **kwargs)
        self.urls = urls
        self._prepare()

    def append_task(self, task):
        """
        Append a new task to the task list.

        Args:
            task (str or dict): If it's a string, it's considered as a URL. If it's a dictionary, it should contain a 'url' key.
        """

        _url = None
        _kwargs = {}

        if isinstance(task, str):
            _url = task
            _kwargs = {}
        elif isinstance(task, dict) and task.get('url'):
            _url = task.pop("url")
            _kwargs = task

        self.generate_tasks(
            target_list=[_url],
            function=fetch_httpx_url,
            **_kwargs
        )
        pawn.console.log(f"IN] url={_url}, kwargs={_kwargs}, max_at_once={self.max_at_once}")

    def _prepare(self):
        """
        Prepare the tasks based on the provided URLs.
        """

        if len(self.urls) > 0:
            for info in self.urls:

                self.append_task(info)


async def fetch_httpx_url(url, method="get", timeout=4, info="", max_keepalive_connections=10, max_connections=20, **kwargs):
    """
    Asynchronously fetch a URL using httpx.

    Args:
        url (str): The URL to fetch.
        method (str): The HTTP method to use. Default is "get".
        timeout (int): The timeout for the request in seconds. Default is 4.
        info (str): Additional information for the request. Default is an empty string.
        max_keepalive_connections (int): The maximum number of keep-alive connections. Default is 10.
        max_connections (int): The maximum number of connections. Default is 20.
        **kwargs: Additional keyword arguments for the httpx request.

    Returns:
        httpx.Response or dict: The response from the server, or an empty dictionary if an error occurred.
    """

    response = None
    try:
        limits = httpx.Limits(max_keepalive_connections=max_keepalive_connections, max_connections=max_connections)
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:

            # pawn.console.log(url, kwargs)

            if method in ALLOWS_HTTP_METHOD:
                response = await getattr(client, method)(url, timeout=timeout, **kwargs)
            else:
                pawn.console.log(f"[ERROR] Unsupported HTTP method -> {method}")
                pawn.app_logger.error(f"[ERROR] Unsupported HTTP method -> {method}")
                raise ValueError(f"[ERROR] Unsupported HTTP method -> {method}")

            # client.post

            #
            # if method == "get":
            #     response = await client.get(url)
            # else:
            #     response = await getattr(client, method)(url)

            if response.status_code != 200:
                pawn.console.log(f"[red][ERROR] fetching {url}, status_code={response.status_code}, response={response.text}")
                pawn.app_logger.error(f"[red][ERROR] fetching {url}, status_code={response.status_code}, response={response.text}")
            return response

    except Exception as e:
        pawn.console.log(f"url={url} e={e}, response={response}, info={info}")
        pawn.app_logger.error(f"url={url} e={e}, response={response}, info={info}")
    return {}
