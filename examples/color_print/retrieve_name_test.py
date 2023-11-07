#!/usr/bin/env python3
import common
from pawnlib.config.globalconfig import pawnlib_config as pawn
from pawnlib.output.color_print import get_variable_name_list, get_variable_name, get_var_name

a = 5
b = a
pawn.console.rule("Gets the variable name. - list")
print(get_variable_name_list(a))
print(get_variable_name_list(b))

pawn.console.rule("Gets the variable name. ")
print(get_variable_name(b))
print(get_variable_name())
print(get_var_name())
