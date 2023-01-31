"""Module that helps integrating with rich library."""
import os
import sys
import inspect
from typing import Any, TextIO

import rich.console as rich_console
from rich.ansi import AnsiDecoder
from rich.file_proxy import FileProxy


class Console(rich_console.Console):
    """Extends rich Console class."""

    def __init__(self, *args: str, redirect: bool = True, pawn_debug: bool = False, **kwargs: Any) -> None:
        """
        enrich console does soft-wrapping by default and this diverge from
        original rich console which does not, creating hard-wraps instead.
        """
        self.redirect = redirect
        self.pawn_debug = pawn_debug

        if "soft_wrap" not in kwargs:
            kwargs["soft_wrap"] = True

        # Unless user already mentioning terminal preference, we use our
        # heuristic to make an informed decision.z
        if "force_terminal" not in kwargs:
            kwargs["force_terminal"] = should_do_markup(
                stream=kwargs.get("file", sys.stdout)
            )

        super().__init__(*args, **kwargs)
        self.extended = True

        if self.redirect:
            if not hasattr(sys.stdout, "rich_proxied_file"):
                sys.stdout = FileProxy(self, sys.stdout)  # type: ignore
            if not hasattr(sys.stderr, "rich_proxied_file"):
                sys.stderr = FileProxy(self, sys.stderr)  # type: ignore

    # https://github.com/python/mypy/issues/4441
    def print(self, *args, **kwargs) -> None:  # type: ignore
        """Print override that respects user soft_wrap preference."""
        # Currently rich is unable to render ANSI escapes with print so if
        # we detect their presence, we decode them.
        # https://github.com/willmcgugan/rich/discussions/404
        if args and isinstance(args[0], str) and "\033" in args[0]:
            text = format(*args) + "\n\n"
            decoder = AnsiDecoder()
            args = list(decoder.decode(text))  # type: ignore
        super().print(*args, **kwargs)

    def debug(self, message, *args, **kwargs) -> None:  # type: ignore
        if self.pawn_debug:
            stack = inspect.stack()
            parent_frame = stack[1][0]
            module = inspect.getmodule(parent_frame)
            function_name = stack[1][3]
            class_name = ''
            if module:
                try:
                    class_name = stack[1][0].f_locals["self"].__class__.__name__+"."
                except:
                    pass
            full_module_name = f"{class_name}{function_name}()"

            message = f"[yellow][DEBUG][/yellow]:face_with_monocle: {full_module_name} {message}"

            if not kwargs.get("_stack_offset", None):
                kwargs['_stack_offset'] = 2
            super().log(message, *args, **kwargs)


def should_do_markup(stream: TextIO = sys.stdout) -> bool:
    """Decide about use of ANSI colors."""
    py_colors = None

    # https://xkcd.com/927/
    for env_var in ["PY_COLORS", "CLICOLOR", "FORCE_COLOR", "ANSIBLE_FORCE_COLOR"]:
        value = os.environ.get(env_var, None)
        if value is not None:
            py_colors = _str2bool(value)
            break

    # If deliverately disabled colors
    if os.environ.get("NO_COLOR", None):
        return False

    # User configuration requested colors
    if py_colors is not None:
        return _str2bool(py_colors)

    term = os.environ.get("TERM", "")
    if "xterm" in term:
        return True

    if term == "dumb":
        return False

    # Use tty detection logic as last resort because there are numerous
    # factors that can make isatty return a misleading value, including:
    # - stdin.isatty() is the only one returning true, even on a real terminal
    # - stderr returting false if user user uses a error stream coloring solution
    return stream.isatty()

def _str2bool(v):
    """
    This function is intended to return a boolean value.

    :param v:
    :return:
    """
    true_list = ("yes", "true", "t", "1", "True", "TRUE")
    if type(v) == bool:
        return v
    if type(v) == str:
        return v.lower() in true_list
    return eval(f"{v}") in true_list
