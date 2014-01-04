from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from freezegun import freeze_time

from billy.renderers import company_adapter
from billy.renderers import customer_adapter
from billy.renderers import plan_adapter
from billy.renderers import subscription_adapter
from billy.renderers import invoice_adapter
from billy.renderers import transaction_adapter
from billy.renderers import transaction_failure_adapter
from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestRenderer(ViewTestCase):

    def setUp(self):
        super(TestRenderer, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            self.customer = self.customer_model.create(
                company=self.company
            )
            self.plan = self.plan_model.create(
                company=self.company,
                frequency=self.plan_model.FREQ_WEEKLY,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=1234,
            )
            self.subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
                appears_on_statement_as='hello baby',
            )
            self.invoice = self.invoice_model.create(
                customer=self.customer,
                amount=7788,
                title='foobar invoice',
                external_id='external ID',
                appears_on_statement_as='hello baby',
                items=[
                    dict(type='debit', name='foo', total=123, amount=5678),
                    dict(name='bar', total=456, quantity=10, unit='hours', 
                         amount=7788),
                ],
                adjustments=[
                    dict(total=20, reason='A Lannister always pays his debts!'),
                    dict(total=3),
                ],
            )
            self.transaction = self.transaction_model.create(
                subscription=self.subscription,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=5678,
                funding_instrument_uri='/v1/cards/tester',
                appears_on_statement_as='hello baby',
                scheduled_at=datetime.datetime.utcnow(),
            )
            self.transaction_failure1 = self.transaction_failure_model.create(
                transaction=self.transaction,
                error_message='boom!',
                error_number=666,
                error_code='damin-it',
            )
            with freeze_time('2013-08-17'):
                self.transaction_failure2 = self.transaction_failure_model.create(
                    transaction=self.transaction,
                    error_message='doomed!',
                    error_number=777,
                    error_code='screw-it',
                )

    def test_company(self):
        company = self.company
        json_data = company_adapter(company, self.dummy_request)
        expected = dict(
            guid=company.guid,
            api_key=company.api_key,
            created_at=company.created_at.isoformat(),
            updated_at=company.updated_at.isoformat(),
        )
        self.assertEqual(json_data, expected)

    def test_customer(self):
        customer = self.customer
        json_data = customer_adapter(customer, self.dummy_request)
        expected = dict(
            guid=customer.guid,
            processor_uri=customer.processor_uri, 
            created_at=customer.created_at.isoformat(),
            updated_at=customer.updated_at.isoformat(),
            company_guid=customer.company_guid, 
            deleted=customer.deleted, 
        )
        self.assertEqual(json_data, expected)

    def test_invoice(self):
        invoice = self.invoice
        json_data = invoice_adapter(invoice, self.dummy_request)
        expected = dict(
            guid=invoice.guid,
            status='init',
            created_at=invoice.created_at.isoformat(),
            updated_at=invoice.updated_at.isoformat(),
            customer_guid=invoice.customer_guid, 
            amount=invoice.amount, 
            total_adjustment_amount=invoice.total_adjustment_amount, 
            title=invoice.title, 
            external_id=invoice.external_id, 
            funding_instrument_uri=None, 
            appears_on_statement_as='hello baby', 
            items=[
                dict(type='debit', name='foo', total=123, quantity=None, 
                     amount=5678, unit=None),
                dict(type=None, name='bar', total=456, quantity=10, 
                     amount=7788, unit='hours'),
            ],
            adjustments=[
                dict(total=20, reason='A Lannister always pays his debts!'),
                dict(total=3, reason=None),
            ],
        )
        self.assertEqual(json_data, expected)

        def assert_status(invoice_status, expected_status):
            invoice.status = invoice_status
            json_data = invoice_adapter(invoice, self.dummy_request)
            self.assertEqual(json_data['status'], expected_status)

        assert_status(self.invoice_model.STATUS_INIT, 'init')
        assert_status(self.invoice_model.STATUS_PROCESSING, 'processing')
        assert_status(self.invoice_model.STATUS_SETTLED, 'settled')
        assert_status(self.invoice_model.STATUS_CANCELED, 'canceled')
        assert_status(self.invoice_model.STATUS_PROCESS_FAILED, 'process_failed')
        assert_status(self.invoice_model.STATUS_REFUNDING, 'refunding')
        assert_status(self.invoice_model.STATUS_REFUNDED, 'refunded')
        assert_status(self.invoice_model.STATUS_REFUND_FAILED, 'refund_failed')

    def test_plan(self):
        plan = self.plan
        json_data = plan_adapter(plan, self.dummy_request)
        expected = dict(
            guid=plan.guid, 
            plan_type='charge',
            frequency='weekly',
            amount=plan.amount,
            interval=plan.interval,
            created_at=plan.created_at.isoformat(),
            updated_at=plan.updated_at.isoformat(),
            company_guid=plan.company_guid,
            deleted=plan.deleted,
        )
        self.assertEqual(json_data, expected)

        def assert_type(plan_type, expected_type):
            plan.plan_type = plan_type 
            json_data = plan_adapter(plan, self.dummy_request)
            self.assertEqual(json_data['plan_type'], expected_type)

        assert_type(self.plan_model.TYPE_CHARGE, 'charge')
        assert_type(self.plan_model.TYPE_PAYOUT, 'payout')

        def assert_frequency(frequency, expected_frequency):
            plan.frequency = frequency 
            json_data = plan_adapter(plan, self.dummy_request)
            self.assertEqual(json_data['frequency'], expected_frequency)

        assert_frequency(self.plan_model.FREQ_DAILY, 'daily')
        assert_frequency(self.plan_model.FREQ_WEEKLY, 'weekly')
        assert_frequency(self.plan_model.FREQ_MONTHLY, 'monthly')
        assert_frequency(self.plan_model.FREQ_YEARLY, 'yearly')

    def test_subscription(self):
        subscription = self.subscription
        json_data = subscription_adapter(subscription, self.dummy_request)
        expected = dict(
            guid=subscription.guid, 
            amount=None,
            effective_amount=subscription.plan.amount,
            funding_instrument_uri=subscription.funding_instrument_uri,
            appears_on_statement_as=subscription.appears_on_statement_as,
            period=subscription.period,
            canceled=subscription.canceled,
            next_transaction_at=subscription.next_transaction_at.isoformat(),
            created_at=subscription.created_at.isoformat(),
            updated_at=subscription.updated_at.isoformat(),
            started_at=subscription.started_at.isoformat(),
            canceled_at=None,
            customer_guid=subscription.customer_guid,
            plan_guid=subscription.plan_guid,
        )
        self.assertEqual(json_data, expected)

        def assert_amount(amount, expected_amount, expected_effective_amount):
            subscription.amount = amount 
            json_data = subscription_adapter(subscription, self.dummy_request)
            self.assertEqual(json_data['amount'], expected_amount)
            self.assertEqual(json_data['effective_amount'], 
                             expected_effective_amount)

        assert_amount(None, None, subscription.plan.amount)
        assert_amount(1234, 1234, 1234)

        def assert_canceled_at(canceled_at, expected_canceled_at):
            subscription.canceled_at = canceled_at 
            json_data = subscription_adapter(subscription, self.dummy_request)
            self.assertEqual(json_data['canceled_at'], expected_canceled_at)

        now = datetime.datetime.utcnow()
        assert_canceled_at(None, None)
        assert_canceled_at(now, now.isoformat())

    def test_transaction(self):
        transaction = self.transaction
        serialized_failures = [
            transaction_failure_adapter(f, self.dummy_request) 
            for f in transaction.failures
        ]

        json_data = transaction_adapter(transaction, self.dummy_request)
        expected = dict(
            guid=transaction.guid, 
            transaction_type='charge',
            transaction_cls='subscription',
            status='init',
            amount=transaction.amount,
            funding_instrument_uri=transaction.funding_instrument_uri,
            processor_uri=transaction.processor_uri,
            appears_on_statement_as=transaction.appears_on_statement_as,
            failure_count=transaction.failure_count,
            created_at=transaction.created_at.isoformat(),
            updated_at=transaction.updated_at.isoformat(),
            scheduled_at=transaction.scheduled_at.isoformat(),
            subscription_guid=transaction.subscription_guid,
            failures=serialized_failures,
        )
        self.assertEqual(json_data, expected)

        def assert_type(transaction_type, expected_type):
            transaction.transaction_type = transaction_type
            json_data = transaction_adapter(transaction, self.dummy_request)
            self.assertEqual(json_data['transaction_type'], expected_type)

        assert_type(self.transaction_model.TYPE_CHARGE, 'charge')
        assert_type(self.transaction_model.TYPE_PAYOUT, 'payout')
        assert_type(self.transaction_model.TYPE_REFUND, 'refund')

        def assert_status(transaction_status, expected_status):
            transaction.status = transaction_status
            json_data = transaction_adapter(transaction, self.dummy_request)
            self.assertEqual(json_data['status'], expected_status)

        assert_status(self.transaction_model.STATUS_INIT, 'init')
        assert_status(self.transaction_model.STATUS_RETRYING, 'retrying')
        assert_status(self.transaction_model.STATUS_FAILED, 'failed')
        assert_status(self.transaction_model.STATUS_DONE, 'done')
        assert_status(self.transaction_model.STATUS_CANCELED, 'canceled')

        # test invoice transaction
        transaction = self.transaction_model.create(
            invoice=self.invoice,
            transaction_cls=self.transaction_model.CLS_INVOICE,
            transaction_type=self.transaction_model.TYPE_CHARGE,
            amount=10,
            funding_instrument_uri='/v1/cards/tester',
            appears_on_statement_as='hello baby',
            scheduled_at=datetime.datetime.utcnow(),
        )
        json_data = transaction_adapter(transaction, self.dummy_request)
        expected = dict(
            guid=transaction.guid, 
            transaction_type='charge',
            transaction_cls='invoice',
            status='init',
            amount=transaction.amount,
            funding_instrument_uri=transaction.funding_instrument_uri,
            processor_uri=transaction.processor_uri,
            appears_on_statement_as=transaction.appears_on_statement_as,
            failure_count=transaction.failure_count,
            created_at=transaction.created_at.isoformat(),
            updated_at=transaction.updated_at.isoformat(),
            scheduled_at=transaction.scheduled_at.isoformat(),
            invoice_guid=transaction.invoice_guid,
            failures=[],
        )
        self.assertEqual(json_data, expected)

    def test_transaction_failure(self):
        transaction_failure = self.transaction_failure1
        json_data = transaction_failure_adapter(transaction_failure, self.dummy_request)
        expected = dict(
            guid=transaction_failure.guid,
            error_message=transaction_failure.error_message,
            error_code=transaction_failure.error_code,
            error_number=transaction_failure.error_number,
            created_at=transaction_failure.created_at.isoformat(),
        )
        self.assertEqual(json_data, expected)
