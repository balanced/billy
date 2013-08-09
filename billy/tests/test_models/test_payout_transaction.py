from __future__ import unicode_literals

from freezegun import freeze_time

from models import PayoutPlanInvoice, PayoutTransactionStatus
from tests import BaseTestCase, fixtures


class PayoutTransactionTest(BaseTestCase):
    def setUp(self):
        super(PayoutTransactionTest, self).setUp()
        self.company = self.test_companies[0]

        self.customer = self.company.create_customer(
            **fixtures.sample_customer())

        self.plan = self.company.create_payout_plan(
            **fixtures.sample_payout())

    def basic_test(self):
        with freeze_time('2014-01-01'):
            # Subscribe the customer to the plan
            sub = self.plan.subscribe(self.customer)
            invoice = sub.current_invoice

        with freeze_time('2014-01-02'):
            count_settled = PayoutPlanInvoice.settle_all()
            self.assertEqual(count_settled, 1)
            invoice = sub.invoices.first()
            # The transaction
            transaction = invoice.transaction
            self.assertTrue(invoice.completed)
            self.assertTrue(invoice.queue_rollover)
            self.assertNotEqual(invoice.amount_payed_out, 0)

            # The transaction will have a sent status
            self.assertEqual(transaction.status, PayoutTransactionStatus.SENT)