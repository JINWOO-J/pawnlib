#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.config.logging_config import setup_app_logger, test_logger
from pawnlib.utils.log import AppLogger
from pawnlib.output import *
import logging

__version = "0.0.1"


def print_banner():
    print(f'[97m')
    print(f'--------------------------------------------------')
    print(f'\n')
    print(f'                         _                               ')
    print(f'                        | |                              ')
    print(f' _____ ____  ____       | | ___   ____  ____ _____  ____ ')
    print(f'(____ |  _ \|  _ \      | |/ _ \ / _  |/ _  | ___ |/ ___)')
    print(f'/ ___ | |_| | |_| |_____| | |_| ( (_| ( (_| | ____| |    ')
    print(f'\_____|  __/|  __(_______)_)___/ \___ |\___ |_____)_|    ')
    print(f'      |_|   |_|                 (_____(_____|            ')
    print(f'')
    print(f' - Description : This is script')
    print(f' - Version     : {__version}')
    print(f' - Author      : jinwoo')
    print(f'\n')
    print(f'--------------------------------------------------')
    print(f'[0m')


def main():
    setup_app_logger(log_type="both", log_level="debug", simple_format=True)


    logging.info("[red]aaaa[/red]")
    logging.debug("[red]aaaa[/red]")
    logging.debug("[red]----- aaaa")
    test_logger()

    # exit()
    # LOG_DIR = f"{get_real_path(__file__)}/logs"
    # APP_NAME = "app_logger"
    # STDOUT = True
    # pawn.set(
    #     PAWN_LOGGER=dict(
    #         log_level="INFO",
    #         stdout_level="INFO",
    #         log_path=LOG_DIR,
    #         stdout=STDOUT,
    #         use_hook_exception=True,
    #     ),
    #     PAWN_DEBUG=True, # Don't use production, because it's not stored exception log.
    #     app_name=APP_NAME,
    #     app_data={}
    # )
    #
    # pawn.app_logger.info("App logger initializing")
    # pawn.error_logger.debug("Debug logger initializing")
    # pawn.error_logger.error("Error logger initializing")
    # pawn.console.log(pawn.to_dict())
    #
    # debug_logging(pawn.to_dict())
    # dump(pawn.to_dict())




if __name__ == "__main__":
    try:
        print_banner()
        main()

    except KeyboardInterrupt:
        pawn.console.log("Keyboard Interrupted")

    except Exception as e:
        logging.error(f"Exception - {e}", stacklevel=3, exc_info=True)
