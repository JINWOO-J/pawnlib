#!/usr/bin/env python3
import common
from pawnlib.typing import const, constants
from pawnlib.config import pawn

def hex_test_value(value="", **kwargs):
    result = hex_to_number(value, **kwargs)
    pawn.console.log(f"Input: {value} | Result: {result} | Type: {type(result).__name__}")

# 테스트 케이스
print(f"Case 1: {hex_to_number('0x2221', is_tint=True, debug=True)}")
print(f"Case 2: {hex_to_number('0x2961fff8ca1a62000000000', is_tint=True, debug=True, is_comma=False)}")
print(f"Case 3: {hex_to_number('0x232323', debug=True, is_comma=True)}")
print(f"Case 4: {hex_to_number('0xff', debug=True, is_comma=True, is_tint=True)}")
print(f"Case 4: {hex_to_number('0x10', debug=True, is_comma=True, is_tint=True)}")

# 다양한 값들에 대한 테스트
hex_test_value("0x429d069189e0000", is_tint=True)  # 큰 수 테스트
hex_test_value("0x1A")  # 작은 16진수
hex_test_value("2F")  # 16진수 접두어가 없는 값
hex_test_value(255)  # 정수 입력
hex_test_value("0xFF", is_tint=True)  # tint 적용된 16진수
hex_test_value("0x1A", is_tint=True)  # tint 적용된 작은 값
hex_test_value("0x1A", is_tint=True, return_decimal_as_str=False)  # Decimal 결과 raw 반환
hex_test_value("0x1A", is_tint=True, debug=True)  # debug 모드
hex_test_value("0x2961fff8ca1a62327300000", is_tint=True, debug=True)  # debug 모드
hex_test_value("0x2961fff8ca1a62327300000", is_tint=True, debug=False)  # debug 모드
hex_test_value("0x2961fff8ca1a62327300000", is_comma=True, is_tint=True, debug=False)  # debug 모드
hex_test_value("0x3ca07d9ee800", is_comma=True, is_tint=True, debug=False)  # debug 모드
hex_test_value("0x38d7ea4c68000", is_comma=True, is_tint=True)  # debug 모드
