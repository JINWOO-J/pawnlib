#!/usr/bin/env python3
import sys
import argparse
import common
import os

from pawnlib.utils import notify
from pawnlib.config import pawnlib_config as pawn


pawn.set(
    PAWN_DEBUG=True,
    PAWN_LOGGER=dict(
        stdout=True,
        use_hook_exception=True
    )
)

pawn.console.log(pawn.__dict__)
pawn.console.log(pawn.to_dict())
slack_token = os.getenv("SLACK_TOKEN")

if slack_token is None:
    pawn.console.log("required SLACK_TOKEN environment")

print(f"slack_token = {slack_token}")
notify.send_slack_token(
    token=slack_token,
    message="test",
    channel_name="jinwoo_test"
)



