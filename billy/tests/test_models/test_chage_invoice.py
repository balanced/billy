from __future__ import unicode_literals
from datetime import datetime

from freezegun import freeze_time

from models import ChargePlanInvoice, ChargeSubscription
from utils.intervals import Intervals
from tests.fixtures import sample_coupon, sample_customer, sample_plan
from tests import BaseTestCase


class InvoiceScenarioTest(BaseTestCase):
    def setUp(self):
        super(InvoiceScenarioTest, self).setUp()
        # Prune old companies
        self.company = self.test_companies[0]

        # Create a plan under the company
        self.plan = self.company.create_charge_plan(**sample_plan())

        # Create a customer under the company
        self.customer = self.company.create_customer(**sample_customer())

        # Create a coupon under the company
        self.coupon = self.company.create_coupon(**sample_coupon())


    def basic_test(self):
        # Lets go to the future
        with freeze_time('2014-01-01'):
            # Create a dummy test company
            # Subscribe the customer to the plan using that coupon
            sub = self.plan.subscribe(self.customer, quantity=1,
                                      coupon=self.coupon)

            # Subscription will now renew and the person is enrolled
            self.assertTrue(sub.is_enrolled)
            self.assertTrue(sub.should_renew)
            # An current invoice is generated for that user
            invoice = sub.current_invoice

            # 10% off coupon:
            self.assertEqual(invoice.remaining_balance_cents, 900)

            # None of its paid yet:
            self.assertEqual(invoice.amount_paid_cents, 0)

            # Invoice should start now:
            self.assertEqual(invoice.start_dt, datetime.utcnow())

            # But it should be due in a week because of the trial
            self.assertTrue(invoice.includes_trial)
            self.assertEqual(invoice.due_dt, datetime.utcnow() + Intervals.WEEK)

        # Moving to when that invoice is due:
        with freeze_time('2014-01-08'):
            all_due = ChargePlanInvoice.all_due(self.customer)

            # Should have one due
            self.assertEqual(len(all_due), 1)
            self.assertEqual(all_due[0], invoice)

            # Run the task to settle all invoices:
            ChargePlanInvoice.settle_all()

            # Should no longer be due
            all_due_new = ChargePlanInvoice.all_due(self.customer)

            # There should be a transaction with the processor:
            transaction = invoice.transaction
            self.assertTrue(transaction)
            self.assertEqual(transaction.amount_cents, 900)



        # Moving to when the next invoice should be generated (1 month + 1 week for trial):
        with freeze_time('2014-02-09'):
            # Shouldn't have a current_invoice
            self.assertIsNone(sub.current_invoice)

            # Lets generate all the next invoices:
            count_invoices_generated = ChargeSubscription.generate_all_invoices()
            self.assertEqual(count_invoices_generated, 1)

            # A new invoice should be generated
            new_invoice = sub.current_invoice
            # With a start_dt the same as the last ones end_dt
            self.assertEqual(new_invoice.start_dt, invoice.end_dt)

            # No longer a trial
            self.assertFalse(new_invoice.includes_trial)
            # So it should end in a month:
            self.assertEqual(new_invoice.end_dt,
                             new_invoice.start_dt + Intervals.MONTH)






