from __future__ import unicode_literals
import unittest


class TestGenericUtils(unittest.TestCase):

    def test_make_b58encode(self):
        from billy.utils.generic import b58encode

        def assert_encode(data, expected):
            self.assertEqual(b58encode(data), expected)

        assert_encode('', '1')
        assert_encode('\00', '1')
        assert_encode('hello world', 'StV1DL6CwTryKyV')

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

    def test_round_down_cent(self):
        from decimal import Decimal
        from billy.utils.generic import round_down_cent

        def assert_round_down(amount, expected):
            self.assertEqual(
                round_down_cent(Decimal(amount)), 
                Decimal(expected)
            )

        assert_round_down('0.0', '0.0')
        assert_round_down('0.1', '0.1')
        assert_round_down('0.11', '0.11')
        assert_round_down('1.0', '1.0')
        assert_round_down('1.12', '1.12')
        assert_round_down('123.0', '123.0')
        assert_round_down('0.123', '0.12')
        assert_round_down('0.1234', '0.12')
        assert_round_down('0.5566', '0.55')
        assert_round_down('0.7788', '0.77')
        assert_round_down('1.23456789', '1.23')
