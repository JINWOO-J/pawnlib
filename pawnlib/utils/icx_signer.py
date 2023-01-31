#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import hashlib
import base64
from os import path
from secp256k1 import PrivateKey, PublicKey
from pawnlib.typing import check
from pawnlib.config import pawnlib_config as pawn
from eth_keyfile import create_keyfile_json, extract_key_from_keyfile


"""secp256k1 library should be used only in this module.
"""

def store_keystore_file_on_the_path(file_path, json_string):
    """Stores a created keystore string data which is JSON format on the file path.
    :param file_path: The path where the file will be saved. type(str)
    :param json_string: Contents of the keystore.
    """
    if path.isfile(file_path):
        raise FileExistsError

    with open(file_path, 'wt') as f:
        f.write(json_string)


def load_wallet_key(file_path, password):
    pawn.console.debug(f"Load wallet from keystore file : {file_path}", "green")
    with open(file_path, 'rb') as file:
        try:
            private_key: bytes = extract_key_from_keyfile(file, bytes(password, 'utf-8'))
            wallet = PrivateKey(private_key)
            public_key: bytes = wallet.public_key.format(compressed=False)
            address = f'hx{sha3_256(public_key[1:]).digest()[-20:].hex()}'
            return {
                "private_key": "0x" + private_key.hex(),
                "address": address,
                "public_key": public_key.hex()
            }

        except ValueError as e:
            if "MAC mismatch" in str(e):
                e = "\t Wrong password"
            pawn.console.log(f"[bold red] Error {e}")

    return {}


def generate_keys():
    """generate privkey and pubkey pair.

    Returns:
        tuple: privkey(bytes, 32), pubkey(bytes, 65)
    """
    privkey = PrivateKey()

    privkey_bytes = privkey.private_key
    pubkey_bytes = privkey.pubkey.serialize(False)

    return privkey_bytes, pubkey_bytes


def get_address(pubkey_bytes):
    """generate address from public key.

    Args:
        pubkey_bytes(bytes): public key bytes

    Returns:
        bytes: icx address (20bytes)
    """

    # Remove the first byte(0x04) of pubkey
    return hashlib.sha3_256(pubkey_bytes[1:]).digest()[-20:]


def verify_recoverable_signature(msg_hash, signature_bytes, recovery_id):
    """
    Args:
        msg_hash(bytes): 256bit hash value
        signature_bytes(bytes):
        recovery_id(int):

    Returns:
    """
    pubkey, signature = \
        recover_signature(msg_hash, signature_bytes, recovery_id)

    return pubkey.ecdsa_verify(msg_hash, signature, True)


def recover_signature(msg_hash, signature_bytes, recovery_id):
    """
    Args:
        msg_hash(bytes): sha3 256bit hash value
        signature_bytes(bytes):
        recovery_id(int):

    Returns:
        pubkey(PublicKey):
        signature(object):
    """
    pubkey = PublicKey(None, False)

    recoverable_signature = pubkey.ecdsa_recoverable_deserialize( \
        signature_bytes, recovery_id)

    public_key = pubkey.ecdsa_recover( \
        msg_hash, recoverable_signature, raw=True)
    pubkey.public_key = public_key

    signature = pubkey.ecdsa_recoverable_convert(recoverable_signature)

    return pubkey, signature


