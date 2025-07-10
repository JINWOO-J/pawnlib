#!/usr/bin/env python3
import time
import common
from pawnlib.config import pawnlib_config as pawn, setup_logger, setup_app_logger
from pawnlib.typing.converter import HexConverter
from pawnlib.utils.http import AsyncIconRpcHelper
import asyncio

logger = setup_app_logger(log_level="debug", propagate=False)
logger.info("logger start")

async def main():
    async with AsyncIconRpcHelper(url="https://lisbon.net.solidwallet.io", max_concurrency=5, logger=logger) as rpc:

        task1 = rpc.get_last_blockheight()
        task2 = rpc.get_network_info()

        results = await asyncio.gather(task1, task2)

        pawn.console.log(results)

        last_blockheight = await rpc.get_last_blockheight()
        network_info = await rpc.get_network_info()
        pawn.console.log(f"last_blockheight={last_blockheight}, network_info={network_info}")


        res = await rpc.get_balance(address="hx191e87b17bc2265953677f1201653b00fe87881f")
        pawn.console.log(f"balance={res}")

    # 추가 비동기 작업 예시
    # balance = await icon_rpc.get_balance(address="hx5a05b58a25a1e5ea0f1d5715e1f655dffc1fb30a")
    # pawn.console.log(f"Balance: {balance} ICX")

if __name__ == "__main__":
    asyncio.run(main())




#
# res2 = icon_rpc.get_balance(address="hx5a05b58a25a1e5ea0f1d5715e1f655dffc1fb30a", is_comma=True)
# res3 = icon_rpc.get_tx(tx_hash="0x2175d5b307b657d1bada071d721b011462c0772e4ac3a4c9f9723a9f1f9de7c0", return_key="result")
# res4 = icon_rpc.rpc_call(method="icx_getTransactionByHash")
# # res3 = icon_rpc.get_tx(tx_hash="0x2175d5b307b657d1bada071d721b011462c0772e4ac3a4c9f9723a9f1f9de7c0")
# # res2 = icon_rpc.get_balance()
#
#
# dump(convert_dict_hex_to_int(res3, ignore_keys=["blockHash", "txHash"]))
# dump(convert_dict_hex_to_int(res3, ignore_keys=["blockHash", 'txHash'], is_comma=True, debug=True, ansi=True))
#
# dump(res3, hex_to_int=True)
#
# pawn.console.log(f"balance = {res2} ICX")
#
# # dump(convert_dict_hex_to_int(res3))
#
# icon_rpc.get_tx_wait(tx_hash="0x2175d5b307b657d1bada071d721b011462c0772e4ac3a4c9f9723a9f1f9de7c0")
#
#
#
#
