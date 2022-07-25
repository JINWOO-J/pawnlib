


## pip3 install pawnlib


from pawnlib.output import *
from pawnlib.config.globalconfig import pawnlib_config as pawn


from pawnlib.utils import http

from pawnlib.utils.operate_handler import *

def sub():
    print(f"child = {pawn.get('asdf')}")

def main():

    pawn.set(a="2")
    pawn.set(a="")
    pawn.set(a=None)
    
    pawn.reset("a")

main()





