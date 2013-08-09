from __future__ import unicode_literals

from freezegun import freeze_time

from utils.intervals import Intervals
from tests import BaseTestCase, fixtures


class PayoutPlanTest(BaseTestCase):
    def setUp(self):
        super(PayoutPlanTest, self).setUp()
        self.company = self.test_companies[0]

        self.customer = self.company.create_customer(
            **fixtures.sample_customer())

    def basic_test(self):
        # Create the plan
        payout = self.company.create_payout_plan(
            your_id='20K_DOLLA_PLAN',
            name='The 5 dollar Payout',
            balance_to_keep_cents=200000,
            payout_interval=Intervals.WEEK
        )

        payout_2 = self.company.create_payout_plan(
            your_id='EMPTY_OUT_PLAN',
            name='The 5 dollar Payout',
            balance_to_keep_cents=0,
            payout_interval=Intervals.MONTH
        )

        with freeze_time('2014-01-01'):
            # Subscribe the customer to the plan
            sub = payout.subscribe(self.customer)

        # We can subscribe to multiple plans at different times
        with freeze_time('2014-01-05'):
            # Lets give subscribe to some IPs for our server now too
            # with 5 IPs
            sub2 = payout_2.subscribe(self.customer)

        # Modifying a subscription is as easy as resubscribing


        self.assertEqual(len(self.customer.payout_subscriptions), 2)
