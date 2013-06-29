from __future__ import unicode_literals

from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from billy_lib.models import Group
from billy_lib.tests import BalancedTransactionalTestCase


class TestGroup(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestGroup, self).setUp()
        self.marketplace = 'BILLY_TEST_MARKETPLACE'

    def test_create(self):
        group = Group.create(self.marketplace)
        self.assertIsInstance(group, Group)

    def test_create_existing(self):
        Group.create(self.marketplace)
        with self.assertRaises(IntegrityError):
            Group.create(self.marketplace)

    def test_create_and_retrieve(self):
        group = Group.create(self.marketplace)
        ret = Group.retrieve(self.marketplace)
        self.assertEqual(group, ret)

    def test_retrieve_dne(self):
        with self.assertRaises(NoResultFound):
            Group.retrieve(self.marketplace)


# def TestRelations(TestGroup):
# Todo
#     def test_temp(self):
#         return True


if __name__ == '__main__':
    import unittest
    unittest.main()
