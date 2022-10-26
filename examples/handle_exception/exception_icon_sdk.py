#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output.color_print import *
from iconsdk.wallet.wallet import KeyWallet
from iconsdk.exception import KeyStoreException, DataTypeException, IconServiceBaseException

from pawnlib.utils import http
dump(pawn.to_dict())

pawn.set(
    PAWN_DEBUG=False,
    PAWN_LOGGER=dict(
        stdout=True,
        use_hook_exception=False,
    )
)



try:
    KeyWallet.load("sdsd", "sdsd")
except IconServiceBaseException as e:
    print(f"IconServiceBaseException = {e}")
