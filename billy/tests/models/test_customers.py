from __future__ import unicode_literals

from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from billy.models import Customer, Group, Coupon, Plan
from billy.utils.intervals import Intervals
from billy.tests import BalancedTransactionalTestCase


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
            external_id=self.external_id,
            group_id=self.group,
            name='Starter',
            price_cents=1000,
            plan_interval=Intervals.MONTH,
            trial_interval=Intervals.WEEK
        )

    def test_update_first(self):
        self.customer.update_plan(
            plan_id=self.plan.external_id,
            charge_at_period_end=False,
            start_dt=None
        )


    def test_update_qty(self):
        pass

    def test_at_period_end(self):
        pass

    def test_custom_start_dt(self):
        pass

    def test_trial_first(self):
        pass

    def test_trial_repeat(self):
        pass

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


class TestProrate(TestCustomer):

    def test_prorate_last_invoice(self):
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
