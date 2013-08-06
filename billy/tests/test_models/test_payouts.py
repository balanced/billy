from __future__ import unicode_literals

from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from models import PayoutPlan, Company
from tests import BalancedTransactionalTestCase
from utils import Intervals


class TestPayout(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestPayout, self).setUp()
        self.your_id = 'MY_TEST_PAYOUT'
        self.group = Company.create('BILLY_TEST_MARKETPLACE')
        self.group_2 = Company.create('BILLY_TEST_MARKETPLACE_2')


class TestCreate(TestPayout):

    def test_create(self):
        PayoutPlan.create(your_id=self.your_id,
                      group_id=self.group.guid,
                      name='PayoutPlan',
                      balance_to_keep_cents=50000,
                      payout_interval=Intervals.TWO_WEEKS
                      )

    def test_create_exists(self):
        PayoutPlan.create(your_id=self.your_id,
                      group_id=self.group.guid,
                      name='PayoutPlan',
                      balance_to_keep_cents=50000,
                      payout_interval=Intervals.TWO_WEEKS
                      )
        with self.assertRaises(IntegrityError):
            PayoutPlan.create(your_id=self.your_id,
                          group_id=self.group.guid,
                          name='PayoutPlan 2',
                          balance_to_keep_cents=20000,
                          payout_interval=Intervals.MONTH
                          )

    def test_create_semi_colliding(self):
        PayoutPlan.create(your_id=self.your_id,
                      group_id=self.group.guid,
                      name='PayoutPlan',
                      balance_to_keep_cents=50000,
                      payout_interval=Intervals.TWO_WEEKS
                      )
        PayoutPlan.create(your_id=self.your_id,
                      group_id=self.group_2.guid,
                      name='PayoutPlan 2',
                      balance_to_keep_cents=20000,
                      payout_interval=Intervals.MONTH
                      )
        ret = PayoutPlan.retrieve(self.your_id, self.group.guid)
        self.assertEqual(ret.payout_interval, Intervals.TWO_WEEKS)
        self.assertEqual(ret.balance_to_keep_cents, 50000)
        ret = PayoutPlan.retrieve(self.your_id, self.group_2.guid)
        self.assertEqual(ret.payout_interval, Intervals.MONTH)
        self.assertEqual(ret.balance_to_keep_cents, 20000)


