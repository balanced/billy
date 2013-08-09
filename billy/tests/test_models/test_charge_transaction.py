from __future__ import unicode_literals

from freezegun import freeze_time

from models import ChargePlanInvoice, ChargeTransactionStatus
from tests import BaseTestCase, fixtures


class ChargeTransactionTest(BaseTestCase):
    def setUp(self):
        super(ChargeTransactionTest, self).setUp()
        self.company = self.test_companies[0]

        self.customer = self.company.create_customer(
            **fixtures.sample_customer())

        self.plan = self.company.create_charge_plan(
            **fixtures.sample_plan(trial_interval=None))

    def basic_test(self):
        with freeze_time('2014-01-01'):
            # Subscribe the customer to the plan
            sub = self.plan.subscribe(self.customer, quantity=1)
            invoice = sub.current_invoice

        with freeze_time('2014-01-02'):
            count_settled = ChargePlanInvoice.settle_all()
            self.assertEqual(count_settled, 1)
            invoice = sub.invoices.first()
            # The transaction
            transaction = invoice.transaction
            self.assertEqual(invoice.remaining_balance_cents, 0)
            self.assertEqual(invoice.amount_paid_cents,
                             transaction.amount_cents)

            # The transaction will have a sent status
            self.assertEqual(transaction.status, ChargeTransactionStatus.SENT)