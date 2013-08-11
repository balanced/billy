from __future__ import unicode_literals
from datetime import datetime

from freezegun import freeze_time

from billy.models import ChargeSubscription
from billy.tests import BaseTestCase, fixtures


class CouponTest(BaseTestCase):
    def setUp(self):
        super(CouponTest, self).setUp()
        self.company = self.test_companies[0]
        self.customer = self.company.create_customer(
            **fixtures.sample_customer())
        self.plan = self.company.create_charge_plan(
            **fixtures.sample_plan(trial_interval=None))


    def basic_test(self):
        # Create the coupon
        coupon = self.company.create_coupon(
            your_id='10_OFF_COUPON',
            name='First Invoice 10 off',
            price_off_cents=0,
            percent_off_int=10,
            max_redeem=-1, # Maximum users on the coupon
            repeating=2,
            expire_at=datetime(year=2014, month=1, day=20)

        )
        with freeze_time('2014-01-01'):
            sub = self.plan.subscribe(self.customer, quantity=1,
                                      coupon=coupon)
            # Current invoice should be using the coupon
            invoice = sub.current_invoice
            self.assertEqual(invoice.coupon, coupon)



        # Shouldn't work since its expired.
        with freeze_time('2014-2-1'):
            with self.assertRaises(ValueError):
                self.plan.subscribe(self.customer, quantity=10, coupon=coupon)

        # Should use coupon since its attached to the subscription:
        with freeze_time('2014-02-2'):
            ChargeSubscription.generate_all_invoices()
            next_invoice = sub.current_invoice
            self.assertEqual(next_invoice.coupon, coupon)
            self.assertNotEqual(invoice, next_invoice)

