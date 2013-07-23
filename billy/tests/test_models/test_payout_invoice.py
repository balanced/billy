from __future__ import unicode_literals
from datetime import datetime

from freezegun import freeze_time
from pytz import UTC
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *

from models import Group, Customer, Payout, PayoutInvoice
from utils.intervals import Intervals
from tests import BalancedTransactionalTestCase


class TestPayoutInvoice(BalancedTransactionalTestCase):

    def setUp(self):
        super(TestPayoutInvoice, self).setUp()
        self.customer = 'MY_TEST_CUSTOMER'
        self.customer_2 = 'MY_TEST_CUSTOMER_2'
        self.customer_3 = 'MY_TEST_CUSTOMER_3'
        self.group = 'BILLY_TEST_MARKETPLACE'
        self.group_2 = 'BILLY_TEST_MARKETPLACE_2'
        self.payout = 'MY_TEST_PAYOUT'
        self.payout_2 = 'MY_TEST_PAYOUT_2'
        self.payout_3 = 'MY_TEST_PAYOUT_3'
        self.now = datetime.now(UTC)
        self.week = self.now + Intervals.WEEK
        self.two_weeks = self.now + Intervals.TWO_WEEKS
        self.month = self.now + Intervals.MONTH
        Group.create(self.group)
        Group.create(self.group_2)
        Customer.create(self.customer, self.group)
        Customer.create(self.customer_2, self.group)
        Customer.create(self.customer_3, self.group_2)
        Payout.create(self.payout, self.group,
                      'Test Payout', 1000, Intervals.TWO_WEEKS)
        Payout.create(self.payout_2, self.group,
                      'Test Payout 2', 1500, Intervals.MONTH)
        Payout.create(self.payout_3, self.group_2,
                      'Test Payout 3', 9700, Intervals.MONTH)


class TestCreate(TestPayoutInvoice):

    def test_create(self):
        PayoutInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_payout=self.payout,
            payout_date=self.week,
            balanced_to_keep_cents=5000
        )

    def test_create_exists(self):
        PayoutInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_payout=self.payout,
            payout_date=self.week,
            balanced_to_keep_cents=5000
        )
        with self.assertRaises(IntegrityError):
            PayoutInvoice.create(
                customer_id=self.customer,
                group_id=self.group,
                relevant_payout=self.payout,
                payout_date=self.week,
                balanced_to_keep_cents=6000
            )

    def test_create_customer_dne(self):
        with self.assertRaises(IntegrityError):
            PayoutInvoice.create(
                customer_id='CUSTOMER_DNE',
                group_id=self.group,
                relevant_payout=self.payout,
                payout_date=self.week,
                balanced_to_keep_cents=6000
            )

    def test_create_payout_dne(self):
        with self.assertRaises(IntegrityError):
            PayoutInvoice.create(
                customer_id=self.customer,
                group_id=self.group,
                relevant_payout='PAYOUT_DNE',
                payout_date=self.week,
                balanced_to_keep_cents=6000
            )

    def test_create_exist_inactive(self):
        var = PayoutInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_payout=self.payout,
            payout_date=self.week,
            balanced_to_keep_cents=6000
        )
        var.active = False
        var.session.commit()
        PayoutInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_payout=self.payout,
            payout_date=self.week,
            balanced_to_keep_cents=6000
        )


class TestRetrieve(TestPayoutInvoice):

    def test_create_and_retrieve(self):
        PayoutInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_payout=self.payout,
            payout_date=self.week,
            balanced_to_keep_cents=12345
        )
        var = PayoutInvoice.retrieve(
            self.customer, self.group, self.payout, active_only=True)
        self.assertEqual(var.balance_to_keep_cents, 12345)

    def test_retrieve_dne(self):
        with self.assertRaises(NoResultFound):
            PayoutInvoice.retrieve(
                'CUSTOMER_DNE', self.group, self.payout, active_only=True)

    def test_retrieve_params(self):
        PayoutInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_payout=self.payout,
            payout_date=self.week,
            balanced_to_keep_cents=12345
        )
        var = PayoutInvoice.retrieve(
            self.customer, self.group, self.payout, active_only=True)
        self.assertEqual(var.customer_id, self.customer)
        self.assertEqual(var.group_id, self.group)
        self.assertEqual(var.relevant_payout, self.payout)
        self.assertFalse(var.completed)
        self.assertTrue(var.active)
        self.assertIsNone(var.cleared_by)

    def test_list(self):
        PayoutInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_payout=self.payout,
            payout_date=self.week,
            balanced_to_keep_cents=12345
        )
        PayoutInvoice.create(
            customer_id=self.customer_3,
            group_id=self.group_2,
            relevant_payout=self.payout_3,
            payout_date=self.week,
            balanced_to_keep_cents=12345
        )
        self.assertEqual(
            len(PayoutInvoice.list(self.group, self.payout, self.customer)), 1)

    def test_list_active_only(self):
        var = PayoutInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_payout=self.payout,
            payout_date=self.week,
            balanced_to_keep_cents=12345
        )
        var.active = False
        var.session.commit()
        PayoutInvoice.create(
            customer_id=self.customer,
            group_id=self.group,
            relevant_payout=self.payout,
            payout_date=self.week,
            balanced_to_keep_cents=12345
        )
        self.assertEqual(
            len(PayoutInvoice.list(self.group, active_only=True)), 1)


