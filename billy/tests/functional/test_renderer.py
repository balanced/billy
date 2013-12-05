from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestRenderer(ViewTestCase):

    def setUp(self):
        from pyramid.testing import DummyRequest
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        from billy.models.plan import PlanModel
        from billy.models.subscription import SubscriptionModel
        from billy.models.transaction import TransactionModel
        from billy.models.invoice import InvoiceModel
        super(TestRenderer, self).setUp()
        company_model = CompanyModel(self.testapp.session)
        customer_model = CustomerModel(self.testapp.session)
        plan_model = PlanModel(self.testapp.session)
        subscription_model = SubscriptionModel(self.testapp.session)
        transaction_model = TransactionModel(self.testapp.session)
        invoice_model = InvoiceModel(self.testapp.session)
        with db_transaction.manager:
            self.company_guid = company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            self.customer_guid = customer_model.create(
                company_guid=self.company_guid
            )
            self.plan_guid = plan_model.create(
                company_guid=self.company_guid,
                frequency=plan_model.FREQ_WEEKLY,
                plan_type=plan_model.TYPE_CHARGE,
                amount=10,
            )
            self.subscription_guid = subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
            self.transaction_guid = transaction_model.create(
                subscription_guid=self.subscription_guid,
                transaction_cls=transaction_model.CLS_SUBSCRIPTION,
                transaction_type=transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
            self.invoice_guid = invoice_model.create(
                customer_guid=self.customer_guid,
                amount=100,
                title='foobar invoice',
                external_id='external ID',
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
        self.dummy_request = DummyRequest()

    def test_company(self):
        from billy.models.company import CompanyModel
        from billy.renderers import company_adapter
        company_model = CompanyModel(self.testapp.session)
        company = company_model.get(self.company_guid)
        json_data = company_adapter(company, self.dummy_request)
        expected = dict(
            guid=company.guid,
            api_key=company.api_key,
            created_at=company.created_at.isoformat(),
            updated_at=company.updated_at.isoformat(),
        )
        self.assertEqual(json_data, expected)

    def test_customer(self):
        from billy.models.customer import CustomerModel
        from billy.renderers import customer_adapter
        customer_model = CustomerModel(self.testapp.session)
        customer = customer_model.get(self.customer_guid)
        json_data = customer_adapter(customer, self.dummy_request)
        expected = dict(
            guid=customer.guid,
            external_id=customer.external_id, 
            created_at=customer.created_at.isoformat(),
            updated_at=customer.updated_at.isoformat(),
            company_guid=customer.company_guid, 
            deleted=customer.deleted, 
        )
        self.assertEqual(json_data, expected)

    def test_invoice(self):
        from billy.models.invoice import InvoiceModel
        from billy.renderers import invoice_adapter
        invoice_model = InvoiceModel(self.testapp.session)
        invoice = invoice_model.get(self.invoice_guid)
        json_data = invoice_adapter(invoice, self.dummy_request)
        expected = dict(
            guid=invoice.guid,
            status='init',
            created_at=invoice.created_at.isoformat(),
            updated_at=invoice.updated_at.isoformat(),
            customer_guid=invoice.customer_guid, 
            amount=invoice.amount, 
            effective_amount=invoice.effective_amount, 
            title=invoice.title, 
            external_id=invoice.external_id, 
            payment_uri=None, 
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

        assert_status(InvoiceModel.STATUS_INIT, 'init')
        assert_status(InvoiceModel.STATUS_PROCESSING, 'processing')
        assert_status(InvoiceModel.STATUS_SETTLED, 'settled')
        assert_status(InvoiceModel.STATUS_CANCELED, 'canceled')
        assert_status(InvoiceModel.STATUS_PROCESS_FAILED, 'process_failed')
        assert_status(InvoiceModel.STATUS_REFUNDING, 'refunding')
        assert_status(InvoiceModel.STATUS_REFUNDED, 'refunded')
        assert_status(InvoiceModel.STATUS_REFUND_FAILED, 'refund_failed')

    def test_plan(self):
        from billy.models.plan import PlanModel
        from billy.renderers import plan_adapter
        plan_model = PlanModel(self.testapp.session)
        plan = plan_model.get(self.plan_guid)
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

        assert_type(PlanModel.TYPE_CHARGE, 'charge')
        assert_type(PlanModel.TYPE_PAYOUT, 'payout')

        def assert_frequency(frequency, expected_frequency):
            plan.frequency = frequency 
            json_data = plan_adapter(plan, self.dummy_request)
            self.assertEqual(json_data['frequency'], expected_frequency)

        assert_frequency(PlanModel.FREQ_DAILY, 'daily')
        assert_frequency(PlanModel.FREQ_WEEKLY, 'weekly')
        assert_frequency(PlanModel.FREQ_MONTHLY, 'monthly')
        assert_frequency(PlanModel.FREQ_YEARLY, 'yearly')

    def test_subscription(self):
        from billy.models.subscription import SubscriptionModel
        from billy.renderers import subscription_adapter
        subscription_model = SubscriptionModel(self.testapp.session)
        subscription = subscription_model.get(self.subscription_guid)
        json_data = subscription_adapter(subscription, self.dummy_request)
        expected = dict(
            guid=subscription.guid, 
            amount=None,
            payment_uri=subscription.payment_uri,
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

        def assert_amount(amount, expected_amount):
            subscription.amount = amount 
            json_data = subscription_adapter(subscription, self.dummy_request)
            self.assertEqual(json_data['amount'], expected_amount)

        assert_amount(None, None)
        assert_amount(1234, 1234)

        def assert_canceled_at(canceled_at, expected_canceled_at):
            subscription.canceled_at = canceled_at 
            json_data = subscription_adapter(subscription, self.dummy_request)
            self.assertEqual(json_data['canceled_at'], expected_canceled_at)

        now = datetime.datetime.utcnow()
        assert_canceled_at(None, None)
        assert_canceled_at(now, now.isoformat())

    def test_transaction(self):
        from billy.models.transaction import TransactionModel
        from billy.renderers import transaction_adapter
        transaction_model = TransactionModel(self.testapp.session)
        transaction = transaction_model.get(self.transaction_guid)
        json_data = transaction_adapter(transaction, self.dummy_request)
        expected = dict(
            guid=transaction.guid, 
            transaction_type='charge',
            transaction_cls='subscription',
            status='init',
            amount=transaction.amount,
            payment_uri=transaction.payment_uri,
            external_id=transaction.external_id,
            failure_count=transaction.failure_count,
            error_message=transaction.error_message,
            created_at=transaction.created_at.isoformat(),
            updated_at=transaction.updated_at.isoformat(),
            scheduled_at=transaction.scheduled_at.isoformat(),
            subscription_guid=transaction.subscription_guid,
        )
        self.assertEqual(json_data, expected)

        def assert_type(transaction_type, expected_type):
            transaction.transaction_type = transaction_type
            json_data = transaction_adapter(transaction, self.dummy_request)
            self.assertEqual(json_data['transaction_type'], expected_type)

        assert_type(TransactionModel.TYPE_CHARGE, 'charge')
        assert_type(TransactionModel.TYPE_PAYOUT, 'payout')
        assert_type(TransactionModel.TYPE_REFUND, 'refund')

        def assert_status(transaction_status, expected_status):
            transaction.status = transaction_status
            json_data = transaction_adapter(transaction, self.dummy_request)
            self.assertEqual(json_data['status'], expected_status)

        assert_status(TransactionModel.STATUS_INIT, 'init')
        assert_status(TransactionModel.STATUS_RETRYING, 'retrying')
        assert_status(TransactionModel.STATUS_FAILED, 'failed')
        assert_status(TransactionModel.STATUS_DONE, 'done')
        assert_status(TransactionModel.STATUS_CANCELED, 'canceled')

        # test invoice transaction
        transaction_guid = transaction_model.create(
            invoice_guid=self.invoice_guid,
            transaction_cls=transaction_model.CLS_INVOICE,
            transaction_type=transaction_model.TYPE_CHARGE,
            amount=10,
            payment_uri='/v1/cards/tester',
            scheduled_at=datetime.datetime.utcnow(),
        )
        transaction = transaction_model.get(transaction_guid)
        json_data = transaction_adapter(transaction, self.dummy_request)
        expected = dict(
            guid=transaction.guid, 
            transaction_type='charge',
            transaction_cls='invoice',
            status='init',
            amount=transaction.amount,
            payment_uri=transaction.payment_uri,
            external_id=transaction.external_id,
            failure_count=transaction.failure_count,
            error_message=transaction.error_message,
            created_at=transaction.created_at.isoformat(),
            updated_at=transaction.updated_at.isoformat(),
            scheduled_at=transaction.scheduled_at.isoformat(),
            invoice_guid=transaction.invoice_guid,
        )
        self.assertEqual(json_data, expected)
