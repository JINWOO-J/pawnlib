#!/usr/bin/env python3
import common
from pawnlib.config import nestednamedtuple, pawnlib_config as pawn
from pawnlib.output import dump

pawn.set(
    stack="stack_value",
    PAWN_LOGGER=dict(
        log_level="INFO",
        stdout_level="INFO",
        use_hook_exception=True,
    ),
    PAWN_DEBUG=True,# Don't use production, because it's not stored exception log.
    dict_stack={
        "sdsd": 111,
        "sssss": 222,
    }
)

pawn.console.log(pawn.to_dict())
ns = pawn.conf()
# pawn.console.log(f"stack_value={ns.stack} ")
pawn.console.log(pawn.get('stack'))

dump(pawn.to_dict())
dump(pawn.get('dict_stack'))

pawn.console.log(f"pawn.get('stack') = {pawn.get('stack')}")
pawn.console.log(f"ns.stack = {ns.stack}")

ns.stack = 1
# dump(ns.dict_stack.sdsd)


# ns2 = nestednamedtuple({"hello": 111})
#
# print(ns2)
#
# print(ns2.hello)
# ns2.hello = 3
# print(ns2.hello)
