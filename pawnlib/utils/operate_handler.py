import logging
import os
import sys
import time
import inspect
import errno
import signal
import atexit
import subprocess
import threading
import itertools
import warnings
from io import TextIOWrapper
from typing import Callable, List, Dict, Union, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from pawnlib.output import dump, debug_print, bcolors
from pawnlib import typing
from functools import wraps

# from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.config import pawn, get_logger
from pawnlib.typing.converter import shorten_text

# warnings.simplefilter('default', DeprecationWarning)

logger = get_logger()


class ThreadPoolRunner:
    """
    A class that runs a function with multiple arguments in parallel using a thread pool.

    :param func: The function to run in parallel.
    :type func: function
    :param tasks: A list of arguments to pass to the function.
    :type tasks: list
    :param max_workers: The maximum number of worker threads to use.
    :type max_workers: int
    :param verbose: Whether to print the results of each task as they complete.
    :type verbose: int
    :param sleep: The number of seconds to sleep between runs when using `forever_run`.
    :type sleep: int

    Example:

        .. code-block:: python

            runner = ThreadPoolRunner(func=my_function, tasks=my_args, max_workers=10, verbose=1, sleep=5)
            results = runner.run()
            runner.forever_run()

    """

    def __init__(self, func=None, tasks=[], max_workers=20, verbose=0, sleep=1):
        self.func = func
        self.tasks = tasks
        self.max_workers = max_workers
        self.results = []
        self.sleep = sleep
        self.verbose = verbose
        self.stop_event = threading.Event()

    def initializer_worker(self):
        """
        A method that is run once by each worker thread when the thread pool is created.
        """
        pass

    def run(self, tasks=None, timeout: int = None) -> List[Any]:
        """
        Run the function with the given arguments in parallel using a thread pool.

        :param tasks: A list or generator of tasks.
        :type tasks: list or generator
        :param timeout: Timeout for each task in seconds. If None, no timeout is applied.
        :type timeout: int or None
        :return: A list of results from each task, in the same order as the input.
        :rtype: list
        """

        tasks = tasks or self.tasks

        with ThreadPoolExecutor(max_workers=self.max_workers, initializer=self.initializer_worker) as pool:
            futures = {pool.submit(self.func, _task): idx for idx, _task in enumerate(tasks)}
            results = [None] * len(tasks)

            try:
                for future in as_completed(futures, timeout=timeout):
                    idx = futures[future]
                    _task = tasks[idx]
                    try:
                        result = future.result(timeout=timeout)
                        results[idx] = result
                        if self.verbose > 4:
                            logger.info(
                                f"Task {idx} completed. "
                                f"Function: {self.func.__name__}(), Arguments: {_task}, Result: {result}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Task {idx} failed. "
                            f"Function: {self.func.__name__}, Arguments: {_task}, Exception: {e}"
                        )
            except TimeoutError:
                logger.error(f"Timeout exceeded while waiting for tasks to complete.")
            except Exception as e:
                logger.error(f"Critical error in thread pool execution: {e}")
                pool.shutdown(wait=False)
                for future in futures:
                    future.cancel()
                raise

        return results

    @staticmethod
    def log_results(results):
        """
        Print the results of each task as they complete.

        :param results: A list of results from each task.
        :type results: list
        """
        if results:
            for result in results:
                if result:
                    print(result)

    # def forever_run(self):
    #     """
    #     Run the function with the given arguments in parallel using a thread pool indefinitely.
    #     """
    #     while True:
    #         self.run()
    #         time.sleep(self.sleep)

    def forever_run(self):
        """
        Run the function with the given arguments in parallel using a thread pool indefinitely.
        """
        try:
            while not self.stop_event.is_set():
                self.run()
                time.sleep(self.sleep)
        except KeyboardInterrupt:
            logger.info("Interrupted by user, stopping...")
            self.stop()

    def stop(self):
        """
        Stop the forever_run loop.
        """
        self.stop_event.set()


