#!/usr/bin/env python3
import time
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo
from pawnlib.utils import icx_signer, http

disable_ssl_warnings()
# icx_signer.compressed = False


def main():
    # private_key = "0x32cf8c963178b1dc15abe5628ce098ce067d7afc8cffa0f27405edd3afa90810"
    private_key = "cd405e346fa7b7da8c29fdbb769c76965e1a764c2e2f54337ccd0b35434bafc3"
    # pawn.console.log(private_key)
    network_info = NetworkInfo(network_name="jw-test", network_api="http://20.20.4.129:9000")
    pawn.console.log(network_info)

    wallet = icx_signer.load_wallet_key(private_key)
    icon_rpc = IconRpcHelper(
        network_info=network_info,
        wallet=wallet,
        raise_on_failure=True,
        tx_method='icx_getTransactionByHash',
    )

    pawn.console.log(icon_rpc.claim_iscore())
    pawn.console.log(icon_rpc.unjail())


if __name__ == '__main__':
    main()
