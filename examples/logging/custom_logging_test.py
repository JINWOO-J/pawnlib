#!/usr/bin/env python3
import common
from pawnlib.config import pawnlib_config

from pawnlib.output import dump, get_real_path
from pawnlib.utils.log import AppLogger, CustomLog

from pawnlib.utils import http

import config_settings
import config_child


def main():
    log_dir = f"{get_real_path(__file__)}/logs"
    print(f"log_dir = {log_dir}")
    app_name = "logger"

    app_logger = CustomLog(app_name)

    app_logger.set_level("INFO")
    app_logger.stream_handler("INFO")
    app_logger.time_rotate_handler(filename=f"{log_dir}/custom_log",
                                   when="M",
                                   interval=2,
                                   backup_count=3,
                                   level="INFO"
                                   )
    pawnlib_config.set(
        PAWN_APP_LOGGER=app_logger.log,
        # PAWN_ERROR_LOGGER=error_logger,
        sdsdsd="sdsdsd"
    )

    pawnlib_config.set(
        sdsdsd="change"
    )

    dump(pawnlib_config)
    print(f"custom log main= {pawnlib_config.to_dict()}")
    dump(pawnlib_config)
    dump(pawnlib_config.to_dict())
    pawnlib_config.app_logger.info("Start Main()")
    print(config_child.logging_func())
    config_child.child_app_logging_func("sssss")
    http.jequest("INVALID_URL")


if __name__ == "__main__":
    main()
