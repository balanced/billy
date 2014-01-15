from __future__ import unicode_literals
import os
import unittest
import tempfile
from decimal import Decimal

from billy.utils.generic import make_guid
from billy.utils.generic import make_api_key
from billy.utils.generic import round_down_cent
from billy.utils.generic import get_git_rev


class TestGenericUtils(unittest.TestCase):

    def test_make_b58encode(self):
        from billy.utils.generic import b58encode

        def assert_encode(data, expected):
            self.assertEqual(b58encode(data), expected)

        assert_encode('', '1')
        assert_encode('\00', '1')
        assert_encode('hello world', 'StV1DL6CwTryKyV')

    def test_make_guid(self):
        # just make sure it is random
        guids = [make_guid() for _ in range(100)]
        self.assertEqual(len(set(guids)), 100)

    def test_make_api_key(self):
        # just make sure it is random
        api_keys = [make_api_key() for _ in range(1000)]
        self.assertEqual(len(set(api_keys)), 1000)

    def test_round_down_cent(self):
        def assert_round_down(amount, expected):
            self.assertEqual(
                round_down_cent(Decimal(amount)),
                Decimal(expected)
            )

        assert_round_down('0', 0)
        assert_round_down('0.1', 0)
        assert_round_down('0.11', 0)
        assert_round_down('1.0', 1)
        assert_round_down('1.12', 1)
        assert_round_down('123.0', 123)
        assert_round_down('123.456', 123)
        assert_round_down('1.23456789', 1)

    def test_get_git_rev(self):
        temp_dir = tempfile.mkdtemp()

        git_dir = os.path.join(temp_dir, '.git')
        head_file = os.path.join(git_dir, 'HEAD')
        refs_dir = os.path.join(git_dir, 'refs')
        heads_dir = os.path.join(refs_dir, 'heads')
        master_file = os.path.join(heads_dir, 'master')

        os.mkdir(git_dir)
        os.mkdir(refs_dir)
        os.mkdir(heads_dir)

        with open(head_file, 'wt') as f:
            f.write('ref: refs/heads/master')

        with open(master_file, 'wt') as f:
            f.write('DUMMY_REV')

        self.assertEqual(get_git_rev(temp_dir), 'DUMMY_REV')

        rev = get_git_rev()
        self.assertNotEqual(rev, None)
        self.assertEqual(len(rev), 40)

        # sometimes it would be a hash revision value there rahter than
        # ref: /path/to/ref
        with open(head_file, 'wt') as f:
            f.write('DUMMY_HASH_REV')

        self.assertEqual(get_git_rev(temp_dir), 'DUMMY_HASH_REV')

    def test_get_git_rev_without_file_existing(self):
        temp_dir = tempfile.mkdtemp()
        self.assertEqual(get_git_rev(temp_dir), None)
