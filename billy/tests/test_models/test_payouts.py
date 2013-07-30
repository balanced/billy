from __future__ import unicode_literals

from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from models import Payout, Group
from tests import BalancedTransactionalTestCase
from utils import Intervals


class TestPayout(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestPayout, self).setUp()
        self.external_id = 'MY_TEST_PAYOUT'
        self.group = Group.create('BILLY_TEST_MARKETPLACE')
        self.group_2 = Group.create('BILLY_TEST_MARKETPLACE_2')


class TestCreate(TestPayout):

    def test_create(self):
        Payout.create(external_id=self.external_id,
                      group_id=self.group.guid,
                      name='Payout',
                      balance_to_keep_cents=50000,
                      payout_interval=Intervals.TWO_WEEKS
                      )

    def test_create_exists(self):
        Payout.create(external_id=self.external_id,
                      group_id=self.group.guid,
                      name='Payout',
                      balance_to_keep_cents=50000,
                      payout_interval=Intervals.TWO_WEEKS
                      )
        with self.assertRaises(IntegrityError):
            Payout.create(external_id=self.external_id,
                          group_id=self.group.guid,
                          name='Payout 2',
                          balance_to_keep_cents=20000,
                          payout_interval=Intervals.MONTH
                          )

    def test_create_semi_colliding(self):
        Payout.create(external_id=self.external_id,
                      group_id=self.group.guid,
                      name='Payout',
                      balance_to_keep_cents=50000,
                      payout_interval=Intervals.TWO_WEEKS
                      )
        Payout.create(external_id=self.external_id,
                      group_id=self.group_2.guid,
                      name='Payout 2',
                      balance_to_keep_cents=20000,
                      payout_interval=Intervals.MONTH
                      )
        ret = Payout.retrieve(self.external_id, self.group.guid)
        self.assertEqual(ret.payout_interval, Intervals.TWO_WEEKS)
        self.assertEqual(ret.balance_to_keep_cents, 50000)
        ret = Payout.retrieve(self.external_id, self.group_2.guid)
        self.assertEqual(ret.payout_interval, Intervals.MONTH)
        self.assertEqual(ret.balance_to_keep_cents, 20000)


class TestRetrieve(TestPayout):

    def test_create_and_retrieve(self):
        Payout.create(external_id=self.external_id,
                      group_id=self.group.guid,
                      name='Payout',
                      balance_to_keep_cents=50000,
                      payout_interval=Intervals.TWO_WEEKS
                      )
        Payout.retrieve(
            external_id="MY_TEST_PAYOUT",
            group_id=self.group.guid
        )

    def test_retrieve_dne(self):
        with self.assertRaises(NoResultFound):
            Payout.retrieve(
                external_id="MY_TEST_DNE",
                group_id=self.group.guid
            )

    def test_retrieve_params(self):
        Payout.create(external_id=self.external_id,
                      group_id=self.group.guid,
                      name='Payout 2',
                      balance_to_keep_cents=123456,
                      payout_interval=Intervals.TWO_WEEKS
                      )
        ret = Payout.retrieve(
            external_id="MY_TEST_PAYOUT",
            group_id=self.group.guid
        )
        self.assertEqual(ret.name, 'Payout 2')
        self.assertEqual(ret.balance_to_keep_cents, 123456)
        self.assertEqual(ret.payout_interval, Intervals.TWO_WEEKS)
        self.assertTrue(ret.guid.startswith('PO'))

    def test_retrieve_active_only(self):
        payout = Payout.create(external_id=self.external_id,
                               group_id=self.group.guid,
                               name='Payout 2',
                               balance_to_keep_cents=123456,
                               payout_interval=Intervals.TWO_WEEKS
                               )
        payout.delete()
        with self.assertRaises(NoResultFound):
            Payout.retrieve(
                self.external_id, self.group.guid, active_only=True)

    def test_list(self):
        Payout.create('MY_TEST_PAYOUT_1', self.group.guid, 'Payout 1', 123456,
                      Intervals.WEEK)
        Payout.create('MY_TEST_PAYOUT_2', self.group.guid, 'Payout 2', 125828,
                      Intervals.TWO_WEEKS)
        Payout.create('MY_TEST_PAYOUT_3', self.group.guid, 'Payout 3', 259295,
                      Intervals.MONTH)
        Payout.create('MY_TEST_PAYOUT_4', self.group.guid, 'Payout 4', 628182,
                      Intervals.THREE_MONTHS)
        Payout.create(
            'MY_TEST_PAYOUT_4', self.group_2.guid, 'Payout 4', 628182,
            Intervals.THREE_MONTHS)
        self.assertEqual(
            len(Payout.query.join(Group).filter(Group.guid == self.group.guid,
                                                Payout.active == True).all()), 4)

    def test_list_active_only(self):
        Payout.create('MY_TEST_PAYOUT_1', self.group.guid, 'Payout 1', 123456,
                      Intervals.WEEK)
        Payout.create('MY_TEST_PAYOUT_2', self.group.guid, 'Payout 2', 125828,
                      Intervals.TWO_WEEKS)
        ret = Payout.create(
            'MY_TEST_PAYOUT_3', self.group.guid, 'Payout 3', 259295,
            Intervals.MONTH)
        Payout.create('MY_TEST_PAYOUT_4', self.group.guid, 'Payout 4', 628182,
                      Intervals.THREE_MONTHS)
        Payout.create(
            'MY_TEST_PAYOUT_4', self.group_2.guid, 'Payout 4', 628182,
            Intervals.THREE_MONTHS)
        ret.delete()
        self.assertEqual(len(
            Payout.query.join(Group).filter(Group.guid == self.group.guid,
                                            Payout.active == True).all()
        ), 3)


class TestUpdateDelete(TestPayout):

    def test_update(self):
        ret = Payout.create(external_id=self.external_id,
                            group_id=self.group.guid,
                            name='Payout 1',
                            balance_to_keep_cents=123456,
                            payout_interval=Intervals.custom(years=1)
                            )
        self.assertEqual(ret.name, 'Payout 1')
        ret.update('new name')
        new = Payout.retrieve(self.external_id, self.group.guid)
        self.assertEqual(new.name, 'new name')

    def test_delete(self):
        ret = Payout.create(external_id=self.external_id,
                            group_id=self.group.guid,
                            name='Payout 2',
                            balance_to_keep_cents=123456,
                            payout_interval=Intervals.TWO_WEEKS
                            )
        self.assertTrue(ret.active)
        ret.delete()
        new = Payout.retrieve(self.external_id, self.group.guid)
        self.assertFalse(new.active)


class TestValidators(TestPayout):

    def test_balance_to_keep_cents(self):
        with self.assertRaises(ValueError):
            Payout.create(external_id=self.external_id,
                          group_id=self.group.guid,
                          name='Payout 2',
                          balance_to_keep_cents=-1000,
                          payout_interval=Intervals.TWO_WEEKS
                          )

    def test_payout_interval(self):
        with self.assertRaises(StatementError):
            Payout.create(external_id=self.external_id,
                          group_id=self.group.guid,
                          name='Payout 2',
                          balance_to_keep_cents=1000,
                          payout_interval="HEY"
                          )


if __name__ == '__main__':
    import unittest

    unittest.main()
