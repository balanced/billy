from __future__ import unicode_literals

from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from models import ChargePlan, Company
from tests import BalancedTransactionalTestCase
from utils import Intervals


class TestPlan(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestPlan, self).setUp()
        self.external_id = 'MY_TEST_PLAN'
        self.group = Company.create('BILLY_TEST_MARKETPLACE')
        self.group_2 = Company.create('BILLY_TEST_MARKETPLACE_2')


class TestCreate(TestPlan):

    def test_create(self):
        ChargePlan.create(
            external_id=self.external_id,
            group_id=self.group.guid,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )

    def test_create_exists(self):
        ChargePlan.create(
            external_id=self.external_id,
            group_id=self.group.guid,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )
        with self.assertRaises(IntegrityError):
            ChargePlan.create(
                external_id=self.external_id,
                group_id=self.group.guid,
                name='Starter',
                price_cents=1000,
                plan_interval=Intervals.MONTH,
                trial_interval=Intervals.WEEK
            )

    def test_create_semi_colliding(self):
        ChargePlan.create(
            external_id=self.external_id,
            group_id=self.group.guid,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )
        ChargePlan.create(
            external_id=self.external_id,
            group_id=self.group_2.guid,
            name='Starter',
            price_cents=1520,
            plan_interval=Intervals.WEEK,
            trial_interval=Intervals.MONTH
        )
        ret = ChargePlan.retrieve(self.external_id, self.group.guid)
        self.assertEqual(ret.price_cents, 1000)
        ret = ChargePlan.retrieve(self.external_id, self.group_2.guid)
        self.assertEqual(ret.price_cents, 1520)


class TestRetrieve(TestPlan):

    def test_create_and_retrieve(self):
        ChargePlan.create(
            external_id=self.external_id,
            group_id=self.group.guid,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )
        ChargePlan.retrieve(self.external_id, self.group.guid)

    def test_retrieve_dne(self):
        with self.assertRaises(NoResultFound):
            ChargePlan.retrieve('MY_TEST_PLAN_DNE', self.group.guid)

    def test_retrieve_params(self):
        ChargePlan.create(
            external_id=self.external_id,
            group_id=self.group.guid,
            name='Premium',
            price_cents=152592,
            plan_interval=Intervals.DAY,
            trial_interval=Intervals.MONTH
        )
        ret = ChargePlan.retrieve(self.external_id, self.group.guid)
        self.assertEqual(ret.name, 'Premium')
        self.assertEqual(ret.trial_interval, Intervals.MONTH)
        self.assertEqual(ret.plan_interval, Intervals.DAY)
        self.assertEqual(ret.price_cents, 152592)
        self.assertTrue(ret.guid.startswith('PL'))

    def test_retrieve_active_only(self):
        var = ChargePlan.create(
            external_id=self.external_id,
            group_id=self.group.guid,
            name='Premium',
            price_cents=152592,
            plan_interval=Intervals.DAY,
            trial_interval=Intervals.MONTH
        )
        var.delete()
        with self.assertRaises(NoResultFound):
            ChargePlan.retrieve(self.external_id, self.group.guid, active_only=True)

    def test_list(self):
        ChargePlan.create('MY_TEST_PLAN1', self.group.guid, 'YO1', 1000,
                    Intervals.WEEK, Intervals.DAY)
        ChargePlan.create('MY_TEST_PLAN2', self.group.guid, 'YO2', 1200,
                    Intervals.TWO_WEEKS, Intervals.MONTH)
        ChargePlan.create('MY_TEST_PLAN3', self.group.guid, 'YO3', 1300,
                    Intervals.WEEK, Intervals.DAY)
        ChargePlan.create('MY_TEST_PLAN4', self.group.guid, 'YO4', 1400,
                    Intervals.THREE_MONTHS, Intervals.WEEK)
        ChargePlan.create('MY_TEST_PLAN4', self.group_2.guid, 'YO4', 1400,
                    Intervals.THREE_MONTHS, Intervals.WEEK)
        results = ChargePlan.list(self.group.guid)
        self.assertEqual(len(results), 4)

    def test_list_active_only(self):
        ChargePlan.create('MY_TEST_PLAN1', self.group.guid, 'YO1', 1000,
                    Intervals.WEEK, Intervals.DAY)
        ChargePlan.create('MY_TEST_PLAN2', self.group.guid, 'YO2', 1200,
                    Intervals.TWO_WEEKS, Intervals.MONTH)
        to_cancel = ChargePlan.create('MY_TEST_PLAN3', self.group.guid, 'YO3', 1300,
                                Intervals.WEEK, Intervals.DAY)
        ChargePlan.create('MY_TEST_PLAN4', self.group.guid, 'YO4', 1400,
                    Intervals.THREE_MONTHS, Intervals.WEEK)
        to_cancel.delete()
        results = ChargePlan.list(self.group.guid, active_only=True)
        self.assertEqual(len(results), 3)


class TestUpdateDelete(TestPlan):

    def test_update(self):
        plan = ChargePlan.create(
            external_id=self.external_id,
            group_id=self.group.guid,
            name='Premium',
            price_cents=152592,
            plan_interval=Intervals.DAY,
            trial_interval=Intervals.MONTH
        )
        plan.update(name='Starter')
        ret = ChargePlan.retrieve(self.external_id, self.group.guid)
        self.assertEqual(ret.name, 'Starter')

    def test_delete(self):
        plan = ChargePlan.create(
            external_id=self.external_id,
            group_id=self.group.guid,
            name='Premium',
            price_cents=152592,
            plan_interval=Intervals.DAY,
            trial_interval=Intervals.MONTH
        )
        plan.delete()
        ret = ChargePlan.retrieve(self.external_id, self.group.guid)
        self.assertFalse(ret.active)


class TestValidators(TestPlan):

    def test_price_cents(self):
        with self.assertRaises(ValueError):
            ChargePlan.create(
                external_id=self.external_id,
                group_id=self.group.guid,
                name='Premium',
                price_cents=-20,
                plan_interval=Intervals.DAY,
                trial_interval=Intervals.MONTH
            )

    def test_trial_interval(self):
        with self.assertRaises(StatementError):
            ChargePlan.create(
                external_id=self.external_id,
                group_id=self.group.guid,
                name='Premium',
                price_cents=20,
                plan_interval=Intervals.DAY,
                trial_interval="HEY",
            )

    def test_plan_interval(self):
        with self.assertRaises(StatementError):
            ChargePlan.create(
                external_id=self.external_id,
                group_id=self.group.guid,
                name='Premium',
                price_cents=20,
                plan_interval="HEY",
                trial_interval=Intervals.WEEK,
            )


if __name__ == '__main__':
    import unittest
    unittest.main()
