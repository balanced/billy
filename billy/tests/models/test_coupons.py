from __future__ import unicode_literals
from datetime import datetime

from freezegun import freeze_time
from pytz import UTC
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from billy.models import Coupon, Group
from billy.tests import BalancedTransactionalTestCase


class TestCoupon(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestCoupon, self).setUp()
        self.marketplace = 'BILLY_TEST_MARKETPLACE'
        self.marketplace_2 = 'BILLY_TEST_MARKETPLACE_2'
        Group.create_group(self.marketplace)
        Group.create_group(self.marketplace_2)


    def test_redeem_count(self):
        pass

    def test_expire(self):
        future = datetime(2013, 7, 1, tzinfo=UTC)
        Coupon.create(external_id='MY_TEST_COUPON',
                      group_id=self.marketplace,
                      name='My Coupon',
                      price_off_cents=20,
                      percent_off_int=1,
                      max_redeem=4,
                      repeating=11,
                      expire_at=future)
        with freeze_time('2013-6-25'):
            Coupon.expire_coupons()
            self.assertEqual(Coupon.retrieve('MY_TEST_COUPON',
                                                    self.marketplace).active,
                             True)
        with freeze_time('2013-7-2'):
            Coupon.expire_coupons()
            self.assertEqual(Coupon.retrieve('MY_TEST_COUPON',
                                            self.marketplace).active, False)


    def test_expire_multiple(self):
        Coupon.create(external_id='MY_TEST_COUPON',
                      group_id=self.marketplace,
                      name='My Coupon',
                      price_off_cents=20,
                      percent_off_int=1,
                      max_redeem=4,
                      repeating=11,
                      expire_at=datetime(2013, 7, 1, tzinfo=UTC))
        Coupon.create(external_id='MY_TEST_COUPON2',
                      group_id=self.marketplace,
                      name='My Coupon 2',
                      price_off_cents=20,
                      percent_off_int=1,
                      max_redeem=4,
                      repeating=11,
                      expire_at=datetime(2013, 7, 5, tzinfo=UTC))
        Coupon.expire_coupons()
        self.assertEqual(len(Coupon.list(self.marketplace,
                                                 active_only=True)), 2)
        with freeze_time('2013-7-6'):
            Coupon.expire_coupons()
        self.assertEqual(len(Coupon.list(self.marketplace,
                                                 active_only=True)), 0)



class TestCreate(TestCoupon):

    def test_create(self):
        now = datetime.now(UTC)
        coupon = Coupon.create(external_id='MY_TEST_COUPON',
                      group_id=self.marketplace,
                      name='My Coupon',
                      price_off_cents=100,
                      percent_off_int=10,
                      max_redeem=5,
                      repeating=-1,
                      expire_at=now)
        self.assertIsInstance(coupon, Coupon)

    def test_create_existing(self):
        now = datetime.now(UTC)
        Coupon.create(external_id='MY_TEST_COUPON',
                               group_id=self.marketplace,
                               name='My Coupon',
                               price_off_cents=120,
                               percent_off_int=11,
                               max_redeem=6,
                               repeating=3,
                               expire_at=now)

        with self.assertRaises(IntegrityError):
            Coupon.create(external_id='MY_TEST_COUPON',
                          group_id=self.marketplace,
                          name='New Name',
                          price_off_cents=130,
                          percent_off_int=15,
                          max_redeem=7,
                          repeating=9,
                          expire_at=now)


    def test_create_semi_colliding(self):
        """
        Collides on external_id but not marketplace. Should work.
        """
        now = datetime.now(UTC)
        Coupon.create(external_id='MY_TEST_COUPON',
                      group_id=self.marketplace,
                      name='My coupon',
                      price_off_cents=100,
                      percent_off_int=10,
                      max_redeem=5,
                      repeating=-1,
                      expire_at=now)
        Coupon.create(external_id='MY_TEST_COUPON',
                      group_id=self.marketplace_2,
                      name='My coupon',
                      price_off_cents=120,
                      percent_off_int=10,
                      max_redeem=5,
                      repeating=-1,
                      expire_at=now)
        ret = Coupon.retrieve("MY_TEST_COUPON", self.marketplace)
        self.assertEqual(ret.price_off_cents, 100)
        ret = Coupon.retrieve("MY_TEST_COUPON", self.marketplace_2)
        self.assertEqual(ret.price_off_cents, 120)


    def test_create_no_expire(self):
        now = datetime.now(UTC)
        Coupon.create(external_id='MY_TEST_COUPON',
                      group_id=self.marketplace,
                      name='My coupon',
                      price_off_cents=100,
                      percent_off_int=10,
                      max_redeem=5,
                      repeating=-1
                      )
        with freeze_time('2025-1-1'):
            Coupon.expire_coupons()
        ret = Coupon.retrieve('MY_TEST_COUPON', self.marketplace)
        self.assertTrue(ret.active)