class TestRetrieve(TestPayout):

    def test_create_and_retrieve(self):
        PayoutPlan.create(your_id=self.your_id,
                      group_id=self.group.guid,
                      name='PayoutPlan',
                      balance_to_keep_cents=50000,
                      payout_interval=Intervals.TWO_WEEKS
                      )
        PayoutPlan.retrieve(
            your_id="MY_TEST_PAYOUT",
            group_id=self.group.guid
        )

    def test_retrieve_dne(self):
        with self.assertRaises(NoResultFound):
            PayoutPlan.retrieve(
                your_id="MY_TEST_DNE",
                group_id=self.group.guid
            )

    def test_retrieve_params(self):
        PayoutPlan.create(your_id=self.your_id,
                      group_id=self.group.guid,
                      name='PayoutPlan 2',
                      balance_to_keep_cents=123456,
                      payout_interval=Intervals.TWO_WEEKS
                      )
        ret = PayoutPlan.retrieve(
            your_id="MY_TEST_PAYOUT",
            group_id=self.group.guid
        )
        self.assertEqual(ret.name, 'PayoutPlan 2')
        self.assertEqual(ret.balance_to_keep_cents, 123456)
        self.assertEqual(ret.payout_interval, Intervals.TWO_WEEKS)
        self.assertTrue(ret.guid.startswith('PO'))

    def test_retrieve_active_only(self):
        payout = PayoutPlan.create(your_id=self.your_id,
                               group_id=self.group.guid,
                               name='PayoutPlan 2',
                               balance_to_keep_cents=123456,
                               payout_interval=Intervals.TWO_WEEKS
                               )
        payout.delete()
        with self.assertRaises(NoResultFound):
            PayoutPlan.retrieve(
                self.your_id, self.group.guid, active_only=True)

    def test_list(self):
        PayoutPlan.create('MY_TEST_PAYOUT_1', self.group.guid, 'PayoutPlan 1', 123456,
                      Intervals.WEEK)
        PayoutPlan.create('MY_TEST_PAYOUT_2', self.group.guid, 'PayoutPlan 2', 125828,
                      Intervals.TWO_WEEKS)
        PayoutPlan.create('MY_TEST_PAYOUT_3', self.group.guid, 'PayoutPlan 3', 259295,
                      Intervals.MONTH)
        PayoutPlan.create('MY_TEST_PAYOUT_4', self.group.guid, 'PayoutPlan 4', 628182,
                      Intervals.THREE_MONTHS)
        PayoutPlan.create(
            'MY_TEST_PAYOUT_4', self.group_2.guid, 'PayoutPlan 4', 628182,
            Intervals.THREE_MONTHS)
        self.assertEqual(
            len(PayoutPlan.query.join(Company).filter(Company.guid == self.group.guid,
                                                PayoutPlan.active == True).all()), 4)

    def test_list_active_only(self):
        PayoutPlan.create('MY_TEST_PAYOUT_1', self.group.guid, 'PayoutPlan 1', 123456,
                      Intervals.WEEK)
        PayoutPlan.create('MY_TEST_PAYOUT_2', self.group.guid, 'PayoutPlan 2', 125828,
                      Intervals.TWO_WEEKS)
        ret = PayoutPlan.create(
            'MY_TEST_PAYOUT_3', self.group.guid, 'PayoutPlan 3', 259295,
            Intervals.MONTH)
        PayoutPlan.create('MY_TEST_PAYOUT_4', self.group.guid, 'PayoutPlan 4', 628182,
                      Intervals.THREE_MONTHS)
        PayoutPlan.create(
            'MY_TEST_PAYOUT_4', self.group_2.guid, 'PayoutPlan 4', 628182,
            Intervals.THREE_MONTHS)
        ret.delete()
        self.assertEqual(len(
            PayoutPlan.query.join(Company).filter(Company.guid == self.group.guid,
                                            PayoutPlan.active == True).all()
        ), 3)


class TestUpdateDelete(TestPayout):

    def test_update(self):
        ret = PayoutPlan.create(your_id=self.your_id,
                            group_id=self.group.guid,
                            name='PayoutPlan 1',
                            balance_to_keep_cents=123456,
                            payout_interval=Intervals.custom(years=1)
                            )
        self.assertEqual(ret.name, 'PayoutPlan 1')
        ret.update('new name')
        new = PayoutPlan.retrieve(self.your_id, self.group.guid)
        self.assertEqual(new.name, 'new name')

    def test_delete(self):
        ret = PayoutPlan.create(your_id=self.your_id,
                            group_id=self.group.guid,
                            name='PayoutPlan 2',
                            balance_to_keep_cents=123456,
                            payout_interval=Intervals.TWO_WEEKS
                            )
        self.assertTrue(ret.active)
        ret.delete()
        new = PayoutPlan.retrieve(self.your_id, self.group.guid)
        self.assertFalse(new.active)


class TestValidators(TestPayout):

    def test_balance_to_keep_cents(self):
        with self.assertRaises(ValueError):
            PayoutPlan.create(your_id=self.your_id,
                          group_id=self.group.guid,
                          name='PayoutPlan 2',
                          balance_to_keep_cents=-1000,
                          payout_interval=Intervals.TWO_WEEKS
                          )

    def test_payout_interval(self):
        with self.assertRaises(StatementError):
            PayoutPlan.create(your_id=self.your_id,
                          group_id=self.group.guid,
                          name='PayoutPlan 2',
                          balance_to_keep_cents=1000,
                          payout_interval="HEY"
                          )


if __name__ == '__main__':
    import unittest

    unittest.main()
