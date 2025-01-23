import os
import hashlib
import codecs


class KeyWallet:
    def __init__(self, private_key):
        self.private_key = private_key
        self.public_key = self._get_public_key()
        self.address = self.get_address()

    @staticmethod
    def create():
        # 새로운 임의의 개인 키 생성
        private_key = os.urandom(32)
        return KeyWallet(private_key)

    def _get_public_key(self):
        # 개인 키로부터 공개 키 유도
        public_key = self._point_multiplication(self.private_key, self._G)
        return public_key

    def get_public_key(self):
        # 개인 키로부터 공개 키 유도
        # return codecs.encode(self.public_key_to_bytes(), 'hex').decode()
        return codecs.encode(self.public_key_to_bytes(), 'hex').decode()

    def get_private_key(self):
        return codecs.encode(self.private_key, 'hex').decode()

    def get_address(self):
        # 공개 키로부터 지갑 주소 생성
        public_key_bytes = self.public_key_to_bytes()
        public_key_hash = hashlib.sha3_256(public_key_bytes).digest()
        wallet_address = 'hx' + codecs.encode(public_key_hash[-20:], 'hex').decode()
        return wallet_address

    def public_key_to_bytes(self):
        # 공개 키 튜플을 바이트로 변환
        x, y = self.public_key
        public_key_bytes = (x.to_bytes(32, 'big') + y.to_bytes(32, 'big'))
        return public_key_bytes

    def compressed_public_key(self):
        # Get the compressed public key (66 digits)
        x, y = self.public_key
        prefix = '03' if (y % 2) == 1 else '02'
        compressed_public_key = prefix + format(x, '064x')
        return compressed_public_key

    def _point_multiplication(self, scalar, point):
        # 타원 곡선에서의 점 곱셈 연산 수행
        result = self._point_at_infinity()
        for bit in scalar:
            if result is not None:
                result = self._point_double(result)
            if bit:
                if result is None:
                    result = point
                else:
                    result = self._point_add(result, point)
        return result

    def _point_double(self, point):
        # 타원 곡선에서의 점 두 배 연산 수행
        if point is None:
            return None
        x, y = point
        if y == 0:
            return self._point_at_infinity()
        slope = (3 * x * x) * self._inverse_mod(2 * y, self._p)
        x3 = (slope * slope - 2 * x) % self._p
        y3 = (slope * (x - x3) - y) % self._p
        return x3, y3

    def _point_add(self, point1, point2):
        # 타원 곡선에서의 점 덧셈 연산 수행
        if point1 is None:
            return point2
        if point2 is None:
            return point1
        x1, y1 = point1
        x2, y2 = point2
        if x1 == x2 and y1 != y2:
            return self._point_at_infinity()
        if x1 == x2:
            slope = (3 * x1 * x1) * self._inverse_mod(2 * y1, self._p)
        else:
            slope = (y1 - y2) * self._inverse_mod(x1 - x2, self._p)
        x3 = (slope * slope - x1 - x2) % self._p
        y3 = (slope * (x1 - x3) - y1) % self._p
        return x3, y3

    def _inverse_mod(self, a, m):
        # 모듈러 역수 계산
        if a < 0 or m <= a:
            a = a % m
        c, d = a, m
        uc, vc, ud, vd = 1, 0, 0, 1
        while c != 0:
            q, c, d = divmod(d, c) + (c,)
            uc, vc, ud, vd = ud - q * uc, vd - q * vc, uc, vc
        return ud % m

    def _point_at_infinity(self):
        # 타원 곡선에서의 무한 원점 반환
        return None

    # 타원 곡선 매개변수 정의 (secp256k1)
    _p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    _G = (
        0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
        0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
    )

# 테스트 수행

