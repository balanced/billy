from __future__ import unicode_literals
from datetime import datetime

from freezegun import freeze_time
from mock import patch
from pytz import UTC
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from models import Group, Customer, Plan, PlanSubscription, PlanInvoice
from utils.intervals import Intervals
from tests import BalancedTransactionalTestCase


class TestPlanInvoice(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestPlanInvoice, self).setUp()
        self.plan_id = 'MY_TEST_PLAN'
        self.plan_id_2 = 'MY_TEST_PLAN_2'
        self.now = datetime.now(UTC)
        self.week = self.now + Intervals.WEEK
        self.two_weeks = self.now + Intervals.WEEK
        self.month = self.now + Intervals.MONTH
        self.group = Group.create('BILLY_TEST_MARKETPLACE')
        self.group_2 = Group.create('BILLY_TEST_MARKETPLACE_2')
        self.customer = Customer.create(
            'MY_TEST_CUSTOMER', self.group.guid, 'TESTBALID')
        self.customer_2 = Customer.create(
            'MY_TEST_CUSTOMER_2', self.group.guid, 'TESTBALID')
        self.customer_group2 = Customer.create(
            'MY_TEST_CUSTOMER_3', self.group_2.guid, 'TESTBALID')
        self.plan = Plan.create(
            external_id=self.plan_id,
            group_id=self.group.guid,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )
        self.plan_2 = Plan.create(
            external_id=self.plan_id_2,
            group_id=self.group.guid,
            name='Starter',
            price_cents=15000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )


class TestCreate(TestPlanInvoice):

    def test_create(self):
        inv = PlanSubscription.subscribe(self.customer, self.plan)
        PlanInvoice.create(
            subscription_id=inv.subscription.guid,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=1000,
            amount_after_coupon_cents=1000,
            amount_paid_cents=1000,
            remaining_balance_cents=1000,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
        )


class TestRetrieve(TestPlanInvoice):

    def test_create_and_retrieve(self):
        inv = PlanSubscription.subscribe(self.customer, self.plan)
        PlanInvoice.create(
            subscription_id=inv.subscription.guid,
            relevant_coupon=None,
            start_dt=self.now,
            end_dt=self.month,
            due_dt=self.week,
            amount_base_cents=1000,
            amount_after_coupon_cents=1000,
            amount_paid_cents=1000,
            remaining_balance_cents=1000,
            quantity=10,
            charge_at_period_end=False,
            includes_trial=False,
        )
        res = PlanInvoice.retrieve(
            self.customer, self.plan, active_only=True, last_only=True)
        self.assertEqual(res.amount_base_cents, 1000)

    def test_retrieve_params(self):
        with freeze_time(str(self.now)):
            inv = PlanSubscription.subscribe(self.customer, self.plan,
                                             quantity=10)
        self.assertEqual(inv.subscription.customer, self.customer)
        self.assertTrue(inv.subscription.is_active)
        self.assertEqual(inv.subscription.plan, self.plan)
        self.assertEqual(inv.relevant_coupon, None)
        self.assertEqual(inv.start_dt, self.now)
        self.assertEqual(inv.due_dt, self.week)
        self.assertEqual(inv.end_dt, self.month + Intervals.WEEK)
        self.assertEqual(inv.amount_base_cents, 10000)
        self.assertEqual(inv.amount_after_coupon_cents, 10000)
        self.assertEqual(inv.amount_paid_cents, 0)
        self.assertEqual(inv.remaining_balance_cents, 10000)
        self.assertEqual(inv.quantity, 10)
        self.assertFalse(inv.charge_at_period_end)
        self.assertTrue(inv.includes_trial)