class Daemon(object):
    """
    A generic daemon class.
    Usage 1: subclass the Daemon class and override the run() method
    Usage 2: subclass the Daemon class and use func parameter

    :param pidfile: pid file location
    :param func: function to run as daemon
    :param stdin: standard input , The default is sys.stdin, and providing a filename will output to a file.
    :param stdout: standard output, The default is sys.stdout, and  providing a filename will output to a file.
    :param stderr: standard error, The default is sys.stderr, and providing a filename will output to a file.
    :param home_dir: home directory
    :param umask: umask
    :param verbose: verbosity level
    :param use_gevent: use gevent
    :param use_eventlet: use eventlet
    \
    Example:

        .. code-block:: python

            from pawnlib.utils.operate_handler import Daemon

            def main():
                while True:
                    print(f"main loop")
                    print("start daemon")
                    time.sleep(5)


            if __name__ == "__main__":
                if len(sys.argv) != 2:
                    sys.exit()
                command = sys.argv[1]
                daemon = Daemon(
                    pidfile="/tmp/jmon_agent.pid",
                    func=main
                )
                if command == "start":
                    daemon.start()
                elif command == "stop":
                    daemon.stop()
                else:
                    print("command not found [start/stop]")


    """

    def __init__(self, pidfile, func=None, stdin=None,
                 stdout=None, stderr=None,
                 home_dir='.', umask=0o22, verbose=1,
                 use_gevent: bool = False, use_eventlet: bool = False):
        self.stdin = stdin if stdin is not None else sys.stdin
        self.stdout = stdout if stdout is not None else sys.stdout
        self.stderr = stderr if stderr is not None else sys.stderr
        self.pidfile = pidfile
        self.func = func
        self.home_dir = home_dir
        self.verbose = verbose
        self.umask = umask
        self.daemon_alive = True
        self.use_gevent = use_gevent
        self.use_eventlet = use_eventlet

    def log(self, *args):
        if self.verbose >= 1:
            print(*args)

    def daemonize(self):
        """
        Do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        if self.use_eventlet:
            import eventlet.tpool
            eventlet.tpool.killall()
        try:
            pid = os.fork()
            if pid > 0:
                # Exit first parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write(
                "fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # Decouple from parent environment
        os.chdir(self.home_dir)
        os.setsid()
        os.umask(self.umask)

        # Do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # Exit from second parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write(
                "fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        if sys.platform != 'darwin':  # This block breaks on OS X
            # Redirect standard file descriptors
            sys.stdout.flush()
            sys.stderr.flush()
            si = open(self.stdin, 'r') if isinstance(self.stdin, str) else self.stdin
            so = open(self.stdout, 'a+') if isinstance(self.stdout, str) else self.stdout
            if self.stderr:
                try:
                    se = open(self.stderr, 'a+') if isinstance(self.stderr, str) else self.stderr
                except ValueError:
                    # Python 3 can't have unbuffered text I/O
                    se = open(self.stderr, 'a+', 1)
            else:
                se = so
            if isinstance(si, TextIOWrapper):
                os.dup2(si.fileno(), sys.stdin.fileno())
            if isinstance(so, TextIOWrapper):
                os.dup2(so.fileno(), sys.stdout.fileno())
            if isinstance(se, TextIOWrapper):
                os.dup2(se.fileno(), sys.stderr.fileno())

        def sigtermhandler(signum, frame):
            self.daemon_alive = False
            sys.exit()

        if self.use_gevent:
            import gevent
            gevent.reinit()
            gevent.signal(signal.SIGTERM, sigtermhandler, signal.SIGTERM, None)
            gevent.signal(signal.SIGINT, sigtermhandler, signal.SIGINT, None)
        else:
            signal.signal(signal.SIGTERM, sigtermhandler)
            signal.signal(signal.SIGINT, sigtermhandler)

        self.log("Started")

        # Write pidfile
        atexit.register(
            self.delpid)  # Make sure pid file is removed if we quit
        pid = str(os.getpid())
        open(self.pidfile, 'w+').write("%s\n" % pid)

    def delpid(self):
        try:
            # the process may fork itself again
            pid = int(open(self.pidfile, 'r').read().strip())
            if pid == os.getpid():
                os.remove(self.pidfile)
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise

    def start(self, *args, **kwargs):
        """
        Start the daemon
        """

        self.log("Starting...")

        # Check for a pidfile to see if the daemon already runs
        try:
            pf = open(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        except SystemExit:
            pid = None

        if pid:
            message = "pidfile %s already exists. Is it already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        if self.func:
            self.func(*args, **kwargs)
        else:
            self.run(*args, **kwargs)

    def stop(self):
        """
        Stop the daemon
        """

        if self.verbose >= 1:
            self.log("Stopping...")

        # Get the pid from the pidfile
        pid = self.get_pid()

        if not pid:
            message = "pidfile %s does not exist. Not running?\n"
            sys.stderr.write(message % self.pidfile)

            # Just to be sure. A ValueError might occur if the PID file is
            # empty but does actually exist
            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)

            return  # Not an error in a restart

        # Try killing the daemon process
        try:
            i = 0
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
                i = i + 1
                if i % 10 == 0:
                    os.kill(pid, signal.SIGHUP)
        except OSError as err:

            if os.path.exists(self.pidfile):
                os.remove(self.pidfile)
            else:
                print(str(err))
                sys.exit(0)

        self.log("Stopped")

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def get_pid(self):
        try:
            pf = open(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        except SystemExit:
            pid = None
        return pid

    def is_running(self):
        pid = self.get_pid()

        if pid is None:
            self.log('Process is stopped')
            return False
        elif os.path.exists('/proc/%d' % pid):
            self.log('Process (pid %d) is running...' % pid)
            return True
        else:
            self.log('Process (pid %d) is killed' % pid)
            return False

    def run(self):
        """
        You should override this method when you subclass Daemon.
        It will be called after the process has been
        daemonized by start() or restart().
        """
        raise NotImplementedError


def timing(f):
    """
    Get the time taken to complete the task.

    :param f:
    :return:
    """

    @wraps(f)
    def wrap(*args, **kwargs):
        function_name = f"{f.__module__}.{f.__name__}()"
        job_start(function_name)
        start_time = time.time()
        ret = f(*args, **kwargs)
        end_time = time.time() - start_time
        # cprint('{:s} function took {:.3f} ms'.format(f.__name__, (time2-time1)*1000.0))
        job_done(full_module_name=function_name, elapsed=end_time)
        return ret
    return wrap


def get_inspect_module(full_module_name=None):
    if full_module_name is None:
        module_name = ''
        stack = inspect.stack()
        parent_frame = stack[1][0]
        module = inspect.getmodule(parent_frame)
        if module:
            module_pieces = module.__name__.split('.')
            module_name = typing.list_to_oneline_string(module_pieces)
        function_name = stack[1][3]
        full_module_name = "%s.%s()" % (module_name, function_name)
    return full_module_name


def job_start(full_module_name=None):
    full_module_name = get_inspect_module(full_module_name)
    if pawn.get('PAWN_VERBOSE', 0) > 0:
        debug_print(f"[START] {full_module_name}", "green")


def job_done(error: str = '', full_module_name: str = '', elapsed: Union[float, int] = 0):
    title = get_inspect_module(full_module_name)
    if pawn.get('PAWN_VERBOSE', 0) > 0:
        if error == '':
            debug_print(f"[DONE ] {title} {elapsed:.3f}sec", "green")
        else:
            debug_print(" NOT DONE %s (%.3fsec)- %s" % (title, elapsed, error), "red")
    return title


def execute_function(module_func):
    if "." in module_func:
        [module_name, function_name] = module_func.split(".")
        dump(globals())
        module = __import__(f"{module_name}")
        func = getattr(module, function_name)
        return func()
    return globals()[module_func]()


def run_execute(*args, **kwargs):
    warnings.warn(
        "run_execute is deprecated. Use execute_command instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return execute_command(*args, **kwargs)


# def execute_command(*args, **kwargs):
#     return run_execute(*args, **kwargs)

#
# def execute_command(
#         cmd: str,
#         text: Optional[str] = None,
#         cwd: Optional[str] = None,
#         check_output: bool = True,
#         capture_output: bool = True,
#         hook_function: Optional[Callable[[str, int], None]] = None,
#         debug: bool = False,
#         **kwargs
# ) -> Dict[str, Any]:
#     """
#     Executes a shell command and captures its output.
#
#     Args:
#         cmd (str): Command to be executed.
#         text (str, optional): Descriptive text or title for the command.
#         cwd (str, optional): Working directory to execute the command in.
#         check_output (bool, optional): If True, logs the command execution result.
#         capture_output (bool, optional): If True, captures the command's stdout.
#         hook_function (Callable[[str, int], None], optional): Function to process each line of stdout.
#         debug (bool, optional): If True, prints debug information.
#         **kwargs: Additional keyword arguments to pass to the hook_function.
#
#     Returns:
#         Dict[str, Any]: A dictionary containing the command's execution results.
#
#     Raises:
#         OSError: If an error occurs while executing the command.
#     """
#     start_time = time.time()
#
#     result = {
#         "stdout": [],
#         "stderr": None,
#         "return_code": 0,
#         "line_no": 0,
#         "elapsed": 0.0,
#     }
#
#     if text is None:
#         text = cmd
#     else:
#         text = f"{text} (cmd='{cmd}')"
#
#     if debug:
#         logger.debug(f"Executing command: {cmd}")
#
#     try:
#         process = subprocess.Popen(
#             cmd,
#             cwd=cwd,
#             shell=True,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True,  # Replaces 'universal_newlines=True'
#         )
#
#         # Process stdout line by line
#         if process.stdout:
#             for line in process.stdout:
#                 line_stripped = line.strip()
#                 if line_stripped:
#                     if callable(hook_function):
#                         hook_function(line=line_stripped, line_no=result['line_no'], **kwargs)
#
#                     if capture_output:
#                         result["stdout"].append(line_stripped)
#
#                     result['line_no'] += 1
#
#         # Wait for the process to complete and capture stderr
#         _, stderr = process.communicate()
#
#         result["return_code"] = process.returncode
#         if stderr:
#             result["stderr"] = stderr.strip()
#
#     except Exception as e:
#         result['stderr'] = str(e)
#         raise OSError(f"Error while running command '{cmd}': {e}") from e
#
#     end_time = time.time()
#     result['elapsed'] = round(end_time - start_time, 3)
#
#     if check_output:
#         if result.get("stderr"):
#             logger.error(f"[FAIL] {text}, Error: '{result.get('stderr')}'")
#         else:
#             logger.info(f"[ OK ] {text}, elapsed={result['elapsed']}s")
#
#     return result


