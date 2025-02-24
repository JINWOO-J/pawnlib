#!/usr/bin/env python3
import common
from pawnlib.config import *
from pawnlib.config.configure import *

print("[Child]")
conf = Configure()

print(conf)
print(f"[config_child] conf.name = {conf.name}")
