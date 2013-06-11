from __future__ import unicode_literals
from datetime import datetime
import unittest

from pytz import UTC
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *
from freezegun import freeze_time

from billy.models import Coupon, Group
from billy.tests import BalancedTransactionalTestCase


class TestCoupon(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestCoupon, self).setUp()
        self.marketplace = 'BILLY_TEST_MARKETPLACE'
        self.marketplace_2 = 'BILLY_TEST_MARKETPLACE_2'
        Group.create_group(self.marketplace)
        Group.create_group(self.marketplace_2)

    def test_create_coupon(self):
        coupon = Coupon.create_coupon('MY_TEST_COUPON', self.marketplace,
                                      'My Coupon', 100, 10, 5, -1,
                                      expire_at=datetime.now(UTC))
        self.assertIsInstance(coupon, Coupon)

    def test_create_existing(self):
        coupon = Coupon.create_coupon('MY_TEST_COUPON', self.marketplace,
                                      'My Coupon', 100, 10, 5, -1,
                                      expire_at=datetime.now(UTC))
        self.assertRaises(FlushError, Coupon.create_coupon, 'MY_TEST_COUPON',
                          self.marketplace, 'Helloo', 120, 11, 6, 3,
                          expire_at=datetime.now(UTC))

    def test_create_semi_colliding(self):
        """
        Collides on external_id but not marketplace. Should work.
        """
        coupon = Coupon.create_coupon('MY_TEST_COUPON', self.marketplace,
                                      'My Coupon', 100, 10, 5, -1,
                                      expire_at=datetime.now(UTC))
        coupon2 = Coupon.create_coupon('MY_TEST_COUPON', self.marketplace_2,
                                       'My Coupon', 120, 10, 5, -1,
                                       expire_at=datetime.now(UTC))
        ret = Coupon.retrieve_coupon("MY_TEST_COUPON", self.marketplace)
        self.assertEqual(ret.price_off_cents, 100)
        ret = Coupon.retrieve_coupon("MY_TEST_COUPON", self.marketplace_2)
        self.assertEqual(ret.price_off_cents, 120)

    def test_create_and_retrieve(self):
        coupon = Coupon.create_coupon('MY_TEST_COUPON', self.marketplace,
                                      'My Coupon', 100, 10, 5, -1,
                                      expire_at=datetime.now(UTC))
        ret_coupon = Coupon.retrieve_coupon('MY_TEST_COUPON', self.marketplace)
        self.assertEqual(coupon, ret_coupon)

    def test_retrieve_dne(self):
        self.assertRaises(NoResultFound, Coupon.retrieve_coupon, "COUPON_DNE",
                          self.marketplace)

    def test_create_no_expire(self):
        coupon = Coupon.create_coupon('MY_TEST_COUPON', self.marketplace,
                                      'My Coupon', 100, 10, 5, -1)

        with freeze_time('2025-1-1'):
            Coupon.expire_coupons()
        ret = Coupon.retrieve_coupon('MY_TEST_COUPON', self.marketplace)
        self.assertTrue(ret.active)


    def test_retrieve_params(self):
        with freeze_time('2013-7-1'):
            now = datetime.now(UTC)
            coupon = Coupon.create_coupon('MY_TEST_COUPON', self.marketplace,
                                          'My Coupon', 60, 5, 3, 10,
                                          expire_at=now)
            ret = Coupon.retrieve_coupon('MY_TEST_COUPON', self.marketplace)
            self.assertEqual(ret.external_id, 'MY_TEST_COUPON')
            self.assertEqual(ret.group_id, self.marketplace)
            self.assertEqual(ret.name, 'My Coupon')
            self.assertEqual(ret.price_off_cents, 60)
            self.assertEqual(ret.percent_off_int, 5)
            self.assertEqual(ret.max_redeem, 3)
            self.assertEqual(ret.repeating, 10)
            self.assertEqual(ret.expire_at, now)
            self.assertLess(ret.created_at, now)
            self.assertTrue(ret.active)
            self.assertIsNone(ret.deleted_at)


    def test_retrieve_active_only(self):
        coupon = Coupon.create_coupon('MY_TEST_COUPON', self.marketplace,
                                      'My Coupon', 60, 5, 3, 10)
        Coupon.retrieve_coupon('MY_TEST_COUPON', self.marketplace)
        coupon.delete()
        self.assertRaises(NoResultFound, Coupon.retrieve_coupon,
                          'MY_TEST_COUPON', self.marketplace, active_only=True)

    def test_list_coupons(self):
        Coupon.create_coupon('MY_TEST_COUPON1', self.marketplace,
                             'My Coupon', 20, 1, 4, 11)
        Coupon.create_coupon('MY_TEST_COUPON2', self.marketplace,
                             'My Coupon', 60, 2, 3, 12)
        Coupon.create_coupon('MY_TEST_COUPON3', self.marketplace,
                             'My Coupon', 60, 3, 2, 13)
        Coupon.create_coupon('MY_TEST_COUPON4', self.marketplace,
                             'My Coupon', 60, 4, 1, 14)
        self.assertEqual(len(Coupon.list_coupons(self.marketplace)), 4)

    def test_list_coupons_active_only(self):
        Coupon.create_coupon('MY_TEST_COUPON1', self.marketplace,
                             'My Coupon', 20, 1, 4, 11)
        Coupon.create_coupon('MY_TEST_COUPON2', self.marketplace,
                             'My Coupon', 60, 2, 3, 12)
        temp = Coupon.create_coupon('MY_TEST_COUPON3', self.marketplace,
                                    'My Coupon', 60, 3, 2, 13)
        Coupon.create_coupon('MY_TEST_COUPON4', self.marketplace,
                             'My Coupon', 60, 4, 1, 14)
        temp.delete()
        self.assertEqual(len(Coupon.list_coupons(self.marketplace,
                                                 active_only=True)), 3)


    def test_update(self):
        now = datetime.now(UTC)
        coup = Coupon.create_coupon('MY_TEST_COUPON1', self.marketplace,
                                    'My Coupon', 20, 1, 4, 11)
        coup.update(new_name='New name', new_max_redeem=10,
                    new_expire_at=now, new_repeating=-1)
        updated_coup = Coupon.retrieve_coupon('MY_TEST_COUPON1',
                                              self.marketplace)
        self.assertEqual(updated_coup.name, 'New name')
        self.assertEqual(updated_coup.expire_at, now)
        self.assertEqual(updated_coup.repeating, -1)
        self.assertEqual(updated_coup.max_redeem, 10)

    def test_update_dne(self):
        self.assertRaises(NoResultFound, Coupon.update_coupon, 'COUPON_DNE',
                          self.marketplace, new_name='Hey')

    def test_update_classmethod(self):
        now = datetime.now(UTC)
        coup = Coupon.create_coupon('MY_TEST_COUPON1', self.marketplace,
                                    'My Coupon', 20, 1, 4, 11)
        Coupon.update_coupon('MY_TEST_COUPON1', self.marketplace,
                             new_name='New name', new_max_redeem=10,
                             new_expire_at=now, new_repeating=-1)
        updated_coup = Coupon.retrieve_coupon('MY_TEST_COUPON1',
                                              self.marketplace)
        self.assertEqual(updated_coup.name, 'New name')
        self.assertEqual(updated_coup.expire_at, now)
        self.assertEqual(updated_coup.repeating, -1)
        self.assertEqual(updated_coup.max_redeem, 10)

    def test_delete(self):
        Coupon.create_coupon('MY_TEST_COUPON', self.marketplace,
                             'My Coupon', 20, 1, 4, 11)
        coup = Coupon.retrieve_coupon('MY_TEST_COUPON', self.marketplace)
        self.assertTrue(coup.active)
        coup.delete()
        self.assertFalse(coup.active)
        coup = Coupon.retrieve_coupon('MY_TEST_COUPON', self.marketplace)
        self.assertFalse(coup.active)

    def test_delete_classmethod(self):
        Coupon.create_coupon('MY_TEST_COUPON', self.marketplace,
                             'My Coupon', 20, 1, 4, 11)
        coup = Coupon.retrieve_coupon('MY_TEST_COUPON', self.marketplace)
        self.assertTrue(coup.active)
        Coupon.delete_coupon('MY_TEST_COUPON', self.marketplace)
        coup = Coupon.retrieve_coupon('MY_TEST_COUPON', self.marketplace)
        self.assertFalse(coup.active)

    def test_delete_dne(self):
        self.assertRaises(NoResultFound, Coupon.delete_coupon, 'COUPON_DNE',
                          self.marketplace)

    def test_redeem_count(self):
        pass

    def test_expire_coupon(self):
        future = datetime(2013, 7, 1, tzinfo=UTC)
        Coupon.create_coupon('MY_TEST_COUPON', self.marketplace,
                             'My Coupon', 20, 1, 4, 11, expire_at=future)
        with freeze_time('2013-6-25'):
            Coupon.expire_coupons()
            self.assertEqual(Coupon.retrieve_coupon('MY_TEST_COUPON',
                                                    self.marketplace).active,
                             True)
        with freeze_time('2013-7-2'):
            Coupon.expire_coupons()
            self.assertEqual(Coupon.retrieve_coupon('MY_TEST_COUPON',
                                                    self.marketplace).active,
                             False)


    def test_expire_multiple(self):
        Coupon.create_coupon('MY_TEST_COUPON', self.marketplace,
                             'My Coupon', 20, 1, 4, 11,
                             expire_at=datetime(2013, 7, 1, tzinfo=UTC))
        Coupon.create_coupon('MY_TEST_COUPON2', self.marketplace,
                             'My Coupon 2', 20, 1, 4, 11,
                             expire_at=datetime(2013, 7, 5, tzinfo=UTC))
        Coupon.expire_coupons()
        self.assertEqual(len(Coupon.list_coupons(self.marketplace,
                                                 active_only=True)), 2)
        with freeze_time('2013-7-6'):
            Coupon.expire_coupons()
        self.assertEqual(len(Coupon.list_coupons(self.marketplace,
                                                 active_only=True)), 0)

    def test_max_redeem_validator(self):
        self.assertRaises(AssertionError, Coupon.create_coupon,
                          'MY_TEST_COUPON', self.marketplace, 'My Coupon',
                          20, 1, -5, 11,
                          expire_at=datetime(2013, 7, 1, tzinfo=UTC))

    def test_repeating_validator(self):
        self.assertRaises(AssertionError, Coupon.create_coupon,
                          'MY_TEST_COUPON', self.marketplace, 'My Coupon',
                          20, 1, 5, -10,
                          expire_at=datetime(2013, 7, 1, tzinfo=UTC))


    def test_percent_off_validator(self):
        self.assertRaises(AssertionError, Coupon.create_coupon,
                          'MY_TEST_COUPON', self.marketplace, 'My Coupon',
                          20, -20, 5, 10,
                          expire_at=datetime(2013, 7, 1, tzinfo=UTC))
        self.assertRaises(AssertionError, Coupon.create_coupon,
                          'MY_TEST_COUPON', self.marketplace, 'My Coupon',
                          20, 115, 5, 10,
                          expire_at=datetime(2013, 7, 1, tzinfo=UTC))


    def test_price_off_validator(self):
        self.assertRaises(AssertionError, Coupon.create_coupon,
                          'MY_TEST_COUPON', self.marketplace, 'My Coupon',
                          -10, 90, 5, 10,
                          expire_at=datetime(2013, 7, 1, tzinfo=UTC))

