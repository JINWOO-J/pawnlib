#!/usr/bin/env python3
import common
from pawnlib.typing.converter import format_size, format_network_traffic
from pawnlib.config import pawn

class Incrementer:
    def __init__(self, start=1000):
        self.current = start

    def increment(self):
        value = self.current
        self.current *= 1000
        return value


def print_formated_size(unit="", unit_type="storage"):
    increment = Incrementer()
    for _ in range(7):
        value = increment.increment()
        formatted_size = format_size(value, unit=unit, decimal_places=5, unit_type=unit_type)
        pawn.console.log(f"{value:>42,} {formatted_size:>20}")


def print_formated_network_size(per_second=False):
    increment = Incrementer()
    for _ in range(7):
        value = increment.increment()
        formatted_size = format_network_traffic(size=value, per_second=per_second)
        pawn.console.log(f"{value:>42,} {formatted_size:>20}")


print_formated_size()
print_formated_size(unit="GB")
print_formated_size( unit_type="network")



print_formated_network_size()
print_formated_network_size(per_second=True)
