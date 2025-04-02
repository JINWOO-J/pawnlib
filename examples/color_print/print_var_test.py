#!/usr/bin/env python3
import common
from pawnlib.utils import log
from pawnlib.config import pawn, NestedNamespace
from pawnlib import output

# from pawnlib.output.color_print import print_var2


STRING_VAR = "default_appsss"
output.print_var(STRING_VAR)
# print_var(STRING_VAR)


DICT_VAR = {"sdsd": "sdsd"}
output.print_var(DICT_VAR)

list_var = ["sdsd", "sdsd", "2323"]
output.print_var(list_var, "This is title")

namespace = NestedNamespace(**DICT_VAR)
output.print_var(namespace)
