#!/usr/bin/env python3
import common
from pawnlib.utils import icx_raw_singer, icx_signer
import codecs



wallet = icx_raw_singer.KeyWallet.create()

# Get the private key, public key, and wallet address
# private_key = wallet.private_key
# public_key = wallet.public_key
private_key = wallet.get_private_key()
public_key = wallet.get_public_key()


address = wallet.address

# Print the private key, public key, and wallet address
print("Private Key:", private_key)
print("Public Key:", public_key)
print("Wallet Address:", address)

res = icx_signer._parse_keystore_key(private_key_hex=private_key)

print(res)


# Verify the address calculation
calculated_address = wallet.get_address()
assert address == calculated_address, "Address calculation is incorrect"

# Verify the public key calculation
calculated_public_key = wallet.get_public_key()
assert public_key == calculated_public_key, "Public key calculation is incorrect"

#
#
# def test_key_wallet():
#     # 새로운 KeyWallet 생성
#     wallet = KeyWallet.create()
#
#     # 개인 키, 공개 키, 지갑 주소 출력
#     private_key = wallet.private_key.hex()
#     public_key = codecs.encode(wallet.public_key_to_bytes(), 'hex').decode()
#     address = wallet.address
#
#     print("개인 키:", private_key)
#     print("공개 키:", public_key)
#     print("지갑 주소:", address)
#
#     # 주소 계산 검증
#     calculated_address = wallet.get_address()
#     assert address == calculated_address, "주소 계산이 올바르지 않음"
#
#     # 공개 키 계산 검증
#     calculated_public_key = wallet.get_public_key()
#     assert wallet.public_key_to_bytes() == calculated_public_key, "공개 키 계산이 올바르지 않음"
#
#     print("테스트 성공)