def execute_command(
        cmd: str,
        text: Optional[str] = None,
        cwd: Optional[str] = None,
        check_output: bool = True,
        capture_output: bool = True,
        hook_function: Optional[Callable[[str, int], None]] = None,
        debug: bool = False,
        use_spinner: bool = False,
        spinner_type: str = "dots",
        spinner_text: Optional[str] = None,
        **kwargs
) -> Dict[str, Any]:
    """
    Executes a shell command and captures its output, with an optional spinner for visual feedback.

    Args:
        cmd (str): Command to be executed.
        text (str, optional): Descriptive text or title for the command.
        cwd (str, optional): Working directory to execute the command in.
        check_output (bool, optional): If True, logs the command execution result.
        capture_output (bool, optional): If True, captures the command's stdout.
        hook_function (Callable[[str, int], None], optional): Function to process each line of stdout.
        debug (bool, optional): If True, prints debug information.
        use_spinner (bool, optional): If True, shows a spinner while the command executes.
        spinner_type (str, optional): The type of spinner to use (from Rich library).
        spinner_text (str, optional): Custom text to display alongside the spinner.
        **kwargs: Additional keyword arguments to pass to the hook_function.

    Returns:
        Dict[str, Any]: A dictionary containing the command's execution results.

    Raises:
        OSError: If an error occurs while executing the command.
    """
    start_time = time.time()

    result = {
        "stdout": [],
        "stderr": None,
        "return_code": 0,
        "line_no": 0,
        "elapsed": 0.0,
    }

    if text is None:
        text = cmd
    else:
        text = f"{text} (cmd='{cmd}')"

    if spinner_text is None:
        spinner_text = f"Executing: {text}"

    if debug:
        pawn.console.log(f"Executing command: {text}")

    try:
        if use_spinner:
            with pawn.console.status(spinner_text, spinner="dots"):
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,  # Replaces 'universal_newlines=True'
                )
                result = _process_command_output(process, capture_output, hook_function, result, **kwargs)
        else:
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            result = _process_command_output(process, capture_output, hook_function, result, **kwargs)

    except Exception as e:
        result['stderr'] = str(e)
        raise OSError(f"Error while running command '{cmd}': {e}") from e

    end_time = time.time()
    result['elapsed'] = round(end_time - start_time, 3)

    if check_output:
        if result.get("stderr"):
            logger.error(f"[bold red][FAIL][/bold red] {text}, Error: '{result.get('stderr')}'")
        else:
            logger.info(f"[bold green][ OK ][/bold green] {text}, elapsed={result['elapsed']}s")

    return result


