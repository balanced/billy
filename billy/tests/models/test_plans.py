from __future__ import unicode_literals

from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from billy.models import Plan, Group
from billy.tests import BalancedTransactionalTestCase
from billy.utils import Intervals


class TestPlan(BalancedTransactionalTestCase):
    def setUp(self):
        super(TestPlan, self).setUp()
        self.external_id = 'MY_TEST_PLAN'
        self.group = 'BILLY_TEST_MARKETPLACE'
        self.group_2 = 'BILLY_TEST_MARKETPLACE_2'
        Group.create_group(self.group)
        Group.create_group(self.group_2)


class TestCreate(TestPlan):
    def test_create(self):
        Plan.create(
            external_id=self.external_id,
            group_id=self.group,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )

    def test_create_exists(self):
        Plan.create(
            external_id=self.external_id,
            group_id=self.group,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )
        with self.assertRaises(IntegrityError):
            Plan.create(
                external_id=self.external_id,
                group_id=self.group,
                name='Starter',
                price_cents=1000,
                plan_interval=Intervals.MONTH,
                trial_interval=Intervals.WEEK
            )

    def test_create_semi_colliding(self):
        Plan.create(
            external_id=self.external_id,
            group_id=self.group,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )
        Plan.create(
            external_id=self.external_id,
            group_id=self.group_2,
            name='Starter',
            price_cents=1520,
            plan_interval=Intervals.WEEK,
            trial_interval=Intervals.MONTH
        )
        ret = Plan.retrieve(self.external_id, self.group)
        self.assertEqual(ret.price_cents, 1000)
        ret = Plan.retrieve(self.external_id, self.group_2)
        self.assertEqual(ret.price_cents, 1520)


class TestRetrieve(TestPlan):
    def test_create_and_retrieve(self):
        Plan.create(
            external_id=self.external_id,
            group_id=self.group,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )
        Plan.retrieve(self.external_id, self.group)


    def test_retrieve_dne(self):
        with self.assertRaises(NoResultFound):
            Plan.retrieve('MY_TEST_PLAN_DNE', self.group)

    def test_retrieve_params(self):
        Plan.create(
            external_id=self.external_id,
            group_id=self.group,
            name='Premium',
            price_cents=152592,
            plan_interval=Intervals.DAY,
            trial_interval=Intervals.MONTH
        )
        ret = Plan.retrieve(self.external_id, self.group)
        self.assertEqual(ret.name, 'Premium')
        self.assertEqual(ret.trial_interval, Intervals.MONTH)
        self.assertEqual(ret.plan_interval, Intervals.DAY)
        self.assertEqual(ret.price_cents, 152592)
        self.assertTrue(ret.guid.startswith('PL'))



    def test_retrieve_active_only(self):
        var = Plan.create(
            external_id=self.external_id,
            group_id=self.group,
            name='Premium',
            price_cents=152592,
            plan_interval=Intervals.DAY,
            trial_interval=Intervals.MONTH
        )
        var.delete()
        with self.assertRaises(NoResultFound):
            Plan.retrieve(self.external_id, self.group, active_only=True)


    def test_list(self):
        Plan.create('MY_TEST_PLAN1', self.group, 'YO1', 1000,
                    Intervals.WEEK, Intervals.DAY)
        Plan.create('MY_TEST_PLAN2', self.group, 'YO2', 1200,
                    Intervals.TWO_WEEKS, Intervals.MONTH)
        Plan.create('MY_TEST_PLAN3', self.group, 'YO3', 1300,
                    Intervals.WEEK, Intervals.DAY)
        Plan.create('MY_TEST_PLAN4', self.group, 'YO4', 1400,
                    Intervals.THREE_MONTHS, Intervals.WEEK)
        Plan.create('MY_TEST_PLAN4', self.group_2, 'YO4', 1400,
                    Intervals.THREE_MONTHS, Intervals.WEEK)
        results = Plan.list(self.group)
        self.assertEqual(len(results), 4)


    def test_list_active_only(self):
        Plan.create('MY_TEST_PLAN1', self.group, 'YO1', 1000,
                    Intervals.WEEK, Intervals.DAY)
        Plan.create('MY_TEST_PLAN2', self.group, 'YO2', 1200,
                    Intervals.TWO_WEEKS, Intervals.MONTH)
        to_cancel = Plan.create('MY_TEST_PLAN3', self.group, 'YO3', 1300,
                                Intervals.WEEK, Intervals.DAY)
        Plan.create('MY_TEST_PLAN4', self.group, 'YO4', 1400,
                    Intervals.THREE_MONTHS, Intervals.WEEK)
        to_cancel.delete()
        results = Plan.list(self.group, active_only=True)
        self.assertEqual(len(results), 3)


class TestUpdateDelete(TestPlan):
    def test_update(self):
        plan = Plan.create(
            external_id=self.external_id,
            group_id=self.group,
            name='Premium',
            price_cents=152592,
            plan_interval=Intervals.DAY,
            trial_interval=Intervals.MONTH
        )
        plan.update(name='Starter')
        ret = Plan.retrieve(self.external_id, self.group)
        self.assertEqual(ret.name, 'Starter')


    def test_delete(self):
        plan = Plan.create(
            external_id=self.external_id,
            group_id=self.group,
            name='Premium',
            price_cents=152592,
            plan_interval=Intervals.DAY,
            trial_interval=Intervals.MONTH
        )
        plan.delete()
        ret = Plan.retrieve(self.external_id, self.group)
        self.assertFalse(ret.active)


class TestValidators(TestPlan):
    def test_price_cents(self):
        with self.assertRaises(ValueError):
            Plan.create(
                external_id=self.external_id,
                group_id=self.group,
                name='Premium',
                price_cents=-20,
                plan_interval=Intervals.DAY,
                trial_interval=Intervals.MONTH
            )

    def test_trial_interval(self):
        with self.assertRaises(StatementError):
            Plan.create(
                external_id=self.external_id,
                group_id=self.group,
                name='Premium',
                price_cents=20,
                plan_interval=Intervals.DAY,
                trial_interval="HEY",
            )

    def test_plan_interval(self):
        with self.assertRaises(StatementError):
            Plan.create(
                external_id=self.external_id,
                group_id=self.group,
                name='Premium',
                price_cents=20,
                plan_interval="HEY",
                trial_interval=Intervals.WEEK,
                )


if __name__ == '__main__':
    import unittest
    unittest.main()