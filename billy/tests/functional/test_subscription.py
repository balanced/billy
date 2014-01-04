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
                amount=1000,
            )

            self.company2 = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY2',
            )
            self.customer2 = self.customer_model.create(
                company=self.company2
            )
            self.plan2 = self.plan_model.create(
                company=self.company2,
                frequency=self.plan_model.FREQ_WEEKLY,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=10,
            )
        self.api_key = str(self.company.api_key)
        self.api_key2 = str(self.company2.api_key)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_create_subscription(self, charge_method):
        amount = 5566
        funding_instrument_uri = 'MOCK_CARD_URI'
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
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount=amount,
                funding_instrument_uri=funding_instrument_uri,
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
        self.assertEqual(res.json['customer_guid'], self.customer.guid)
        self.assertEqual(res.json['plan_guid'], self.plan.guid)
        self.assertEqual(res.json['funding_instrument_uri'], funding_instrument_uri)
        self.assertEqual(res.json['appears_on_statement_as'], 
                         appears_on_statement_as)
        self.assertEqual(res.json['canceled'], False)

        subscription = self.subscription_model.get(res.json['guid'])
        self.assertEqual(len(subscription.transactions), 1)
        transaction = subscription.transactions[0]
        charge_method.assert_called_once_with(transaction)
        self.assertEqual(transaction.processor_uri, 
                         'MOCK_DEBIT_URI')
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        self.assertEqual(transaction.appears_on_statement_as, 
                         subscription.appears_on_statement_as)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_create_subscription_with_charge_failure(self, charge_method):
        error = RuntimeError('Oops!')
        charge_method.side_effect = error

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        subscription = self.subscription_model.get(res.json['guid'])
        self.assertEqual(len(subscription.transactions), 1)
        transaction = subscription.transactions[0]
        self.assertEqual(transaction.failure_count, 1)
        self.assertEqual(transaction.failures[0].error_message, unicode(error))
        self.assertEqual(transaction.status, 
                         self.transaction_model.STATUS_RETRYING)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_create_subscription_with_charge_failure_exceed_limit(
        self, 
        charge_method,
    ):
        self.model_factory.settings['billy.transaction.maximum_retry'] = 3
        error = RuntimeError('Oops!')
        charge_method.side_effect = error

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        subscription = self.subscription_model.get(res.json['guid'])
        transaction = subscription.transactions[0]

        for i in range(2):
            self.transaction_model.process_one(transaction)
            self.assertEqual(transaction.failure_count, 2 + i)
            self.assertEqual(transaction.status, 
                             self.transaction_model.STATUS_RETRYING)

        self.transaction_model.process_one(transaction)
        self.assertEqual(transaction.failure_count, 4)
        self.assertEqual(transaction.status, 
                         self.transaction_model.STATUS_FAILED)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.prepare_customer')
    def test_create_subscription_with_default_funding_instrument_uri(self, prepare_customer):
        amount = 5566

        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount=amount,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        prepare_customer.assert_called_once_with(self.customer, None)

    def test_create_subscription_to_a_deleted_plan(self):
        with db_transaction.manager:
            self.plan_model.delete(self.plan)

        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount='123',
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_create_subscription_to_a_deleted_customer(self):
        with db_transaction.manager:
            self.customer_model.delete(self.customer)

        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount='123',
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_create_subscription_with_none_amount(self):
        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json['amount'], None)

    def test_create_subscription_with_past_started_at(self):
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
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
        assert_bad_parameters(dict(customer_guid=self.customer.guid))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.plan.guid,
            amount='BAD_AMOUNT',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.plan.guid,
            amount='-12345',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.plan.guid,
            amount=0,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.plan.guid,
            amount=49,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.plan.guid,
            started_at='BAD_DATETIME',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.plan.guid,
            plan_guid=self.plan.guid,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.customer.guid,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.customer.guid,
            amount=999,
            appears_on_statement_as='bad\tstatement',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            plan_guid=self.customer.guid,
            amount=999,
            appears_on_statement_as='bad\0statement',
        ))

    def test_create_subscription_with_started_at(self):
        amount = 5566
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()
        # next week
        next_transaction_at = datetime.datetime(2013, 8, 17)
        next_iso = next_transaction_at.isoformat()

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
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
        self.assertEqual(res.json['customer_guid'], self.customer.guid)
        self.assertEqual(res.json['plan_guid'], self.plan.guid)

    def test_create_subscription_with_started_at_and_timezone(self):
        amount = 5566
        # next week
        next_transaction_at = datetime.datetime(2013, 8, 17)
        next_iso = next_transaction_at.isoformat()
        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
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
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
            ),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_subscription(self):
        res = self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
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
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
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
        res = self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=self.customer2.guid,
                plan_guid=self.plan2.guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key2), 
            status=200,
        )
        other_guid = res.json['guid']

        self.testapp.get(
            '/v1/subscriptions/{}'.format(other_guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_create_subscription_to_other_company_customer(self):
        self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=self.customer2.guid,
                plan_guid=self.plan.guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_create_subscription_to_other_company_plan(self):
        self.testapp.post(
            '/v1/subscriptions', 
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan2.guid,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_cancel_subscription(self):
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
            self.transaction_model.create(
                subscription=subscription,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100, 
                scheduled_at=now,
            )

        with freeze_time('2013-08-16 07:00:00'):
            canceled_at = datetime.datetime.utcnow()
            res = self.testapp.post(
                '/v1/subscriptions/{}/cancel'.format(subscription.guid), 
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=200,
            )

        subscription = res.json
        self.assertEqual(subscription['canceled'], True)
        self.assertEqual(subscription['canceled_at'], canceled_at.isoformat())

    def test_cancel_a_canceled_subscription(self):
        now = datetime.datetime.utcnow()

        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
            self.transaction_model.create(
                subscription=subscription,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100, 
                scheduled_at=now,
            )

        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription.guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription.guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_cancel_subscription_to_other_company(self):
        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )

        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription.guid), 
            extra_environ=dict(REMOTE_USER=self.api_key2), 
            status=403,
        )

    def _create_charge_transaction(self):
        now = datetime.datetime.utcnow()
        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
                amount=10000,
            )
            subscription.period = 1
            subscription.next_transaction_at = datetime.datetime(2013, 8, 23)
            charge_transaction = self.transaction_model.create(
                subscription=subscription,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=10000, 
                scheduled_at=now,
            )
            charge_transaction.status = self.transaction_model.STATUS_DONE
            charge_transaction.processor_uri = 'MOCK_BALANCED_DEBIT_URI'
        return charge_transaction

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.refund')
    def test_cancel_subscription_with_prorated_refund(self, refund_method):
        charge_transaction = self._create_charge_transaction()
        refund_method.return_value = 'MOCK_REFUND_URI'

        with freeze_time('2013-08-17'):
            canceled_at = datetime.datetime.utcnow()
            res = self.testapp.post(
                '/v1/subscriptions/{}/cancel'.format(
                    charge_transaction.subscription.guid
                ), 
                dict(prorated_refund=True),
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=200,
            )

        subscription = res.json
        self.assertEqual(subscription['canceled'], True)
        self.assertEqual(subscription['canceled_at'], canceled_at.isoformat())

        transaction = refund_method.call_args[0][0]
        self.assertEqual(refund_method.call_count, 1)
        self.assertEqual(transaction.refund_to, charge_transaction)
        self.assertEqual(transaction.subscription.guid, subscription['guid'])
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
        self.assertEqual(
            set(guids), 
            set([charge_transaction.guid, transaction.guid]),
        )

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.refund')
    def test_cancel_subscription_with_refund_amount(self, refund_method):
        charge_transaction = self._create_charge_transaction()
        refund_method.return_value = 'MOCK_REFUND_URI'

        res = self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(
                charge_transaction.subscription.guid,
            ), 
            dict(
                refund_amount=234,
                appears_on_statement_as='good bye',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        subscription = res.json

        transaction = refund_method.call_args[0][0]
        self.assertEqual(transaction.refund_to, charge_transaction)
        self.assertEqual(transaction.subscription.guid, subscription['guid'])
        self.assertEqual(transaction.amount, 234)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        self.assertEqual(transaction.appears_on_statement_as, 'good bye')

        res = self.testapp.get(
            '/v1/transactions', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        guids = [item['guid'] for item in res.json['items']]
        self.assertEqual(
            set(guids), 
            set([charge_transaction.guid, transaction.guid]),
        )

    def test_cancel_subscription_with_bad_arguments(self):
        charge_transaction = self._create_charge_transaction()

        def assert_bad_parameters(kwargs):
            self.testapp.post(
                '/v1/subscriptions/{}/cancel'.format(
                    charge_transaction.subscription.guid,
                ), 
                kwargs,
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=400,
            )
        assert_bad_parameters(dict(prorated_refund=True, refund_amount=10))
        assert_bad_parameters(dict(refund_amount=10001))

    def test_transaction_list_by_subscription(self):
        with db_transaction.manager:
            subscription1 = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
            subscription2 = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
            # make a transaction in other comapny, make sure it will not be
            # included in listing result
            subscription3 = self.subscription_model.create(
                customer=self.customer2,
                plan=self.plan2,
            )
            self.transaction_model.create(
                subscription=subscription3,
                transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                transaction_type=self.transaction_model.TYPE_CHARGE,
                amount=100,
                funding_instrument_uri='/v1/cards/tester',
                scheduled_at=datetime.datetime.utcnow(),
            )

        guids1 = []
        guids2 = []
        with db_transaction.manager:
            for i in range(10):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        subscription=subscription1,
                        transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                        transaction_type=self.transaction_model.TYPE_CHARGE,
                        amount=10 * i,
                        funding_instrument_uri='/v1/cards/tester',
                        scheduled_at=datetime.datetime.utcnow(),
                    )
                    guids1.append(transaction.guid)
            for i in range(20):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        subscription=subscription2,
                        transaction_cls=self.transaction_model.CLS_SUBSCRIPTION,
                        transaction_type=self.transaction_model.TYPE_CHARGE,
                        amount=10 * i,
                        funding_instrument_uri='/v1/cards/tester',
                        scheduled_at=datetime.datetime.utcnow(),
                    )
                    guids2.append(transaction.guid)
        guids1 = list(reversed(guids1))
        guids2 = list(reversed(guids2))

        res = self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription1.guid),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids1)

        res = self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription2.guid),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids2)

    def test_transaction_list_by_subscription_with_bad_api_key(self):
        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )

        self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription.guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_subscription_list(self):
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    subscription = self.subscription_model.create(
                        customer=self.customer,
                        plan=self.plan,
                    )
                    guids.append(subscription.guid)
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
