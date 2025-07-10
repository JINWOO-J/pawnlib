#!/usr/bin/env python3
from pawnlib.config import pawnlib_config as pawn
from pawnlib.utils.http import jequest, disable_ssl_warnings, icon_rpc_call, IconRpcHelper, NetworkInfo

disable_ssl_warnings()

icon_rpc = IconRpcHelper()

payload = icon_rpc.create_governance_payload("getPReps", {})
pawn.console.log(payload)
