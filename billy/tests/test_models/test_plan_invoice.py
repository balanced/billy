from __future__ import unicode_literals
from datetime import datetime

from freezegun import freeze_time
from mock import patch
from pytz import UTC
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from models import Company, Customer, ChargePlan, ChargeSubscription, ChargePlanInvoice
from utils.intervals import Intervals
from tests import BalancedTransactionalTestCase


class TestPlanInvoice(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestPlanInvoice, self).setUp()
        self.plan_id = 'MY_TEST_PLAN'
        self.plan_id_2 = 'MY_TEST_PLAN_2'
        self.now = datetime.utcnow()
        self.week = self.now + Intervals.WEEK
        self.two_weeks = self.now + Intervals.WEEK
        self.month = self.now + Intervals.MONTH
        self.group = Company.create('BILLY_TEST_MARKETPLACE')
        self.group_2 = Company.create('BILLY_TEST_MARKETPLACE_2')
        self.customer = Customer.create(
            'MY_TEST_CUSTOMER', self.group.id, 'TESTBALID')
        self.customer_2 = Customer.create(
            'MY_TEST_CUSTOMER_2', self.group.id, 'TESTBALID')
        self.customer_group2 = Customer.create(
            'MY_TEST_CUSTOMER_3', self.group_2.id, 'TESTBALID')
        self.plan = ChargePlan.create(
            your_id=self.plan_id,
            group_id=self.group.id,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )
        self.plan_2 = ChargePlan.create(
            your_id=self.plan_id_2,
            group_id=self.group.id,
            name='Starter',
            price_cents=15000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )


class TestCreate(TestPlanInvoice):

    def test_create(self):
        inv = ChargeSubscription.subscribe(self.customer, self.plan)
        ChargePlanInvoice.create(
            subscription_id=inv.subscription.id,
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
        inv = ChargeSubscription.subscribe(self.customer, self.plan)
        ChargePlanInvoice.create(
            subscription_id=inv.subscription.id,
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
        res = ChargePlanInvoice.retrieve(
            self.customer, self.plan, active_only=True, last_only=True)
        self.assertEqual(res.amount_base_cents, 1000)

    def test_retrieve_params(self):
        with freeze_time(str(self.now)):
            inv = ChargeSubscription.subscribe(self.customer, self.plan,
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
            sub = ChargeSubscription(customer_id=self.customer.id,
                                   plan_id=self.plan.id)
            sub2 = ChargeSubscription(customer_id=self.customer.id,
                                    plan_id=self.plan_2.id)
            sub3 = ChargeSubscription(customer_id=self.customer_2.id,
                                    plan_id=self.plan.id)
            ChargeSubscription.session.add_all([sub, sub2, sub3])
            ChargeSubscription.session.commit()
            ChargePlanInvoice.create(
                subscription_id=sub.id,
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
            ChargePlanInvoice.create(
                subscription_id=sub2.id,
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
            ChargePlanInvoice.create(
                subscription_id=sub3.id,
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
            list = ChargePlanInvoice.needs_plan_debt_cleared()
            for each in list:
                each.clear_plan_debt()
            list = ChargePlanInvoice.need_rollover()
            self.assertEqual(len(list), 3)

    def test_rollover(self):
        with freeze_time(str(self.month)):
            list = ChargePlanInvoice.needs_plan_debt_cleared()
            for each in list:
                each.clear_plan_debt()
            invoices = ChargePlanInvoice.need_rollover()
            for invoice in invoices:
                invoice.reinvoice()

    def test_rollover_all(self):
        with freeze_time(str(self.month + Intervals.TWO_WEEKS)):
            ChargePlanInvoice.clear_all_plan_debt()
            count_invoices = ChargePlanInvoice.rollover_all()
            self.assertEqual(count_invoices, 3)

    def test_needs_debt_cleared(self):
        list = ChargePlanInvoice.needs_plan_debt_cleared()
        self.assertEqual(len(list), 0)
        with freeze_time(str(self.two_weeks)):
            list = ChargePlanInvoice.needs_plan_debt_cleared()
            self.assertEqual(len(list), 1)
        with freeze_time(str(self.month)):
            list = ChargePlanInvoice.needs_plan_debt_cleared()
            self.assertEqual(len(list), 2)

    def test_clear_all_plan_debt(self):
        with freeze_time(str(self.month)):
            ChargePlanInvoice.clear_all_plan_debt()
            self.assertEqual(len(ChargePlanInvoice.needs_plan_debt_cleared()), 0)


class TestValidators(TestPlanInvoice):

    def setUp(self):
        super(TestValidators, self).setUp()
        self.sub_id = ChargeSubscription.subscribe(
            self.customer, self.plan).subscription.id

    def test_amount_base_cents(self):
        with self.assertRaises(ValueError):
            ChargePlanInvoice.create(
                subscription_id=self.sub_id,
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
            ChargePlanInvoice.create(
                subscription_id=self.sub_id,
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
            ChargePlanInvoice.create(
                subscription_id=self.sub_id,
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
            ChargePlanInvoice.create(
                subscription_id=self.sub_id,
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
