#!/usr/bin/env python3
import common
from pawnlib.typing.converter import shorten_text

text = "asdf"*10


for i in range(1, len(text)):
    res = shorten_text(text, width=i)
    print(f"width={i}, len={len(res)}, result={res}")

print()
