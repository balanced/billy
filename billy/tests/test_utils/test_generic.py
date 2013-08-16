from __future__ import unicode_literals
import math
import unittest


class TestGenericUtils(unittest.TestCase):

    def test_make_b58encode(self):
        from billy.utils.generic import b58encode

        def assert_encode(data, expected):
            self.assertEqual(b58encode(data), expected)

        assert_encode(b'\00', b'1')
        assert_encode(b'hello world', b'StV1DL6CwTryKyV')

    def test_make_guid(self):
        from billy.utils.generic import make_guid

        # just make sure it is random
        guids = [make_guid() for _ in range(100)]
        self.assertEqual(len(set(guids)), 100)

    def test_make_api_key(self):
        from billy.utils.generic import make_api_key

        # just make sure it is random
        api_keys = [make_api_key() for _ in range(1000)]
        self.assertEqual(len(set(api_keys)), 1000)

        def check_size(key_size):
            real_num = math.log((2 ** (8 * key_size)), 58)
            expected_encoded_size = int(math.ceil(real_num))
            self.assertEqual(len(make_api_key(key_size)), expected_encoded_size)

        check_size(32)
        check_size(100)
        check_size(256)
