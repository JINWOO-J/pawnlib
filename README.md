# ♟️ Pawnlib

A collection of libraries that can be used like pawns on a chessboard.
Pawnlib is a collection of libraries for IaC.

utils, globals vars, logging, http, network, pretty printing, resource, converter ...


[![Build Docker Images](https://github.com/JINWOO-J/pawnlib/actions/workflows/docker-push.yml/badge.svg)](https://github.com/JINWOO-J/pawnlib/actions/workflows/docker-push.yml)
[![Docs](https://github.com/JINWOO-J/pawnlib/actions/workflows/docs-publish.yml/badge.svg)](https://github.com/JINWOO-J/pawnlib/actions/workflows/docs-publish.yml)
[![pages-build-deployment](https://github.com/JINWOO-J/pawnlib/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/JINWOO-J/pawnlib/actions/workflows/pages/pages-build-deployment)

[![PyPI version](https://badge.fury.io/py/pawnlib.svg)](https://badge.fury.io/py/pawnlib)



### Installing pawnlib

pawnlib is available on PyPI:

```
pip3 install pawnlib

```

pawnlib with wallet is available on PyPI:

```
pip3 install pawnlib[wallet]

```

### Global Config

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

### app builder 

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
Officially supports Python 3.9+.

### Documentation

Documentation and tutorials are available at https://docs.jinwoo.xyz
