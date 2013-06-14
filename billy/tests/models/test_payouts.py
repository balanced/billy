from __future__ import unicode_literals

from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from billy.models import Payout, Group
from billy.tests import BalancedTransactionalTestCase
from billy.utils import Intervals


class TestPayout(BalancedTransactionalTestCase):
    def setUp(self):
        super(TestPayout, self).setUp()
        self.group = 'BILLY_TEST_MARKETPLACE'
        self.group_2 = 'BILLY_TEST_MARKETPLACE_2'
        Group.create_group(self.group)
        Group.create_group(self.group_2)


class TestCreate(TestPayout):
    def test_create(self):
        pass

    def test_create_exists(self):
        pass

    def test_create_semi_colliding(self):
        pass


class TestRetrieve(TestPayout):
    def test_create_and_retrieve(self):
        pass


    def test_retrieve_dne(self):
        pass

    def test_retrieve_params(self):
        pass


    def test_retrieve_active_only(self):
        pass

    def test_list(self):
        pass


    def test_list_active_only(self):
        pass


class TestUpdateDelete(TestPayout):
    def test_update(self):
        pass


    def test_delete(self):
        pass


class TestValidators(TestPayout):
    def test_balance_to_keep_cents(self):
        pass


    def test_payout_interval(self):
        pass


if __name__ == '__main__':
    import unittest

    unittest.main()