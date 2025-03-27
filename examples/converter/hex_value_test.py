#!/usr/bin/env python3
import common
from pawnlib.typing import const, constants
from pawnlib.config import pawn
from pawnlib.typing import hex_to_number
from pawnlib.models.response import HexValue, HexTintValue

a = HexValue("0x2323")
b = HexValue("0x2321")
a_plus_b = a + b
pawn.console.log(a.output())
pawn.console.log(b.output())
pawn.console.log(a_plus_b.output())


def test_hex_operations():
    # 초기화
    hex1 = HexValue("0x1")
    hex2 = HexValue("0x2")
    hex3 = HexValue("0x3")

    pawn.console.log(f"Initial Values: hex1 = {hex1}, hex2 = {hex2}, hex3 = {hex3}")

    # 더하기
    hex_add = hex1 + hex2  # 0x1 + 0x2 = 0x3
    pawn.console.log(f"Addition: {hex1} + {hex2} = {hex_add.numeric}")
    assert hex_add.numeric == hex3.numeric, f"Expected {hex3.numeric}, got {hex_add.numeric}"

    # 빼기
    hex_subtract = hex3 - hex1  # 0x3 - 0x1 = 0x2
    pawn.console.log(f"Subtraction: {hex3} - {hex1} = {hex_subtract.numeric}")
    assert hex_subtract.numeric == hex2.numeric, f"Expected {hex2.numeric}, got {hex_subtract.numeric}"

    # 곱하기
    hex_multiply = hex1 * hex2  # 0x1 * 0x2 = 0x2
    pawn.console.log(f"Multiplication: {hex1} * {hex2} = {hex_multiply.numeric}")
    assert hex_multiply.numeric == hex2.numeric, f"Expected {hex2.numeric}, got {hex_multiply.numeric}"

    # 나누기
    hex_divide = hex3 / hex1  # 0x3 / 0x1 = 0x3
    pawn.console.log(f"Division: {hex3} / {hex1} = {hex_divide}")
    assert hex_divide.numeric == hex3.numeric, f"Expected {hex3.numeric}, got {hex_divide.numeric}"

    # 나머지
    hex_mod = hex3 % hex2  # 0x3 % 0x2 = 0x1
    pawn.console.log(f"Modulus: {hex3} % {hex2} = {hex_mod}")
    assert hex_mod.numeric == hex1.numeric, f"Expected {hex1.numeric}, got {hex_mod.numeric}"

    # 정수 나눗셈
    hex_floordiv = hex3 // hex2  # 0x3 // 0x2 = 0x1
    pawn.console.log(f"Floor Division: {hex3} // {hex2} = {hex_floordiv}")
    assert hex_floordiv.numeric == hex1.numeric, f"Expected {hex1.numeric}, got {hex_floordiv.numeric}"

    # 비교 연산
    pawn.console.log(f"Comparisons: hex1 < hex2 = {hex1 < hex2}, hex3 > hex2 = {hex3 > hex2}, hex1 == hex1 = {hex1 == hex1}, hex1 != hex2 = {hex1 != hex2}")
    assert hex1 < hex2, "Expected hex1 < hex2 to be True"
    assert hex3 > hex2, "Expected hex3 > hex2 to be True"
    assert hex1 == hex1, "Expected hex1 == hex1 to be True"
    assert hex1 != hex2, "Expected hex1 != hex2 to be True"

    # 단항 연산
    hex_neg = -hex1
    pawn.console.log(f"Unary Negation: -{hex1} = {hex_neg}")
    assert hex_neg.numeric == -hex1.numeric, f"Expected {-hex1.numeric}, got {hex_neg.numeric}"

    # 거듭제곱
    hex_pow = hex2 ** 2  # 0x2 ** 2 = 0x4
    pawn.console.log(f"Exponentiation: {hex2} ** 2 = {hex_pow}")
    assert hex_pow.numeric == HexValue("0x4").numeric, f"Expected {HexValue('0x4').numeric}, got {hex_pow.numeric}"

    pawn.console.log("All tests passed successfully!")

    pawn.console.log(hex3 + 1)
    pawn.console.log(hex3 -1)
    pawn.console.log(HexValue(222))
    pawn.console.log(HexValue(222) + "0x222")

    hex_value = HexValue(16)

    # Floor division with hex string
    result_floordiv = hex_value // "0x2"
    print(result_floordiv)  # Expected: HexValue with numeric = 8

    # Reverse floor division with hex string
    result_rfloordiv = "0x20" // hex_value
    print(result_rfloordiv)  # Expected: HexValue with numeric = 2

    # Modulus with hex string
    result_mod = hex_value % "0xA"
    print(result_mod)  # Expected: HexValue with numeric = 6

    # Reverse modulus with hex string
    result_rmod = HexValue("0x20") % hex_value
    print(result_rmod)  # Expected: HexValue with numeric = 0

    # Exponentiation with hex string
    result_pow = hex_value ** "0x3"
    print(result_pow)  # Expected: HexValue with numeric = 4096

    # Reverse exponentiation with hex string
    result_rpow = "0x2" ** hex_value
    print(result_rpow)  # Expected: HexValue with numeric = 65536

    
    HexValue.set_default_max_unit('M')

    readable = HexValue("0x295bcc94a74a601db62c206").format_readable()
    pawn.console.log(f"========== {readable}")

    pawn.console.log(repr(HexValue("0x295bcc94a74a601db62c206")))
    pawn.console.log(repr(HexValue("0x38d7ea4c68000")))
    
    

    pawn.console.log(repr(HexTintValue("0x295bcc94a74a601db62c206")))
    pawn.console.log(repr(HexTintValue("0x38d7ea4c68000")))
    pawn.console.log(repr(HexTintValue(0.00122222222222)))
    pawn.console.log(repr(HexTintValue(0.0000000133343)))
    

    







# 실행
test_hex_operations()