def _process_command_output(process, capture_output, hook_function, result, **kwargs):
    """
    Processes the output from the subprocess.
    """
    if process.stdout:
        for line in process.stdout:
            line_stripped = line.strip()
            if line_stripped:
                if callable(hook_function):
                    hook_function(line=line_stripped, line_no=result['line_no'], **kwargs)

                if capture_output:
                    result["stdout"].append(line_stripped)

                result['line_no'] += 1

    # Wait for the process to complete and capture stderr
    _, stderr = process.communicate()

    result["return_code"] = process.returncode
    if stderr:
        result["stderr"] = stderr.strip()

    return result


def execute_command_batch(
        tasks: Union[List[str], List[Dict[str, Any]]],
        stop_on_error: bool = False,
        slack_url: Optional[str] = None,
        default_kwargs: Optional[Dict[str, Any]] = None,
        function_registry=None,
) -> List[Dict[str, Any]]:
    """
    Executes a batch of tasks, where each task can be a string (command) or a dictionary
    containing arguments for execute_command. Handles errors and sends optional Slack notifications.

    Args:
        tasks (Union[List[str], List[Dict[str, Any]]]): List of commands (as strings or dictionaries).
        stop_on_error (bool, optional): If True, stops execution upon encountering an error.
        slack_url (str, optional): Slack webhook URL for sending notifications.
        default_kwargs (Dict[str, Any], optional): Default arguments to apply to each task.

    Returns:
        List[Dict[str, Any]]: A list of results from execute_command for each task.
    """
    from pawnlib.utils.notify import send_slack
    function_registry = function_registry or {}
    results = []
    default_kwargs = default_kwargs or {"debug":False, "check_output": False}

    for idx, task_item in enumerate(tasks):
        # If task is a string, treat it as a simple command
        if isinstance(task_item, str):
            task_args = {"cmd": task_item}
        elif isinstance(task_item, dict):
            task_args = task_item
        else:
            logger.error(f"Invalid task format at index {idx}. Skipping task.")
            continue

        # Merge with default kwargs, with task-specific arguments taking precedence
        task_args = {**default_kwargs, **task_args}
        # Extract 'cmd' for logging purposes
        cmd = task_args.get('cmd')
        task_type = task_args.get('type', 'shell')

        if not cmd:
            logger.error(f"Task {idx + 1} is missing the 'cmd' argument.")
            continue

        text = task_args.get('text', f"Task {idx + 1}/{len(tasks)}: {cmd}")
        status_emoji = "🚀"  # Default emoji for in-progress status

        try:
            if task_type == "function":
                result = execute_registered_function(cmd, function_registry=function_registry)
                cmd += "()"
            else:
                result = execute_command(**task_args)

            # success = result["return_code"] == 0
            success = result["return_code"] in [0, 2]
            elapsed = result["elapsed"]
            error_msg = result.get('stderr')

            status_emoji = "✅" if success else "❌"
            status = "SUCCESS" if success else "FAILED"

            if task_args.get('text'):
                text_command = f"{task_args.get('text')} (cmd='{cmd}')"
            else:
                text_command = f"Command: '{cmd}'"

            logger.info(
                # f"{status_emoji} Task {idx + 1}/{len(tasks)} | Command: '{cmd}' | Status: {status} | "
                f"{status_emoji} Task {idx + 1}/{len(tasks)} | {text_command} | Status: {status} | "
                f"Elapsed: {elapsed:.3f}s"
            )
            if error_msg:
                logger.error(f"{status_emoji} Task {idx + 1}/{len(tasks)} | {error_msg}")
            results.append(result)

            if slack_url:
                command_stdout = shorten_text("\n".join(result.get("stdout", [])) if success else "", width=30)
                command_stderr =  shorten_text(result.get("stderr", "") if not success else "", width=30, truncate_side="left")

                send_slack(
                    url=slack_url,
                    msg_text={
                        "Command": cmd,
                        "Elapsed": f"{elapsed:.3f}s",
                        # "Output": "\n".join(result.get("stdout", [])) if success else "",
                        "Output": command_stdout,
                        # "Error": result.get("stderr", "") if not success else "",
                        "Error": command_stderr,
                        "Return Code": result['return_code']
                    },
                    title=f"Task {idx + 1}/{len(tasks)} {status}",
                    send_user_name="TaskRunnerBot",
                    msg_level="info" if success else "error",
                    status="success" if success else "failed"
                )

            if not success and stop_on_error:
                logger.error("Execution stopped due to an error.")
                break

        except Exception as e:
            status_emoji = "❌"
            logger.error(
                f"{status_emoji} Task {idx + 1}/{len(tasks)} | Command: '{cmd}' | Status: EXCEPTION | "
                f"Error: {e}"
            )
            result = {
                "cmd": cmd,
                "stdout": [],
                "stderr": str(e),
                "return_code": -1,
                "elapsed": None,
            }
            results.append(result)

            # Send Slack notification for exception
            if slack_url:
                send_slack(
                    url=slack_url,
                    msg_text={
                        "Command": cmd,
                        "Error": str(e)
                    },
                    title=f"Task {idx + 1}/{len(tasks)} Exception",
                    send_user_name="TaskRunnerBot",
                    msg_level="error",
                    status="critical"
                )

            if stop_on_error:
                logger.error("Execution stopped due to an exception.")
                break

    return results


