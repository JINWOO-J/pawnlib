#!/usr/bin/env python3
import sentry_sdk
from pawnlib.config import pawnlib_config as pawn
# from pawnlib.output import dump, get_script_path, debug_logging


__version = "0.0.1"


sentry_sdk.init(
    dsn="https://7084e062dab3203866ecab4bedfb6061@o406458.ingest.sentry.io/4505633932181504",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,

    # Alternatively, to control sampling dynamically
    # profiles_sampler=profiles_sampler
)


def print_banner():
    print('[97m')
    print('--------------------------------------------------')
    print('\n')
    print('                                                                            ')
    print('                   _                      _                                 ')
    print('  ___ _____ ____ _| |_  ____ _   _      _| |_  ____ _____  ____ _____  ____ ')
    print(' /___) ___ |  _ (_   _)/ ___) | | |    (_   _)/ ___|____ |/ ___) ___ |/ ___)')
    print('|___ | ____| | | || |_| |   | |_| |______| |_| |   / ___ ( (___| ____| |  _ ')
    print('(___/|_____)_| |_| \__)_|    \__  (_______)__)_|   \_____|\____)_____)_| (_)')
    print('                            (____/                                          ')
    print('             ')
    print('             ')
    print(' ____  _   _ ')
    print('|  _ \| | | |')
    print('| |_| | |_| |')
    print('|  __/ \__  |')
    print('|_|   (____/ ')
    print('')
    print(' - Description : This is script')
    print(' - Version     : {__version}')
    print(' - Author      : root')
    print('\n')
    print('--------------------------------------------------')
    print('[0m')


def main():
    app_name = "sentry_tracer.py"
    log_time_format = '%Y-%m-%d %H:%M:%S.%f'
    # current_path = get_script_path(__file__)
    stdout = True
    pawn.set(
        # PAWN_PATH=current_path,
        PAWN_LOGGER=dict(
            log_level="INFO",
            stdout_level="INFO",
            # log_path=f"{current_path}/logs",
            stdout=stdout,
            use_hook_exception=True,
        ),
        # PAWN_TIME_FORMAT=log_time_format,
        # PAWN_CONSOLE=dict(
        #     redirect=True,
        #     record=True
        # ),
        PAWN_DEBUG=True, # Don't use production, because it's not stored exception log.
        app_name=app_name,
        data={}
    )


    # pawn.app_logger.info("App logger initializing")
    # pawn.error_logger.debug("Debug logger initializing")
    # # pawn.error_logger.error("Error logger initializing")
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
        pawn.console.print_exception(
            show_locals=pawn.get("PAWN_DEBUG", False),
            width=160
        )

