from __future__ import unicode_literals

from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from billy.models import Group
from billy.tests import BalancedTransactionalTestCase


class TestGroup(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestGroup, self).setUp()
        self.marketplace = 'BILLY_TEST_MARKETPLACE'

    def test_create(self):
        group = Group.create_group(self.marketplace)
        self.assertIsInstance(group, Group)

    def test_create_existing(self):
        Group.create_group(self.marketplace)
        with self.assertRaises(IntegrityError):
            Group.create_group(self.marketplace)

    def test_create_and_retrieve(self):
        group = Group.create_group(self.marketplace)
        ret = Group.retrieve_group(self.marketplace)
        self.assertEqual(group, ret)

    def test_retrieve_dne(self):
        with self.assertRaises(NoResultFound):
            Group.retrieve_group(self.marketplace)


def TestRelations(TestGroup):
    # Todo
    def test_temp(self):
        return True


if __name__ == '__main__':
    import unittest
    unittest.main()