class TestRetrieve(TestCoupon):

    def test_create_and_retrieve(self):
        coupon = Coupon.create(external_id='MY_TEST_COUPON',
                      group_id=self.marketplace,
                      name='My coupon',
                      price_off_cents=100,
                      percent_off_int=10,
                      max_redeem=5,
                      repeating=-1,
                      )
        ret_coupon = Coupon.retrieve('MY_TEST_COUPON', self.marketplace)
        self.assertEqual(coupon, ret_coupon)

    def test_retrieve_dne(self):
        with self.assertRaises(NoResultFound):
            Coupon.retrieve("COUPON_DNE",self.marketplace)



    def test_retrieve_params(self):
        with freeze_time('2013-7-1'):
            now = datetime.now(UTC)
            coupon = Coupon.create(external_id='MY_TEST_COUPON',
                                   group_id=self.marketplace,
                                   name='My coupon',
                                   price_off_cents=60,
                                   percent_off_int=5,
                                   max_redeem=3,
                                   repeating=10,
                                   expire_at=now)
            ret = Coupon.retrieve('MY_TEST_COUPON', self.marketplace)
            self.assertEqual(ret.external_id, 'MY_TEST_COUPON')
            self.assertEqual(ret.group_id, self.marketplace)
            self.assertEqual(ret.name, 'My coupon')
            self.assertEqual(ret.price_off_cents, 60)
            self.assertEqual(ret.percent_off_int, 5)
            self.assertEqual(ret.max_redeem, 3)
            self.assertEqual(ret.repeating, 10)
            self.assertEqual(ret.expire_at, now)
            self.assertLess(ret.created_at, now)
            self.assertTrue(ret.active)
            self.assertIsNone(ret.deleted_at)

    def test_retrieve_active_only(self):
        coupon = Coupon.create(external_id='MY_TEST_COUPON',
                               group_id=self.marketplace,
                               name='My coupon',
                               price_off_cents=60,
                               percent_off_int=5,
                               max_redeem=3,
                               repeating=10,
                               )
        Coupon.retrieve('MY_TEST_COUPON', self.marketplace)
        coupon.delete()
        with self.assertRaises(NoResultFound):
            Coupon.retrieve('MY_TEST_COUPON', self.marketplace,
                            active_only=True)

    def test_list(self):
        Coupon.create('MY_TEST_COUPON1', self.marketplace,
                      'My Coupon', 20, 1, 4, 11)
        Coupon.create('MY_TEST_COUPON2', self.marketplace,
                      'My Coupon', 60, 2, 3, 12)
        Coupon.create('MY_TEST_COUPON3', self.marketplace,
                      'My Coupon', 60, 3, 2, 13)
        Coupon.create('MY_TEST_COUPON4', self.marketplace,
                      'My Coupon', 60, 4, 1, 14)
        self.assertEqual(len(Coupon.list(self.marketplace)), 4)

    def test_list_active_only(self):
        Coupon.create('MY_TEST_COUPON1', self.marketplace,
                      'My Coupon', 20, 1, 4, 11)
        Coupon.create('MY_TEST_COUPON2', self.marketplace,
                      'My Coupon', 60, 2, 3, 12)
        temp = Coupon.create('MY_TEST_COUPON3', self.marketplace,
                             'My Coupon', 60, 3, 2, 13)
        Coupon.create('MY_TEST_COUPON4', self.marketplace,
                      'My Coupon', 60, 4, 1, 14)
        temp.delete()
        self.assertEqual(len(Coupon.list(self.marketplace,
                                         active_only=True)), 3)


class TestUpdateDelete(TestCoupon):

    def test_update(self):
        now = datetime.now(UTC)
        coup = Coupon.create(external_id='MY_TEST_COUPON1',
                             group_id=self.marketplace,
                             name='My coupon',
                             price_off_cents=20,
                             percent_off_int=1,
                             max_redeem=4,
                             repeating=11,
                             )
        coup.update(new_name='New name', new_max_redeem=10,
                    new_expire_at=now, new_repeating=-1)
        updated_coup = Coupon.retrieve('MY_TEST_COUPON1',
                                       self.marketplace)
        self.assertEqual(updated_coup.name, 'New name')
        self.assertEqual(updated_coup.expire_at, now)
        self.assertEqual(updated_coup.repeating, -1)
        self.assertEqual(updated_coup.max_redeem, 10)



    def test_delete(self):
        Coupon.create(external_id='MY_TEST_COUPON',
                      group_id=self.marketplace,
                      name='My coupon',
                      price_off_cents=20,
                      percent_off_int=1,
                      max_redeem=4,
                      repeating=11,
                      )
        coup = Coupon.retrieve('MY_TEST_COUPON', self.marketplace)
        self.assertTrue(coup.active)
        coup.delete()
        self.assertFalse(coup.active)
        coup = Coupon.retrieve('MY_TEST_COUPON', self.marketplace)
        self.assertFalse(coup.active)



class TestValidators(TestCoupon):

    def test_max_redeem_validator(self):
        with self.assertRaises(AssertionError):
            Coupon.create(external_id='MY_TEST_COUPON1',
                          group_id=self.marketplace,
                          name='My coupon',
                          price_off_cents=20,
                          percent_off_int=1,
                          max_redeem=-5,
                          repeating=11,
                          )

    def test_repeating_validator(self):
        with self.assertRaises(AssertionError):
            Coupon.create(external_id='MY_TEST_COUPON1',
                          group_id=self.marketplace,
                          name='My coupon',
                          price_off_cents=20,
                          percent_off_int=1,
                          max_redeem=-5,
                          repeating=-10,
                          )

    def test_percent_off_validator(self):
        with self.assertRaises(AssertionError):
            Coupon.create(external_id='MY_TEST_COUPON1',
                          group_id=self.marketplace,
                          name='My coupon',
                          price_off_cents=20,
                          percent_off_int=-20,
                          max_redeem=-5,
                          repeating=10,
                          )
        with self.assertRaises(AssertionError):
            Coupon.create(external_id='MY_TEST_COUPON1',
                          group_id=self.marketplace,
                          name='My coupon',
                          price_off_cents=110,
                          percent_off_int=-20,
                          max_redeem=-5,
                          repeating=10,
                          )


    def test_price_off_validator(self):
        with self.assertRaises(AssertionError):
            Coupon.create(external_id='MY_TEST_COUPON1',
                          group_id=self.marketplace,
                          name='My coupon',
                          price_off_cents=-10,
                          percent_off_int=20,
                          max_redeem=5,
                          repeating=10,
                          )


if __name__ == '__main__':
    import unittest
    unittest.main()