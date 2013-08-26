from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestTransactionViews(ViewTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        from billy.models.plan import PlanModel
        from billy.models.subscription import SubscriptionModel
        from billy.models.transaction import TransactionModel
        super(TestTransactionViews, self).setUp()
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
        company = company_model.get(self.company_guid)
        self.api_key = str(company.api_key)

    def test_get_transaction(self):
        from billy.models.transaction import TransactionModel
        transaction_model = TransactionModel(self.testapp.session)
        res = self.testapp.get(
            '/v1/transactions/{}'.format(self.transaction_guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        transaction = transaction_model.get(self.transaction_guid)
        self.assertEqual(res.json['guid'], transaction.guid)
        self.assertEqual(res.json['created_at'], 
                         transaction.created_at.isoformat())
        self.assertEqual(res.json['updated_at'], 
                         transaction.updated_at.isoformat())
        self.assertEqual(res.json['scheduled_at'], 
                         transaction.scheduled_at.isoformat())
        self.assertEqual(res.json['amount'], str(transaction.amount))
        self.assertEqual(res.json['payment_uri'], transaction.payment_uri)
        self.assertEqual(res.json['transaction_type'], 'charge')
        self.assertEqual(res.json['status'], 'init')
        self.assertEqual(res.json['error_message'], None)
        self.assertEqual(res.json['failure_count'], 0)
        self.assertEqual(res.json['external_id'], None)
        self.assertEqual(res.json['subscription_guid'], 
                         transaction.subscription_guid)

    def test_transaction_list_by_company(self):
        from billy.models.transaction import TransactionModel
        transaction_model = TransactionModel(self.testapp.session)
        guids = [self.transaction_guid]
        with db_transaction.manager:
            for i in range(9):
                guid = transaction_model.create(
                    subscription_guid=self.subscription_guid,
                    transaction_type=transaction_model.TYPE_CHARGE,
                    amount=10 * i,
                    payment_uri='/v1/cards/tester',
                    scheduled_at=datetime.datetime.utcnow(),
                )
                guids.append(guid)
        res = self.testapp.get(
            '/v1/transactions/?offset=5&limit=3',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json['offset'], 5)
        self.assertEqual(res.json['limit'], 3)
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(set(result_guids), set(guids[5:8]))

    def test_transaction_list_by_company_with_bad_api_key(self):
        self.testapp.get(
            '/v1/transactions/',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_transaction_with_different_types(self):
        from billy.models.transaction import TransactionModel
        transaction_model = TransactionModel(self.testapp.session)

        def assert_type(tx_type, expected):
            with db_transaction.manager:
                transaction = transaction_model.get(self.transaction_guid)
                transaction.transaction_type = tx_type
                self.testapp.session.add(transaction)

            res = self.testapp.get(
                '/v1/transactions/{}'.format(self.transaction_guid), 
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=200,
            )
            transaction = transaction_model.get(self.transaction_guid)
            self.assertEqual(res.json['transaction_type'], expected)

        assert_type(transaction_model.TYPE_CHARGE, 'charge')
        assert_type(transaction_model.TYPE_PAYOUT, 'payout')
        assert_type(transaction_model.TYPE_REFUND, 'refund')

    def test_get_transaction_with_different_status(self):
        from billy.models.transaction import TransactionModel
        transaction_model = TransactionModel(self.testapp.session)

        def assert_status(status, expected):
            with db_transaction.manager:
                transaction = transaction_model.get(self.transaction_guid)
                transaction.status = status
                self.testapp.session.add(transaction)

            res = self.testapp.get(
                '/v1/transactions/{}'.format(self.transaction_guid), 
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=200,
            )
            transaction = transaction_model.get(self.transaction_guid)
            self.assertEqual(res.json['status'], expected)

        assert_status(transaction_model.STATUS_INIT, 'init')
        assert_status(transaction_model.STATUS_RETRYING, 'retrying')
        assert_status(transaction_model.STATUS_FAILED, 'failed')
        assert_status(transaction_model.STATUS_DONE, 'done')

    def test_get_non_existing_transaction(self):
        self.testapp.get(
            '/v1/transactions/NON_EXIST', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=404
        )

    def test_get_transaction_with_bad_api_key(self):
        self.testapp.get(
            '/v1/transactions/{}'.format(self.transaction_guid), 
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_transaction_of_other_company(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        from billy.models.plan import PlanModel
        from billy.models.subscription import SubscriptionModel
        from billy.models.transaction import TransactionModel
        company_model = CompanyModel(self.testapp.session)
        customer_model = CustomerModel(self.testapp.session)
        plan_model = PlanModel(self.testapp.session)
        subscription_model = SubscriptionModel(self.testapp.session)
        transaction_model = TransactionModel(self.testapp.session)
        with db_transaction.manager:
            other_company_guid = company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_customer_guid = customer_model.create(
                company_guid=other_company_guid
            )
            other_plan_guid = plan_model.create(
                company_guid=other_company_guid,
                frequency=plan_model.FREQ_WEEKLY,
                plan_type=plan_model.TYPE_CHARGE,
                amount=10,
            )
            other_subscription_guid = subscription_model.create(
                customer_guid=other_customer_guid,
                plan_guid=other_plan_guid,
            )
            other_transaction_guid = transaction_model.create(
                subscription_guid=other_subscription_guid,
                transaction_type=transaction_model.TYPE_CHARGE,
                amount=10,
                payment_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
        self.testapp.get(
            '/v1/transactions/{}'.format(other_transaction_guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )
