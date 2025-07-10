#!/usr/bin/env python3
import time
import common
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo
# from pawnlib.utils.icon import rpc_call
from pawnlib.output import dump, syntax_highlight, print_var
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing import generator
from pawnlib.utils import icx_signer, http
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.live import Live


disable_ssl_warnings()
# icx_signer.compressed = False


def send_transaction(wallet, network_info, status=None):

    icon_rpc = IconRpcHelper(
        network_info=network_info,
        wallet=wallet,
        raise_on_failure=True,
        tx_method='icx_getTransactionByHash',
    )
    payload = generator.json_rpc(
        method="icx_sendTransaction",
        params={
            'version': "0x3",
            'nid': "0x53",
            'to': generator.random_token_address(),
            'value': hex(icx_signer.icx_to_wei(0.1)),
            # 'fee': hex(icx_to_wei(fee)),
            # 'stepLimit': hex(2000000),
            'timestamp': hex(icx_signer.get_timestamp_us())
        }
    )

    signed_transaction = icon_rpc.sign_tx(payload=payload, check_balance=False)
    tx_result = icon_rpc.sign_send(is_block_time=True)

    return tx_result


def main():
    private_key = "0x32cf8c963178b1dc15abe5628ce098ce067d7afc8cffa0f27405edd3afa90810"
    # pawn.console.log(private_key)
    network_info = NetworkInfo(network_name="jw-test", network_api="http://20.20.4.129:9000")
    pawn.console.log(network_info)

    wallet = icx_signer.load_wallet_key(private_key)
    hosts = range(1, 10000)

    with pawn.console.status("working") as pawn.console_status:
        with ThreadPoolExecutor(max_workers=100) as executor:
            # futures = {executor.submit(send_transaction, wallet, network_info, progress, task_ids[host]): host
            #            for host, tx_hash in zip(hosts, tx_hashes)}
            futures = {executor.submit(send_transaction, wallet, network_info, pawn.console_status): host for host in hosts}
            for future in as_completed(futures):
                host = futures[future]
                try:
                    future.result()
                except Exception as exc:
                    pawn.console.log(f"[{host}] Error: {str(exc)}")


if __name__ == '__main__':
    main()