def execute_registered_function(function_name: str, args: Optional[Dict[str, Any]] = None, debug: bool = False, function_registry=None) -> Dict[str, Any]:
    """
    Executes the specified function by name and returns the result.

    Args:
        function_name (str): The name of the function to execute.
        args (Optional[Dict[str, Any]]): A dictionary of arguments to pass to the function.
        debug (bool, optional): If True, enables debug logging.
        function_registry (dict, optional): A registry of available functions.

    Returns:
        Dict[str, Any]: A dictionary containing the execution results, including 'stdout', 'stderr', 'return_code', 'line_no', and 'elapsed'.
    """
    try:
        func = function_registry.get(function_name)

        if not callable(func):
            raise ValueError(f"{function_name} is not a callable function.")
        if debug:
            logger.info(f"Executing function: {function_name} with args: {args}")

        start_time = time.time()
        result = func(**(args or {}))
        end_time = time.time()
        elapsed = round(end_time - start_time, 3)

        return {
            "stdout": [str(result)],
            "stderr": None,
            "return_code": 0,
            "line_no": 0,
            "elapsed": elapsed,
        }
    except AttributeError:
        error_msg = f"Function '{function_name}' not found."
        logger.error(error_msg)
        return {
            "stdout": [],
            "stderr": error_msg,
            "return_code": -1,
            "line_no": 0,
            "elapsed": 0.0,
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error executing function '{function_name}': {error_msg}")
        return {
            "stdout": [],
            "stderr": error_msg,
            "return_code": -1,
            "line_no": 0,
            "elapsed": 0.0,
        }


def hook_print(*args, **kwargs):
    """
    Print to output every 10th line

    :param args:
    :param kwargs:
    :return:
    """
    if "amplify" in kwargs.get("line"):
        print(f"[output hook - matching keyword] {args} {kwargs}")

    if kwargs.get("line_no") % 100 == 0:
        print(f"[output hook - matching line_no] {args} {kwargs}")
    # print(kwargs.get('line'))


class Spinner:
    """
    Create a spinning cursor

    :param text: text
    :param delay: sleep time

    :Example

        .. code-block:: python

            from pawnlib.utils.operate_handler import Spinner
            with Spinner(text="Wait message"):
                time.sleep(10)

    """
    def __init__(self, text="", delay=0.1):

        self._spinner_items = itertools.cycle(['-', '/', '|', '\\'])
        self.delay = delay
        self.busy = False
        self.spinner_visible = False
        self.text = text
        self._screen_lock = None
        self.thread = None
        self.spin_message = ""
        self.line_up = '\033[1A'
        self.line_up = '\x1b[1A'
        self.line_clear = '\x1b[2K'
        self.start_time = 0

        if type(sys.stdout).__name__ == "FileProxy":
            self._sys_stdout = getattr(sys.stdout, "rich_proxied_file", sys.stdout)
        else:
            self._sys_stdout = sys.stdout

    def title(self, text=None):
        # print(end=self.line_up)
        self.text = text

    def write_next(self):
        with self._screen_lock:
            if not self.spinner_visible:
                if self.text:
                    self.spin_message = f"{self.text} ... {next(self._spinner_items)}"
                else:
                    self.spin_message = next(self._spinner_items)
                # sys.stdout.write(next(self.spinner))
                self._sys_stdout.write(self.spin_message)

                self.spinner_visible = True
                self._sys_stdout.flush()

    def remove_spinner(self, cleanup=False):
        with self._screen_lock:
            if self.spinner_visible:
                b = len(self.spin_message)
                self._sys_stdout.write('\b' * b)
                self.spinner_visible = False
                if cleanup:
                    self._sys_stdout.write(' ')       # overwrite spinner with blank
                    self._sys_stdout.write('\r')      # move to next line
                self._sys_stdout.flush()

    def spinner_task(self):
        while self.busy:
            self.write_next()
            time.sleep(self.delay)
            self.remove_spinner()

    def start(self):
        self._screen_lock = threading.Lock()
        self.busy = True
        self.thread = threading.Thread(target=self.spinner_task)
        self.thread.start()
        self.start_time = time.time()  # 시작 시간 기록

    def stop(self):
        self.busy = False
        self.remove_spinner(cleanup=True)
        elapsed_time = time.time() - self.start_time  # 경과 시간 계산
        print(f"[DONE] {self.text} (took {elapsed_time:.2f} seconds)")  # 경과 시간 출력

    def __enter__(self):
        if self._sys_stdout.isatty():
            self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_traceback):
        if self._sys_stdout.isatty():
            self.stop()
            print(f"[DONE] {self.text}")
        else:
            self._sys_stdout.write('\r')


