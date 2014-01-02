from __future__ import unicode_literals
import datetime

import mock
import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestSubscriptionViews(ViewTestCase):

    def setUp(self):
        super(TestSubscriptionViews, self).setUp()
        with db_transaction.manager:
            self.company_guid = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            self.customer_guid = self.customer_model.create(
                company_guid=self.company_guid
            )
            self.plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                frequency=self.plan_model.FREQ_WEEKLY,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=1000,
            )
        company = self.company_model.get(self.company_guid)
        self.api_key = str(company.api_key)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_create_subscription(self, charge_method):
        customer_guid = self.customer_guid
        plan_guid = self.plan_guid
        amount = 5566
        payment_uri = 'MOCK_CARD_URI'
        appears_on_statement_as = 'hello baby'
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()
        # next week
        next_transaction_at = datetime.datetime(2013, 8, 23)
        next_iso = next_transaction_at.isoformat()
        charge_method.return_value = 'MOCK_DEBIT_URI'

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                amount=amount,
                payment_uri=payment_uri,
                appears_on_statement_as=appears_on_statement_as,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['canceled_at'], None)
        self.assertEqual(res.json['next_transaction_at'], next_iso)
        self.assertEqual(res.json['period'], 1)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['customer_guid'], customer_guid)
        self.assertEqual(res.json['plan_guid'], plan_guid)
        self.assertEqual(res.json['payment_uri'], payment_uri)
        self.assertEqual(res.json['appears_on_statement_as'], 
                         appears_on_statement_as)
        self.assertEqual(res.json['canceled'], False)

        subscription = self.subscription_model.get(res.json['guid'])
        self.assertEqual(len(subscription.transactions), 1)
        transaction = subscription.transactions[0]
        charge_method.assert_called_once_with(transaction)
        self.assertEqual(transaction.external_id, 
                         'MOCK_DEBIT_URI')
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        self.assertEqual(transaction.appears_on_statement_as, 
                         subscription.appears_on_statement_as)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.prepare_customer')
    def test_create_subscription_with_default_payment_uri(self, prepare_customer):
        customer = self.customer_model.get(self.customer_guid)
        amount = 5566

        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                amount=amount,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        prepare_customer.assert_called_once_with(customer, None)

    def test_create_subscription_to_a_deleted_plan(self):
        with db_transaction.manager:
            plan_guid = self.plan_model.create(
                company_guid=self.company_guid,
                frequency=self.plan_model.FREQ_WEEKLY,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
            )
            self.plan_model.delete(plan_guid)

        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer_guid,
                plan_guid=plan_guid,
                amount='123',
                payment_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_create_subscription_to_a_deleted_customer(self):
        with db_transaction.manager:
            customer_guid = self.customer_model.create(
                company_guid=self.company_guid
            )
            self.customer_model.delete(customer_guid)

        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=customer_guid,
                plan_guid=self.plan_guid,
                amount='123',
                payment_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_create_subscription_with_none_amount(self):
        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                payment_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json['amount'], None)

    def test_create_subscription_with_past_started_at(self):
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                started_at='2013-08-15T23:59:59Z',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_create_subscription_with_bad_parameters(self):
        def assert_bad_parameters(params):
            self.testapp.post(
                '/v1/subscriptions',
                params, 
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=400,
            )
        assert_bad_parameters({})
        assert_bad_parameters(dict(customer_guid=self.customer_guid))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.plan_guid,
            amount='BAD_AMOUNT',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.plan_guid,
            amount='-12345',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.plan_guid,
            amount=0,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.plan_guid,
            amount=49,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.plan_guid,
            started_at='BAD_DATETIME',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.plan_guid,
            plan_guid=self.plan_guid,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.customer_guid,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.customer_guid,
            amount=999,
            appears_on_statement_as='bad\tstatement',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            plan_guid=self.customer_guid,
            amount=999,
            appears_on_statement_as='bad\0statement',
        ))

    def test_create_subscription_with_started_at(self):
        customer_guid = self.customer_guid
        plan_guid = self.plan_guid
        amount = 5566
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()
        # next week
        next_transaction_at = datetime.datetime(2013, 8, 17)
        next_iso = next_transaction_at.isoformat()

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                amount=amount,
                started_at='2013-08-17T00:00:00Z',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['next_transaction_at'], next_iso)
        self.assertEqual(res.json['period'], 0)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['customer_guid'], customer_guid)
        self.assertEqual(res.json['plan_guid'], plan_guid)

    def test_create_subscription_with_started_at_and_timezone(self):
        customer_guid = self.customer_guid
        plan_guid = self.plan_guid
        amount = 5566
        # next week
        next_transaction_at = datetime.datetime(2013, 8, 17)
        next_iso = next_transaction_at.isoformat()

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=customer_guid,
                plan_guid=plan_guid,
                amount=amount,
                started_at='2013-08-17T08:00:00+08:00',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['next_transaction_at'], next_iso)
        self.assertEqual(res.json['period'], 0)

    def test_create_subscription_with_bad_api(self):
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_subscription(self):
        res = self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_subscription = res.json

        guid = created_subscription['guid']
        res = self.testapp.get(
            '/v1/subscriptions/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json, created_subscription)

    def test_get_non_existing_subscription(self):
        self.testapp.get(
            '/v1/subscriptions/NON_EXIST', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=404
        )

    def test_get_subscription_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )

        guid = res.json['guid']
        res = self.testapp.get(
            '/v1/subscriptions/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_subscription_of_other_company(self):
        with db_transaction.manager:
            other_company_guid = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_customer_guid = self.customer_model.create(
                company_guid=other_company_guid
            )
            other_plan_guid = self.plan_model.create(
                company_guid=other_company_guid,
                frequency=self.plan_model.FREQ_WEEKLY,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
            )
        other_company = self.company_model.get(other_company_guid)
        other_api_key = str(other_company.api_key)

        res = self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=other_customer_guid,
                plan_guid=other_plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=other_api_key), 
            status=200,
        )
        other_guid = res.json['guid']

        self.testapp.get(
            '/v1/subscriptions/{}'.format(other_guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_create_subscription_to_other_company_customer(self):
        with db_transaction.manager:
            other_company_guid = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_customer_guid = self.customer_model.create(
                company_guid=other_company_guid
            )

        self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=other_customer_guid,
                plan_guid=self.plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_create_subscription_to_other_company_plan(self):
        with db_transaction.manager:
            other_company_guid = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_plan_guid = self.plan_model.create(
                company_guid=other_company_guid,
                frequency=self.plan_model.FREQ_WEEKLY,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
            )

        self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=self.customer_guid,
                plan_guid=other_plan_guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_cancel_subscription(self):
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            subscription_guid = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
            self.transaction_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100, 
                scheduled_at=now,
            )

        with freeze_time('2013-08-16 07:00:00'):
            canceled_at = datetime.datetime.utcnow()
            res = self.testapp.post(
                '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=200,
            )

        subscription = res.json
        self.assertEqual(subscription['canceled'], True)
        self.assertEqual(subscription['canceled_at'], canceled_at.isoformat())

    def test_cancel_a_canceled_subscription(self):
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            subscription_guid = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
            self.transaction_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100, 
                scheduled_at=now,
            )

        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_cancel_subscription_to_other_company(self):
        with db_transaction.manager:
            subscription_guid = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
            other_company_guid = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_company = self.company_model.get(other_company_guid)
            other_api_key = str(other_company.api_key)

        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
            extra_environ=dict(REMOTE_USER=other_api_key), 
            status=403,
        )

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.refund')
    def test_cancel_subscription_with_prorated_refund(self, refund_method):
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            subscription_guid = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                amount=10000,
            )
            tx_guid = self.transaction_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10000, 
                scheduled_at=now,
            )
            subscription = self.subscription_model.get(subscription_guid)
            subscription.period = 1
            subscription.next_transaction_at = datetime.datetime(2013, 8, 23)
            self.testapp.session.add(subscription)

            transaction = self.transaction_model.get(tx_guid)
            transaction.status = self.transaction_model.STATUS_DONE
            transaction.external_id = 'MOCK_BALANCED_DEBIT_URI'
            self.testapp.session.add(transaction)

        refund_method.return_value = 'MOCK_REFUND_URI'

        with freeze_time('2013-08-17'):
            canceled_at = datetime.datetime.utcnow()
            res = self.testapp.post(
                '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
                dict(prorated_refund=True),
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=200,
            )

        subscription = res.json
        self.assertEqual(subscription['canceled'], True)
        self.assertEqual(subscription['canceled_at'], canceled_at.isoformat())

        transaction = refund_method.call_args[0][0]
        self.assertEqual(refund_method.call_count, 1)
        self.assertEqual(transaction.refund_to.guid, tx_guid)
        self.assertEqual(transaction.subscription_guid, subscription_guid)
        # only one day is elapsed, and it is a weekly plan, so
        # it should be 10000 - (10000 / 7) and round to cent, 8571
        self.assertEqual(transaction.amount, 8571)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)

        res = self.testapp.get(
            '/v1/transactions', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        guids = [item['guid'] for item in res.json['items']]
        self.assertEqual(set(guids), set([tx_guid, transaction.guid]))

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.refund')
    def test_cancel_subscription_with_refund_amount(self, refund_method):
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            subscription_guid = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
            tx_guid = self.transaction_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=1000, 
                scheduled_at=now,
            )
            subscription = self.subscription_model.get(subscription_guid)
            subscription.period = 1
            subscription.next_transaction_at = datetime.datetime(2013, 8, 23)
            self.testapp.session.add(subscription)

            transaction = self.transaction_model.get(tx_guid)
            transaction.status = self.transaction_model.STATUS_DONE
            transaction.external_id = 'MOCK_BALANCED_DEBIT_URI'
            self.testapp.session.add(transaction)

        refund_method.return_value = 'MOCK_REFUND_URI'

        res = self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
            dict(
                refund_amount=234,
                appears_on_statement_as='good bye',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        subscription = res.json

        transaction = refund_method.call_args[0][0]
        self.assertEqual(transaction.refund_to.guid, tx_guid)
        self.assertEqual(transaction.subscription_guid, subscription_guid)
        self.assertEqual(transaction.amount, 234)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        self.assertEqual(transaction.appears_on_statement_as, 'good bye')

        res = self.testapp.get(
            '/v1/transactions', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        guids = [item['guid'] for item in res.json['items']]
        self.assertEqual(set(guids), set([tx_guid, transaction.guid]))

    def test_cancel_subscription_with_bad_arguments(self):
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            subscription_guid = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
                amount=10000,
            )
            tx_guid = self.transaction_model.create(
                subscription_guid=subscription_guid,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10000, 
                scheduled_at=now,
            )
            subscription = self.subscription_model.get(subscription_guid)
            subscription.period = 1
            subscription.next_transaction_at = datetime.datetime(2013, 8, 23)
            self.testapp.session.add(subscription)

            transaction = self.transaction_model.get(tx_guid)
            transaction.status = self.transaction_model.STATUS_DONE
            transaction.external_id = 'MOCK_BALANCED_DEBIT_URI'
            self.testapp.session.add(transaction)

        def assert_bad_parameters(kwargs):
            self.testapp.post(
                '/v1/subscriptions/{}/cancel'.format(subscription_guid), 
                kwargs,
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=400,
            )
        assert_bad_parameters(dict(prorated_refund=True, refund_amount=10))
        assert_bad_parameters(dict(refund_amount=10001))

    def test_transaction_list_by_subscription(self):
        with db_transaction.manager:
            subscription_guid1 = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
            subscription_guid2 = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )
        guids1 = []
        guids2 = []
        with db_transaction.manager:
            for i in range(10):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    guid = self.transaction_model.create(
                        subscription_guid=subscription_guid1,
                        transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                        transaction_type=self.transaction_model.TYPE_CHARGE,
                        amount=10 * i,
                        payment_uri='/v1/cards/tester',
                        scheduled_at=datetime.datetime.utcnow(),
                    )
                    guids1.append(guid)
            for i in range(20):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    guid = self.transaction_model.create(
                        subscription_guid=subscription_guid2,
                        transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                        transaction_type=self.transaction_model.TYPE_CHARGE,
                        amount=10 * i,
                        payment_uri='/v1/cards/tester',
                        scheduled_at=datetime.datetime.utcnow(),
                    )
                    guids2.append(guid)
        guids1 = list(reversed(guids1))
        guids2 = list(reversed(guids2))

        res = self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription_guid1),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids1)

        res = self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription_guid2),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids2)

    def test_transaction_list_by_subscription_with_bad_api_key(self):
        with db_transaction.manager:
            subscription_guid = self.subscription_model.create(
                customer_guid=self.customer_guid,
                plan_guid=self.plan_guid,
            )

        self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription_guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_subscription_list(self):
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    guid = self.subscription_model.create(
                        customer_guid=self.customer_guid,
                        plan_guid=self.plan_guid,
                    )
                    guids.append(guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/subscriptions',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_subscription_list_with_bad_api_key(self):
        self.testapp.get(
            '/v1/subscriptions',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )
