from __future__ import unicode_literals
import math
import unittest


class TestGenericUtils(unittest.TestCase):

    def test_make_b58encode(self):
        from billy.utils.generic import b58encode

        def assert_encode(data, expected):
            self.assertEqual(b58encode(data), expected)

        assert_encode(b'', b'1')
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