class TestUtils(TestPlanInvoice):

    def setUp(self):
        super(TestUtils, self).setUp()

        with freeze_time(str(self.now)):
            sub = PlanSubscription(customer_id=self.customer.guid,
                                   plan_id=self.plan.guid)
            sub2 = PlanSubscription(customer_id=self.customer.guid,
                                    plan_id=self.plan_2.guid)
            sub3 = PlanSubscription(customer_id=self.customer_2.guid,
                                    plan_id=self.plan.guid)
            PlanSubscription.session.add_all([sub, sub2, sub3])
            PlanSubscription.session.commit()
            PlanInvoice.create(
                subscription_id=sub.guid,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.week,
                amount_base_cents=2000,
                amount_after_coupon_cents=800,
                amount_paid_cents=200,
                remaining_balance_cents=600,
                quantity=10,
                charge_at_period_end=False,
                includes_trial=False,
            )
            PlanInvoice.create(
                subscription_id=sub2.guid,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.week,
                amount_base_cents=2000,
                amount_after_coupon_cents=800,
                amount_paid_cents=200,
                remaining_balance_cents=600,
                quantity=10,
                charge_at_period_end=False,
                includes_trial=False,
            )
            PlanInvoice.create(
                subscription_id=sub3.guid,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.month,
                amount_base_cents=1000,
                amount_after_coupon_cents=800,
                amount_paid_cents=200,
                remaining_balance_cents=600,
                quantity=10,
                charge_at_period_end=False,
                includes_trial=False,
            )

    def test_needs_rollover(self):
        with freeze_time(str(self.month)):
            list = PlanInvoice.needs_plan_debt_cleared()
            for each in list:
                each.clear_plan_debt()
            list = PlanInvoice.need_rollover()
            self.assertEqual(len(list), 3)

    def test_rollover(self):
        with freeze_time(str(self.month)):
            list = PlanInvoice.needs_plan_debt_cleared()
            for each in list:
                each.clear_plan_debt()
            invoices = PlanInvoice.need_rollover()
            for invoice in invoices:
                invoice.rollover()

    def test_rollover_all(self):
        with freeze_time(str(self.month + Intervals.TWO_WEEKS)):
            PlanInvoice.clear_all_plan_debt()
            count_invoices = PlanInvoice.rollover_all()
            self.assertEqual(count_invoices, 3)

    def test_needs_debt_cleared(self):
        list = PlanInvoice.needs_plan_debt_cleared()
        self.assertEqual(len(list), 0)
        with freeze_time(str(self.two_weeks)):
            list = PlanInvoice.needs_plan_debt_cleared()
            self.assertEqual(len(list), 1)
        with freeze_time(str(self.month)):
            list = PlanInvoice.needs_plan_debt_cleared()
            self.assertEqual(len(list), 2)

    def test_clear_all_plan_debt(self):
        with freeze_time(str(self.month)):
            PlanInvoice.clear_all_plan_debt()
            self.assertEqual(len(PlanInvoice.needs_plan_debt_cleared()), 0)


class TestValidators(TestPlanInvoice):

    def setUp(self):
        super(TestValidators, self).setUp()
        self.sub_guid = PlanSubscription.subscribe(
            self.customer, self.plan).subscription.guid

    def test_amount_base_cents(self):
        with self.assertRaises(ValueError):
            PlanInvoice.create(
                subscription_id=self.sub_guid,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.week,
                amount_base_cents=-1000,
                amount_after_coupon_cents=1000,
                amount_paid_cents=1000,
                remaining_balance_cents=1000,
                quantity=10,
                charge_at_period_end=False,
                includes_trial=False,
            )

    def test_amount_after_coupon_cents(self):
        with self.assertRaises(ValueError):
            PlanInvoice.create(
                subscription_id=self.sub_guid,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.week,
                amount_base_cents=1000,
                amount_after_coupon_cents=-1000,
                amount_paid_cents=1000,
                remaining_balance_cents=1000,
                quantity=10,
                charge_at_period_end=False,
                includes_trial=False,
            )

    def test_amount_paid_cents(self):
        with self.assertRaises(ValueError):
            PlanInvoice.create(
                subscription_id=self.sub_guid,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.week,
                amount_base_cents=1000,
                amount_after_coupon_cents=1000,
                amount_paid_cents=-1000,
                remaining_balance_cents=1000,
                quantity=10,
                charge_at_period_end=False,
                includes_trial=False,
            )

    def test_quantity(self):
        with self.assertRaises(ValueError):
            PlanInvoice.create(
                subscription_id=self.sub_guid,
                relevant_coupon=None,
                start_dt=self.now,
                end_dt=self.month,
                due_dt=self.week,
                amount_base_cents=1000,
                amount_after_coupon_cents=1000,
                amount_paid_cents=1000,
                remaining_balance_cents=1000,
                quantity=-10,
                charge_at_period_end=False,
                includes_trial=False,
            )
