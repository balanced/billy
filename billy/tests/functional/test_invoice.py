from __future__ import unicode_literals
import datetime

import mock
import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


@freeze_time('2013-08-16')
class TestInvoiceViews(ViewTestCase):

    def setUp(self):
        super(TestInvoiceViews, self).setUp()
        with db_transaction.manager:
            self.company = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            self.customer = self.customer_model.create(company=self.company)

            self.company2 = self.company_model.create(
                processor_key='MOCK_PROCESSOR_KEY2',
            )
            self.customer2 = self.customer_model.create(company=self.company2)
        self.api_key = str(self.company.api_key)
        self.api_key2 = str(self.company2.api_key)

    def _encode_item_params(self, items):
        """Encode items (a list of dict) into key/value parameters for URL

        """
        item_params = {}
        for i, item in enumerate(items):
            item_params['item_name{}'.format(i)] = item['name']
            item_params['item_total{}'.format(i)] = item['total']
            if 'unit' in item:
                item_params['item_unit{}'.format(i)] = item['unit'] 
            if 'quantity' in item:
                item_params['item_quantity{}'.format(i)] = item['quantity'] 
            if 'amount' in item:
                item_params['item_amount{}'.format(i)] = item['amount'] 
            if 'type' in item:
                item_params['item_type{}'.format(i)] = item['type'] 
        return item_params

    def _encode_adjustment_params(self, items):
        """Encode adjustment (a list of dict) into key/value parameters for URL

        """
        adjustment_params = {}
        for i, item in enumerate(items):
            adjustment_params['adjustment_total{}'.format(i)] = item['total']
            if 'reason' in item:
                adjustment_params['adjustment_reason{}'.format(i)] = item['reason'] 
        return adjustment_params 

    def test_create_invoice(self):
        amount = 5566
        title = 'foobar invoice'
        external_id = 'external ID'
        appears_on_statement_as = 'hello baby'
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
                title=title,
                external_id=external_id,
                appears_on_statement_as=appears_on_statement_as,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['title'], title)
        self.assertEqual(res.json['external_id'], external_id)
        self.assertEqual(res.json['appears_on_statement_as'], 
                         appears_on_statement_as)
        self.assertEqual(res.json['customer_guid'], self.customer.guid)
        self.assertEqual(res.json['funding_instrument_uri'], None)

        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 0)

    def test_create_invoice_with_zero_amount(self):
        amount = 0

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['amount'], amount)

    def test_create_invoice_with_external_id(self):
        amount = 5566
        external_id = 'external ID'

        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
                external_id=external_id,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        # ensure duplicate (customer, external_d) cannot be created
        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
                external_id=external_id,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=409,
        )

    def test_create_invoice_with_items(self):
        items = [
            dict(name='foo', total=1234),
            dict(name='bar', total=5678, unit='unit'),
            dict(name='special service', total=9999, unit='hours'),
        ]
        item_params = self._encode_item_params(items)

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
                item_namexxx='SHOULD NOT BE PARSED',
                **item_params
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['funding_instrument_uri'], None)

        item_result = res.json['items']
        for item in item_result:
            for key, value in list(item.iteritems()):
                if value is None:
                    del item[key]
        self.assertEqual(item_result, items)

    def test_create_invoice_with_adjustments(self):
        adjustments = [
            dict(total=-100, reason='A Lannister always pays his debts!'),
            dict(total=20, reason='you owe me'),
            dict(total=3, reason='foobar'),
        ]
        adjustment_params = self._encode_adjustment_params(adjustments)

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=200,
                adjustment_amountxxx='SHOULD NOT BE PARSED',
                **adjustment_params
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['total_adjustment_amount'], -100 + 20 + 3)

        adjustment_result = res.json['adjustments']
        for adjustment in adjustment_result:
            for key, value in list(adjustment.iteritems()):
                if value is None:
                    del adjustment[key]
        self.assertEqual(adjustment_result, adjustments)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_create_invoice_with_funding_instrument_uri(self, charge_method):
        amount = 5566
        funding_instrument_uri = 'MOCK_CARD_URI'
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()

        charge_method.return_value = 'MOCK_DEBIT_URI'

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
                funding_instrument_uri=funding_instrument_uri,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['title'], None)
        self.assertEqual(res.json['customer_guid'], self.customer.guid)
        self.assertEqual(res.json['funding_instrument_uri'], 
                         funding_instrument_uri)

        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.processor_uri, 
                         'MOCK_DEBIT_URI')
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        charge_method.assert_called_once_with(transaction)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_create_invoice_with_funding_instrument_uri_with_zero_amount(self, charge_method):
        amount = 0
        funding_instrument_uri = 'MOCK_CARD_URI'
        charge_method.return_value = 'MOCK_DEBIT_URI'

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
                funding_instrument_uri=funding_instrument_uri,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)

        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 0)
        self.assertFalse(charge_method.called)

    def test_create_invoice_with_bad_parameters(self):
        def assert_bad_parameters(params):
            self.testapp.post(
                '/v1/invoices',
                params, 
                extra_environ=dict(REMOTE_USER=self.api_key), 
                status=400,
            )
        assert_bad_parameters({})
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            funding_instrument_uri='MOCK_CARD_URI',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
        ))
        assert_bad_parameters(dict(
            amount=123,
            funding_instrument_uri='MOCK_CARD_URI',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            amount=-1,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            amount=999,
            title='t' * 129,
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            amount=999,
            appears_on_statement_as='illegal\tstatement', 
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer.guid,
            amount=999,
            appears_on_statement_as='illegal\0statement', 
        ))

    def test_create_invoice_to_other_company_customer(self):
        self.testapp.post(
            '/v1/invoices', 
            dict(
                customer_guid=self.customer2.guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_create_invoice_with_bad_api(self):
        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_create_invoice_to_a_deleted_customer(self):
        with db_transaction.manager:
            self.customer_model.delete(self.customer)

        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=123,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_get_invoice(self):
        res = self.testapp.post(
            '/v1/invoices', 
            dict(
                customer_guid=self.customer.guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_invoice = res.json
        guid = created_invoice['guid']

        res = self.testapp.get(
            '/v1/invoices/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json, created_invoice)

    def test_get_non_existing_invoice(self):
        self.testapp.get(
            '/v1/invoices/NON_EXIST', 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=404
        )

    def test_get_invoice_with_bad_api_key(self):
        res = self.testapp.post(
            '/v1/invoices', 
            dict(
                customer_guid=self.customer.guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_invoice = res.json
        guid = created_invoice['guid']

        self.testapp.get(
            '/v1/invoices/{}'.format(guid), 
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403
        )

    def test_get_invoice_of_other_company(self):
        res = self.testapp.post(
            '/v1/invoices', 
            dict(
                customer_guid=self.customer2.guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key2), 
            status=200,
        )
        other_guid = res.json['guid']

        self.testapp.get(
            '/v1/invoices/{}'.format(other_guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_invoice_list(self):
        # make some invoice for other company, to make sure they won't be 
        # included in the result
        with db_transaction.manager:
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    self.invoice_model.create(
                        customer=self.customer2,
                        amount=9999,
                    )

        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    invoice = self.invoice_model.create(
                        customer=self.customer,
                        amount=(i + 1) * 1000,
                    )
                    guids.append(invoice.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/invoices',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_invoice_transaction_list(self):
        # create transaction in other company to make sure they will not be
        # included in the result
        with db_transaction.manager:
            other_invoice = self.invoice_model.create(
                customer=self.customer2,
                amount=9999,
            )
        with db_transaction.manager:
            for i in range(4):
                self.transaction_model.create(
                    invoice=other_invoice,
                    transaction_cls=self.transaction_model.CLS_INVOICE,
                    transaction_type=self.transaction_model.TYPE_CHARGE,
                    amount=100,
                    funding_instrument_uri='/v1/cards/tester',
                    scheduled_at=datetime.datetime.utcnow(),
                )

        with db_transaction.manager:
            invoice = self.invoice_model.create(
                customer=self.customer,
                amount=9999,
            )
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    transaction = self.transaction_model.create(
                        invoice=invoice,
                        transaction_cls=self.transaction_model.CLS_INVOICE,
                        transaction_type=self.transaction_model.TYPE_CHARGE,
                        amount=100,
                        funding_instrument_uri='/v1/cards/tester',
                        scheduled_at=datetime.datetime.utcnow(),
                    )
                    guids.append(transaction.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/invoices/{}/transactions'.format(invoice.guid),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_invoice_list_with_external_id(self):
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    external_id = i
                    if i >= 2:
                        external_id = None
                    # external_id will be 0, 1, None, None
                    invoice = self.invoice_model.create(
                        customer=self.customer,
                        amount=(i + 1) * 1000,
                        external_id=external_id,
                    )
                    guids.append(invoice.guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/invoices',
            dict(external_id=0),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, [guids[-1]])

        res = self.testapp.get(
            '/v1/invoices',
            dict(external_id=1),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, [guids[-2]])

    def test_invoice_list_with_bad_api_key(self):
        with db_transaction.manager:
            invoice = self.invoice_model.create(
                customer=self.customer,
                amount=9999,
            )
        self.testapp.get(
            '/v1/invoices',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )
        self.testapp.get(
            '/v1/invoices/{}/transactions'.format(invoice.guid),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_update_invoice_title(self):
        res = self.testapp.post(
            '/v1/invoices', 
            dict(
                customer_guid=self.customer.guid,
                amount=1234,
                title='old title',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_invoice = res.json
        guid = created_invoice['guid']

        res = self.testapp.put(
            '/v1/invoices/{}'.format(guid),
            dict(
                title='new title',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json['title'], 'new title')

        res = self.testapp.get(
            '/v1/invoices/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json['title'], 'new title')

    def test_update_invoice_items(self):
        old_items = [
            dict(name='foo', total=1234, quantity=10),
            dict(name='bar', total=5678, unit='unit'),
            dict(name='special service', total=9999, unit='hours'),
        ]
        item_params = self._encode_item_params(old_items)
        res = self.testapp.post(
            '/v1/invoices', 
            dict(
                customer_guid=self.customer.guid,
                amount=1234,
                **item_params
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        created_invoice = res.json
        guid = created_invoice['guid']

        new_items = [
            dict(name='new foo', total=55),
            dict(name='new bar', total=66, quantity=123, unit='unit'),
        ]
        item_params = self._encode_item_params(new_items)
        res = self.testapp.put(
            '/v1/invoices/{}'.format(guid),
            item_params,
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        item_result = res.json['items']
        for item in item_result:
            for key, value in list(item.iteritems()):
                if value is None:
                    del item[key]
        self.assertEqual(item_result, new_items)

        res = self.testapp.get(
            '/v1/invoices/{}'.format(guid),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        item_result = res.json['items']
        for item in item_result:
            for key, value in list(item.iteritems()):
                if value is None:
                    del item[key]
        self.assertEqual(item_result, new_items)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_update_invoice_funding_instrument_uri(self, charge_method):
        amount = 5566
        funding_instrument_uri = 'MOCK_CARD_URI'
        charge_method.return_value = 'MOCK_DEBIT_URI'

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['funding_instrument_uri'], None)
        guid = res.json['guid']

        res = self.testapp.put(
            '/v1/invoices/{}'.format(guid),
            dict(
                funding_instrument_uri=funding_instrument_uri,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json['funding_instrument_uri'], funding_instrument_uri)

        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.processor_uri, 
                         'MOCK_DEBIT_URI')
        self.assertEqual(transaction.status, self.transaction_model.STATUS_DONE)
        charge_method.assert_called_once_with(transaction)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.charge')
    def test_update_invoice_funding_instrument_uri_with_zero_amount(self, charge_method):
        amount = 0
        funding_instrument_uri = 'MOCK_CARD_URI'
        charge_method.return_value = 'MOCK_DEBIT_URI'

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['funding_instrument_uri'], None)
        self.assertFalse(charge_method.called)
        guid = res.json['guid']

        res = self.testapp.put(
            '/v1/invoices/{}'.format(guid),
            dict(
                funding_instrument_uri=funding_instrument_uri,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.assertEqual(res.json['funding_instrument_uri'], funding_instrument_uri)

        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 0)
        self.assertFalse(charge_method.called)
