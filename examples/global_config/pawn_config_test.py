#!/usr/bin/env python3
import common
import os
from pawnlib.config.globalconfig import pawnlib_config as pawn, PawnlibConfig
from pawnlib.output import *


def main():
    config = PawnlibConfig(global_name="ssss")
    # pawn_local = PawnlibConfig(global_name="pawnlib_global_config", debug=True).init_with_env()
    LOG_DIR = f"{get_script_path(__file__)}/logs"
    APP_NAME = "default_app"
    STDOUT = True
    pawn.set(
        PAWN_PATH=get_script_path(__file__),
        # PAWN_PATH="/Users/jinwoo/work/python_prj",
        PAWN_LOGGER=dict(
            log_level="INFO",
            stdout_level="INFO",
            log_path=LOG_DIR,
            stdout=STDOUT,
            use_hook_exception=True,
        ),
        PAWN_CONSOLE=dict(
            redirect=True,
            record=True,
            log_time_format=f"%Y-%m-%d %H:%M:%S.%f",
        ),
        PAWN_DEBUG=True, # Don't use production, because it's not stored exception log.
        PAWN_VERBOSE=3,
        app_name=APP_NAME,
        app_data={},

    )

    dump(pawn.to_dict(), debug=False)
    # dump(pawn.to_dict())
    #
    # json_sample = [{"measurement": "PEER.STAT", "duration": 0.346, "tags": {"hostname": "jinwoo-1.local", "local_ip": "10.211.3.194", "public_ip": "58.234.156.141", "region": "KOR", "service": "cdnet", "role": "goloop"}, "fields": {"state": "started", "cid": "0x87b86", "nid": "0x53", "lastError": "", "buildVersion": "v1.2.7", "consensus_height": 6640807, "consensus_height_duration": 2020, "consensus_round": 0, "consensus_round_duration": 2020, "jsonrpc_call_avg": 0, "jsonrpc_call_cnt": 6, "jsonrpc_estimate_step_avg": 0, "jsonrpc_estimate_step_cnt": 0, "jsonrpc_failure_avg": 0, "jsonrpc_failure_cnt": 0, "jsonrpc_get_trace_avg": 0, "jsonrpc_get_trace_cnt": 0, "jsonrpc_retrieve_avg": 0, "jsonrpc_retrieve_cnt": 1, "jsonrpc_send_transaction_and_wait_avg": 0, "jsonrpc_send_transaction_and_wait_cnt": 0, "jsonrpc_send_transaction_avg": 0, "jsonrpc_send_transaction_cnt": 1, "jsonrpc_wait_transaction_result_avg": 0, "jsonrpc_wait_transaction_result_cnt": 0, "network_recv_cnt": 91760288, "network_recv_sum": 13539554973, "network_send_cnt": 95304698, "network_send_sum": 13859676196, "txlatency_commit": 0, "txlatency_finalize": 1010, "txpool_add_cnt": 1, "txpool_add_sum": 142, "txpool_drop_cnt": 1, "txpool_drop_sum": 142, "txpool_remove_cnt": 0, "txpool_remove_sum": 0, "txpool_user_add_cnt": 1, "txpool_user_add_sum": 142, "txpool_user_drop_cnt": 1, "txpool_user_drop_sum": 142, "txpool_user_remove_cnt": 0.0, "txpool_user_remove_sum": 0, "peer_role": 3, "address": "hx55f6e58565988bfcd324d9cedda6db8bb6f52600", "p2p_endpoint": "20.20.1.242:7100", "seeds_count": 5, "roots_count": 5, "uncles_count": 0, "trust_count": 4, "child_count": 0, "normalTxPool": 0}}]
    #
    # dump(json_sample)
    # print("<<< plugin result >>>")
    # print(json_sample)

    pawn.console.log("Before changed log format")
    pawn.set(
        PAWN_CONSOLE=dict(
            log_time_format=f"%Y-%m-%d %H:%M"
        )
    )
    pawn.console.log("After log format")
    pawn.console.print("[red]---")
    pawn.console.out("Localssss", locals())
    print(get_real_path(__file__))

    print('getcwd:      ', os.getcwd())
    print('__file__:    ', __file__)
    print('basename:    ', os.path.basename(__file__))
    print('dirname:     ', os.path.dirname(__file__))


if __name__ == "__main__":
    main()
