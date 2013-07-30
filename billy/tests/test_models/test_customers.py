from __future__ import unicode_literals
from datetime import datetime
from decimal import Decimal

from freezegun import freeze_time
from pytz import UTC
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from models import *
from utils.intervals import Intervals
from tests import BalancedTransactionalTestCase, rel_delta_to_sec


class TestCustomer(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestCustomer, self).setUp()
        self.external_id = 'MY_TEST_CUSTOMER'
        self.group_obj = Group.create('BILLY_TEST_MARKETPLACE')
        self.group = self.group_obj.guid
        self.group_2 = Group.create('BILLY_TEST_MARKETPLACE_2').guid


class TestCreate(TestCustomer):

    def test_create(self):
        Customer.create(
            external_id=self.external_id,
            group_id=self.group,
            balanced_id='TESTBALID'
        )

    def test_create_exists(self):
        Customer.create(
            external_id=self.external_id,
            group_id=self.group,
            balanced_id='TESTBALID'
        )
        with self.assertRaises(IntegrityError):
            Customer.create(
                external_id=self.external_id,
                group_id=self.group,
                balanced_id='TESTBALID'
            )

    def test_create_semi_colliding(self):
        Customer.create(
            external_id=self.external_id,
            group_id=self.group,
            balanced_id='TESTBALID'
        )
        Customer.create(
            external_id=self.external_id,
            group_id=self.group_2,
            balanced_id='TESTBALID'
        )
        first = Customer.retrieve(self.external_id, self.group)
        second = Customer.retrieve(self.external_id, self.group_2)
        self.assertNotEqual(first.guid, second.guid)


class TestRetrieve(TestCustomer):

    def test_create_and_retrieve(self):
        customer = Customer.create(
            external_id=self.external_id,
            group_id=self.group,
            balanced_id='TESTBALID'
        )
        ret = Customer.retrieve(self.external_id, self.group)
        self.assertEqual(customer, ret)

    def test_retrieve_dne(self):
        self.assertIsNone(Customer.retrieve('CUSTOMER_DNE', self.group))

    def test_retrieve_params(self):
        customer = Customer.create(
            external_id=self.external_id,
            group_id=self.group,
            balanced_id='TESTBALID'
        )
        ret = Customer.retrieve(self.external_id, self.group)
        self.assertEqual(customer.balanced_id, ret.balanced_id)
        self.assertEqual(customer.external_id, ret.external_id)
        self.assertEqual(customer.group_id, ret.group_id)

    def test_list(self):
        Customer.create('MY_TEST_CUS_1', self.group, 'TESTBALID')
        Customer.create('MY_TEST_CUS_2', self.group, 'TESTBALID')
        Customer.create('MY_TEST_CUS_3', self.group, 'TESTBALID')
        Customer.create('MY_TEST_CUS_4', self.group, 'TESTBALID')
        Customer.create('MY_TEST_CUS_1', self.group_2, 'TESTBALID')
        self.assertEqual(len(self.group_obj.customers), 4)


