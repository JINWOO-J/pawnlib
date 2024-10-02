#!/usr/bin/env python3
import common
from pawnlib.typing.converter import shorten_text

text = "abcd"*10


for i in range(0, len(text)):
    res = shorten_text(text, width=i)
    print(f"width={i}, len={len(res)}, result={res}")

print()

for i in range(0, len(text)):
    res = shorten_text(text, width=i, shorten_middle=True, placeholder="...")
    print(f"width={i}, len={len(res)}, result={res}")

print()
print(shorten_text("Hello World", width=8))
