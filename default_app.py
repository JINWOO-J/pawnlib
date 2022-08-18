#!/usr/bin/env python3
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.log import AppLogger
from pawnlib.output import *
import sys
import time
from pawnlib.utils.operate_handler import Daemon


__version = "0.0.1"


def print_banner():
    print(f'[97m')
    print(f'--------------------------------------------------')
    print(f'\n')
    print(f'     _          ___             _                                 ')
    print(f'    | |        / __)           | |  _                             ')
    print(f'  __| |_____ _| |__ _____ _   _| |_| |_         _____ ____  ____  ')
    print(f' / _  | ___ (_   __|____ | | | | (_   _)       (____ |  _ \|  _ \ ')
    print(f'( (_| | ____| | |  / ___ | |_| | | | |_ _______/ ___ | |_| | |_| |')
    print(f' \____|_____) |_|  \_____|____/ \_) \__|_______)_____|  __/|  __/ ')
    print(f'                                                     |_|   |_|    ')
    print(f'')
    print(f' - Description : This is script')
    print(f' - Version     : {__version}')
    print(f' - Author      : jinwoo')
    print(f'\n')
    print(f'--------------------------------------------------')
    print(f'[0m')


def main():
    LOG_DIR = f"{get_real_path(__file__)}/logs"
    APP_NAME = "default_app"
    STDOUT = True
    pawn.set(
        PAWN_LOGGER=dict(
            log_level="INFO",
            stdout_level="INFO",
            log_path=LOG_DIR,
            stdout=STDOUT,
            use_hook_exception=True,
        ),
        PAWN_DEBUG=True, # Don't use production, because it's not stored exception log.
        app_name=APP_NAME,
        app_data={}
    )

    pawn.app_logger.info("App logger initializing")
    pawn.error_logger.debug("Debug logger initializing")
    pawn.error_logger.error("Error logger initializing")
    pawn.console.log(pawn.to_dict())

    debug_logging(pawn.to_dict())
    dump(pawn.to_dict())

    while True:
        # MainLoop
        print("This is Daemon")
        time.sleep(1)
    


if __name__ == "__main__":
    try:
        print_banner()
        if len(sys.argv) != 2:
            print("command not found [start/stop]")
            sys.exit()
        command = sys.argv[1]
        daemon = Daemon(
            pidfile="/tmp/default_app.pid",
            func=main
        )
        if command == "start":
            daemon.start()
        elif command == "stop":
            daemon.stop()
        else:
            print("command not found [start/stop]")
    except KeyboardInterrupt:
        pawn.console.log("Keyboard Interrupted")
