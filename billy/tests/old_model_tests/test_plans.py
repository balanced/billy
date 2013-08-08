from __future__ import unicode_literals

from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from models import ChargePlan, Company
from tests import BalancedTransactionalTestCase
from utils import Intervals


class TestPlan(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestPlan, self).setUp()
        self.your_id = 'MY_TEST_PLAN'
        self.group = Company.create('BILLY_TEST_MARKETPLACE')
        self.group_2 = Company.create('BILLY_TEST_MARKETPLACE_2')


class TestCreate(TestPlan):

    def test_create(self):
        ChargePlan.create(
            your_id=self.your_id,
            group_id=self.group.id,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )

    def test_create_exists(self):
        ChargePlan.create(
            your_id=self.your_id,
            group_id=self.group.id,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )
        with self.assertRaises(IntegrityError):
            ChargePlan.create(
                your_id=self.your_id,
                group_id=self.group.id,
                name='Starter',
                price_cents=1000,
                plan_interval=Intervals.MONTH,
                trial_interval=Intervals.WEEK
            )

    def test_create_semi_colliding(self):
        ChargePlan.create(
            your_id=self.your_id,
            group_id=self.group.id,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )
        ChargePlan.create(
            your_id=self.your_id,
            group_id=self.group_2.id,
            name='Starter',
            price_cents=1520,
            plan_interval=Intervals.WEEK,
            trial_interval=Intervals.MONTH
        )
        ret = ChargePlan.retrieve(self.your_id, self.group.id)
        self.assertEqual(ret.price_cents, 1000)
        ret = ChargePlan.retrieve(self.your_id, self.group_2.id)
        self.assertEqual(ret.price_cents, 1520)


class TestRetrieve(TestPlan):

    def test_create_and_retrieve(self):
        ChargePlan.create(
            your_id=self.your_id,
            group_id=self.group.id,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )
        ChargePlan.retrieve(self.your_id, self.group.id)

    def test_retrieve_dne(self):
        with self.assertRaises(NoResultFound):
            ChargePlan.retrieve('MY_TEST_PLAN_DNE', self.group.id)

    def test_retrieve_params(self):
        ChargePlan.create(
            your_id=self.your_id,
            group_id=self.group.id,
            name='Premium',
            price_cents=152592,
            plan_interval=Intervals.DAY,
            trial_interval=Intervals.MONTH
        )
        ret = ChargePlan.retrieve(self.your_id, self.group.id)
        self.assertEqual(ret.name, 'Premium')
        self.assertEqual(ret.trial_interval, Intervals.MONTH)
        self.assertEqual(ret.plan_interval, Intervals.DAY)
        self.assertEqual(ret.price_cents, 152592)
        self.assertTrue(ret.id.startswith('PL'))

    def test_retrieve_active_only(self):
        var = ChargePlan.create(
            your_id=self.your_id,
            group_id=self.group.id,
            name='Premium',
            price_cents=152592,
            plan_interval=Intervals.DAY,
            trial_interval=Intervals.MONTH
        )
        var.delete()
        with self.assertRaises(NoResultFound):
            ChargePlan.retrieve(self.your_id, self.group.id, active_only=True)

    def test_list(self):
        ChargePlan.create('MY_TEST_PLAN1', self.group.id, 'YO1', 1000,
                    Intervals.WEEK, Intervals.DAY)
        ChargePlan.create('MY_TEST_PLAN2', self.group.id, 'YO2', 1200,
                    Intervals.TWO_WEEKS, Intervals.MONTH)
        ChargePlan.create('MY_TEST_PLAN3', self.group.id, 'YO3', 1300,
                    Intervals.WEEK, Intervals.DAY)
        ChargePlan.create('MY_TEST_PLAN4', self.group.id, 'YO4', 1400,
                    Intervals.THREE_MONTHS, Intervals.WEEK)
        ChargePlan.create('MY_TEST_PLAN4', self.group_2.id, 'YO4', 1400,
                    Intervals.THREE_MONTHS, Intervals.WEEK)
        results = ChargePlan.list(self.group.id)
        self.assertEqual(len(results), 4)

    def test_list_active_only(self):
        ChargePlan.create('MY_TEST_PLAN1', self.group.id, 'YO1', 1000,
                    Intervals.WEEK, Intervals.DAY)
        ChargePlan.create('MY_TEST_PLAN2', self.group.id, 'YO2', 1200,
                    Intervals.TWO_WEEKS, Intervals.MONTH)
        to_cancel = ChargePlan.create('MY_TEST_PLAN3', self.group.id, 'YO3', 1300,
                                Intervals.WEEK, Intervals.DAY)
        ChargePlan.create('MY_TEST_PLAN4', self.group.id, 'YO4', 1400,
                    Intervals.THREE_MONTHS, Intervals.WEEK)
        to_cancel.delete()
        results = ChargePlan.list(self.group.id, active_only=True)
        self.assertEqual(len(results), 3)


class TestUpdateDelete(TestPlan):

    def test_update(self):
        plan = ChargePlan.create(
            your_id=self.your_id,
            group_id=self.group.id,
            name='Premium',
            price_cents=152592,
            plan_interval=Intervals.DAY,
            trial_interval=Intervals.MONTH
        )
        plan.update(name='Starter')
        ret = ChargePlan.retrieve(self.your_id, self.group.id)
        self.assertEqual(ret.name, 'Starter')

    def test_delete(self):
        plan = ChargePlan.create(
            your_id=self.your_id,
            group_id=self.group.id,
            name='Premium',
            price_cents=152592,
            plan_interval=Intervals.DAY,
            trial_interval=Intervals.MONTH
        )
        plan.delete()
        ret = ChargePlan.retrieve(self.your_id, self.group.id)
        self.assertFalse(ret.active)


class TestValidators(TestPlan):

    def test_price_cents(self):
        with self.assertRaises(ValueError):
            ChargePlan.create(
                your_id=self.your_id,
                group_id=self.group.id,
                name='Premium',
                price_cents=-20,
                plan_interval=Intervals.DAY,
                trial_interval=Intervals.MONTH
            )

    def test_trial_interval(self):
        with self.assertRaises(StatementError):
            ChargePlan.create(
                your_id=self.your_id,
                group_id=self.group.id,
                name='Premium',
                price_cents=20,
                plan_interval=Intervals.DAY,
                trial_interval="HEY",
            )

    def test_plan_interval(self):
        with self.assertRaises(StatementError):
            ChargePlan.create(
                your_id=self.your_id,
                group_id=self.group.id,
                name='Premium',
                price_cents=20,
                plan_interval="HEY",
                trial_interval=Intervals.WEEK,
            )


if __name__ == '__main__':
    import unittest
    unittest.main()
