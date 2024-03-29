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


    def test_wait_for2(self):
        res = wait_for_port_open(self.interface, self.port)
        self.assertTrue(res)

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


class TestConnectHttp(unittest.TestCase):
    sock = None
    interface = "0.0.0.0"
    port = 9899

    def test_wait_for(self):
        url_dict = {
            "https://httpbin.org": True,
            "http://httpbin.org": True,
            "https://httpbin.org:2222": False,
            "httpbin.org:80": True,
            "httpbin.org:443": True,
        }

        for url, expected_value in url_dict.items():
            res = check_port(url, timeout=1)
            pawn.console.log(f"url={url}, expected={expected_value}, res={res}")
            self.assertEqual(check_port(url), expected_value)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNetworkUtils)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