class WaitStateLoop:
    """
    loop_function is continuously executed and values ​​are compared with exit_function.

    :param loop_function:  function to run continuously
    :param exit_function: function to exit the loop
    :param timeout:
    :param delay: sleep time
    :param text: text message


    Example:

        .. code-block:: python

            from pawnlib.utils.operate_handler import WaitStateLoop
            from functools import partial

            def check_func(param=None):
                time.sleep(0.2)
                random_int = random.randint(1, 1000)
                # print(f"param= {param}, random_int = {random_int}")
                return random_int

            def loop_exit_func(result):
                if result % 10 == 1.5:
                    return True
                return False

            WaitStateLoop(
                loop_function=partial(check_func, "param_one"),
                exit_function=loop_exit_func,
                timeout=10
            ).run()

    """
    def __init__(self,
                 loop_function: Callable,
                 exit_function: Callable,
                 timeout=30, delay=0.5, text="WaitStateLoop",
                 ):
        self.loop_function = loop_function
        self.exit_function = exit_function
        self.timeout = timeout
        self.delay = delay
        self.text = text

    def run(self):
        """
        run()

        :return:
        """
        spin_text = ""
        error_text = ""
        count = 0
        start_time = time.time()
        if getattr(self.loop_function, "func"):
            func_name = self.loop_function.func.__name__
            spin_text = f"[{self.text}] Wait for {func_name}{self.loop_function.args}"

        with Spinner(text=spin_text) as spinner:
            while True:
                result = self.loop_function()
                is_success = self.exit_function(result)
                elapsed = int(time.time() - start_time)
                # spinner.title(f"{error_text}[{count}]{spin_text}: result={result}, is_success={is_success}, {elapsed} {time.time()} < {start_time + self.timeout}")
                if is_success is True:
                    return result
                spinner.title(f"{error_text}[{count}]{spin_text}: result={shorten_text(result, 30)}, is_success={is_success}, {elapsed} secs passed")
                # spinner.title(f" {elapsed} secs passed")
                time.sleep(self.delay)

                try:
                    assert time.time() < start_time + self.timeout
                except AssertionError:
                    # text = f"[{count:.1f}s] [{timeout_limit}s Timeout] Waiting for {exec_function_name} / '{func_args}' :: '{wait_state}' -> {check_state} , {error_msg}"
                    error_text = f"[TIMEOUT]"
                count += 1


