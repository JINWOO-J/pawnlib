#!/usr/bin/env python3
import common
from pawnlib.typing.converter import  analyze_jail_flags
from pawnlib.typing.constants import ICONJailFlags, const
from pawnlib.output.color_print import dump, classdump
from pawnlib.config import pawnlib_config as pawn


pawn.console.log(ICONJailFlags.FLAGS)
pawn.console.log(const.ICONJailFlagsConstants.FLAGS)

for flag in range(0, 16):
    pawn.console.log(flag, analyze_jail_flags(flag))
    pawn.console.log(ICONJailFlags.get_jail_flags(flag))
