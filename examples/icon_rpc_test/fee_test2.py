#!/usr/bin/env python3
import common
import time
from pawnlib.config import pawnlib_config as pawn
from pawnlib.typing import int_to_loop_hex
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, json_rpc, icx_signer, NetworkInfo
from pawnlib.output import dump, print_var
from pawnlib.typing.converter import convert_dict_hex_to_int, hex_to_number
from pawnlib.typing.constants import const

disable_ssl_warnings()
network_info = NetworkInfo(network_name="jw-test", network_api="http://100.65.0.35:9000")
# network_info = NetworkInfo(network_name="berlin")
wallet = icx_signer.load_wallet_key("0x32cf8c963178b1dc15abe5628ce098ce067d7afc8cffa0f27405edd3afa90811")

# wallet2 = icx_signer.load_wallet_key("aa6b56d56dcaa42c90b0344307e1095eec09b37e2fe72cc7450f99cd113839ac")

step_costs = {
    "apiCall": "0x2710",
    "contractCall": "0x61a8",
    "contractCreate": "0x3b9aca00",
    "contractSet": "0x3a98",
    "contractUpdate": "0x3b9aca00",
    "default": "0x186a0",
    "delete": "-0xf0",
    "deleteBase": "0xc8",
    "get": "0x19",
    "getBase": "0xbb8",
    "input": "0xc8",
    "log": "0x64",
    "logBase": "0x1388",
    "schema": "0x1",
    "set": "0x140",
    "setBase": "0x2710"
}


def send_all_icx(from_wallet, to_address, step_kind="apiCall", fee=None):
    pawn.console.log(f"Starting ICX transfer from {from_wallet} to {to_address}")
    pawn.console.log(f"Step Kind: {step_kind}")

    # Initialize Icon RPC Helper
    icon_rpc = IconRpcHelper(
        network_info=network_info,
        wallet=from_wallet,
        raise_on_failure=False
    )
    pawn.console.log(f"Using network: {network_info}")

    # Get sender's address and balance
    from_address = icon_rpc.wallet.get("address")
    balance_icx = icon_rpc.get_balance(return_as_hex=False)
    pawn.console.log(f"Sender Address: {from_address}, Balance: {balance_icx} ICX")

    # Prepare the transaction payload
    payload = json_rpc(
        method="icx_sendTransaction",
        params={
            "from": from_address,
            "to": to_address,
        }
    )
    pawn.console.log(f"Initial payload: {payload}")

    # Estimate the gas (step) requirements and get the step cost and price
    estimated_steps_hex = icon_rpc.get_estimate_step(tx=payload)
    step_cost_hex = icon_rpc.get_step_cost(step_kind)
    step_price_hex = icon_rpc.get_step_price()

    # Convert the step values from hex to numbers
    estimated_steps = hex_to_number(estimated_steps_hex)
    step_cost = hex_to_number(step_cost_hex)
    step_price = hex_to_number(step_price_hex)

    # Calculate the step limit and the transaction fee in ICX
    step_limit = estimated_steps + step_cost
    step_limit_hex = hex(step_limit)
    transaction_fee_icx = (step_limit * step_price) / const.TINT if fee is None else fee

    pawn.console.log(f"Estimated Steps: {estimated_steps} (Hex: {estimated_steps_hex})")
    pawn.console.log(f"Step Cost ({step_kind}): {step_cost} (Hex: {step_cost_hex})")
    pawn.console.log(f"Step Price: {step_price} (Hex: {step_price_hex})")
    pawn.console.log(f"Step Limit: {step_limit} (Hex: {step_limit_hex})")

    # Log whether fee was provided or calculated
    if fee is not None:
        pawn.console.log(f"Using user-provided transaction fee: {transaction_fee_icx} ICX")
    else:
        pawn.console.log(f"Calculated Transaction Fee: {transaction_fee_icx} ICX")

    # Convert transaction fee to hex for further calculations
    fee_hex = int_to_loop_hex(transaction_fee_icx)
    pawn.console.log(f"Transaction Fee in hex: {fee_hex}")

    # Calculate the remaining balance after fee deduction
    transfer_icx = max(0, balance_icx - transaction_fee_icx)
    transfer_amount_loop = int(transfer_icx * const.ICX_IN_LOOP)
    transfer_amount_hex = hex(transfer_amount_loop)
    pawn.console.log(f"Amount to Transfer: {transfer_icx} ICX ({transfer_amount_loop} loop, Hex: {transfer_amount_hex})")

    # Update the payload with the final value to transfer
    payload['params']['value'] = transfer_amount_hex
    pawn.console.log(f"Final Payload for Transaction: {payload}")

    # Sign and send the transaction
    icon_rpc.sign_tx(payload=payload)
    result = icon_rpc.sign_send()

    pawn.console.log(f"Transaction sent, result: {result}, balance={icon_rpc.get_balance()}")


# send_all_icx(from_wallet=wallet, to_address="hx6e17cf7407e46cfa1ba0a6ac34d18eaa2c40fb6a")
send_all_icx(from_wallet=wallet, to_address="hx6e17cf7407e46cfa1ba0a6ac34d18eaa2c40fb6a", step_kind="setBase")

exit()

# dump(convert_dict_hex_to_int(res3))

step_price = icon_rpc.get_step_price()

pawn.console.log(f"step_price={hex_to_number(step_price, debug=True)}")
# pawn.console.log(f"get_step_cost={icon_rpc.get_step_costs()}")
pawn.console.log(convert_dict_hex_to_int(icon_rpc._get_step_costs(), debug=True))
# pawn.console.log("---", convert_dict_hex_to_int(icon_rpc.get_step_cost(), debug=True))

estimate_payload = json_rpc(
    method="icx_sendTransaction",
    params={
        "from": "hx5a05b58a25a1e5ea0f1d5715e1f655dffc1fb30a",
        "to": "hx5a05b58a25a1e5ea0f1d5715e1f655dffc1fb30a",
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

pawn.console.log(estimate_payload)
exit()

signed_transaction = icon_rpc.sign_tx(payload=estimate_payload)
pawn.console.log(signed_transaction)
tx_result = icon_rpc.sign_send()

print_var(tx_result)
