from __future__ import unicode_literals
import datetime

import mock
import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase
from billy.errors import BillyError


@freeze_time('2013-08-16')
class TestCustomerViews(ViewTestCase):

    def setUp(self):
        super(TestCustomerViews, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )

            self.company2 = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY2',
            )
        self.api_key = str(self.company.api_key)
        self.api_key2 = str(self.company2.api_key)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.validate_customer')
    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.create_customer')
    def test_create_customer(
        self, 
        create_customer_method, 
        validate_customer_method,
    ):
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()
        validate_customer_method.return_value = True

        res = self.testapp.post(
            '/v1/customers',
            dict(processor_uri='MOCK_CUSTOMER_URI'),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['processor_uri'], 'MOCK_CUSTOMER_URI')
        self.assertEqual(res.json['company_guid'], self.company.guid)
        self.assertEqual(res.json['deleted'], False)
        self.assertFalse(create_customer_method.called)
        validate_customer_method.assert_called_once_with('MOCK_CUSTOMER_URI')

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.validate_customer')
    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.create_customer')
    def test_create_customer_without_processor_uri(
        self, 
        create_customer_method, 
        validate_customer_method,
    ):
        create_customer_method.return_value = 'MOCK_CUSTOMER_URI'
        res = self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        customer = self.customer_model.get(res.json['guid'])
        self.assertEqual(res.json['processor_uri'], 'MOCK_CUSTOMER_URI')
        self.assertFalse(validate_customer_method.called)
        create_customer_method.assert_called_once_with(customer)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.validate_customer')
    def test_create_customer_with_bad_processor_uri(
        self, 
        validate_customer_method,
    ):
        validate_customer_method.side_effect = BillyError('Boom!')
        res = self.testapp.post(
            '/v1/customers',
            dict(processor_uri='BAD_PROCESSOR'),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )
        self.assertEqual(res.json['error_class'], 'BillyError')
        self.assertEqual(res.json['error_message'], 'Boom!')

    def test_create_customer_with_bad_api_key(self):
        self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )
        self.testapp.post(
            '/v1/customers',
            status=403,
        )

    def test_get_customer(self):
        res = self.testapp.post(
            '/v1/customers', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_customer = res.json

        guid = created_customer['guid']
        res = self.testapp.get(
            '/v1/customers/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json, created_customer)

    def test_get_customer_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/customers', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_customer = res.json

        guid = created_customer['guid']
        self.testapp.get(
            '/v1/customers/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_get_non_existing_customer(self):
        self.testapp.get(
            '/v1/customers/NON_EXIST', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=404
        )

    def test_get_customer_of_other_company(self):
        res = self.testapp.post(
            '/v1/customers', 
            extra_environ=dict(REMOTE_USER=self.api_key2), 
            status=200,
        )
        guid = res.json['guid']
        res = self.testapp.get(
            '/v1/customers/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_customer_list(self):
        # create some customers in other company to make sure they will not
        # be included in the result
        with db_transaction.manager:
            for i in range(4):
                self.customer_model.create(self.company2)

        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    customer = self.customer_model.create(self.company)
                    guids.append(customer.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_customer_list_with_processor_uri(self):
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    processor_uri = i
                    if i >= 2:
                        processor_uri = None
                    customer = self.customer_model.create(
                        self.company,
                        processor_uri=processor_uri,
                    )
                    guids.append(customer.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/customers',
            dict(processor_uri=0),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, [guids[-1]])

        res = self.testapp.get(
            '/v1/customers',
            dict(processor_uri=1),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, [guids[-2]])

    def test_customer_invoice_list(self):
        # create some invoices in other to make sure they will not be included
        # in the result
        with db_transaction.manager:
            other_customer = self.customer_model.create(self.company2)
            for i in range(4):
                self.invoice_model.create(
                    customer=other_customer,
                    amount=1000,
                )

        with db_transaction.manager:
            customer = self.customer_model.create(self.company)
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    invoice = self.invoice_model.create(
                        customer=customer,
                        amount=1000,
                    )
                    guids.append(invoice.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/customers/{}/invoices'.format(customer.guid),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_customer_subscription_list(self):
        # create some subscriptions in other to make sure they will not be included
        # in the result
        with db_transaction.manager:
            other_customer = self.customer_model.create(self.company2)
            other_plan = self.plan_model.create(
                company=self.company2,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=7788,
                frequency=self.plan_model.FREQ_DAILY,
            )
            for i in range(4):
                self.subscription_model.create(
                    customer=other_customer,
                    plan=other_plan,
                )

        with db_transaction.manager:
            customer = self.customer_model.create(self.company)
            plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=5566,
                frequency=self.plan_model.FREQ_DAILY,
            )
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    subscription = self.subscription_model.create(
                        customer=customer,
                        plan=plan,
                    )
                    guids.append(subscription.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/customers/{}/subscriptions'.format(customer.guid),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_customer_transaction_list(self):
        # create some transactions in other to make sure they will not be included
        # in the result
        with db_transaction.manager:
            other_customer = self.customer_model.create(self.company2)
            other_plan = self.plan_model.create(
                company=self.company2,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=7788,
                frequency=self.plan_model.FREQ_DAILY,
            )
            other_subscription = self.subscription_model.create(
                customer=other_customer,
                plan=other_plan,
            )
            other_invoice = self.invoice_model.create(
                customer=other_customer,
                amount=9999,
            )
            for i in range(4):
                self.transaction_model.create(
                    invoice=other_invoice,
                    transaction_type=self.transaction_model.TYPE_CHARGE,
                    amount=100,
                    funding_instrument_uri='/v1/cards/tester',
                )
            for i in range(4):
                self.transaction_model.create(
                    invoice=other_subscription.invoices[0],
                    transaction_type=self.transaction_model.TYPE_CHARGE,
                    amount=100,
                    funding_instrument_uri='/v1/cards/tester',
                )

        with db_transaction.manager:
            customer = self.customer_model.create(self.company)
            plan = self.plan_model.create(
                company=self.company,
                plan_type=self.plan_model.TYPE_CHARGE,
                amount=5566,
                frequency=self.plan_model.FREQ_DAILY,
            )
            subscription = self.subscription_model.create(
                customer=customer,
                plan=plan,
            )
            invoice = self.invoice_model.create(
                customer=customer,
                amount=7788,
            )
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        invoice=invoice,
                        transaction_type=self.transaction_model.TYPE_CHARGE,
                        amount=100,
                        funding_instrument_uri='/v1/cards/tester',
                    )
                    guids.append(transaction.guid)
            for i in range(4):
                with freeze_time('2013-08-16 02:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        invoice=subscription.invoices[0],
                        transaction_type=self.transaction_model.TYPE_CHARGE,
                        amount=100,
                        funding_instrument_uri='/v1/cards/tester',
                    )
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/customers/{}/transactions'.format(customer.guid),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_customer_list_with_bad_api_key(self):
        with db_transaction.manager:
            customer = self.customer_model.create(self.company)
        self.testapp.get(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )
        for list_name in [
            'invoices',
            'subscriptions',
            'transactions',
        ]:
            self.testapp.get(
                '/v1/customers/{}/{}'.format(customer.guid, list_name),
                extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
                status=403,
            )

    def test_delete_customer(self):
        res = self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_customer = res.json
        res = self.testapp.delete(
            '/v1/customers/{}'.format(created_customer['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        deleted_customer = res.json
        self.assertEqual(deleted_customer['deleted'], True)

    def test_delete_a_deleted_customer(self):
        res = self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_customer = res.json
        self.testapp.delete(
            '/v1/customers/{}'.format(created_customer['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.testapp.delete(
            '/v1/customers/{}'.format(created_customer['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_delete_customer_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/customers',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_customer = res.json
        self.testapp.delete(
            '/v1/customers/{}'.format(created_customer['guid']),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_delete_customer_of_other_company(self):
        with db_transaction.manager:
            other_company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
        other_api_key = str(other_company.api_key)
        res = self.testapp.post(
            '/v1/customers', 
            extra_environ=dict(REMOTE_USER=other_api_key), 
            status=200,
        )
        guid = res.json['guid']
        self.testapp.delete(
            '/v1/customers/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )
