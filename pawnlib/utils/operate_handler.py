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
from typing import Callable, List, Dict

from pawnlib.output import *
from pawnlib import typing
from functools import wraps

from pawnlib.config.globalconfig import pawnlib_config as pawn
from typing import Union


class Daemon(object):
    """
    A generic daemon class.
    Usage 1: subclass the Daemon class and override the run() method
    Usage 2: subclass the Daemon class and use func parameter

    :param pidfile: pid file location
    :param func:
    :param stdin:
    :param stdout:
    :param stderr:
    :param home_dir:
    :param umask:
    :param verbose:
    :param use_gevent:
    :param use_eventlet:

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

    def __init__(self, pidfile, func=None, stdin=os.devnull,
                 stdout=os.devnull, stderr=os.devnull,
                 home_dir='.', umask=0o22, verbose=1,
                 use_gevent: bool = False, use_eventlet: bool = False):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
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
            si = open(self.stdin, 'r')
            so = open(self.stdout, 'a+')
            if self.stderr:
                try:
                    se = open(self.stderr, 'a+', 0)
                except ValueError:
                    # Python 3 can't have unbuffered text I/O
                    se = open(self.stderr, 'a+', 1)
            else:
                se = so
            os.dup2(si.fileno(), sys.stdin.fileno())
            os.dup2(so.fileno(), sys.stdout.fileno())
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
            # module_name = module_pieces[-1].capitalize()
            # cprint(module_name, "red")
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
        # module = __import__(f"lib.{module_name}", fromlist=["lib", "..", "."])
        module = __import__(f"{module_name}")
        func = getattr(module, function_name)
        return func()
    return globals()[module_func]()


def run_execute(text=None, cmd=None, cwd=None, check_output=True, capture_output=True, hook_function=None, debug=False, **kwargs):
    """
    Helps run commands

    :param text: just a title name
    :param cmd: command to be executed
    :param cwd: the function changes the working directory to cwd
    :param check_output:
    :param capture_output:
    :param hook_function:
    :param debug:
    :return:
    """

    if cmd is None:
        cmd = text

    start = time.time()

    result = dict(
        stdout=[],
        stderr=None,
        return_code=0,
        line_no=0
    )

    if text != cmd:
        text = f"text='{text}', cmd='{cmd}' :: "
    else:
        text = f"cmd='{cmd}'"

    # if check_output:
    #     # cprint(f"[START] run_execute(), {text}", "green")
    #     cfg.logger.info(f"[START] run_execute() , {text}")
    try:
        # process = subprocess.run(cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        process = subprocess.Popen(cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, shell=True)

        for line in process.stdout:
            line_striped = line.strip()
            if line_striped:
                if callable(hook_function):
                    if hook_function == print:
                        print(f"[{result['line_no']}] {line_striped}")
                    else:
                        hook_function(line=line_striped, line_no=result['line_no'], **kwargs)

                if capture_output:
                    result["stdout"].append(line_striped)
                result['line_no'] += 1

        out, err = process.communicate()

        if process.returncode:
            result["return_code"] = process.returncode
            result["stderr"] = err.strip()

    except Exception as e:
        result['stderr'] = e
        raise OSError(f"Error while running command cmd='{cmd}', error='{e}'")

    end = round(time.time() - start, 3)

    if check_output:
        if result.get("stderr"):
            # cprint(f"[FAIL] {text}, Error = '{result.get('stderr')}'", "red")
            pawn.error_logger.info(f"[FAIL] {text}, Error = '{result.get('stderr')}'") if pawn.error_logger else False
        else:
            # cprint(f"[ OK ] {text}, timed={end}", "green")
            pawn.app_logger.info(f"[ OK ] {text}, timed={end}") if pawn.app_logger else False
    return result


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

        self.spinner = itertools.cycle(['-', '/', '|', '\\'])
        self.delay = delay
        self.busy = False
        self.spinner_visible = False
        self.text = text
        self._screen_lock = None
        self.thread = None
        self.spin_message = ""
        # self.line_up = '\033[1A'
        self.line_up = '\x1b[1A'
        self.line_clear = '\x1b[2K'

        if type(sys.stdout).__name__ == "FileProxy":
            # self._sys_stdout = sys.stdout.rich_proxied_file
            self._sys_stdout = getattr(sys.stdout, "rich_proxied_file", sys.stdout)
        else:
            self._sys_stdout = sys.stdout

    def title(self, text=None):
        print(end=self.line_up)
        self.text = text

    def write_next(self):
        with self._screen_lock:
            if not self.spinner_visible:
                if self.text:
                    self.spin_message = f"{self.text} ... {next(self.spinner)}"
                else:
                    self.spin_message = next(self.spinner)
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

    def stop(self):
        self.busy = False
        self.remove_spinner(cleanup=True)

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
                spinner.title(f"{error_text}[{count}]{spin_text}: result={result}, is_success={is_success}, {elapsed} secs passed")
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
    # if type(func_args) is str:
    if isinstance(func_args, str):
        tmp_args = ()
        tmp_args = tmp_args + (func_args,)
        func_args = tmp_args

    exec_function_name = exec_function.__name__
    # classdump(exec_function.__qualname__)
    # print(exec_function.__qualname__)
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

        if force_dict:
            if isinstance(response.get("json"), list):
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

    # return {
    #     "elapsed": time.time() - start_time,
    #     "json": response.get("json"),
    #     "status_code": response.get("status_code", 0),
    # }


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
