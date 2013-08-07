from __future__ import unicode_literals

from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from models import Company
from tests import BalancedTransactionalTestCase


class TestGroup(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestGroup, self).setUp()
        self.marketplace = 'BILLY_TEST_MARKETPLACE'

    def test_create(self):
        group = Company.create(self.marketplace)
        self.assertIsInstance(group, Company)

    def test_create_existing(self):
        Company.create(self.marketplace)
        with self.assertRaises(IntegrityError):
            Company.create(self.marketplace)

    def test_create_and_retrieve(self):
        group = Company.create(self.marketplace)
        ret = Company.retrieve(self.marketplace)
        self.assertEqual(group, ret)

    def test_retrieve_dne(self):
        with self.assertRaises(NoResultFound):
            Company.retrieve(self.marketplace)


if __name__ == '__main__':
    import unittest
    unittest.main()
