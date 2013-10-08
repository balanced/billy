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
        super(TestRenderer, self).setUp()
        company_model = CompanyModel(self.testapp.session)
        customer_model = CustomerModel(self.testapp.session)
        plan_model = PlanModel(self.testapp.session)
        subscription_model = SubscriptionModel(self.testapp.session)
        transaction_model = TransactionModel(self.testapp.session)
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
                transaction_type=transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
        self.dummy_request = DummyRequest()

    def test_transaction(self):
        from billy.models.transaction import TransactionModel
        from billy.renderers import transaction_adapter
        transaction_model = TransactionModel(self.testapp.session)
        transaction = transaction_model.get(self.transaction_guid)
        json_data = transaction_adapter(transaction, self.dummy_request)
        expected = dict(
            guid=transaction.guid, 
            transaction_type='charge',
            status='init',
            amount=str(transaction.amount),
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
