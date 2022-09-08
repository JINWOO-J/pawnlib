#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass

from functools import partial
from pawnlib.resource.net import *
from pawnlib.utils.operate_handler import *
from pawnlib.config import pawnlib_config as pawn

interface = "0.0.0.0"
port = 9899
sock = listen_socket(interface, port)


# while True:
#     time.sleep(1)
#     check_result = check_port(interface, port)
#     pawn.console.log(f"check_result={check_result}, sock={sock}")
#     if check_result:
#         break

# spin_text = "sdsd"
# with Spinner(text=spin_text):
#     time.sleep(10)
pawn.console.rule("[bold red] wait for 1")

WaitStateLoop(
    loop_function=partial(check_port, interface, port),
    exit_function=lambda result: result,
    timeout=10,
    delay=1,
    text="checking port"
).run()

pawn.console.rule("[bold red] wait for 2")

wait_for_port_open(interface, port)

pawn.console.rule("[bold red] wait for 3")

with pawn.console.status("[bold green]Working on tasks...") as status:
    _port = 9850
    while True:
        time.sleep(0.1)
        status.update(f"checking {_port}")
        if check_port(interface, _port):
            status.stop()
            pawn.console.log(f"Done, {_port}")
            break
        _port += 1
