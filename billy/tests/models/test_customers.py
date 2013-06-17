from __future__ import unicode_literals
from datetime import datetime
from decimal import Decimal

from freezegun import freeze_time
from pytz import UTC
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from billy.models import Customer, Group, Coupon, Plan, PlanInvoice
from billy.utils.intervals import Intervals
from billy.tests import BalancedTransactionalTestCase, rel_delta_to_sec


class TestCustomer(BalancedTransactionalTestCase):
    def setUp(self):
        super(TestCustomer, self).setUp()
        self.external_id = 'MY_TEST_CUSTOMER'
        self.group = 'BILLY_TEST_MARKETPLACE'
        self.group_2 = 'BILLY_TEST_MARKETPLACE_2'
        Group.create_group(self.group)
        Group.create_group(self.group_2)


class TestCreate(TestCustomer):
    def test_create(self):
        Customer.create(
            external_id=self.external_id,
            group_id=self.group
        )

    def test_create_exists(self):
        Customer.create(
            external_id=self.external_id,
            group_id=self.group
        )
        with self.assertRaises(IntegrityError):
            Customer.create(
                external_id=self.external_id,
                group_id=self.group
            )

    def test_create_semi_colliding(self):
        Customer.create(
            external_id=self.external_id,
            group_id=self.group
        )
        Customer.create(
            external_id=self.external_id,
            group_id=self.group_2
        )
        first = Customer.retrieve(self.external_id, self.group)
        second = Customer.retrieve(self.external_id, self.group_2)
        self.assertNotEqual(first.guid, second.guid)


class TestRetrieve(TestCustomer):
    def test_create_and_retrieve(self):
        customer = Customer.create(
            external_id=self.external_id,
            group_id=self.group
        )
        ret = Customer.retrieve(self.external_id, self.group)
        self.assertEqual(customer, ret)

    def test_retrieve_dne(self):
        with self.assertRaises(NoResultFound):
            Customer.retrieve('CUSTOMER_DNE', self.group)

    def test_retrieve_params(self):
        customer = Customer.create(
            external_id=self.external_id,
            group_id=self.group
        )
        ret = Customer.retrieve(self.external_id, self.group)
        self.assertEqual(customer, ret)

    def test_list(self):
        Customer.create('MY_TEST_CUS_1', self.group)
        Customer.create('MY_TEST_CUS_2', self.group)
        Customer.create('MY_TEST_CUS_3', self.group)
        Customer.create('MY_TEST_CUS_4', self.group)
        Customer.create('MY_TEST_CUS_1', self.group_2)
        self.assertEqual(len(Customer.list(self.group)), 4)


class TestCoupon(TestCustomer):
    def test_apply_coupon(self):
        customer = Customer.create(
            external_id=self.external_id,
            group_id=self.group
        )
        coupon = Coupon.create(external_id=self.external_id,
                               group_id=self.group,
                               name='My coupon',
                               price_off_cents=100,
                               percent_off_int=10,
                               max_redeem=5,
                               repeating=-1,
        )
        customer.apply_coupon(coupon.external_id)
        self.assertEqual(customer.current_coupon, coupon.external_id)

    def test_increase_max_redeem(self):
        coupon = Coupon.create(external_id='MY_TEST_COUPON',
                               group_id=self.group,
                               name='My coupon',
                               price_off_cents=100,
                               percent_off_int=10,
                               max_redeem=3,
                               repeating=-1,
        )
        Customer.create('MY_TEST_CUS_1', self.group).apply_coupon(coupon
        .external_id)
        self.assertEqual(coupon.count_redeemed, 1)
        Customer.create('MY_TEST_CUS_2', self.group).apply_coupon(coupon
        .external_id)
        self.assertEqual(coupon.count_redeemed, 2)
        customer = Customer.create('MY_TEST_CUS_3', self.group).apply_coupon(
            coupon
            .external_id)
        self.assertEqual(coupon.count_redeemed, 3)
        with self.assertRaises(ValueError):
            Customer.create('MY_TEST_CUS_4', self.group).apply_coupon(
                coupon
                .external_id)
        customer.remove_coupon()
        Customer.retrieve('MY_TEST_CUS_4', self.group).apply_coupon(
            coupon.external_id)

    def test_apply_inactive_coupon(self):
        coupon = Coupon.create(external_id='MY_TEST_COUPON',
                               group_id=self.group,
                               name='My coupon',
                               price_off_cents=100,
                               percent_off_int=10,
                               max_redeem=3,
                               repeating=-1,
        )
        coupon.delete()
        with self.assertRaises(NoResultFound):
            Customer.create('MY_TEST_CUS_3', self.group).apply_coupon(coupon
            .external_id)

    def test_apply_coupon_dne(self):
        with self.assertRaises(NoResultFound):
            Customer.create(self.external_id, self.group).apply_coupon(
                'TEST_COUPON_DNE'
            )

    def test_remove_coupon(self):
        customer = Customer.create(self.external_id, self.group)
        coupon = Coupon.create(external_id='MY_TEST_COUPON',
                               group_id=self.group,
                               name='My coupon',
                               price_off_cents=100,
                               percent_off_int=10,
                               max_redeem=3,
                               repeating=-1,
        )
        customer.apply_coupon(coupon.external_id)
        self.assertEqual(customer.current_coupon, coupon.external_id)
        customer.remove_coupon()
        self.assertIsNone(customer.current_coupon)

    def test_remove_coupon_empty(self):
        customer = Customer.create(self.external_id, self.group)
        customer.remove_coupon()


