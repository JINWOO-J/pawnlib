# ♟️ Pawnlib

A collection of libraries that can be used like pawns on a chessboard.
Pawnlib is a collection of libraries for IaC.

It provides a collection of utility functions and classes that aim to enhance productivity and streamline code development. The library is particularly useful for developers looking to reduce repetitive coding patterns and improve code readability.

utils, globals vars, logging, http, network, pretty printing, resource, converter ...


[![Build Docker Images](https://github.com/JINWOO-J/pawnlib/actions/workflows/docker-push.yml/badge.svg)](https://github.com/JINWOO-J/pawnlib/actions/workflows/docker-push.yml)
[![Docs](https://github.com/JINWOO-J/pawnlib/actions/workflows/docs-publish.yml/badge.svg)](https://github.com/JINWOO-J/pawnlib/actions/workflows/docs-publish.yml)
[![pages-build-deployment](https://github.com/JINWOO-J/pawnlib/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/JINWOO-J/pawnlib/actions/workflows/pages/pages-build-deployment)

[![PyPI version](https://badge.fury.io/py/pawnlib.svg)](https://badge.fury.io/py/pawnlib)

<p align="center">
	<img src="https://img.shields.io/github/last-commit/JINWOO-J/pawnlib?style=default&logo=git&logoColor=white&color=0080ff" alt="last-commit">
	<img src="https://img.shields.io/github/languages/top/JINWOO-J/pawnlib?style=default&color=0080ff" alt="repo-top-language">
	<img src="https://img.shields.io/github/languages/count/JINWOO-J/pawnlib?style=default&color=0080ff" alt="repo-language-count">
<p>


### Installing pawnlib
- **Installing pawnlib**

pawnlib is available on PyPI:

```
pip3 install pawnlib

```

pawnlib with wallet is available on PyPI:

```
pip3 install pawnlib[wallet]

```

## Global Config
-  **Global Config**

You can use the global config. 

```python
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output import *


def main():
    current_path = get_script_path(__file__)
    log_time_format = '%Y-%m-%d %H:%M:%S.%f'
    app_name = "default_app"
    stdout = True
    pawn.set(
        PAWN_PATH=current_path,        
        PAWN_TIME_FORMAT=log_time_format,
        PAWN_LOGGER=dict(
            log_level="INFO",
            stdout_level="INFO",
            log_path=f"{current_path}/logs",
            stdout=stdout,
            use_hook_exception=True,
        ),
        PAWN_CONSOLE=dict(
            redirect=True,
            record=True,
            log_time_format=f"%Y-%m-%d %H:%M:%S.%f",
        ),
        PAWN_DEBUG=True, # Don't use production, because it's not stored exception log.
        PAWN_VERBOSE=3,
        app_name=app_name,
        app_data={},
    )
    
    pawn.console.log("START APP")
    pawn.console.log(pawn.to_dict())

```
### pawns

`pawns` CLI supports the following commands: icon, server, proxy, net, top, docker, aws, rpc, http, gs, init, info, banner, websocket, wallet.


```
$ pawns 
--------------------------------------------------

__________  _____  __      _________    _________
\______   \/  _  \/  \    /  \      \  /   _____/
 |     ___/  /_\  \   \/\/   /   |   \ \_____  \
 |    |  /    |    \        /    |    \/        \
 |____|  \____|__  /\__/\  /\____|__  /_______  /
                 \/      \/         \/        \/

 - Description :
 - Version     : 2.0.15
 - Author      : jinwoo

--------------------------------------------------


The pawns is designed to serve as the main command-line interface (CLI)

optional arguments:
  -h, --help            show this help message and exit


sub-module:
  {icon,server,proxy,net,top,docker,aws,rpc,http,gs,init,info,banner,websocket,wallet}
    icon                icon module
    server              This command is used to check and verify the server’s resources.
    proxy               A Proxy Reflector Tool
    net                 This is a tool to measure your server's resources.
    top                 This is a tool to measure your server's resources.
    docker              docker module
    aws                 Get meta information from AWS EC2.
    rpc                 This tool uses JSON remote procedure calls, or RPCs, commonly used on the ICON blockchain.
    http                This is a tool to measure RTT on HTTP/S requests.
    gs                  Genesis Tool
    init                Advanced Python application builder: Easily initialize your Python development environment with
                        customizable templates and best practices.
    info                This command displays server resource information.
    banner              Command to test the banner.
    websocket           Connect to the Goloop network with WebSocket to receive blocks.
    wallet              A tool for managing ICON wallets. It supports creating new wallets and loading existing ones.
```



### app builder 
- **app builder** 

You can create a simple application based on pawnlib with the command below.


```bash

$ pawns init
[10:35:21,837] main_cli wrapper                                                                                               main_cli.py:117
[10:35:21,840] args = Namespace(proxy=None, init=Namespace(command='init')), command = init                                   main_cli.py:119

--------------------------------------------------


___.         .__.__       .___
\_ |__  __ __|__|  |    __| _/___________
 | __ \|  |  \  |  |   / __ |/ __ \_  __ \
 | \_\ \  |  /  |  |__/ /_/ \  ___/|  | \/
 |___  /____/|__|____/\____ |\___  >__|
     \/                    \/    \/

 - Description : Initialize Python Development Environment
 - Version     : 0.0.28
 - Author      : jinwoo


--------------------------------------------------

PWD = /Users/jinwoo/work/python_prj/pawnlib


What's your python3 app name? (default_app):
What's your name? (jinwoo):
Please explain this script. (This is script):
Project directory => /Users/jinwoo/work/python_prj/pawnlib ? [y/n] (y):
Do you want to logger? [y/n] (y):
Do you want to daemon? [y/n] (n):
```


### simple reflector proxy
- **simple reflector proxy**

Simple Python HTTP Server which reflects the client HTTP request header in server logs to see the header fields forwarded by web servers. 


```bash

$ pawns proxy -l 8080 -f 127.0.0.1:8200
[10:34:33,898] main_cli wrapper                                                                                               main_cli.py:117
[10:34:33,902] args = Namespace(proxy=Namespace(listen='8080', forward='127.0.0.1:8200', buffer_size=4096, delay=0.0001,      main_cli.py:119
               timeout=3), init=None), command = proxy

--------------------------------------------------



_____________  _______  ______.__.
\____ \_  __ \/  _ \  \/  <   |  |
|  |_> >  | \(  <_> >    < \___  |
|   __/|__|   \____/__/\_ \/ ____|
|__|                     \/\/
                _____.__                 __
_______   _____/ ____\  |   ____   _____/  |_  ___________
\_  __ \_/ __ \   __\|  | _/ __ \_/ ___\   __\/  _ \_  __ \
 |  | \/\  ___/|  |  |  |_\  ___/\  \___|  | (  <_> )  | \/
 |__|    \___  >__|  |____/\___  >\___  >__|  \____/|__|
             \/                \/     \/

 - Description : proxy reflector
 - Version     : 0.0.28
 - Author      : jinwoo


--------------------------------------------------

[10:34:33,904] args = Namespace(listen='8080', forward='127.0.0.1:8200', buffer_size=4096, delay=0.0001, timeout=3)              proxy.py:173
[10:34:33,905] Listen 0.0.0.0:8080 => Forward 127.0.0.1:8200

```

### httping
- **httping**

`http` module offers a streamlined and efficient way to perform HTTP requests and handle responses.

```bash

$ pawns http

--------------------------------------------------


.__     __    __         .__
|  |___/  |__/  |_______ |__| ____    ____
|  |  \   __\   __\____ \|  |/    \  / ___\
|   Y  \  |  |  | |  |_> >  |   |  \/ /_/  >
|___|  /__|  |__| |   __/|__|___|  /\___  /
     \/           |__|           \//_____/

 - Description : This is a tool to measure RTT on HTTP/S requests.
 - base_dir    : /Users/jinwoo/work/python_prj/pawnlib
 - logs_dir    : /Users/jinwoo/work/python_prj/pawnlib/logs

 - Version     : 1.0.84
 - Author      : jinwoo


--------------------------------------------------

[11:25:46,975] Invalid url: name=default, url=
usage: local_cli.py [-h] [-c CONFIG_FILE] [-v] [-q] [-i INTERVAL] [-m METHOD] [-t TIMEOUT] [-b BASE_DIR] [--success SUCCESS [SUCCESS ...]]
                    [--logical-operator {and,or}] [--ignore-ssl IGNORE_SSL] [-d DATA] [--headers HEADERS] [-w WORKERS] [--stack-limit STACK_LIMIT]
                    [--dynamic-increase-stack-limit DYNAMIC_INCREASE_STACK_LIMIT] [--slack-url SLACK_URL] [--log-level LOG_LEVEL] [-bk BLOCKHEIGHT_KEY]
                    [--dry-run]
                    [url]

httping

positional arguments:
  url                   URL to be checked


optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Path to the configuration file. Defaults to "config.ini".
  -v, --verbose         Enables verbose mode. Higher values increase verbosity level. Default is 1.
  -q, --quiet           Enables quiet mode. Suppresses all messages. Default is 0.
  -i INTERVAL, --interval INTERVAL
                        Interval time in seconds between checks. Default is 1 second.
  -m METHOD, --method METHOD
                        HTTP method to use (e.g., GET, POST). Default is "GET".
  -t TIMEOUT, --timeout TIMEOUT
                        Timeout in seconds for each HTTP request. Default is 10 seconds.
  -b BASE_DIR, --base-dir BASE_DIR
                        Base directory for httping operations. Default is the current working directory.
  --success SUCCESS [SUCCESS ...]
                        Criteria for success. Can specify multiple criteria. Default is ["status_code==200"].
  --logical-operator {and,or}
                        Logical operator for evaluating success criteria. Choices are "and", "or". Default is "and".
  --ignore-ssl IGNORE_SSL
                        Ignores SSL certificate validation if set to True. Default is True.
  -d DATA, --data DATA  Data to be sent in the HTTP request body. Expected in JSON format. Default is an empty dictionary.
  --headers HEADERS     HTTP headers to be sent with the request. Expected in JSON format. Default is an empty dictionary.
  -w WORKERS, --workers WORKERS
                        Maximum number of worker processes. Default is 10.
  --stack-limit STACK_LIMIT
                        Error stack limit. Default is 5.
  --dynamic-increase-stack-limit DYNAMIC_INCREASE_STACK_LIMIT
                        Dynamically increases the error stack limit if set to True. Default is True.
  --slack-url SLACK_URL
                        URL for sending notifications to Slack. Optional.
  --log-level LOG_LEVEL
                        Log level.
  -bk BLOCKHEIGHT_KEY, --blockheight-key BLOCKHEIGHT_KEY
                        JSON key to extract the blockheight information, e.g., 'result.sync_info.latest_block_height'. The script will check if the blockheight at
                        this path is increasing.
  --dry-run             Executes a dry run without making actual HTTP requests. Default is False.

This script provides various options to check the HTTP status of URLs.

Usage examples:
  1. Basic usage:
        pawns http https://example.com

  2. Verbose mode:
        pawns http https://example.com -v

  3. Using custom headers and POST method:
        pawns http https://example.com -m POST --headers '{"Content-Type": "application/json"}' --data '{"param": "value"}'

  4. Ignoring SSL verification and setting a custom timeout:
        pawns http https://example.com --ignore-ssl True --timeout 5

  5. Checking with specific success criteria and logical operator:
        pawns http https://example.com --success 'status_code==200' 'response_time<2' --logical-operator and

  6. Running with a custom config file and interval:
        pawns http https://example.com -c http_config.ini -i 3

    http_config.ini
    [default]
    success = status_code==200
    slack_url =
    interval = 3
    method = get
    ; data = sdsd
    data = {"sdsd": "sd222sd"}

    [post]
    url = http://httpbin.org/post
    method = post

    [http_200_ok]
    url = http://httpbin.org/status/200
    success = status_code==200

    [http_300_ok_and_2ms_time]
    url = http://httpbin.org/status/300
    success = ['status_code==300', 'response_time<0.02']

    [http_400_ok]
    url = http://httpbin.org/status/400
    success = ["status_code==400"]


  7. Setting maximum workers and stack limit:
        pawns http https://example.com -w 5 --stack-limit 10

  8. Dry run without actual HTTP request:
        pawns http https://example.com --dry-run

  9. Sending notifications to a Slack URL on failure:
        pawns http https://example.com --slack-url 'https://hooks.slack.com/services/...'

 10. Checking blockheight increase:
        pawns http http://test-node-01:26657/status --blockheight-key "result.sync_info.latest_block_height" -i 5

```

Officially supports Python 3.9+.

### Documentation

Documentation and tutorials are available at https://pawnlib.readthedocs.io
