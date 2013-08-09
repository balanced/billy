from __future__ import unicode_literals

from freezegun import freeze_time

from tests import BaseTestCase, fixtures


class PayoutPlanSubscriptionTest(BaseTestCase):
    def setUp(self):
        super(PayoutPlanSubscriptionTest, self).setUp()
        self.company = self.test_companies[0]

        self.customer = self.company.create_customer(
            **fixtures.sample_customer())

        self.plan = self.company.create_payout_plan(**fixtures.sample_payout())

    def basic_test(self):
        with freeze_time('2014-01-01'):
            # Subscribe the customer to the plan
            sub = self.plan.subscribe(self.customer)
            invoice = sub.current_invoice

        with freeze_time('2014-01-05'):
            # Wont do anything since there is a current invoice
            sub.generate_next_invoice()
            self.assertEqual(sub.current_invoice, invoice)

        with freeze_time('2014-02-01'):
            # The task the generates the next invoice for the subscription
            invoice_new = sub.generate_next_invoice()
            self.assertNotEqual(invoice, invoice_new)

        with freeze_time('2014-02-15'):
            # We can safely cancel a subscription half way which will prorate
            # it automatically for us.
            sub.cancel()