class IcxSigner(object):
    """Digital Signing  using secp256k1
    """

    def __init__(self, data=None, raw=True):
        """Constructor

        Args:
            data(object): bytes or der
            raw(bool): True(bytes) False(der)
        """
        self._check_private_key(data)
        self._private_key_hex = None
        self._private_key_bytes = None

        self.__privkey = PrivateKey(self._private_key_bytes, raw)

    def _check_private_key(self, private_key=None):

        if isinstance(private_key, bytes):
            self._private_key_hex = private_key.hex()
        elif check.is_hex(private_key):
            self._private_key_hex = private_key
        else:
            raise ValueError(f"Invalid Private Key - {private_key}")

        if self._private_key_hex.startswith("0x"):
            self._private_key_hex = self._private_key_hex[2:]

        self._private_key_bytes = bytes.fromhex(self._private_key_hex)

    def set_privkey_bytes(self, data):
        """Set private key using private key data in bytes.

        Args:
            data(bytes): private key data
        """
        self.__privkey.set_raw_privkey(data)

    def get_privkey_bytes(self):
        """Get private key data in bytes.

        Returns:
            bytes: private key data (32 bytes)
        """
        return self.__privkey.private_key

    def get_pubkey_bytes(self):
        return self.__privkey.pubkey.serialize(compressed=False)

    def get_address(self):
        """Create an address with pubkey.
        address is made from pubkey.

        Returns:
            str: address represented in hexadecimal string starting with '0x'
        """
        pubkey_bytes = self.__privkey.pubkey.serialize(compressed=False)
        return get_address(pubkey_bytes)

    def get_hx_address(self):
        """Create an address with pubkey.
        address is made from pubkey.

        Returns:
            str: address represented in hexadecimal string starting with '0x'
        """

        return f"hx{self.get_address().hex()}"

    def sign_tx(self, tx=None):
        if isinstance(tx, dict) and tx.get('params'):
            tx_hash_bytes = get_tx_hash("icx_sendTransaction", tx['params'])
            signature_bytes, recovery_id = self.sign_recoverable(tx_hash_bytes)
            signature_bytes_big = bytes(bytearray(signature_bytes) + recovery_id.to_bytes(1, 'big'))
            tx['params']['signature'] = base64.b64encode(signature_bytes_big).decode()
        return tx

    def sign(self, msg_hash):
        """Make a signature using the hash value of msg.

        Args:
            msg_hash(bytes): msg_hash = sha3_256(msg)

        Returns:
            bytes: signature bytes
        """
        privkey = self.__privkey
        signature = privkey.ecdsa_sign(msg_hash, raw=True)
        return privkey.ecdsa_serialize(signature)

    def store(self, file_path: str, password: str):
        try:
            key_store_contents = create_keyfile_json(
                self.get_privkey_bytes(),
                bytes(password, 'utf-8'),
                iterations=16384,
                kdf="scrypt"
            )
            key_store_contents['address'] = self.get_hx_address()
            key_store_contents['coinType'] = 'icx'

            # validate the  contents of a keystore file.
            import json
            if key_store_contents:
                json_string_keystore_data = json.dumps(key_store_contents)
                store_keystore_file_on_the_path(file_path, json_string_keystore_data)
                pawn.console.debug(f"Stored Wallet. Address: {self.get_address()}, File path: {file_path}")
        except FileExistsError:
            raise ValueError("File already exists.")
        except PermissionError:
            raise ValueError("Not enough permission.")
        except FileNotFoundError:
            raise ValueError("File not found.")
        except IsADirectoryError:
            raise ValueError("Directory is invalid.")

    def sign_recoverable(self, msg_hash):
        """Make a recoverable signature using message hash data
        We can extract public key from recoverable signature.

        Args:
            msg_hash(bytes): hash data of message

        Returns:
            tuple:
                bytes: 65 bytes data
                int: recovery id
        """
        privkey = self.__privkey
        recoverable_signature = privkey.ecdsa_sign_recoverable(msg_hash, raw=True)
        return privkey.ecdsa_recoverable_serialize(recoverable_signature)

    @staticmethod
    def from_bytes(data):
        return IcxSigner(data, raw=True)

    @staticmethod
    def from_der(data):
        return IcxSigner(data, raw=False)


