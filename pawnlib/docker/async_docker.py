from pawnlib.output import *
from pawnlib.typing.generator import generate_number_list
# from pawnlib.asyncio import AsyncTasks, async_partial
import aiodocker
import asyncio
import re
from functools import partial
from devtools import debug
import aiometer
from pawnlib.config import pawnlib_config as pawn


class AsyncDocker:
    def __init__(self, client=None, filters={}, client_options={}, max_at_once=10, max_per_second=10, container_name="", count=0):
        if client:
            self.client = client
        else:
            self.client = aiodocker.Docker(**client_options)
        self.client_options = client_options
        self.image_list = []
        self.container_list = []
        self.loop = None
        self.max_at_once = max_at_once
        self.max_per_second = max_per_second
        self.skip = False
        self.container_name = container_name
        self.count = count

        self.filters = filters
        self.loop_state = {}

        self.default_control_option = {
            "delete": {
                "force": True
            },
            "stats": {
                "stream": False
            }
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pawn.console.debug(f"__exit__ :: before session: {self.client.session.closed} ")
        res = asyncio.run(self.close())
        pawn.console.debug(f"__exit__ :: after session: {res} == session: {self.client.session.closed} ")

    async def close(self):
        await self.client.close()
        if self.loop:
            self.loop.close()

    # @staticmethod
    def run_async_loop(self, function):
        pawn.console.debug(f"Execute function={function.__name__}()")
        self.loop = asyncio.get_event_loop()
        result = self.loop.run_until_complete(function, )
        return result

    def client_decorator(func):
        # debug(f"{func} decorator :: ", f"{skip}")
        async def wrapper(self, *args, **kwargs):
            pawn.console.log(f"execute {func.__name__}() client_decorator() skip={self.skip}")
            pawn.console.log(f"[IN] Decorator args = {args}")

            if self.client:
                pawn.console.log(f"[red] session closed = {self.client.session.closed}")

            if self.skip is False:
                self.client = aiodocker.Docker(**self.client_options)
                debug(self.client.docker_host)

            ret = await func(self, *args, **kwargs)

            if self.skip is False:
                pawn.console.log(f"[red] session closing => {self.client.session.closed}")
                await self.client.close()
                self.skip = False

            return ret

        return wrapper

    # @client_decorator

    async def _async_pull_image(self, image=None):
        try:
            await self.client.images.pull(image)
        except Exception as e:
            pawn.console.log(f"[red][ERROR] {e}")

    async def _async_get_images(self, simple=True):
        # print(f"Simple = {simple}")
        # pawn.console.log(f"---")
        # # self.client = aiodocker.Docker(**self.client_options)
        # pawn.console.log(f"---> {self.client}")
        for image in (await self.client.images.list()):
            # pawn.console.debug(image)
            # tags = image['RepoTags'][0] if image['RepoTags'] else ''
            if isinstance(image['RepoTags'], list):
                tags_list = image['RepoTags']
            else:
                tags_list = [""]

            for tags in tags_list:
                if simple:
                    self.image_list.append({"id": image['Id'].replace("sha256:", "")[:12], "tags": tags})
                else:
                    self.image_list.append(image)

        # await self.client.close()

        return self.image_list

    def pull_image(self, *args, **kwargs):
        return self.run_async_loop(function=self._async_pull_image(*args, **kwargs))

    def get_images(self, *args, **kwargs):
        return self.run_async_loop(function=self._async_get_images(*args, **kwargs))

    def find_image(self, image=None):
        self.get_images()
        for _image in self.image_list:
            if _image.get('tags') == image:
                return True
        return False

    # @client_decorator
    async def _async_get_containers(self, filters={}, **kwargs):
        self.container_list = []
        for container in (await self.client.containers.list(**kwargs)):
            container = self.parse_container_dict(container)
            # debug(f"[get_containers]", container._container['Names'])
            if filters == {} or self.filtering_dict(container._container, filters):
                self.container_list.append(container)

        pawn.console.log(f"[FILTER] condition regex={filters}, matched container={len(self.container_list)}")

        return self.container_list

    def filtering_dict(self, item, filters=None):
        matched = False
        if filters is None:
            filters = self.filters
        if isinstance(item, dict) and isinstance(filters, dict):
            for filter_key, filter_value in filters.items():
                filtering_target = item.get(filter_key, "NNN" * 10)
                # p = re.compile(filter_value)
                # match_regex = re.match(filter_value, filtering_target)
                match_regex = re.fullmatch(fr"{filter_value}", filtering_target)
                # match_regex = re.fullmatch(pattern, filtering_target)
                if match_regex:
                    # cprint(f"[Filter] filter_key={filter_value}, filter_value={filter_value}, "
                    #        f"target={filtering_target}, {match_regex.groups()}")
                    matched = True
        return matched

    def get_containers(self, *args, **kwargs):
        return self.run_async_loop(function=self._async_get_containers(*args, **kwargs))

    def parse_container_dict(self, container):
        # df = pandas.DataFrame(columns=container._container.keys())
        if isinstance(container, aiodocker.containers.DockerContainer):
            # remove the first '/'
            container._container['Names'] = re.sub("^/", "", " ".join(container._container['Names']))
            container._container['Id'] = container._container['Id'][:12]
            container._container['ImageID'] = container._container['ImageID'].replace("sha256:", "")[:12]

            # debug(container._container)
        return container
        # container
        # # df = df.append(container._container.__dict__, ignore_index=True)

    async def delete_container(self, container, container_total, count):
        print(f"[{count}/{container_total}] Delete to {container._id} {container._container['Names']}")
        await container.delete(force=True)

    @staticmethod
    def _callback(function=None, loop_state={}, *args, **kwargs):
        if kwargs:
            pawn.console.log(f"_callback:: {kwargs}")
        res = function(**kwargs)
        container_info = ""
        if loop_state.get('container', None) and isinstance(loop_state['container'], aiodocker.containers.DockerContainer):
            container_info = f" {loop_state['container']._container['Id']}," \
                             f" {loop_state['container']._container['Names']}"

        if loop_state:
            pawn.console.log(f"[{loop_state['count']:>3}/{loop_state['total']}] {function.__name__} the container {container_info}")

            # cprint(f"[{loop_state['count']:>3}/{loop_state['total']}]", "white")
            # f"{function.__name__} the container {loop_state['container']._container['Id']},"
            # f" {loop_state['container']._container['Names']}", "white")
        return res


    async def _generate_echo_containers(self):
        attach_list = []
        for numbering in generate_number_list(start=10000, count=self.count, convert_func=str):
            container_name = f"{self.container_name}_{numbering}"
            options = dict(
                config={
                    'Image': 'jmalloc/echo-server',
                    'Hostname': container_name,
                    'Env': [
                        f"PORT={numbering}"
                    ],
                    "NetworkMode": "host"
                },
                name=container_name,
            )
            attach_list.append(options)
        return attach_list

    async def _print_container_name_in_list(self, containers):
        _count = 0
        pawn.console.rule(f"Container name in list")
        for container in containers:
            container_info = container._container
            pawn.console.log(f"[{_count}] {container_info['Id']}, {container_info['Names']}, {container_info['Status']}")
            _count += 1

    async def _async_control_aiometer_container(self, method, *args, **kwargs):
        if kwargs is None:
            kwargs = {}

        pawn.console.log(f"_async_control_aiometer_container() method={method}, args={args}, "
                         f"kwargs={kwargs}, {self.default_control_option.get(method, {})}")
        results = []
        tasks = []
        count = 0

        if method == "create_or_replace":
            attach_list = self._generate_echo_containers()
        else:
            attach_list = await self._async_get_containers(*args, **kwargs)

        if method == "ls":
            await self._print_container_name_in_list(attach_list)
        else:
            total = len(attach_list)
            for item in attach_list:
                count += 1
                loop_state = {
                    "container": item,
                    "total": total,
                    "count": count
                }
                if isinstance(item, aiodocker.containers.DockerContainer):
                    container = item
                    params = self.default_control_option.get(method, {})
                else:
                    params = item
                    container = self.client.containers

                _function = partial(
                    self._callback,
                    function=getattr(container, method),
                    loop_state=loop_state,
                    # **self.default_control_option.get(method, {})
                    **params
                )

                tasks.append(_function)
            if len(tasks) > 0:
                results = await aiometer.run_all(tasks, max_at_once=self.max_at_once, max_per_second=self.max_per_second)

        return results

    def control_container(self, method=None, *args, **kwargs):
        self.run_async_loop(function=self._async_control_aiometer_container(method=method, *args, **kwargs))

    async def _async_await(self, function=None, method=None, *args, **kwargs):
        container_name = ""
        if isinstance(function, aiodocker.containers.DockerContainer):
            container_name = function._container['Names']

        pawn.console.log(f"_async_await => {function}.{method}() {container_name}")
        if method in ["start"]:
            args = []
            kwargs = {}
        client = aiodocker.Docker()
        function.docker = client
        # func = getattr(function, method)
        res = await getattr(function, method)(*args, **kwargs)
        # await client.close()
        return res

    async def _async_control_container(self, container, container_total=0, count=0, **kwargs):
        # client = aiodocker.Docker().DockerContainer(container)
        client = aiodocker.Docker()
        pawn.console.log(f"[{count}/{container_total}] Delete to {container._id}")
        await client._query_json(f"containers/{container._id}", method="DELETE", params=kwargs)
        await client.close()


async def delete_container(container, container_total=0, count=0):
    print(f"[{count}/{container_total}] Delete to {container._id}")
    await container.delete(force=True)


async def list_things(args, filters={}):
    debug(filters)
    image_list = []
    container_list = []
    print('== Images ==')
    for image in (await args.client.images.list()):
        tags = image['RepoTags'][0] if image['RepoTags'] else ''
        # print(image['Id'], tags)
        image_list.append({"id": image['Id'], "tags": tags})
    print('== Containers ==')
    for container in (await args.client.containers.list()):
        print(f" {container._id}")
        for fk, fv in filters.items():
            filtering_target = container._container.get(fk, "NNN")
            if isinstance(filtering_target, list):
                filtering_target = "".join(filtering_target)
            if fv in filtering_target:
                container_list.append(container)
    return image_list, container_list


async def rm_container(args):
    args.client = aiodocker.Docker()
    image_list, container_list = await list_things(args, filters={"Names": args.name})
    tasks = []
    container_total = len(container_list)
    count = 0
    for container in container_list:
        count += 1
        container_name = "".join(container._container['Names'])
        debug(container._id, container_name)
        # tasks.append(asyncio.ensure_future(container.delete(force=True)))
        tasks.append(partial(delete_container, container, container_total, count))
    if len(tasks) > 0:
        results = await aiometer.run_all(tasks, max_at_once=args.max_at_once, max_per_second=args.max_per_second)
    await args.client.close()


async def run_container(numbering, *args, **kwargs):
    client = aiodocker.Docker()
    args = kwargs.get('args')
    container_name = f"{args.name}_{numbering}"

    if args.__dict__.get('env_key'):
        env_key = args.env_key
    else:
        env_key = "PORT"

    if args.image:
        docker_image = args.image
    else:
        docker_image = "jmalloc/echo-server"

    container_config = {
        'Image': docker_image,
        'Hostname': container_name,
        'Env': [
            f"{env_key}={numbering}"
        ],
        # 'Cmd': ['/bin/ash', '-c', 'echo "hello world"'],
        # "Ports": {
        #     "8080": f"1{numbering}/tcp"
        # },
        "NetworkMode": "host"
    }

    pawn.console.log(f'== Running a "{docker_image}" container => {container_name}, args={args}, container_config={container_config}')

    container = await client.containers.create_or_replace(
        config=container_config,
        name=container_name,
    )
    await container.start()
    logs = await container.log(stdout=True)

    container_name = container.__dict__['_container']['Name'].lstrip("/")
    pawn.console.log(f"container={container_name}, logs={''.join(logs).strip()}")
    # pawn.console.log(''.join(logs))

    await client.close()
    # await container.delete(force=True)
    # await args.client.close()


async def run_dyn_container(config, *args, **kwargs):
    client = aiodocker.Docker()
    pawn.console.debug(f"config={config}")
    pawn.console.debug(f"args={args}")
    pawn.console.debug(f"kwargs={kwargs}")
    container_name = kwargs.get('container_name')

    pawn.console.log(f"[CONTAINER][{pawn.get('count')}] Running container_name={container_name}")

    container = await client.containers.create_or_replace(
        config=config,
        name=container_name,
    )
    await container.start()
    await asyncio.sleep(1)

    if kwargs['args'].show_container_log:
        logs = await container.log(stdout=True, stderr=True, tail=2)
        container_name = container.__dict__['_container']['Name'].lstrip("/")
        pawn.console.log(f"container={container_name}, logs={''.join(logs).strip()}")

    await client.close()
    #


def extract_upper_key_to_env_list(config=None):
    if not config:
        config = pawn.to_dict().get('PAWN_CONFIG')

    result = []
    if config.get('default'):
        for key,value in config['default'].items():
            if key.isupper():
                result.append(f"{key}={value}")
    return result
