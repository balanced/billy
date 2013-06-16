import sys
sys.argv.append('test')
from billy.tests import BalancedTransactionalTestCase
from billy.customer.utils import create_customer, retrieve_customer, \
    list_customers, apply_coupon_to_customer, remove_customer_coupon, \
    change_customer_plan, cancel_customer_plan, prorate_last_invoice, \
    cancel_customer_payout
from billy.coupons.utils import create_coupon
from billy.errors import NotFoundError, LimitReachedError, AlreadyExistsError
from datetime import datetime, timedelta
from pytz import UTC
from billy.models.create_tables import delete_and_replace_tables


class TestCustomer(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestCustomer, self).setUp()
        self.marketplace = 'test_my_marketplace'

    def test_create_and_retrieve(self):
        # Create the customer
        customer_id = 'test_my_customer_1'
        create_customer(customer_id, self.marketplace)
        # Retrieve the customer:
        result = retrieve_customer(customer_id, self.marketplace)
        self.assertEqual(result.customer_id, customer_id)
        self.assertEqual(result.marketplace, self.marketplace)
        self.assertLess(
            result.created_at - datetime.now(UTC), timedelta(seconds=30))
        # Try Creating duplicate
        self.assertRaises(AlreadyExistsError,
                          create_customer, customer_id, self.marketplace)
        # Retrieve notexisting customer:
        self.assertRaises(NotFoundError, retrieve_customer,
                          'test_my_customer_DNE', self.marketplace)

    def test_apply_coupon(self):
        # Create a coupon
        customer_id = 'test_my_customer_2'
        coupon_id = 'test_coupon'
        create_customer(customer_id, self.marketplace)
        create_coupon(coupon_id, self.marketplace, 'YO', 10, 5, -1, -1)
        apply_coupon_to_customer(customer_id, self.marketplace, coupon_id)
        customer_obj = retrieve_customer(customer_id, self.marketplace)
        self.assertEqual(customer_obj.current_coupon, coupon_id)
        self.assertEqual(customer_obj.coupon.coupon_id, coupon_id)

    # def test_apply_coupon_past_limit(self):
    #     max_limit = random.randint(1,40)
    #     create_coupon('limit_coupon', self.marketplace, 'Test', 10, 10,
    #                   max_limit, -1)
    #     for each in xrange(max_limit):
    #         cust_id =  "{}_id".format(each)
    #         create_customer(cust_id, self.marketplace)
    #         apply_coupon_to_customer(cust_id, self.marketplace, 'limit_coupon')
    #     self.assertRaises(LimitReachedError, apply_coupon_to_customer,
    #                       'extra', self.marketplace, 'limit_coupon')
    def test_apply_dne_coupon(self):
        cust_id = 'test_my_customer_5'
        create_customer(cust_id, self.marketplace)
        retrieve_customer(cust_id, self.marketplace)
        self.assertRaises(NotFoundError, apply_coupon_to_customer, cust_id,
                          self.marketplace, 'COUPON_DNE')

    # def test_update_plan(self):
    #     plan_id = 'test_my_plan_3'
    #     plan_name = ('Test Plan','New plan name')
    #     create_plan(plan_id, self.marketplace, plan_name[0], 1000,
    #                 Intervals.WEEK, Intervals.DAY)
    #     new_plan = retrieve_plan(plan_id, self.marketplace)
    #     self.assertEqual(new_plan.name, plan_name[0])
    #     update_plan(plan_id, self.marketplace, plan_name[1])
    #     changed_plan = retrieve_plan(plan_id, self.marketplace)
    #     self.assertEqual(changed_plan.name, plan_name[1])
    #
    #
    # def test_delete_plan(self):
    #     plan_id = 'test_my_plan_4'
    #     marketplace = self.marketplace
    #     create_plan(plan_id, marketplace, 'Test', 1000, Intervals.TWO_WEEKS, Intervals.DAY)
    #     current_plan = retrieve_plan(plan_id, marketplace)
    #     self.assertEqual(current_plan.active, True)
    #     delete_plan(plan_id, marketplace)
    #     deleted_plan = retrieve_plan(plan_id, self.marketplace)
    #     self.assertEqual(deleted_plan.active, False)
    #     self.assertLess(deleted_plan.deleted_at - datetime.now(UTC), timedelta(seconds=30))
    #     self.assertRaises(NotFoundError, delete_plan, 'test_coupon_DNE', self.marketplace)
    #
    #
    def test_list_customers(self):
        create_customer('test_my_customer_5', self.marketplace)
        create_customer('test_my_customer_6', self.marketplace,)
        list_of_plans = list_customers(self.marketplace)
        self.assertEqual(len(list_of_plans), 2)
    #
    # def tearDown(self):
    #     query_tool.query(Plan).filter(Plan.marketplace == self.marketplace).delete()
    #     self.assertFalse(list(self.marketplace))