class IcxSignVerifier(object):
    """Digial signature verification
    """

    def __init__(self, data, raw=True):
        """
        Refer to https://github.com/ludbb/secp256k1-py api documents.

        Args:
            data(bytes): 65 bytes data which PublicKey.serialize() returns
            raw(bool): if False, it is assumed that pubkey has gone through PublicKey.deserialize already, otherwise it must be specified as bytes.

        Returns:
            None
        """
        self.__pubkey = PublicKey(data, raw)

    def get_address(self):
        """Create an address with pubkey.
        address is made from pubkey.

        Returns:
            str: address represented in hexadecimal string starting with '0x'
        """
        pubkey_bytes = self.__pubkey.serialize(compressed=False)
        return get_address(pubkey_bytes)

    def verify(self, msg_hash, signature_bytes):
        """Check whether signature is valid or not.

        Args:
            pubkey_bytes(bytes): byte data of pubkey
            msg_hash(bytes): hash value of msg
            signature_bytes(bytes): signature data

        Returns:
            bool: the result of signature verification
        """
        pubkey = self.__pubkey

        signature = pubkey.ecdsa_deserialize(signature_bytes)
        return pubkey.ecdsa_verify(msg_hash, signature, True)

    @staticmethod
    def from_bytes(data):
        """
        Args:
            data(bytes): bytes data which PublicKey.serialize() returns
            raw(bool): if False, it is assumed that pubkey has gone through PublicKey.deserialize already, otherwise it must be specified as bytes.

        Returns:
            None
        """
        return IcxSignVerifier(data, True)


def get_timestamp_us():
    """Get epoch time in us.
    """
    return int(time.time() * 10 ** 6)


def icx_to_wei(icx):
    """Convert amount in icx unitt to wei unit.

    Args:
        icx(float): float value in icx unit

    Returns:
        int: int value in wei unit
    """
    return int(icx * 10 ** 18)


def get_string_decimal(value, place):
    """value를 10의 place 제곱으로 나눈 값을 string으로 변환하여 반환

    Args:
        value(int)
        place : 10의 몇 제곱을 나눌지 입력받음
    """
    str_value = str(value)
    if value >= 10 ** place:
        str_int = str_value[:len(str_value) - place]
        str_decimal = str_value[len(str_value) - place:]
        result = f'{str_int}.{str_decimal}'
        return result

    else:
        zero = "0."
        val_point = len(str_value)  #val_point : 몇자릿수인지 계산
        point_difference = place - val_point
        str_zero = "0" * point_difference
        result = f'{zero}{str_zero}{value}'
        return result


def sha3_256(data):
    """Get hash value using sha3_256 hash function

    Args:
        data(bytes): data to hash

    Returns:
        bytes: 256bit hash value (32 bytes)
    """
    return hashlib.sha3_256(data).digest()


def get_tx_hash(method, params):
    """Create tx_hash from params object.

    :param method: the value of 'method' key in jsonrpc
    :param params: the value of 'params' key in jsonrpc

    Returns:
        bytes: sha3_256 hash value

    """
    tx_phrase = get_tx_phrase(method, params)
    pawn.console.debug(f"serialize tx={tx_phrase}")
    return sha3_256(tx_phrase.encode())


def get_tx_phrase(method, params):
    """Create tx phrase from method and params.
    tx_phrase means input text to create tx_hash.

    :param method: the value of 'method' key in jsonrpc
    :param params: the value of 'params' key in jsonrpc


    Returns:
        str: sha3_256 hash format without '0x' prefix
    """
    keys = [ key for key in params ]
    keys.sort()

    key_count = len(keys)
    if key_count == 0:
        return method

    phrase = f'{keys[0]}.{params[keys[0]]}'
    for i in range(1, key_count):
        key = keys[i]
        phrase += f'.{key}.{params[key]}'

    return f'{method}.{phrase}'


def sign_recoverable(privkey_bytes, tx_hash_bytes):
    """
    :param privkey_bytes:
    :param tx_hash_bytes: 32byte tx_hash data

    Returns:
        bytes: signature_bytes + recovery_id(1)

    """
    signer = IcxSigner.from_bytes(privkey_bytes)
    signature_bytes, recovery_id = signer.sign_recoverable(tx_hash_bytes)

    # append recover_id(1 byte) to signature_bytes.
    return bytes(bytearray(signature_bytes) + recovery_id.to_bytes(1, 'big'))
