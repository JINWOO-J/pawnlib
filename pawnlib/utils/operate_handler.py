import os
import sys
import time
import inspect
import errno
import signal
import atexit
import subprocess
from pawnlib.output import *
from pawnlib import typing
from functools import wraps

from pawnlib.config.globalconfig import pawnlib_config as pawn
from typing import Union


class Daemon(object):
    """
    A generic daemon class.
    Usage: subclass the Daemon class and override the run() method
    """

    def __init__(self, pidfile, func=None, stdin=os.devnull,
                 stdout=os.devnull, stderr=os.devnull,
                 home_dir='.', umask=0o22, verbose=1,
                 use_gevent=False, use_eventlet=False):
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
    if pawnlib_config.get('PAWN_VERBOSE', 0) > 0:
        cprint(f"[START] {full_module_name}", "green")


def job_done(error: str = '', full_module_name: str = '', elapsed: Union[float, int] = 0):
    title = get_inspect_module(full_module_name)
    if pawnlib_config.get('PAWN_VERBOSE', 0) > 0:
        if error == '':
            cprint(f"[DONE ] {title} {elapsed:.3f}sec", "green")
        else:
            cprint(" NOT DONE %s (%.3fsec)- %s" % (title, elapsed, error), "red")
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


