#!/usr/bin/env python3
from pawnlib.config import pawnlib_config as pawn
from pawnlib.output import dump, get_script_path, debug_logging


__version = "0.0.1"


def print_banner():
    print(f'[97m')
    print(f'--------------------------------------------------')
    print(f'\n')
    print(f'                                           _         _                         ')
    print(f'               _                          | |       | |                        ')
    print(f' _____ _   _ _| |_ _____  ____ ____  _____| |       | | ___   ____  ____ _____ ')
    print(f'| ___ ( \ / |_   _) ___ |/ ___)  _ \(____ | |       | |/ _ \ / _  |/ _  | ___ |')
    print(f'| ____|) X (  | |_| ____| |   | | | / ___ | | ______| | |_| ( (_| ( (_| | ____|')
    print(f'|_____|_/ \_)  \__)_____)_|   |_| |_\_____|\_|_______)_)___/ \___ |\___ |_____)')
    print(f'                                                            (_____(_____|      ')
    print(f'                                             ')
    print(f'          _                _                 ')
    print(f'  ____  _| |_ _____  ___ _| |_   ____  _   _ ')
    print(f' / ___)(_   _) ___ |/___|_   _) |  _ \| | | |')
    print(f'| |______| |_| ____|___ | | |_ _| |_| | |_| |')
    print(f'|_(_______)__)_____|___/   \__|_)  __/ \__  |')
    print(f'                                |_|   (____/ ')
    print(f'')
    print(f' - Description : This is script')
    print(f' - Version     : {__version}')
    print(f' - Author      : root')
    print(f'\n')
    print(f'--------------------------------------------------')
    print(f'[0m')


def main():
    app_name = "external_logger_test"
    log_time_format = '%Y-%m-%d %H:%M:%S.%f'
    current_path = get_script_path(__file__)
    stdout = True
    pawn.set(
        PAWN_PATH=current_path,
        PAWN_LOGGER=dict(
            log_level="DEBUG",
            stdout_level="DEBUG",
            log_path=f"{current_path}/logs",
            stdout=stdout,
            use_hook_exception=True,
        ),
        PAWN_TIME_FORMAT=log_time_format,
        PAWN_CONSOLE=dict(
            redirect=True,
            record=True
        ),
        PAWN_DEBUG=True, # Don't use production, because it's not stored exception log.
        app_name=app_name,
        data={}
    )

    pawn.app_logger.info("App logger initializing")
    pawn.error_logger.debug("Debug logger initializing")
    pawn.error_logger.error("Error logger initializing")
    pawn.console.log(pawn.to_dict())

    debug_logging(pawn.to_dict())
    dump(pawn.to_dict())
    import iconsdk
    iconsdk.logger = pawn.app_logger
    from iconsdk.utils import set_logger
    set_logger('DEBUG')
    from iconsdk.wallet.wallet import KeyWallet
    wallet = KeyWallet.create()


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

