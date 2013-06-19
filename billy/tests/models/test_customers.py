from __future__ import unicode_literals
from datetime import datetime
from decimal import Decimal

from freezegun import freeze_time
from pytz import UTC
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from billy.models import Customer, Group, Coupon, Plan, PlanInvoice, Payout, PayoutInvoice
from billy.utils.intervals import Intervals
from billy.tests import BalancedTransactionalTestCase, rel_delta_to_sec


class TestCustomer(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestCustomer, self).setUp()
        self.external_id = 'MY_TEST_CUSTOMER'
        self.group = 'BILLY_TEST_MARKETPLACE'
        self.group_2 = 'BILLY_TEST_MARKETPLACE_2'
        Group.create(self.group)
        Group.create(self.group_2)


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
        self.plan_2 = Plan.create(
            external_id='MY_TEST_PLAN_2',
            group_id=self.group,
            name='Starter',
            price_cents=500,
            plan_interval=Intervals.TWO_WEEKS,
            trial_interval=Intervals.MONTH
        )

    def test_update_first(self):
        with freeze_time('2013-02-01'):
            self.customer.update_plan(self.plan.external_id)
            invoice = PlanInvoice.retrieve(
                self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
                active_only=True)
            self.assertEqual(invoice.relevant_plan, self.plan.external_id)
            self.assertEqual(invoice.start_dt, datetime.now(UTC))
            should_end = datetime.now(
                UTC) + self.plan.plan_interval + self.plan.trial_interval
            self.assertEqual(invoice.end_dt, should_end)
            self.assertEqual(invoice.original_end_dt, should_end)
            self.assertEqual(
                invoice.due_dt, datetime.now(UTC) + self.plan.trial_interval)
            self.assertEqual(invoice.amount_base_cents, self.plan.price_cents)
            self.assertEqual(
                invoice.amount_after_coupon_cents, self.plan.price_cents)
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
        invoice_old = PlanInvoice.retrieve(
            self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
            active_only=False)
        invoice_new = PlanInvoice.retrieve(
            self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
            active_only=True)
        self.assertEqual(invoice_new.remaining_balance_cents, 5000)
        self.assertAlmostEqual(
            Decimal(invoice_old.remaining_balance_cents) / Decimal(1000), Decimal(ratio), places=1)

    def test_at_period_end(self):
        self.customer.update_plan(
            self.plan.external_id, quantity=1, charge_at_period_end=True)
        invoice_new = PlanInvoice.retrieve(
            self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
            active_only=True)
        self.assertEqual(invoice_new.end_dt, invoice_new.due_dt)

    def test_custom_start_dt(self):
        dt = datetime(2013, 2, 1, tzinfo=UTC)
        self.customer.update_plan(
            self.plan.external_id, quantity=1, start_dt=dt)
        invoice_new = PlanInvoice.retrieve(
            self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
            active_only=True)
        self.assertEqual(invoice_new.start_dt, dt)
        self.assertEqual(
            invoice_new.due_dt, invoice_new.start_dt + self.plan.trial_interval)
        self.assertEqual(invoice_new.end_dt, invoice_new.start_dt +
                         self.plan.trial_interval + self.plan.plan_interval)

    def test_can_trial(self):
        with freeze_time('2013-01-01'):
            self.customer.update_plan(self.plan.external_id, quantity=1)
        with freeze_time('2013-01-15'):
            self.customer.update_plan(self.plan.external_id, quantity=5)
        invoice_old = PlanInvoice.retrieve(
            self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
            active_only=False)
        invoice_new = PlanInvoice.retrieve(
            self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
            active_only=True)
        self.assertEqual(
            invoice_old.due_dt, invoice_old.start_dt + self.plan.trial_interval)
        self.assertEqual(invoice_new.due_dt, invoice_new.start_dt)

    def test_with_coupon(self):
        price_off = 500
        percent_off = 50
        new_coupon = Coupon.create(
            'MY_TEST_COUPON', self.group, 'Yo', price_off_cents=price_off,
            percent_off_int=percent_off, max_redeem=5, repeating=2)
        self.customer.apply_coupon(new_coupon.external_id)
        self.customer.update_plan(self.plan.external_id, quantity=1)
        invoice = PlanInvoice.retrieve(
            self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
            active_only=True)
        self.assertEqual(invoice.remaining_balance_cents, (
            self.plan.price_cents - 500) * Decimal(percent_off) / 100)

    def test_cancel_now(self):
        with freeze_time('2013-01-01'):
            self.customer.update_plan(self.plan.external_id, quantity=1)
        with freeze_time('2013-01-15'):
            self.customer.cancel_plan(
                self.plan.external_id, cancel_at_period_end=False)
            invoice = PlanInvoice.retrieve(
                self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
                active_only=False)
            self.assertEqual(invoice.end_dt.astimezone(UTC), datetime.now(UTC))

    def test_cancel_at_end(self):
        with freeze_time('2013-01-01'):
            self.customer.update_plan(self.plan.external_id, quantity=1)
        with freeze_time('2013-01-15'):
            self.customer.cancel_plan(
                self.plan.external_id, cancel_at_period_end=True)
        with freeze_time('2013-01-17'):
            self.customer.update_plan(self.plan.external_id, quantity=1)
            invoice_old = PlanInvoice.retrieve(
                self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
                active_only=False)
            self.assertEqual(invoice_old.end_dt, datetime.now(UTC))
            invoice_new = PlanInvoice.retrieve(
                self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
                active_only=True)
            self.assertFalse(invoice_old.active, False)
            self.assertEqual(invoice_old.prorated, True)

    def test_can_trial_plan(self):
        with freeze_time('2013-01-01'):
            self.customer.update_plan(self.plan.external_id, quantity=1)
        with freeze_time('2013-01-15'):
            self.customer.update_plan(self.plan.external_id, quantity=1)
        invoice_old = PlanInvoice.retrieve(
            self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
            active_only=False)
        invoice_new = PlanInvoice.retrieve(
            self.customer.external_id, self.customer.group_id, 'MY_TEST_PLAN',
            active_only=True)
        self.assertTrue(invoice_old.includes_trial)
        self.assertFalse(invoice_new.includes_trial)

    def test_active_plans(self):
        self.customer.update_plan(self.plan.external_id, quantity=1)
        self.assertEqual(len(self.customer.active_plans), 1)
        self.customer.update_plan(self.plan_2.external_id, quantity=3)
        self.assertEqual(len(self.customer.active_plans), 2)

    def test_current_debt(self):
        with freeze_time('2013-01-01'):
            self.customer.update_plan(self.plan.external_id, quantity=1)
            self.assertEqual(self.customer.current_debt, 0)
        with freeze_time('2013-01-09'):
            self.assertEqual(self.customer.current_debt, 1000)

    def test_is_debtor(self):
        with freeze_time('2013-01-01'):
            self.customer.update_plan(self.plan.external_id, quantity=1)
            self.assertEqual(self.customer.current_debt, 0)
        with freeze_time('2013-01-09'):
            self.assertTrue(self.customer.is_debtor(900), 1000)




