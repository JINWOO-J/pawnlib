#!/usr/bin/env python3
import unittest
try:
    import common
except:
    pass
import os
from pawnlib.output import get_parent_path, cprint, is_file, open_json
from parameterized import parameterized
from pawnlib.utils import icx_signer


class TestMethodRequest(unittest.TestCase):

    def setUp(self):
        self.keystore_file = "keystore_test_case.json"
        self.keystore_password = "testtest"
        if is_file(self.keystore_file):
            os.remove(self.keystore_file)

        icx_signer.generate_wallet(file_path=self.keystore_file, password=self.keystore_password)
        self.wallet_dict = icx_signer.load_wallet_key(self.keystore_file, self.keystore_password)
        self.address = self.wallet_dict.get('address')

    def tearDown(self):
        os.remove(self.keystore_file)

    def test_01_generate_keystore_from_private_key(self,):
        wallet_dict_private_key = icx_signer.load_wallet_key(self.wallet_dict.get('private_key'))
        self.assertEqual(self.address, wallet_dict_private_key['address'])

    def test_02_generate_keystore_from_file(self,):
        wallet_dict = icx_signer.load_wallet_key(self.keystore_file, self.keystore_password)
        self.assertEqual(self.address, wallet_dict['address'])

    def test_03_generate_keystore_from_object(self,):
        wallet_dict = icx_signer.load_wallet_key(open_json(self.keystore_file), self.keystore_password)
        self.assertEqual(self.address, wallet_dict['address'])


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMethodRequest)
    testResult = unittest.TextTestRunner(verbosity=3).run(suite)