def wait_state_loop(
        exec_function=None,
        func_args=[],
        check_key="status",
        wait_state="0x1",
        timeout_limit=30,
        increase_sec=0.5,
        health_status=None,
        description="",
        force_dict=True,
        logger=None
):
    start_time = time.time()
    count = 0
    # arguments 가 한개만 있을 때의 예외
    if isinstance(func_args, str):
        tmp_args = ()
        tmp_args = tmp_args + (func_args,)
        func_args = tmp_args

    exec_function_name = exec_function.__name__
    act_desc = f"desc={description}, function={exec_function_name}, args={func_args}"
    spinner = Halo(text=f"[START] Wait for {description} , {exec_function_name}, {func_args}", spinner='dots')
    if logger and hasattr(logger, "info"):
        logger.info(f"[SR] [START] {act_desc}")

    spinner.start()

    while True:
        if isinstance(func_args, dict):
            response = exec_function(**func_args)
        else:
            response = exec_function(*func_args)

        if not isinstance(response, dict):
            response = response.__dict__

        if force_dict and isinstance(response.get("json"), list):
            response['json'] = response['json'][0]

        check_state = ""
        error_msg = ""

        if response.get("json") or health_status:
            response_result = response.get("json")
            check_state = response_result.get(check_key, "")
            response_status = response.get("status_code")
            if check_state == wait_state or health_status == response_status:
                status_header = bcolors.OKGREEN + "[DONE]" + bcolors.ENDC
                text = f"\t[{description}] count={count}, func={exec_function_name}, args={str(func_args)[:30]}, wait_state='{wait_state}', check_state='{check_state}'"
                if health_status:
                    text += f", health_status={health_status}, status={response_status}"
                spinner.succeed(f'{status_header} {text}')
                spinner.stop()
                spinner.clear()
                # spinner.stop_and_persist(symbol='🦄'.encode('utf-8'), text="[DONE]")
                break
            else:
                if type(response_result) == dict or type(check_state) == dict:
                    if response_result.get("failure"):
                        if response_result.get("failure").get("message"):
                            print("\n\n\n")
                            spinner.fail(f'[FAIL] {response_result.get("failure").get("message")}')
                            spinner.stop()
                            spinner.clear()
                            break

        text = f"[{count:.1f}s] Waiting for {exec_function_name} / {func_args} :: '{wait_state}' -> '{check_state}' , {error_msg}"
        spinner.start(text=text)

        if logger and hasattr(logger, "info"):
            logger.info(f"[SR] {text}")

        try:
            assert time.time() < start_time + timeout_limit
        except AssertionError:
            text = f"[{count:.1f}s] [{timeout_limit}s Timeout] Waiting for {exec_function_name} / '{func_args}' :: '{wait_state}' -> {check_state} , {error_msg}"
            spinner.start(text=text)

            if logger and hasattr(logger, "error"):
                logger.info(f"[SR] {text}")

        count = count + increase_sec
        time.sleep(increase_sec)

        spinner.stop()

    if logger and hasattr(logger, "info"):
        logger.info(f"[SR] [DONE] {act_desc}")

    if health_status:
        return response


def run_with_keyboard_interrupt(command, *args, **kwargs):
    """
    run with KeyboardInterrupt
    :param command:
    :param args:
    :param kwargs:
    :return:


    Example:

        .. code-block:: python

            from pawnlib.utils.operate_handler import run_with_keyboard_interrupt

            run_with_keyboard_interrupt(run_func, args, kwargs)


    """
    try:
        if callable(command):
            command(*args, **kwargs)
        else:
            pawn.console.print(f"\n[red] {command} not callable ")
    except KeyboardInterrupt:
        pawn.console.print(f"\n\n[red] ^C KeyboardInterrupt - {command.__name__}{str(args)[:-1]}{kwargs}) \n")


def handle_keyboard_interrupt_signal():
    import signal

    def handle_ctrl_c(_signal, _frame):
        pawn.console.rule(f"[red] KeyboardInterrupt, Going down! Signal={_signal}")
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_ctrl_c)