class TestPayout(TestCustomer):

    def setUp(self):
        super(TestPayout, self).setUp()
        self.customer = Customer.create(
            external_id=self.external_id,
            group_id=self.group
        )
        self.payout = Payout.create(
            external_id='MY_TEST_PAYOUT',
            group_id=self.group,
            name='Pay me out!',
            balance_to_keep_cents=5000,
            payout_interval=Intervals.TWO_WEEKS
        )

    def test_change_payout(self):
        with freeze_time('2013-2-15'):
            self.customer.add_payout(self.payout.external_id)
            invoice = PayoutInvoice.retrieve(
                self.customer.external_id, self.group, self.payout.external_id, active_only=True)
            self.assertEqual(
                invoice.payout_date, datetime.now(UTC) + self.payout.payout_interval)

    def test_change_payout_dne(self):
        with self.assertRaises(NoResultFound):
            self.customer.add_payout('MY)PAYOUT_DNE')

    def test_add_payout_first_now(self):
        with freeze_time('2013-2-15'):
            self.customer.add_payout(self.payout.external_id, first_now=True)
            invoice = PayoutInvoice.retrieve(
                self.customer.external_id, self.group, self.payout.external_id, active_only=True)
            self.assertEqual(invoice.payout_date, datetime.now(UTC))

    def add_payout_not_first_now(self):
        with freeze_time('2013-2-15'):
            self.customer.add_payout(self.payout.external_id)
            invoice = PayoutInvoice.retrieve(
                self.customer.external_id, self.group, self.payout.external_id, active_only=True)
            self.assertEqual(
                invoice.payout_date, datetime.now(UTC) + self.payout.payout_interval)

    def test_add_payout_custom_start_dt(self):
        start_dt = datetime(2013, 4, 5, tzinfo=UTC)
        self.customer.add_payout(
            self.payout.external_id, first_now=True, start_dt=start_dt)
        invoice = PayoutInvoice.retrieve(
            self.customer.external_id, self.group, self.payout.external_id, active_only=True)
        self.assertEqual(invoice.payout_date, start_dt)

    def test_cancel_payout(self):
        self.customer.add_payout(self.payout.external_id)
        PayoutInvoice.retrieve(
            self.customer.external_id, self.customer.group_id, active_only=True)
        self.customer.cancel_payout(self.payout.external_id)
        with self.assertRaises(NoResultFound):
            PayoutInvoice.retrieve(
                self.customer.external_id, self.customer.group_id, active_only=True)

    def test_cancel_payout_dne(self):
        with self.assertRaises(NoResultFound):
            self.customer.cancel_payout('MY_PAYOUT_DNE')

    def test_cancel_payout_already_scheduled(self):
        self.customer.add_payout(self.payout.external_id)
        PayoutInvoice.retrieve(
            self.customer.external_id, self.customer.group_id, active_only=True)
        self.customer.cancel_payout(
            self.payout.external_id, cancel_scheduled=True)
        invoice = PayoutInvoice.retrieve(
            self.customer.external_id, self.customer.group_id,
            relevant_payout=self.payout.external_id)
        self.assertTrue(invoice.completed)
        self.assertFalse(invoice.active)


