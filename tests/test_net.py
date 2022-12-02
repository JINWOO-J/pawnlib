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


class TestNetworkUtils(unittest.TestCase):
    sock = None
    interface = "0.0.0.0"
    port = 9899

    def setUp(self) -> None:
        """
        Preparing works for each TestCase
        :return:
        """
        self.sock = listen_socket(self.interface, self.port)

    def test_wait_for(self):

        WaitStateLoop(
            loop_function=partial(check_port, self.interface, self.port),
            exit_function=lambda result: result,
            timeout=10,
            delay=1,
            text="checking port"
        ).run()

        self.assertEqual(True, True)

    def test_wait_for2(self):
        res = wait_for_port_open(self.interface, self.port)
        self.assertEqual(res, True)

    def test_wait_for3(self):
        with pawn.console.status("[bold green]Working on tasks...") as status:
            _port = 9890
            while True:
                time.sleep(0.1)
                status.update(f"checking {_port}")
                if check_port(self.interface, _port):
                    status.stop()
                    pawn.console.log(f"Done, {_port}")
                    break
                _port += 1

    def tearDown(self) -> None:
        self.sock.close()

