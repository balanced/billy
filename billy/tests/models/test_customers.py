from __future__ import unicode_literals

from sqlalchemy.exc import *
from sqlalchemy.orm import *

from billy.models import Customer, Group
from billy.tests import BalancedTransactionalTestCase


class TestCustomer(BalancedTransactionalTestCase):
    def setUp(self):
        super(TestCustomer, self).setUp()
        self.group = 'BILLY_TEST_MARKETPLACE'
        self.group_2 = 'BILLY_TEST_MARKETPLACE_2'
        Group.create_group(self.group)
        Group.create_group(self.group_2)


class TestCreate(TestCustomer):
    def test_create(self):
        pass


    def test_create_exists(self):
        pass


    def test_create_semi_colliding(self):
        pass


class TestRetrieve(TestCustomer):
    def test_create_and_retrieve(self):
        pass


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


class TestProrate(TestCustomer):
    def test_prorate_last_invoice(self):
        pass



class Test


class TestRelations(TestCustomer):
    pass


class TestValidators(TestCustomer):
    pass