class TestUpdatePlan(TestCustomer):
    def setUp(self):
        super(TestUpdatePlan, self).setUp()
        self.customer = Customer.create(
            external_id=self.external_id,
            group_id=self.group
        )
        self.plan = Plan.create(
            external_id='MY_TEST_PLAN',
            group_id=self.group,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )

    def test_update_first(self):
        with freeze_time('2013-02-01'):
            self.customer.update_plan(self.plan.external_id)
            invoice = PlanInvoice.retrieve_invoice(self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
                                                   active_only=True)
            self.assertEqual(invoice.relevant_plan, self.plan.external_id)
            self.assertEqual(invoice.start_dt, datetime.now(UTC))
            should_end = datetime.now(UTC) + self.plan.plan_interval + self.plan.trial_interval
            self.assertEqual(invoice.end_dt, should_end)
            self.assertEqual(invoice.original_end_dt, should_end)
            self.assertEqual(invoice.due_dt, datetime.now(UTC) + self.plan.trial_interval)
            self.assertEqual(invoice.amount_base_cents, self.plan.price_cents)
            self.assertEqual(invoice.amount_after_coupon_cents, self.plan.price_cents)
            self.assertTrue(invoice.includes_trial)
            self.assertFalse(invoice.charge_at_period_end)
            self.assertEqual(invoice.quantity, 1)

    def test_update_plan_dne(self):
        with self.assertRaises(NoResultFound):
            self.customer.update_plan('MY_PLAN_DNE')

    def test_update_qty(self):
        with freeze_time('2013-01-01'):
            first = datetime.now(UTC)
            self.customer.update_plan(self.plan.external_id, quantity=1)
        with freeze_time('2013-01-15'):
            second = datetime.now(UTC)
            self.customer.update_plan(self.plan.external_id, quantity=5)
        ratio = (second - (first + self.plan.trial_interval)).total_seconds() / rel_delta_to_sec(
            self.plan.plan_interval)
        invoice_old = PlanInvoice.retrieve_invoice(self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
                                                   active_only=False)
        invoice_new = PlanInvoice.retrieve_invoice(self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
                                                   active_only=True)
        self.assertEqual(invoice_new.remaining_balance_cents, 5000)
        self.assertAlmostEqual(Decimal(invoice_old.remaining_balance_cents) / Decimal(1000), Decimal(ratio), places=1)

    def test_at_period_end(self):
        self.customer.update_plan(self.plan.external_id, quantity=1, charge_at_period_end=True)
        invoice_new = PlanInvoice.retrieve_invoice(self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
                                                   active_only=True)
        self.assertEqual(invoice_new.end_dt, invoice_new.due_dt)

    def test_custom_start_dt(self):
        dt = datetime(2013, 2, 1, tzinfo=UTC)
        self.customer.update_plan(self.plan.external_id, quantity=1, start_dt=dt)
        invoice_new = PlanInvoice.retrieve_invoice(self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
                                                   active_only=True)
        self.assertEqual(invoice_new.start_dt, dt)
        self.assertEqual(invoice_new.due_dt, invoice_new.start_dt + self.plan.trial_interval)
        self.assertEqual(invoice_new.end_dt, invoice_new.start_dt + self.plan.trial_interval + self.plan.plan_interval)

    def test_can_trial(self):
        with freeze_time('2013-01-01'):
            self.customer.update_plan(self.plan.external_id, quantity=1)
        with freeze_time('2013-01-15'):
            self.customer.update_plan(self.plan.external_id, quantity=5)
        invoice_old = PlanInvoice.retrieve_invoice(self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
                                                   active_only=False)
        invoice_new = PlanInvoice.retrieve_invoice(self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
                                                   active_only=True)
        self.assertEqual(invoice_old.due_dt, invoice_old.start_dt + self.plan.trial_interval)
        self.assertEqual(invoice_new.due_dt, invoice_new.start_dt)

    def test_with_coupon(self):
        pass

    def test_cancel_plan_now(self):
        pass

    def test_cancel_plan_at_period_end(self):
        pass

    def test_can_trial_plan(self):
        pass

    def test_sum_plan_debt(self):
        pass

    def test_is_debtor(self):
        pass


class TestPayout(TestCustomer):
    def add_payout(self):
        pass

    def add_payout_dne(self):
        pass

    def add_payout_first_now(self):
        pass

    def add_payout_not_first_now(self):
        pass

    def test_add_payout_custom_start_dt(self):
        pass

    def cancel_payout(self):
        pass

    def cancel_payout_dne(self):
        pass

    def cancel_payout_already_scheduled(self):
        pass


class TestProperties(TestCustomer):
    def test_active_plans(self):
        pass

    def test_plan_invoices_due(self):
        pass


class TestTask(TestCustomer):
    def test_clear_plan_debt_none(self):
        pass

    def test_clear_plan_deb(self):
        pass

    def test_retry(self):
        pass

    def test_coupon_repeating(self):
        pass


class TestRelations(TestCustomer):
    def test_coupons(self):
        pass

    def test_plan_invoices(self):
        pass

    def test_payout_invoices(self):
        pass

    def test_plan_transactions(self):
        pass

    def test_payout_transactions(self):
        pass
