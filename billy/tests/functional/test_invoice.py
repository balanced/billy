from __future__ import unicode_literals

import mock
import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase
from billy.errors import BillyError
from billy.utils.generic import utc_now


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
            item_params['item_amount{}'.format(i)] = item['amount']
            if 'unit' in item:
                item_params['item_unit{}'.format(i)] = item['unit']
            if 'quantity' in item:
                item_params['item_quantity{}'.format(i)] = item['quantity']
            if 'volume' in item:
                item_params['item_volume{}'.format(i)] = item['volume']
            if 'type' in item:
                item_params['item_type{}'.format(i)] = item['type']
        return item_params

    def _encode_adjustment_params(self, items):
        """Encode adjustment (a list of dict) into key/value parameters for URL

        """
        adjustment_params = {}
        for i, item in enumerate(items):
            adjustment_params['adjustment_amount{}'.format(i)] = item['amount']
            if 'reason' in item:
                adjustment_params['adjustment_reason{}'.format(i)] = item['reason']
        return adjustment_params

    def test_create_invoice(self):
        amount = 5566
        title = 'foobar invoice'
        external_id = 'external ID'
        appears_on_statement_as = 'hello baby'
        now = utc_now()
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

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.validate_funding_instrument')
    def test_create_invoice_with_invalid_funding_instrument(
        self,
        validate_funding_instrument_method,
    ):
        validate_funding_instrument_method.side_effect = BillyError('Invalid card!')
        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=999,
                funding_instrument_uri='BAD_INSTRUMENT_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )
        validate_funding_instrument_method.assert_called_once_with('BAD_INSTRUMENT_URI')

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
            dict(name='foo', amount=1234),
            dict(name='bar', amount=5678, unit='unit'),
            dict(name='special service', amount=9999, unit='hours'),
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
            dict(amount=-100, reason='A Lannister always pays his debts!'),
            dict(amount=20, reason='you owe me'),
            dict(amount=3, reason='foobar'),
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
        self.assertEqual(res.json['effective_amount'],
                         200 + res.json['total_adjustment_amount'])

        adjustment_result = res.json['adjustments']
        for adjustment in adjustment_result:
            for key, value in list(adjustment.iteritems()):
                if value is None:
                    del adjustment[key]
        self.assertEqual(adjustment_result, adjustments)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_create_invoice_with_funding_instrument_uri(self, debit_method):
        amount = 5566
        funding_instrument_uri = 'MOCK_CARD_URI'
        now = utc_now()
        now_iso = now.isoformat()
        adjustments = [
            dict(amount=-100, reason='A Lannister always pays his debts!'),
        ]
        adjustment_params = self._encode_adjustment_params(adjustments)

        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=amount,
                funding_instrument_uri=funding_instrument_uri,
                **adjustment_params
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['effective_amount'], amount - 100)
        self.assertEqual(res.json['title'], None)
        self.assertEqual(res.json['customer_guid'], self.customer.guid)
        self.assertEqual(res.json['funding_instrument_uri'],
                         funding_instrument_uri)

        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.amount, invoice.effective_amount)
        self.assertEqual(transaction.processor_uri,
                         'MOCK_DEBIT_URI')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.DONE)
        self.assertEqual(transaction.status,
                         self.transaction_model.statuses.SUCCEEDED)
        debit_method.assert_called_once_with(transaction)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_create_invoice_with_funding_instrument_uri_with_zero_amount(self, debit_method):
        amount = 0
        funding_instrument_uri = 'MOCK_CARD_URI'
        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )

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
        self.assertFalse(debit_method.called)

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
                    amount=other_invoice.effective_amount,
                    transaction_type=other_invoice.transaction_type,
                    funding_instrument_uri=other_invoice.funding_instrument_uri,
                    appears_on_statement_as=other_invoice.appears_on_statement_as,
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
                        amount=invoice.effective_amount,
                        transaction_type=invoice.transaction_type,
                        funding_instrument_uri=invoice.funding_instrument_uri,
                        appears_on_statement_as=invoice.appears_on_statement_as,
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

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_update_invoice_funding_instrument_uri(self, debit_method):
        amount = 5566
        funding_instrument_uri = 'MOCK_CARD_URI'
        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )

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
        self.assertEqual(transaction.submit_status, self.transaction_model.submit_statuses.DONE)
        debit_method.assert_called_once_with(transaction)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_update_invoice_funding_instrument_uri_for_settled_invoice(
        self,
        debit_method,
    ):
        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.testapp.put(
            '/v1/invoices/{}'.format(res.json['guid']),
            dict(
                funding_instrument_uri='MOCK_CARD_URI2',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_update_invoice_funding_instrument_uri_with_mutiple_failures(
        self,
        debit_method
    ):
        # make it fail immediately
        self.model_factory.settings['billy.transaction.maximum_retry'] = 0
        debit_method.side_effect = RuntimeError('Ouch!')

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
                funding_instrument_uri='instrument1',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(invoice.status,
                         self.invoice_model.statuses.FAILED)
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument1')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.FAILED)
        self.assertEqual(transaction.status, None)

        def update_instrument_uri(when, uri):
            with freeze_time(when):
                self.testapp.put(
                    '/v1/invoices/{}'.format(invoice.guid),
                    dict(
                        funding_instrument_uri=uri,
                    ),
                    extra_environ=dict(REMOTE_USER=self.api_key),
                    status=200,
                )

        update_instrument_uri('2013-08-17', 'instrument2')
        self.assertEqual(invoice.status,
                         self.invoice_model.statuses.FAILED)
        self.assertEqual(len(invoice.transactions), 2)
        transaction = invoice.transactions[-1]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument2')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.FAILED)
        self.assertEqual(transaction.status, None)

        self.model_factory.settings['billy.transaction.maximum_retry'] = 1
        update_instrument_uri('2013-08-18', 'instrument3')
        self.assertEqual(invoice.status,
                         self.invoice_model.statuses.PROCESSING)
        self.assertEqual(len(invoice.transactions), 3)
        transaction = invoice.transactions[-1]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument3')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.RETRYING)
        self.assertEqual(transaction.status, None)

        update_instrument_uri('2013-08-19', 'instrument4')
        self.assertEqual(invoice.status,
                         self.invoice_model.statuses.PROCESSING)
        self.assertEqual(len(invoice.transactions), 4)
        # make sure previous retrying transaction was canceled
        transaction = invoice.transactions[-2]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument3')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.CANCELED)
        transaction = invoice.transactions[-1]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument4')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.RETRYING)
        self.assertEqual(transaction.status, None)

        debit_method.side_effect = None
        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )
        update_instrument_uri('2013-08-20', 'instrument5')
        self.assertEqual(invoice.status,
                         self.invoice_model.statuses.SETTLED)
        self.assertEqual(len(invoice.transactions), 5)
        # make sure previous retrying transaction was canceled
        transaction = invoice.transactions[-2]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument4')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.CANCELED)
        transaction = invoice.transactions[-1]
        self.assertEqual(transaction.funding_instrument_uri, 'instrument5')
        self.assertEqual(transaction.processor_uri, 'MOCK_DEBIT_URI')
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.DONE)
        self.assertEqual(transaction.status,
                         self.transaction_model.statuses.SUCCEEDED)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_update_invoice_funding_instrument_uri_with_zero_amount(self, debit_method):
        amount = 0
        funding_instrument_uri = 'MOCK_CARD_URI'
        debit_method.return_value = dict(
            processor_uri='MOCK_DEBIT_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )

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
        self.assertFalse(debit_method.called)
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
        self.assertFalse(debit_method.called)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.refund')
    def test_invoice_refund(self, refund_method):
        refund_method.return_value = dict(
            processor_uri='MOCK_REFUND_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        with freeze_time('2013-08-17'):
            self.testapp.post(
                '/v1/invoices/{}/refund'.format(res.json['guid']),
                dict(amount=1234),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )
        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(invoice.status, self.invoice_model.statuses.SETTLED)
        self.assertEqual(len(invoice.transactions), 2)
        transaction = invoice.transactions[-1]
        refund_method.assert_called_once_with(transaction)
        self.assertEqual(transaction.funding_instrument_uri, None)
        self.assertEqual(transaction.amount, 1234)
        self.assertEqual(transaction.status,
                         self.transaction_model.statuses.SUCCEEDED)
        self.assertEqual(transaction.submit_status, self.transaction_model.submit_statuses.DONE)
        self.assertEqual(transaction.transaction_type,
                         self.transaction_model.types.REFUND)
        self.assertEqual(transaction.appears_on_statement_as, None)
        self.assertEqual(transaction.processor_uri, 'MOCK_REFUND_URI')

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.refund')
    def test_invoice_mutiple_refund(self, refund_method):
        refund_method.return_value = dict(
            processor_uri='MOCK_REFUND_URI',
            status=self.transaction_model.statuses.SUCCEEDED,
        )
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )

        invoice = self.invoice_model.get(res.json['guid'])

        def refund(when, amount):
            with freeze_time(when):
                self.testapp.post(
                    '/v1/invoices/{}/refund'.format(res.json['guid']),
                    dict(amount=amount),
                    extra_environ=dict(REMOTE_USER=self.api_key),
                    status=200,
                )

            self.assertEqual(invoice.status, self.invoice_model.statuses.SETTLED)
            transaction = invoice.transactions[-1]
            refund_method.assert_called_with(transaction)
            self.assertEqual(transaction.funding_instrument_uri, None)
            self.assertEqual(transaction.amount, amount)
            self.assertEqual(transaction.status,
                             self.transaction_model.statuses.SUCCEEDED)
            self.assertEqual(transaction.submit_status,
                             self.transaction_model.submit_statuses.DONE)
            self.assertEqual(transaction.transaction_type,
                             self.transaction_model.types.REFUND)
            self.assertEqual(transaction.appears_on_statement_as, None)
            self.assertEqual(transaction.processor_uri, 'MOCK_REFUND_URI')

        refund('2013-08-17', 1000)
        refund('2013-08-18', 2000)
        refund('2013-08-19', 2000)

        # exceed the invoice amount
        self.testapp.post(
            '/v1/invoices/{}/refund'.format(res.json['guid']),
            dict(amount=9999),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    def test_invoice_cancel(self):
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        with freeze_time('2013-08-17'):
            self.testapp.post(
                '/v1/invoices/{}/cancel'.format(res.json['guid']),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )
        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(invoice.status, self.invoice_model.statuses.CANCELED)
        self.assertEqual(len(invoice.transactions), 0)

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_invoice_cancel_while_processing(self, debit_method):
        debit_method.side_effect = RuntimeError('Shit!')
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
                funding_instrument_uri='MOCK_CARD_URI',
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        with freeze_time('2013-08-17'):
            self.testapp.post(
                '/v1/invoices/{}/cancel'.format(res.json['guid']),
                extra_environ=dict(REMOTE_USER=self.api_key),
                status=200,
            )
        invoice = self.invoice_model.get(res.json['guid'])
        self.assertEqual(invoice.status, self.invoice_model.statuses.CANCELED)
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.submit_status,
                         self.transaction_model.submit_statuses.CANCELED)

    def test_invoice_cancel_already_canceled_invoice(self):
        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer.guid,
                amount=5566,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.testapp.post(
            '/v1/invoices/{}/cancel'.format(res.json['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=200,
        )
        self.testapp.post(
            '/v1/invoices/{}/cancel'.format(res.json['guid']),
            extra_environ=dict(REMOTE_USER=self.api_key),
            status=400,
        )

    @mock.patch('billy.tests.fixtures.processor.DummyProcessor.debit')
    def test_invoice_create_status(self, debit_method):
        amount = 123
        funding_instrument_uri = 'MOCK_CARD_URI'

        def assert_status(tx_status, expected_status):
            debit_method.return_value = dict(
                processor_uri='MOCK_DEBIT_URI',
                status=tx_status,
            )

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
            self.assertEqual(invoice.status, expected_status)

        ts = self.transaction_model.statuses
        ivs = self.invoice_model.statuses

        assert_status(ts.PENDING, ivs.PROCESSING)
        assert_status(ts.SUCCEEDED, ivs.SETTLED)
        assert_status(ts.FAILED, ivs.FAILED)