class TestRelations(TestCustomer):

    def setUp(self):
        super(TestRelations, self).setUp()
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
        self.plan_2 = Plan.create(
            external_id='MY_TEST_PLAN_2',
            group_id=self.group,
            name='Starter',
            price_cents=500,
            plan_interval=Intervals.TWO_WEEKS,
            trial_interval=Intervals.MONTH
        )
        self.payout = Payout.create(
            external_id='MY_TEST_PAYOUT',
            group_id=self.group,
            name='Pay me out!',
            balance_to_keep_cents=5000,
            payout_interval=Intervals.TWO_WEEKS
        )
        self.payout_2 = Payout.create(
            external_id='MY_TEST_PAYOUT_2',
            group_id=self.group,
            name='Pay me out!',
            balance_to_keep_cents=5000,
            payout_interval=Intervals.TWO_WEEKS
        )

    def test_coupons(self):
        coupon = Coupon.create(
            'MY_TEST_COUPON', self.group, 'my coup', 100, 5, 1, 20)
        self.customer.apply_coupon(coupon.external_id)
        self.assertTrue(self.customer.coupon)

    def test_plan_invoices(self):
        self.customer.update_plan(self.plan.external_id)
        self.customer.update_plan(self.plan_2.external_id)
        self.assertEqual(len(self.customer.plan_invoices), 2)

    def test_payout_invoices(self):
        self.customer.add_payout(self.payout.external_id)
        self.customer.add_payout(self.payout_2.external_id)
        self.assertEqual(len(self.customer.payout_invoices), 2)

    def test_plan_transactions(self):
        # Todo
        pass

    def test_payout_transactions(self):
        # Todo
        pass
