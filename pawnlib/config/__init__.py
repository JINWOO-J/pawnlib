from .globalconfig import (
    ConfigHandler,
    nestednamedtuple,
    PawnlibConfig,
    pawnlib_config,
    global_verbose,
    NestedNamespace,
    pawn,
    pconf,
    create_pawn
)
from .first_run_checker import FirstRunChecker, one_time_run
from .logging_config import (
    ConsoleLoggerAdapter,
    setup_logger,
    getPawnLogger,
    setup_app_logger,
    add_logger,
    get_logger,
    LoggerMixin,
    change_log_level,
    change_propagate_setting,
    LoggerMixinVerbose,
    LoggerFactory,
    create_app_logger
)

# TODO: improve test
# from .globalconfig import (
#     ConfigHandler,
#     nestednamedtuple,
#     PawnlibConfig,
#     pawnlib_config,
#     global_verbose,
#     NestedNamespace,
#     # pawn,
#     # pconf,

#     pawn as pawn_legacy,
#     pconf as pconf_legacy,
#     #
#     create_pawn
# )

# from .improved_globalconfig import (
#     ImprovedPawnlibConfig,
#     improved_pawnlib_config,
#     pawn_improved,
#     pconf_improved,
#     create_improved_config,
#     ThreadSafeConfigManager,
#     ConfigState,
#     PawnlibConfigSchema
# )

# # Configuration constants for easy transition between legacy and new code
# USE_IMPROVED_CONFIG = False  # Set to False to use legacy config

# if USE_IMPROVED_CONFIG:
#     # pawn = pawn_legacy
#     # pconf = pconf_legacy

#     pawn = pawn_improved
#     pconf = pconf_improved
# else:
#     pawn = pawn_legacy
#     pconf = pconf_legacy

# from .first_run_checker import FirstRunChecker, one_time_run
# from .logging_config import (
#     ConsoleLoggerAdapter,
#     setup_logger,
#     getPawnLogger,
#     setup_app_logger,
#     add_logger,
#     get_logger,
#     LoggerMixin,
#     change_log_level,
#     change_propagate_setting,
#     LoggerMixinVerbose,
#     LoggerFactory,
#     create_app_logger
# )
#
