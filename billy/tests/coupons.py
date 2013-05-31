from unittest import TestCase
from billy.coupons.utils import create_coupon, delete_coupon, update_coupon, retrieve_coupon, list_coupons
from billy.errors import NotFoundError, AlreadyExistsError
from pytz import UTC
from datetime import datetime, timedelta
from billy.settings import query_tool
from billy.coupons.models import Coupon


class TestCoupons(TestCase):

    def setUp(self):
        self.marketplace = 'test_my_marketplace'
        self.next_week = datetime.now(UTC) + timedelta(days=7)
        self.next_day = datetime.now(UTC) + timedelta(days=1)
        query_tool.query(Coupon).filter(Coupon.marketplace == self.marketplace).delete()


    def test_create_and_retrieve(self):
        coupon_id = "test_my_coupon_1"
        create_coupon(coupon_id, self.marketplace, "Test Coupon", 200, 5, self.next_week, 10, -1)
        result = retrieve_coupon(coupon_id, self.marketplace)
        #check params
        self.assertEqual(result.coupon_id, coupon_id)
        self.assertEqual(result.marketplace, self.marketplace)
        self.assertEqual(result.name, "Test Coupon")
        self.assertEqual(result.price_off_cents, 200)
        self.assertEqual(result.percent_off_int, 5)
        self.assertEqual(result.expire, self.next_week)
        self.assertEqual(result.max_redeem, 10)
        self.assertEqual(result.repeating, -1)
        #Try creating duplicate
        self.assertRaises(AlreadyExistsError,create_coupon, coupon_id, self.marketplace, "Test Coupon 2", 300, 6,
                          self.next_day, 11, 5)
        self.assertRaises(NotFoundError, retrieve_coupon,'test_my_coupon_DNE', self.marketplace)

    def test_update_coupon(self):
        coupon_id = 'test_my_coupon_3'
        name = ('old name', 'new name')
        expire = (self.next_week, self.next_day)
        max_redeem = (10, 4)
        repeating = (-1, 1)
        create_coupon(coupon_id, self.marketplace, name[0], 200, 5, expire[0], max_redeem[0], repeating[0])
        current_coupon = retrieve_coupon(coupon_id, self.marketplace)
        self.assertEqual(current_coupon.name, name[0])
        self.assertEqual(current_coupon.max_redeem, max_redeem[0])
        self.assertEqual(current_coupon.repeating, repeating[0])
        self.assertEqual(current_coupon.expire, expire[0])
        update_coupon(coupon_id, self.marketplace, name[1], max_redeem[1], expire[1], repeating[1])
        updated_coupon = retrieve_coupon(coupon_id, self.marketplace)
        self.assertEqual(updated_coupon.name, name[1])
        self.assertEqual(updated_coupon.max_redeem, max_redeem[1])
        self.assertEqual(updated_coupon.repeating, repeating[1])
        self.assertEqual(updated_coupon.expire, expire[1])

    def test_delete_coupon(self):
        coupon_id = 'test_my_coupon_4'
        marketplace = self.marketplace
        create_coupon(coupon_id, self.marketplace, "Test Coupon", 200, 5, self.next_week, 10, -1)
        current_coupon = retrieve_coupon(coupon_id, marketplace)
        self.assertEqual(current_coupon.active, True)
        delete_coupon(coupon_id, marketplace)
        deleted_plan = retrieve_coupon(coupon_id, self.marketplace)
        self.assertEqual(deleted_plan.active, False)
        self.assertLess(deleted_plan.deleted_at - datetime.now(UTC), timedelta(seconds=30))
        self.assertRaises(NotFoundError, delete_coupon, 'test_coupon_DNE', self.marketplace)

    def test_list_coupon(self):
        create_coupon("test_coupon_5", self.marketplace, "Test Coupon 5", 200, 5, self.next_week, 10, -1)
        create_coupon("test_coupon_6", self.marketplace, "Test Coupon 6", 20, 10, self.next_week, 15, 5)
        list_of_plans = list_coupons(self.marketplace)
        self.assertEqual(len(list_of_plans), 2)
    #Todo TEST ACITVE ONLY
    #Todo test coupon limit/count
    #Todo Test coupon expiring
    #Todo test incr/decr max_redeem below times_used should max it inactive or active

    def tearDown(self):
        query_tool.query(Coupon).filter(Coupon.marketplace == self.marketplace).delete()
        self.assertFalse(list_coupons(self.marketplace))
        #TODO-me: Figure out why the last row isn't tearing down...SWITCH TO TRANSACTIONAL