class TestUtils(TestPayoutInvoice):

    def test_needs_payout_made(self):
        with freeze_time(str(self.now)):
            Customer.retrieve(
                self.customer, self.group).add_payout(self.payout)
            Customer.retrieve(
                self.customer_2, self.group).add_payout(self.payout_2)
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)
        with freeze_time(str(self.week)):
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)
        with freeze_time(str(self.two_weeks)):
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 1)
        with freeze_time(str(self.month)):
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 2)

    def test_needs_rollover(self):
        with freeze_time(str(self.now)):
            Customer.retrieve(
                self.customer, self.group).add_payout(self.payout)
            Customer.retrieve(
                self.customer_2, self.group).add_payout(self.payout_2)
        with freeze_time(str(self.month)):
            PayoutInvoice.make_all_payouts()
            self.assertEqual(len(PayoutInvoice.needs_rollover()), 2)
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)

    def test_rollover_all(self):
        with freeze_time(str(self.now)):
            Customer.retrieve(
                self.customer, self.group).add_payout(self.payout)
            Customer.retrieve(
                self.customer_2, self.group).add_payout(self.payout_2)
        with freeze_time(str(self.month)):
            PayoutInvoice.make_all_payouts()
            self.assertEqual(len(PayoutInvoice.needs_rollover()), 2)
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)
            PayoutInvoice.rollover_all()
            self.assertEqual(len(PayoutInvoice.needs_rollover()), 0)

    def test_rollover(self):
        with freeze_time(str(self.now)):
            Customer.retrieve(
                self.customer, self.group).add_payout(self.payout)
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)
        with freeze_time(str(self.month)):
            needs_payout = PayoutInvoice.needs_payout_made()
            self.assertEqual(len(needs_payout), 1)
            invoice = needs_payout[0].make_payout()
            self.assertTrue(invoice.completed)
            self.assertTrue(invoice.active)
            self.assertIsNotNone(invoice.cleared_by)

    def test_payout(self):
        with freeze_time(str(self.now)):
            Customer.retrieve(
                self.customer, self.group).add_payout(self.payout)
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)
        with freeze_time(str(self.month)):
            needs_payout = PayoutInvoice.needs_payout_made()
            self.assertEqual(len(needs_payout), 1)
            invoice = needs_payout[0].make_payout()
            self.assertTrue(invoice.completed)
            self.assertTrue(invoice.active)
            self.assertIsNotNone(invoice.cleared_by)

    def test_payout_all(self):
        with freeze_time(str(self.now)):
            Customer.retrieve(
                self.customer, self.group).add_payout(self.payout)
            Customer.retrieve(
                self.customer_2, self.group).add_payout(self.payout_2)
        with freeze_time(str(self.month)):
            PayoutInvoice.make_all_payouts()
            self.assertEqual(len(PayoutInvoice.needs_payout_made()), 0)


class TestValidators(TestPayoutInvoice):

    def test_balance_to_keep_cents(self):
        with self.assertRaises(ValueError):
            PayoutInvoice.create(
                customer_id=self.customer,
                group_id=self.group,
                relevant_payout=self.payout,
                payout_date=self.week,
                balanced_to_keep_cents=-5000
            )

    def test_amount_payed_out(self):
        with self.assertRaises(ValueError):
            var = PayoutInvoice.create(
                customer_id=self.customer,
                group_id=self.group,
                relevant_payout=self.payout,
                payout_date=self.week,
                balanced_to_keep_cents=5000
            )
            var.amount_payed_out = -1
            var.session.flush()

    def test_balance_at_exec(self):
        with self.assertRaises(ValueError):
            var = PayoutInvoice.create(
                customer_id=self.customer,
                group_id=self.group,
                relevant_payout=self.payout,
                payout_date=self.week,
                balanced_to_keep_cents=5000
            )
            var.balance_at_exec = -20
            var.session.flush()

    def test_attempts_made(self):
        with self.assertRaises(ValueError):
            var = PayoutInvoice.create(
                customer_id=self.customer,
                group_id=self.group,
                relevant_payout=self.payout,
                payout_date=self.week,
                balanced_to_keep_cents=5000
            )
            var.attempts_made = -5
            var.session.flush()
