from __future__ import unicode_literals

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
from billy.utils.generic import utc_now


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
                frequency=self.plan_model.frequencies.WEEKLY,
                plan_type=self.plan_model.types.DEBIT,
                amount=1234,
            )
            self.subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
                appears_on_statement_as='hello baby',
            )
            self.customer_invoice = self.invoice_model.create(
                customer=self.customer,
                amount=7788,
                title='foobar invoice',
                external_id='external ID',
                appears_on_statement_as='hello baby',
                items=[
                    dict(type='debit', name='foo', amount=123, volume=5678),
                    dict(name='bar', amount=456, quantity=10, unit='hours',
                         volume=7788),
                ],
                adjustments=[
                    dict(amount=20, reason='A Lannister always pays his debts!'),
                    dict(amount=3),
                ],
            )
            self.subscription_invoice = self.invoice_model.create(
                subscription=self.subscription,
                amount=7788,
                title='foobar invoice',
                external_id='external ID2',
                appears_on_statement_as='hello baby',
                items=[
                    dict(type='debit', name='foo', amount=123, volume=5678),
                    dict(name='bar', amount=456, quantity=10, unit='hours',
                         volume=7788),
                ],
                adjustments=[
                    dict(amount=20, reason='A Lannister always pays his debts!'),
                    dict(amount=3),
                ],
                scheduled_at=utc_now(),
            )
            self.transaction = self.transaction_model.create(
                invoice=self.customer_invoice,
                transaction_type=self.transaction_model.types.DEBIT,
                amount=5678,
                funding_instrument_uri='/v1/cards/tester',
                appears_on_statement_as='hello baby',
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

    def test_company_with_callback_key(self):
        company = self.company
        self.dummy_request.registry.settings = {}
        settings = self.dummy_request.registry.settings
        settings['billy.company.display_callback_key'] = True
        json_data = company_adapter(company, self.dummy_request)
        expected = dict(
            guid=company.guid,
            api_key=company.api_key,
            callback_key=company.callback_key,
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
        invoice = self.customer_invoice
        json_data = invoice_adapter(invoice, self.dummy_request)
        expected = dict(
            guid=invoice.guid,
            invoice_type='customer',
            transaction_type='debit',
            status='staged',
            created_at=invoice.created_at.isoformat(),
            updated_at=invoice.updated_at.isoformat(),
            customer_guid=invoice.customer_guid,
            amount=invoice.amount,
            effective_amount=invoice.effective_amount,
            total_adjustment_amount=invoice.total_adjustment_amount,
            title=invoice.title,
            external_id=invoice.external_id,
            funding_instrument_uri=None,
            appears_on_statement_as='hello baby',
            items=[
                dict(type='debit', name='foo', amount=123, quantity=None,
                     volume=5678, unit=None),
                dict(type=None, name='bar', amount=456, quantity=10,
                     volume=7788, unit='hours'),
            ],
            adjustments=[
                dict(amount=20, reason='A Lannister always pays his debts!'),
                dict(amount=3, reason=None),
            ],
        )
        self.assertEqual(json_data, expected)

        def assert_status(invoice_status, expected_status):
            invoice.status = invoice_status
            json_data = invoice_adapter(invoice, self.dummy_request)
            self.assertEqual(json_data['status'], expected_status)

        assert_status(self.invoice_model.statuses.STAGED, 'staged')
        assert_status(self.invoice_model.statuses.PROCESSING, 'processing')
        assert_status(self.invoice_model.statuses.SETTLED, 'settled')
        assert_status(self.invoice_model.statuses.CANCELED, 'canceled')
        assert_status(self.invoice_model.statuses.FAILED, 'failed')

        invoice = self.subscription_invoice
        json_data = invoice_adapter(invoice, self.dummy_request)
        expected = dict(
            guid=invoice.guid,
            invoice_type='subscription',
            transaction_type='debit',
            status='staged',
            created_at=invoice.created_at.isoformat(),
            updated_at=invoice.updated_at.isoformat(),
            scheduled_at=invoice.scheduled_at.isoformat(),
            subscription_guid=invoice.subscription_guid,
            amount=invoice.amount,
            effective_amount=invoice.effective_amount,
            total_adjustment_amount=invoice.total_adjustment_amount,
            title=invoice.title,
            funding_instrument_uri=None,
            appears_on_statement_as='hello baby',
            items=[
                dict(type='debit', name='foo', amount=123, quantity=None,
                     volume=5678, unit=None),
                dict(type=None, name='bar', amount=456, quantity=10,
                     volume=7788, unit='hours'),
            ],
            adjustments=[
                dict(amount=20, reason='A Lannister always pays his debts!'),
                dict(amount=3, reason=None),
            ],
        )
        self.assertEqual(json_data, expected)

    def test_plan(self):
        plan = self.plan
        json_data = plan_adapter(plan, self.dummy_request)
        expected = dict(
            guid=plan.guid,
            plan_type='debit',
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

        assert_type(self.plan_model.types.DEBIT, 'debit')
        assert_type(self.plan_model.types.CREDIT, 'credit')

        def assert_frequency(frequency, expected_frequency):
            plan.frequency = frequency
            json_data = plan_adapter(plan, self.dummy_request)
            self.assertEqual(json_data['frequency'], expected_frequency)

        assert_frequency(self.plan_model.frequencies.DAILY, 'daily')
        assert_frequency(self.plan_model.frequencies.WEEKLY, 'weekly')
        assert_frequency(self.plan_model.frequencies.MONTHLY, 'monthly')
        assert_frequency(self.plan_model.frequencies.YEARLY, 'yearly')

    def test_subscription(self):
        subscription = self.subscription
        json_data = subscription_adapter(subscription, self.dummy_request)
        expected = dict(
            guid=subscription.guid,
            amount=None,
            effective_amount=subscription.plan.amount,
            funding_instrument_uri=subscription.funding_instrument_uri,
            appears_on_statement_as=subscription.appears_on_statement_as,
            invoice_count=subscription.invoice_count,
            canceled=subscription.canceled,
            next_invoice_at=subscription.next_invoice_at.isoformat(),
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

        now = utc_now()
        assert_canceled_at(None, None)
        assert_canceled_at(now, now.isoformat())

    def test_transaction(self):
        transaction = self.transaction
        serialized_failures = [
            transaction_failure_adapter(f, self.dummy_request)
            for f in transaction.failures
        ]

        json_data = transaction_adapter(transaction, self.dummy_request)
        self.maxDiff = None
        expected = dict(
            guid=transaction.guid,
            transaction_type='debit',
            submit_status='staged',
            status=None,
            amount=transaction.amount,
            funding_instrument_uri=transaction.funding_instrument_uri,
            processor_uri=transaction.processor_uri,
            appears_on_statement_as=transaction.appears_on_statement_as,
            failure_count=transaction.failure_count,
            created_at=transaction.created_at.isoformat(),
            updated_at=transaction.updated_at.isoformat(),
            invoice_guid=transaction.invoice_guid,
            failures=serialized_failures,
        )
        self.assertEqual(json_data, expected)

        def assert_type(transaction_type, expected_type):
            transaction.transaction_type = transaction_type
            json_data = transaction_adapter(transaction, self.dummy_request)
            self.assertEqual(json_data['transaction_type'], expected_type)

        assert_type(self.transaction_model.types.DEBIT, 'debit')
        assert_type(self.transaction_model.types.CREDIT, 'credit')
        assert_type(self.transaction_model.types.REFUND, 'refund')

        def assert_submit_status(status, expected_status):
            transaction.submit_status = status
            json_data = transaction_adapter(transaction, self.dummy_request)
            self.assertEqual(json_data['submit_status'], expected_status)

        assert_submit_status(self.transaction_model.submit_statuses.STAGED, 'staged')
        assert_submit_status(self.transaction_model.submit_statuses.RETRYING, 'retrying')
        assert_submit_status(self.transaction_model.submit_statuses.FAILED, 'failed')
        assert_submit_status(self.transaction_model.submit_statuses.DONE, 'done')
        assert_submit_status(self.transaction_model.submit_statuses.CANCELED, 'canceled')

        def assert_status(status, expected_status):
            transaction.status = status
            json_data = transaction_adapter(transaction, self.dummy_request)
            self.assertEqual(json_data['status'], expected_status)

        assert_status(self.transaction_model.statuses.PENDING, 'pending')
        assert_status(self.transaction_model.statuses.SUCCEEDED, 'succeeded')
        assert_status(self.transaction_model.statuses.FAILED, 'failed')

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
