#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass

from parameterized import parameterized
from devtools import debug
from pawnlib.typing import converter
import os
import random
from parameterized import parameterized

from pawnlib.output import *
from pawnlib.utils.log import *

from socketserver import ThreadingMixIn
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading
import time
import requests
from pawnlib.resource.net import *
import json


class MyRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/check':
            self.response = {
                "result": "OK"
            }
            self.protocol_version = 'HTTP/1.1'
            self.send_response(200, 'OK')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            # self.wfile.write(bytes(json.dumps(self.response)))
            self.wfile.write(bytes(json.dumps(self.response), "utf-8"))
            # self.path = '/'
            return
            # return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


class ThreadingChecker(object):
    """ Threading example class
    The run() method will be started and it will run in the background
    until the application exits.
    """

    def __init__(self, ipaddr=None, port=None, interval=1):
        """ Constructor
        :type interval: int
        :param interval: Check interval, in seconds
        """
        self.interval = interval
        self.ipaddr = ipaddr
        self.port = port
        self.count = 0
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

    def run(self):
        """ Method that runs forever """
        while True:
            check_url = f"http://{self.ipaddr}:{self.port}/check"
            print(f'[{self.count}] Trying connect to {check_url}')
            self.count += 1
            time.sleep(self.interval)
            try:
                response = requests.get(f"{check_url}", verify=False, timeout=2)
                res_json = response.json().get("result", "")
            except Exception as e:
                res_json = "FAIL"
                print(f"[FAIL] Cant accessible - {self.ipaddr}:{self.port} -> {e}")
            if res_json == "OK":
                print(f"[OK] Accessible - {self.ipaddr}:{self.port}")
                os._exit(0)


interface = "0.0.0.0"
port = 9899

SimpleHTTPRequestHandler = MyRequestHandler
server = ThreadingSimpleServer((interface, port), SimpleHTTPRequestHandler)

# checker = ThreadingChecker(ipaddr=interface, port=port)

try:
    while True:
        sys.stdout.flush()
        check_result = check_port(interface, 9822)

        pawn.console.log(f"TRYING -->  {check_result}")

        server.handle_request()

except KeyboardInterrupt:
    print(' Finished.')


