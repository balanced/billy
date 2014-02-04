from __future__ import unicode_literals
import datetime

import mock
import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase
from billy.errors import BillyError
from billy.utils.generic import utc_now
from billy.utils.generic import utc_datetime


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
                frequency=self.plan_model.frequencies.WEEKLY,
                plan_type=self.plan_model.types.DEBIT,
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
                frequency=self.plan_model.frequencies.WEEKLY,
                plan_type=self.plan_model.types.DEBIT,
                amount=10,
            )
        self.api_key = str(self.company.api_key)
        self.api_key2 = str(self.company2.api_key)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.configure_api_key')
    def test_processor_configure_api_key(self, configure_api_key_method):
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount=999,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        configure_api_key_method.assert_called_with(
            self.company.processor_key,
        )

        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer2.guid,
                plan_guid=self.plan2.guid,
                amount=999,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key2),
            status=200,
        )
        configure_api_key_method.assert_called_with(
            self.company2.processor_key,
        )

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.validate_funding_instrument')
    def test_create_subscription_with_invalid_funding_instrument(
        self,
        validate_funding_instrument_method,
    ):
        validate_funding_instrument_method.side_effect = BillyError('Invalid card!')
        self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                amount=999,
                funding_instrument_uri='BAD_INSTRUMENT_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )
        validate_funding_instrument_method.assert_called_once_with('BAD_INSTRUMENT_URI')

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_create_subscription(self, debit_method):
        amount = 5566
        funding_instrument_uri = 'MOCK_CARD_URI'
        appears_on_statement_as = 'hello baby'
        now = utc_now()
        now_iso = now.isoformat()
        # next week
        next_invoice_at = utc_datetime(2013, 8, 23)
        next_iso = next_invoice_at.isoformat()
        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )

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
        self.assertEqual(res.json['next_invoice_at'], next_iso)
        self.assertEqual(res.json['invoice_count'], 1)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['effective_amount'], amount)
        self.assertEqual(res.json['customer_guid'], self.customer.guid)
        self.assertEqual(res.json['plan_guid'], self.plan.guid)
        self.assertEqual(res.json['funding_instrument_uri'], funding_instrument_uri)
        self.assertEqual(res.json['appears_on_statement_as'],
                         appears_on_statement_as)
        self.assertEqual(res.json['canceled'], False)

        subscription = self.subscription_model.get(res.json['guid'])
        self.assertEqual(subscription.invoice_count, 1)

        invoice = subscription.invoices[0]
        self.assertEqual(len(invoice.transactions), 1)
        self.assertEqual(invoice.amount, amount)
        self.assertEqual(invoice.scheduled_at, now)
        self.assertEqual(invoice.transaction_type,
                         self.invoice_model.transaction_types.DEBIT)
        self.assertEqual(invoice.invoice_type,
                         self.invoice_model.types.SUBSCRIPTION)
        self.assertEqual(invoice.appears_on_statement_as,
                         appears_on_statement_as)

        transaction = invoice.transactions[0]
        debit_method.assert_called_once_with(transaction)
        self.assertEqual(transaction.processor_uri,
                         'MOCK_DEBIT_URI')
        self.assertEqual(transaction.submit_status, self.transaction_model.submit_statuses.DONE)
        self.assertEqual(transaction.appears_on_statement_as,
                         subscription.appears_on_statement_as)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.transaction_type,
                         self.transaction_model.types.DEBIT)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_create_subscription_with_charge_failure(self, debit_method):
        error = RuntimeError('Oops!')
        debit_method.side_effect = error

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                funding_instrument_uri='/v1/cards/foobar',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        subscription = self.subscription_model.get(res.json['guid'])
        self.assertEqual(subscription.invoice_count, 1)

        invoice = subscription.invoices[0]
        self.assertEqual(len(invoice.transactions), 1)

        transaction = invoice.transactions[0]
        self.assertEqual(transaction.failure_count, 1)
        self.assertEqual(transaction.failures[0].error_message, unicode(error))
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.RETRYING)

    def test_create_subscription_without_funding_instrument(self):
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
        self.assertEqual(subscription.invoice_count, 1)
        invoice = subscription.invoices[0]
        self.assertEqual(len(invoice.transactions), 0)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_create_subscription_with_charge_failure_exceed_limit(
        self,
        debit_method,
    ):
        self.model_factory.settings['billy.transaction.maximum_retry'] = 3
        error = RuntimeError('Oops!')
        debit_method.side_effect = error

        res = self.testapp.post(
            '/v1/subscriptions',
            dict(
                customer_guid=self.customer.guid,
                plan_guid=self.plan.guid,
                funding_instrument_uri='/v1/cards/foobar',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        subscription = self.subscription_model.get(res.json['guid'])
        self.assertEqual(subscription.invoice_count, 1)
        invoice = subscription.invoices[0]
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]

        for i in range(2):
            self.transaction_model.process_one(transaction)
            self.assertEqual(transaction.failure_count, 2 + i)
            self.assertEqual(transaction.submit_status,
                             self.transaction_model.submit_statuses.RETRYING)

        self.transaction_model.process_one(transaction)
        self.assertEqual(transaction.failure_count, 4)
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.FAILED)

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
        now = utc_now()
        now_iso = now.isoformat()
        # next week
        next_invoice_at = utc_datetime(2013, 8, 17)
        next_iso = next_invoice_at.isoformat()

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
        self.assertEqual(res.json['next_invoice_at'], next_iso)
        self.assertEqual(res.json['invoice_count'], 0)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['customer_guid'], self.customer.guid)
        self.assertEqual(res.json['plan_guid'], self.plan.guid)

    def test_create_subscription_with_started_at_and_timezone(self):
        amount = 5566
        # next week
        next_invoice_at = utc_datetime(2013, 8, 17)
        next_iso = next_invoice_at.isoformat()
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
        self.assertEqual(res.json['next_invoice_at'], next_iso)
        self.assertEqual(res.json['invoice_count'], 0)

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
        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )

        with freeze_time('2013-08-16 07:00:00'):
            canceled_at = utc_now()
            res = self.testapp.post(
                '/v1/subscriptions/{}/cancel'.format(subscription.guid),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )

        subscription = res.json
        self.assertEqual(subscription['canceled'], True)
        self.assertEqual(subscription['canceled_at'], canceled_at.isoformat())

    def test_canceled_subscription_will_not_yield_invoices(self):
        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
        self.assertEqual(subscription.invoice_count, 1)
        self.testapp.post(
            '/v1/subscriptions/{}/cancel'.format(subscription.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        with freeze_time('2014-01-01'):
            invoices = self.subscription_model.yield_invoices([subscription])
        self.assertFalse(invoices)
        self.assertEqual(subscription.invoice_count, 1)

    def test_cancel_a_canceled_subscription(self):
        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
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

    def test_subscription_invoice_list(self):
        # create other stuff that shouldn't be included in the result
        with db_transaction.manager:
            self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
            # other company
            self.subscription_model.create(
                customer=self.customer2,
                plan=self.plan2,
            )

        with db_transaction.manager:
            plan = self.plan_model.create(
                company=self.company,
                frequency=self.plan_model.frequencies.DAILY,
                plan_type=self.plan_model.types.DEBIT,
                amount=1000,
            )
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=plan,
            )
            # 4 days passed, there should be 1 + 4 invoices
            with freeze_time('2013-08-20'):
                self.subscription_model.yield_invoices([subscription])

        invoices = subscription.invoices
        self.assertEqual(invoices.count(), 5)
        first_invoice = invoices[-1]
        expected_scheduled_at = [
            first_invoice.scheduled_at + datetime.timedelta(days=4),
            first_invoice.scheduled_at + datetime.timedelta(days=3),
            first_invoice.scheduled_at + datetime.timedelta(days=2),
            first_invoice.scheduled_at + datetime.timedelta(days=1),
            first_invoice.scheduled_at,
        ]
        invoice_scheduled_at = [invoice.scheduled_at for invoice in invoices]
        self.assertEqual(invoice_scheduled_at, expected_scheduled_at)

        expected_guids = [invoice.guid for invoice in invoices]
        res = self.testapp.get(
            '/v1/subscriptions/{}/invoices'.format(subscription.guid),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, expected_guids)

    def test_subscription_transaction_list(self):
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
            self.subscription_model.create(
                customer=self.customer2,
                plan=self.plan2,
                funding_instrument_uri='/v1/cards/mock',
            )

        guids1 = []
        guids2 = []
        with db_transaction.manager:
            for i in range(10):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        invoice=subscription1.invoices[0],
                        transaction_type=self.transaction_model.types.DEBIT,
                        amount=10 * i,
                        funding_instrument_uri='/v1/cards/tester',
                    )
                    guids1.append(transaction.guid)
            for i in range(20):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        invoice=subscription2.invoices[0],
                        transaction_type=self.transaction_model.types.DEBIT,
                        amount=10 * i,
                        funding_instrument_uri='/v1/cards/tester',
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
        with db_transaction.manager:
            subscription = self.subscription_model.create(
                customer=self.customer,
                plan=self.plan,
            )
        self.testapp.get(
            '/v1/subscriptions',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )
        self.testapp.get(
            '/v1/subscriptions/{}/transactions'.format(subscription.guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )
        self.testapp.get(
            '/v1/subscriptions/{}/invoices'.format(subscription.guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'),
            status=403,
        )
