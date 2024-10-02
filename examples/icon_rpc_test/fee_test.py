#!/usr/bin/env python3
import common
import time
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, json_rpc, icx_signer, NetworkInfo
from pawnlib.output import dump, print_var
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing.constants import const

disable_ssl_warnings()
network_info = NetworkInfo(network_name="sejong")
wallet = icx_signer.load_wallet_key("0x32cf8c963178b1dc15abe5628ce098ce067d7afc8cffa0f27405edd3afa90811")
pawn.console.log(wallet)
icon_rpc = IconRpcHelper(
    network_info=network_info,
    wallet=wallet,
    raise_on_failure=False
)
checked_balance = icon_rpc.get_balance(is_comma=True)
pawn.console.log(network_info)
pawn.console.log(f"balance = {checked_balance} ICX")

# dump(convert_dict_hex_to_int(res3))

step_price = icon_rpc.get_step_price()

pawn.console.log(f"step_price={hex_to_number(step_price, debug=True)}")
# pawn.console.log(f"get_step_cost={icon_rpc.get_step_costs()}")
pawn.console.log(convert_dict_hex_to_int(icon_rpc._get_step_costs(), debug=True))

estimate_payload = json_rpc(
    method="icx_sendTransaction",
    params={
        "from": "hx5a05b58a25a1e5ea0f1d5715e1f655dffc1fb30a",
        "to": "hx5a05b58a25a1e5ea0f1d5715e1f655dffc1fb30a",
        # "timestamp": "0x563a6cf330136",
        # 'timestamp': hex(icx_signer.get_timestamp_us()),
        "version": "0x3",
        "nid": "0x53",
        "data": [
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
            "ssssddddddddddddd",
        ]
    }
)

fee = icon_rpc.get_fee(tx=estimate_payload)
step_limit = icon_rpc.get_step_limit(tx=estimate_payload)
pawn.console.log(f"fee={fee}, step_limit={step_limit}")
estimate = icon_rpc.get_estimate_step(tx=estimate_payload)
step_cost = hex_to_number(icon_rpc.get_step_cost("get"))
step_limit = hex(hex_to_number(estimate) + hex_to_number(step_cost))
icx_fee = hex_to_number(step_limit) * hex_to_number(step_price) / const.TINT

pawn.console.log(f"icx_fee => estimate[i]({hex_to_number(estimate, debug=True)})[/i] * "
                 f"step_price[i]({hex_to_number(step_price, debug=True)})[/i] = {icx_fee}")
pawn.console.log(f"step_limit => {hex_to_number(step_limit, debug=True)}")


# pawn.console.log(icon_rpc.get_step_limit(tx=estimate_payload))

signed_transaction = icon_rpc.sign_tx(payload=estimate_payload)
pawn.console.log(signed_transaction)
tx_result = icon_rpc.sign_send()

print_var(tx_result)
