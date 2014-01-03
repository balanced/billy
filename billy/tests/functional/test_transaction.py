from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestTransactionViews(ViewTestCase):

    def setUp(self):
        super(TestTransactionViews, self).setUp()
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
                amount=10,
            )
            self.subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
            self.transaction = self.transaction_model.create(
                subscription=self.subscription,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
        self.api_key = str(self.company.api_key)

    def test_get_transaction(self):
        res = self.testapp.get(
            '/v1/transactions/{}'.format(self.transaction.guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        transaction = self.transaction_model.get(self.transaction.guid)
        self.assertEqual(res.json['guid'], transaction.guid)
        self.assertEqual(res.json['created_at'], 
                         transaction.created_at.isoformat())
        self.assertEqual(res.json['updated_at'], 
                         transaction.updated_at.isoformat())
        self.assertEqual(res.json['scheduled_at'], 
                         transaction.scheduled_at.isoformat())
        self.assertEqual(res.json['amount'], transaction.amount)
        self.assertEqual(res.json['funding_instrument_uri'], transaction.funding_instrument_uri)
        self.assertEqual(res.json['transaction_type'], 'charge')
        self.assertEqual(res.json['transaction_cls'], 'subscription')
        self.assertEqual(res.json['status'], 'init')
        self.assertEqual(res.json['error_message'], None)
        self.assertEqual(res.json['failure_count'], 0)
        self.assertEqual(res.json['processor_uri'], None)
        self.assertEqual(res.json['subscription_guid'], 
                         transaction.subscription_guid)

    def test_transaction_list_by_company(self):
        guids = [self.transaction.guid]
        with db_transaction.manager:
            for i in range(9):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        subscription=self.subscription,
                        transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                        transaction_type=self.transaction_model.TYPE_CHARGE,
                        amount=10 * i,
                        funding_instrument_uri='/v1/cards/tester',
                        scheduled_at=datetime.datetime.utcnow(),
                    )
                    guids.append(transaction.guid)
        guids = list(reversed(guids))
        res = self.testapp.get(
            '/v1/transactions?offset=5&limit=3',
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
            '/v1/transactions',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_transaction_with_different_types(self):
        def assert_type(tx_type, expected):
            with db_transaction.manager:
                self.transaction.transaction_type = tx_type

            res = self.testapp.get(
                '/v1/transactions/{}'.format(self.transaction.guid), 
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=200,
            )
            self.assertEqual(res.json['transaction_type'], expected)

        assert_type(self.transaction_model.TYPE_CHARGE, 'charge')
        assert_type(self.transaction_model.TYPE_PAYOUT, 'payout')
        assert_type(self.transaction_model.TYPE_REFUND, 'refund')

    def test_get_transaction_with_different_status(self):
        def assert_status(status, expected):
            with db_transaction.manager:
                self.transaction.status = status

            res = self.testapp.get(
                '/v1/transactions/{}'.format(self.transaction.guid), 
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=200,
            )
            self.assertEqual(res.json['status'], expected)

        assert_status(self.transaction_model.STATUS_INIT, 'init')
        assert_status(self.transaction_model.STATUS_RETRYING, 'retrying')
        assert_status(self.transaction_model.STATUS_FAILED, 'failed')
        assert_status(self.transaction_model.STATUS_DONE, 'done')

    def test_get_non_existing_transaction(self):
        self.testapp.get(
            '/v1/transactions/NON_EXIST', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=404
        )

    def test_get_transaction_with_bad_api_key(self):
        self.testapp.get(
            '/v1/transactions/{}'.format(self.transaction.guid), 
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_transaction_of_other_company(self):
        with db_transaction.manager:
            other_company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_customer = self.customer_model.create(
                company=other_company
            )
            other_plan = self.plan_model.create(
                company=other_company,
                frequency=self.plan_model.FREQ_WEEKLY,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
            )
            other_subscription = self.subscription_model.create(
                customer=other_customer,
                plan=other_plan,
            )
            other_transaction = self.transaction_model.create(
                subscription=other_subscription,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                amount=10,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )
        self.testapp.get(
            '/v1/transactions/{}'.format(other_transaction.guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )
