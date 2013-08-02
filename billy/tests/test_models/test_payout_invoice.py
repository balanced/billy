from __future__ import unicode_literals
from datetime import datetime

from freezegun import freeze_time
from pytz import UTC
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from models import Company, Customer, Payout, PayoutInvoice, PayoutSubscription
from utils.intervals import Intervals
from tests import BalancedTransactionalTestCase


class TestPayoutInvoice(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestPayoutInvoice, self).setUp()
        self.now = datetime.utcnow()
        self.week = self.now + Intervals.WEEK
        self.two_weeks = self.now + Intervals.TWO_WEEKS
        self.month = self.now + Intervals.MONTH
        self.group = Company.create('BILLY_TEST_MARKETPLACE')
        self.group_2 = Company.create('BILLY_TEST_MARKETPLACE_2')
        self.customer = Customer.create(
            'MY_TEST_CUSTOMER', self.group.guid, 'TESTBALID')
        self.customer_2 = Customer.create(
            'MY_TEST_CUSTOMER_2', self.group.guid, 'TESTBALID')
        self.customer_3 = Customer.create(
            'MY_TEST_CUSTOMER_3', self.group_2.guid, 'TESTBALID')
        self.payout = Payout.create('MY_TEST_PAYOUT', self.group.guid,
                                    'Test Payout', 1000, Intervals.TWO_WEEKS)
        self.payout_2 = Payout.create('MY_TEST_PAYOUT_2', self.group.guid,
                                      'Test Payout 2', 1500, Intervals.MONTH)
        self.payout_3 = Payout.create('MY_TEST_PAYOUT_3', self.group_2.guid,
                                      'Test Payout 3', 9700, Intervals.MONTH)


class TestCreate(TestPayoutInvoice):

    def test_create(self):
        invoice = PayoutSubscription.subscribe(self.customer, self.payout)
        PayoutInvoice.create(
            subscription_id=invoice.subscription.guid,
            payout_date=self.week,
            balanced_to_keep_cents=5000
        )


class TestRetrieve(TestPayoutInvoice):

    def test_create_and_retrieve(self):
        inv = PayoutSubscription.subscribe(self.customer, self.payout)
        var = PayoutInvoice.create(
            subscription_id=inv.subscription.guid,
            payout_date=self.week,
            balanced_to_keep_cents=12345,
        )
        self.assertEqual(var.balance_to_keep_cents, 12345)

    def test_retrieve_params(self):
        inv = PayoutSubscription.subscribe(self.customer, self.payout)
        var = PayoutInvoice.create(
            subscription_id=inv.subscription.guid,
            payout_date=self.week,
            balanced_to_keep_cents=12345
        )
        self.assertEqual(var.subscription.customer, self.customer)
        self.assertEqual(var.subscription.payout, self.payout)
        self.assertFalse(var.completed)
        self.assertTrue(var.subscription.is_active)
        self.assertIsNone(var.cleared_by_txn)


class TestUtils(TestPayoutInvoice):

    def test_needs_payout_made(self):
        with freeze_time(str(self.now)):
            PayoutSubscription.subscribe(self.customer, self.payout)
            PayoutSubscription.subscribe(self.customer, self.payout_2)
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)
        with freeze_time(str(self.week)):
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)
        with freeze_time(str(self.two_weeks)):
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 1)
        with freeze_time(str(self.month)):
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 2)

    def test_needs_rollover(self):
        with freeze_time(str(self.now)):
            PayoutSubscription.subscribe(self.customer, self.payout)
            PayoutSubscription.subscribe(self.customer, self.payout_2)
        with freeze_time(str(self.month)):
            PayoutInvoice.make_all_payouts()
            self.assertEqual(len(PayoutInvoice.needs_rollover()), 2)
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)

    def test_rollover_all(self):
        with freeze_time(str(self.now)):
            PayoutSubscription.subscribe(self.customer, self.payout)
            PayoutSubscription.subscribe(self.customer, self.payout_2)
        with freeze_time(str(self.month)):
            PayoutInvoice.make_all_payouts()
            self.assertEqual(len(PayoutInvoice.needs_rollover()), 2)
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)
            PayoutInvoice.rollover_all()
            self.assertEqual(len(PayoutInvoice.needs_rollover()), 0)

    def test_rollover(self):
        with freeze_time(str(self.now)):
            PayoutSubscription.subscribe(self.customer, self.payout)
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)
        with freeze_time(str(self.month)):
            needs_payout = PayoutInvoice.needs_payout_made()
            self.assertEqual(len(needs_payout), 1)
            invoice = needs_payout[0].make_payout()
            self.assertTrue(invoice.completed)
            self.assertTrue(invoice.subscription.is_active)
            self.assertIsNotNone(invoice.cleared_by)

    def test_payout(self):
        with freeze_time(str(self.now)):
            PayoutSubscription.subscribe(self.customer, self.payout)
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)
        with freeze_time(str(self.month)):
            needs_payout = PayoutInvoice.needs_payout_made()
            self.assertEqual(len(needs_payout), 1)
            invoice = needs_payout[0].make_payout()
            self.assertTrue(invoice.completed)
            self.assertTrue(invoice.subscription.is_active)
            self.assertIsNotNone(invoice.cleared_by)

    def test_payout_all(self):
        with freeze_time(str(self.now)):
            PayoutSubscription.subscribe(self.customer, self.payout)
            PayoutSubscription.subscribe(self.customer, self.payout_2)
        with freeze_time(str(self.month)):
            PayoutInvoice.make_all_payouts()
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)


class TestValidators(TestPayoutInvoice):

    def setUp(self):
        super(TestValidators, self).setUp()
        self.sub_guid = PayoutSubscription.subscribe(
            self.customer, self.payout).subscription.guid

    def test_balance_to_keep_cents(self):
        with self.assertRaises(ValueError):
            PayoutInvoice.create(
                subscription_id=self.sub_guid,
                payout_date=self.week,
                balanced_to_keep_cents=-5000
            )

    def test_amount_payed_out(self):
        with self.assertRaises(ValueError):
            var = PayoutInvoice.create(
                subscription_id=self.sub_guid,
                payout_date=self.week,
                balanced_to_keep_cents=5000
            )
            var.amount_payed_out = -1
            var.session.flush()

    def test_balance_at_exec(self):
        with self.assertRaises(ValueError):
            var = PayoutInvoice.create(
                subscription_id=self.sub_guid,
                payout_date=self.week,
                balanced_to_keep_cents=5000
            )
            var.balance_at_exec = -20
            var.session.flush()

    def test_attempts_made(self):
        with self.assertRaises(ValueError):
            var = PayoutInvoice.create(
                subscription_id=self.sub_guid,
                payout_date=self.week,
                balanced_to_keep_cents=5000
            )
            var.attempts_made = -5
            var.session.flush()
