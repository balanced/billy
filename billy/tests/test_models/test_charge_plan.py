from __future__ import unicode_literals

from freezegun import freeze_time

from billy.utils.intervals import Intervals
from billy.tests import BaseTestCase, fixtures


class ChargePlanTest(BaseTestCase):
    def setUp(self):
        super(ChargePlanTest, self).setUp()
        self.company = self.test_companies[0]

        self.customer = self.company.create_customer(
            **fixtures.sample_customer())

    def basic_test(self):
        # Create the plan
        server_plan = self.company.create_charge_plan(
            your_id='BIG_SERVER', # What you call the plan
            name='The Big Server', # Display name
            price_cents=1000, # $10
            plan_interval=Intervals.MONTH, # Monthly plan
            trial_interval=Intervals.WEEK # 1 week trial
        )
        ip_plan = self.company.create_charge_plan(
            your_id='IPs',
            name='Daily IPs',
            price_cents=1000,
            plan_interval=Intervals.DAY,
            trial_interval=None
        )

        with freeze_time('2014-01-01'):
            # Subscribe the customer to the plan
            sub = server_plan.subscribe(self.customer, quantity=1)

        # We can subscribe to multiple plans at different times
        with freeze_time('2014-01-05'):
            # Lets give subscribe to some IPs for our server now too
            # with 5 IPs
            sub2 = ip_plan.subscribe(self.customer, quantity=5)

        # Modifying a subscription is as easy as resubscribing
        with freeze_time('2014-01-10'):
            # Lets up them to 10 IPs
            sub2 = ip_plan.subscribe(self.customer, quantity=10)

        self.assertEqual(len(self.customer.charge_subscriptions), 2)
