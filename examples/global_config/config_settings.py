import common
from pawnlib.config.globalconfig import *
from dotenv import dotenv_values, find_dotenv

# load_dotenv(find_dotenv())

dotenv_path = find_dotenv()


config = dotenv_values(dotenv_path)

print(config)





# from pawnlib.utils.log import AppLogger

# pawnlib_config.make_config(a="bbb", b="asdasdas")
# pawnlib_config.put_config(b="bb")
# print(f"main = {pawnlib_config.conf()}")
#
#
# app_logger, error_logger = AppLogger(app_name="global_config_test").get_logger()
# make_config(
#     hello="world",
#     app_logger=app_logger,
#     error_logger=error_logger
# )
#
# print(f"[config_settings] conf() {conf()}")
# print(f"[config_settings] {config()}")


# app_logger, error_logger = AppLogger().get_logger()
