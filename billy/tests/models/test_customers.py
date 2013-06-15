from __future__ import unicode_literals

from sqlalchemy.exc import *
from sqlalchemy.orm import *

from billy.models import Customer, Group
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
        Customer.create(
            external_id=self.external_id,
            group_id=self.group
        )
        ret = Customer.retrieve(self.external_id, self.group)




    def test_retrieve_dne(self):
        pass


    def test_retrieve_params(self):
        pass

    def test_list(self):
        pass


class TestCoupon(TestCustomer):
    def test_apply_coupon(self):
        pass


    def test_apply_coupon_dne(self):
        pass


    def test_coupon_max_redeemed(self):
        pass

    def test_remove_coupon(self):
        pass


    def test_remove_coupon_empty(self):
        pass


    def test_coupon_repeating(self):
        pass


class TestUpdatePlan(TestCustomer):
    def test_update_plan(self):
        pass

    def test_at_period_end(self):
        pass

    def test_custom_start_dt(self):
        pass


    def test_trial_first(self):
        pass


    def test_trial_repeat(self):
        pass


    def test_without_coupon(self):
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


    def test_is_debtor_low(self):
        pass

    def test_is_debtor_high(self):
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