class TestCoupon(TestCustomer):

    def test_apply_coupon(self):
        customer = Customer.create(
            external_id=self.external_id,
            group_id=self.group,
            balanced_id='TESTBALID'
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
        self.assertEqual(customer.current_coupon, coupon.guid)

    def test_increase_max_redeem(self):
        coupon = Coupon.create(external_id='MY_TEST_COUPON',
                               group_id=self.group,
                               name='My coupon',
                               price_off_cents=100,
                               percent_off_int=10,
                               max_redeem=3,
                               repeating=-1,
                               )
        Customer.create('MY_TEST_CUS_1', self.group, 'TESTBALID').apply_coupon(coupon
                                                                               .external_id)
        self.assertEqual(coupon.count_redeemed, 1)
        Customer.create('MY_TEST_CUS_2', self.group, 'TESTBALID').apply_coupon(coupon
                                                                               .external_id)
        self.assertEqual(coupon.count_redeemed, 2)
        customer = Customer.create('MY_TEST_CUS_3', self.group, 'TESTBALID').apply_coupon(
            coupon.external_id)
        self.assertEqual(coupon.count_redeemed, 3)
        with self.assertRaises(ValueError):
            Customer.create('MY_TEST_CUS_4', self.group, 'TESTBALID').apply_coupon(
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
            Customer.create('MY_TEST_CUS_3', self.group, 'TESTBALID').apply_coupon(coupon
                                                                                   .external_id)

    def test_apply_coupon_dne(self):
        with self.assertRaises(NoResultFound):
            Customer.create(self.external_id, self.group, 'TESTBALID').apply_coupon(
                'TEST_COUPON_DNE'
            )

    def test_remove_coupon(self):
        customer = Customer.create(self.external_id, self.group, 'TESTBALID')
        coupon = Coupon.create(external_id='MY_TEST_COUPON',
                               group_id=self.group,
                               name='My coupon',
                               price_off_cents=100,
                               percent_off_int=10,
                               max_redeem=3,
                               repeating=-1,
                               )
        customer.apply_coupon(coupon.external_id)
        self.assertEqual(customer.current_coupon, coupon.guid)
        customer.remove_coupon()
        self.assertIsNone(customer.current_coupon)

    def test_remove_coupon_empty(self):
        customer = Customer.create(self.external_id, self.group, 'TESTBALID')
        customer.remove_coupon()


class TestUpdatePlan(TestCustomer):

    def setUp(self):
        super(TestUpdatePlan, self).setUp()
        self.customer = Customer.create(
            external_id=self.external_id,
            group_id=self.group,
            balanced_id='TESTBALID'
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
            PlanSubscription.subscribe(self.customer, self.plan)
            invoice = PlanInvoice.retrieve(self.customer, self.plan,
                                           last_only=True)
            self.assertEqual(invoice.subscription.plan, self.plan)
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

    def test_update_qty(self):
        with freeze_time('2013-01-01'):
            first = datetime.now(UTC)
            invoice_old = PlanSubscription.subscribe(self.customer, self.plan)
        with freeze_time('2013-01-15'):
            second = datetime.now(UTC)
            invoice_new = PlanSubscription.subscribe(self.customer, self.plan,
                                                     quantity=5)
        ratio = (second - (first + self.plan.trial_interval)).total_seconds() / rel_delta_to_sec(
            self.plan.plan_interval)
        self.assertEqual(invoice_new.remaining_balance_cents, 5000)
        self.assertAlmostEqual(
            Decimal(invoice_old.remaining_balance_cents) / Decimal(1000),
            Decimal(ratio), places=1)

    def test_at_period_end(self):
        PlanSubscription.subscribe(self.customer, self.plan,
                                   quantity=1, charge_at_period_end=True)
        invoice_new = PlanInvoice.retrieve(
            self.customer, self.plan, True, True)
        self.assertEqual(invoice_new.end_dt, invoice_new.due_dt)

    def test_custom_start_dt(self):
        dt = datetime(2013, 2, 1, tzinfo=UTC)
        invoice_new = PlanSubscription.subscribe(self.customer, self.plan,
                                                 start_dt=dt)
        self.assertEqual(invoice_new.start_dt, dt)
        self.assertEqual(
            invoice_new.due_dt, invoice_new.start_dt + self.plan.trial_interval)
        self.assertEqual(invoice_new.end_dt, invoice_new.start_dt +
                         self.plan.trial_interval + self.plan.plan_interval)

    def test_can_trial(self):
        with freeze_time('2013-01-01'):
            invoice_old = PlanSubscription.subscribe(
                self.customer, self.plan, 1)
        with freeze_time('2013-01-15'):
            invoice_new = PlanSubscription.subscribe(
                self.customer, self.plan, 5)
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
        invoice = PlanSubscription.subscribe(self.customer, self.plan)
        self.assertEqual(invoice.remaining_balance_cents, (
            self.plan.price_cents - 500) * Decimal(percent_off) / 100)

    def test_cancel_now(self):
        with freeze_time('2013-01-01'):
            old_invoice = PlanSubscription.subscribe(self.customer, self.plan)
        with freeze_time('2013-01-15'):
            invoice = PlanSubscription.unsubscribe(self.customer,
                                                   self.plan, cancel_at_period_end=False)
            self.assertEqual(invoice.end_dt, datetime.now(UTC))

    def test_cancel_at_end(self):
        with freeze_time('2013-01-01'):
            invoice_old = PlanSubscription.subscribe(self.customer, self.plan)
        with freeze_time('2013-01-15'):
            PlanSubscription.unsubscribe(self.customer, self.plan,
                                         cancel_at_period_end=True)
            sub = PlanSubscription.query.filter(
                PlanSubscription.customer_id == self.customer.guid,
                PlanSubscription.plan_id == self.plan.guid).first()
            self.assertEqual(sub.is_active, False)
        with freeze_time('2013-01-17'):
            invoice_new = PlanSubscription.subscribe(self.customer, self.plan)
            self.assertEqual(invoice_old.end_dt, datetime.now(UTC))
            self.assertEqual(invoice_old.prorated, True)

    def test_can_trial_plan(self):
        with freeze_time('2013-01-01'):
            invoice_old = PlanSubscription.subscribe(self.customer, self.plan)
        with freeze_time('2013-01-15'):
            invoice_new = PlanSubscription.subscribe(self.customer, self.plan)
        self.assertTrue(invoice_old.includes_trial)
        self.assertFalse(invoice_new.includes_trial)

    def test_active_plans(self):
        PlanSubscription.subscribe(self.customer, self.plan)
        self.assertEqual(len(PlanSubscription.active_plans(self.customer)), 1)
        PlanSubscription.subscribe(self.customer, self.plan_2, quantity=3)
        self.assertEqual(len(PlanSubscription.active_plans(self.customer)), 2)

    def test_current_debt(self):
        with freeze_time('2013-01-01'):
            PlanSubscription.subscribe(self.customer, self.plan)
            self.assertEqual(self.customer.plan_debt, 0)
        with freeze_time('2013-01-09'):
            self.assertEqual(self.customer.plan_debt, 1000)

    def test_is_debtor(self):
        with freeze_time('2013-01-01'):
            PlanSubscription.subscribe(self.customer, self.plan)
            self.assertEqual(self.customer.plan_debt, 0)
        with freeze_time('2013-01-09'):
            self.assertTrue(self.customer.is_debtor(900))


class TestPayout(TestCustomer):

    def setUp(self):
        super(TestPayout, self).setUp()
        self.customer = Customer.create(
            external_id=self.external_id,
            group_id=self.group,
            balanced_id='TESTBALID'
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
            invoice = PayoutSubscription.subscribe(self.customer, self.payout)
            self.assertEqual(
                invoice.payout_date, datetime.now(UTC) + self.payout.payout_interval)

    def test_add_payout_first_now(self):
        with freeze_time('2013-2-15'):
            invoice = PayoutSubscription.subscribe(
                self.customer, self.payout, True)
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
        invoice = PayoutSubscription.subscribe(
            self.customer, self.payout, True, start_dt)
        self.assertEqual(invoice.payout_date, start_dt)

    def test_cancel_payout(self):
        PayoutSubscription.subscribe(self.customer, self.payout)
        result = PayoutSubscription.query.filter(
            PayoutSubscription.customer_id == self.customer.guid,
            PayoutSubscription.payout_id == self.payout.guid,
            PayoutSubscription.is_active == True).one()
        PayoutSubscription.unsubscribe(self.customer, self.payout)
        with self.assertRaises(NoResultFound):
            PayoutSubscription.query.filter(
                PayoutSubscription.customer_id == self.customer.guid,
                PayoutSubscription.payout_id == self.payout.guid,
                PayoutSubscription.is_active == True).one()

    def test_cancel_payout_already_scheduled(self):
        invoice = PayoutSubscription.subscribe(self.customer, self.payout)
        PayoutSubscription.unsubscribe(self.customer, self.payout,
                                       cancel_scheduled=True)
        invoice = PayoutSubscription.query.filter(
            PayoutSubscription.customer_id == self.customer.guid,
            PayoutSubscription.payout_id == self.payout.guid).one().invoices[0]
        self.assertTrue(invoice.completed)
        self.assertFalse(invoice.subscription.is_active)


class TestRelations(TestCustomer):

    def setUp(self):
        super(TestRelations, self).setUp()
        self.customer = Customer.create(
            external_id=self.external_id,
            group_id=self.group,
            balanced_id='TESTBALID'
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
        PlanSubscription.subscribe(self.customer, self.plan)
        PlanSubscription.subscribe(self.customer, self.plan_2)
        self.assertEqual(len(self.customer.plan_invoices), 2)

    def test_payout_invoices(self):
        PayoutSubscription.subscribe(self.customer, self.payout)
        PayoutSubscription.subscribe(self.customer, self.payout_2)
        self.assertEqual(len(self.customer.payout_invoices), 2)

    def test_plan_transactions(self):
        # Todo
        pass

    def test_payout_transactions(self):
        # Todo
        pass
