from __future__ import unicode_literals
from datetime import datetime

from freezegun import freeze_time

from models import PayoutPlanInvoice
from tests import BaseTestCase, fixtures


class PayoutInvoiceTest(BaseTestCase):
    def setUp(self):
        super(PayoutInvoiceTest, self).setUp()
        # Prune old companies
        self.company = self.test_companies[0]

        # Create a plan under the company
        self.plan = self.company.create_payout_plan(**fixtures.sample_payout())

        # Create a customer under the company
        self.customer = self.company.create_customer(
            **fixtures.sample_customer())

    def basic_test(self):
        # Lets go to the future
        with freeze_time('2014-01-01'):
            # Subscribe the customer to the plan using that coupon
            sub = self.plan.subscribe(self.customer)

            # Subscription is_active and not queued for rollover.
            self.assertTrue(sub.is_active)

            # An current invoice is generated for that user
            invoice = sub.current_invoice
            self.assertFalse(invoice.queue_rollover)

            # Should keep $5 in balance
            self.assertEqual(invoice.balance_to_keep_cents, 500)

            # None of its paid out yet:
            self.assertEqual(invoice.amount_payed_out, 0)

            # first_now true so:
            self.assertEqual(invoice.payout_date, datetime.utcnow())

        # Moving to when that invoice is due:
        with freeze_time('2014-01-08'):
            # Run the task to settle all invoices:
            PayoutPlanInvoice.settle_all()

            # There should be a transaction with the processor:
            transaction = invoice.transaction
            self.assertTrue(transaction)
            # Since dummy plan returns some random balance:
            self.assertNotEqual(transaction.amount_cents, 0)






