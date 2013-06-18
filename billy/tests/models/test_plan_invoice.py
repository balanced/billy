from __future__ import unicode_literals

from billy.models import Group, Customer, PlanInvoice
from billy.tests import BalancedTransactionalTestCase

class TestPlanInvoice(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestPlanInvoice, self).setUp()
        self.customer = 'MY_TEST_CUSTOMER'
        self.customer_2 = 'MY_TEST_CUSTOMER_2'
        self.group = 'BILLY_TEST_MARKETPLACE'
        self.group_2 = 'BILLY_TEST_MARKETPLACE_2'
        Group.create_group(self.group)
        Group.create_group(self.group_2)
        Customer.create(self.customer, self.group)
        Customer.create(self.customer_2, self.group)






class TestCreate(TestPlanInvoice):

    def test_create(self):
        pass


    def test_create_exists(self):
        pass


    def test_create_exist_inactive(self):
        pass


    def test_create_semi_colliding(self):
        pass



class TestRetrieve(TestPlanInvoice):

    def test_create_and_retrieve(self):
        pass


    def test_retrieve_dne(self):
        pass


    def test_retrieve_params(self):
        pass


    def test_retrieve_active_only(self):
        pass

    def test_list(self):
        pass

    def test_list_active_only(self):
        pass



class TestUtils(TestPlanInvoice):


    def test_needs_debt_cleared(self):
        pass


    def test_needs_rollover(self):
        pass


    def test_rollover(self):
        pass


    def test_rollover_all(self):
        pass


    def test_clear_all_plan_debt(self):
        pass


class TestValidators(TestPlanInvoice):

    def test_amount_base_cents(self):
        pass

    def test_amount_after_coupon_cents(self):
        pass

    def test_amount_paid_cents(self):
        pass

    def test_remaining_balance_cents(self):
        pass

    def test_quantity(self):
        pass









