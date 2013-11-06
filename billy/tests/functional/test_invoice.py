from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from flexmock import flexmock
from freezegun import freeze_time

from billy.tests.functional.helper import ViewTestCase


class DummyProcessor(object):

    def create_customer(self, customer):
        pass

    def prepare_customer(self, customer, payment_uri=None):
        pass

    def charge(self, transaction):
        pass

    def payout(self, transaction):
        pass

    def refund(self, transaction):
        pass


@freeze_time('2013-08-16')
class TestInvoiceViews(ViewTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        self.settings = {
            'billy.processor_factory': DummyProcessor
        }
        super(TestInvoiceViews, self).setUp()
        company_model = CompanyModel(self.testapp.session)
        customer_model = CustomerModel(self.testapp.session)
        with db_transaction.manager:
            self.company_guid = company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            self.customer_guid = customer_model.create(
                company_guid=self.company_guid
            )
        company = company_model.get(self.company_guid)
        self.api_key = str(company.api_key)

    def test_create_invoice(self):
        from billy.models.invoice import InvoiceModel

        customer_guid = self.customer_guid
        amount = 5566
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=customer_guid,
                amount=amount,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['customer_guid'], customer_guid)
        self.assertEqual(res.json['payment_uri'], None)

        invoice_model = InvoiceModel(self.testapp.session)
        invoice = invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 0)

    def test_create_invoice_with_payment_uri(self):
        from billy.models.invoice import InvoiceModel 
        from billy.models.transaction import TransactionModel

        customer_guid = self.customer_guid
        amount = 5566
        payment_uri = 'MOCK_CARD_URI'
        now = datetime.datetime.utcnow()
        now_iso = now.isoformat()

        def mock_charge(transaction):
            self.assertEqual(transaction.invoice.customer_guid, 
                             customer_guid)
            return 'MOCK_PROCESSOR_TRANSACTION_ID'

        mock_processor = flexmock(DummyProcessor)
        (
            mock_processor
            .should_receive('create_customer')
            .once()
        )

        (
            mock_processor
            .should_receive('charge')
            .replace_with(mock_charge)
            .once()
        )

        res = self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=customer_guid,
                amount=amount,
                payment_uri=payment_uri,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        self.failUnless('guid' in res.json)
        self.assertEqual(res.json['created_at'], now_iso)
        self.assertEqual(res.json['updated_at'], now_iso)
        self.assertEqual(res.json['amount'], amount)
        self.assertEqual(res.json['customer_guid'], customer_guid)
        self.assertEqual(res.json['payment_uri'], payment_uri)

        invoice_model = InvoiceModel(self.testapp.session)
        invoice = invoice_model.get(res.json['guid'])
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.external_id, 
                         'MOCK_PROCESSOR_TRANSACTION_ID')
        self.assertEqual(transaction.status, TransactionModel.STATUS_DONE)

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
            customer_guid=self.customer_guid,
            payment_uri='MOCK_CARD_URI',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            amount=0,
        ))
        assert_bad_parameters(dict(
            amount=123,
            payment_uri='MOCK_CARD_URI',
        ))
        assert_bad_parameters(dict(
            customer_guid=self.customer_guid,
            amount=-123,
        ))

    def test_create_invoice_to_other_company_customer(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel

        company_model = CompanyModel(self.testapp.session)
        customer_model = CustomerModel(self.testapp.session)
        with db_transaction.manager:
            other_company_guid = company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_customer_guid = customer_model.create(
                company_guid=other_company_guid
            )

        self.testapp.post(
            '/v1/invoices', 
            dict(
                customer_guid=other_customer_guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_create_invoice_with_bad_api(self):
        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=self.customer_guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )

    def test_create_invoice_to_a_deleted_customer(self):
        from billy.models.customer import CustomerModel

        customer_model = CustomerModel(self.testapp.session)

        with db_transaction.manager:
            customer_guid = customer_model.create(
                company_guid=self.company_guid
            )
            customer_model.delete(customer_guid)

        self.testapp.post(
            '/v1/invoices',
            dict(
                customer_guid=customer_guid,
                amount=123,
            ),
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=400,
        )

    def test_get_invoice(self):
        res = self.testapp.post(
            '/v1/invoices', 
            dict(
                customer_guid=self.customer_guid,
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
                customer_guid=self.customer_guid,
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
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel

        company_model = CompanyModel(self.testapp.session)
        customer_model = CustomerModel(self.testapp.session)
        with db_transaction.manager:
            other_company_guid = company_model.create(
                processor_key='MOCK_PROCESSOR_KEY',
            )
            other_customer_guid = customer_model.create(
                company_guid=other_company_guid
            )
        other_company = company_model.get(other_company_guid)
        other_api_key = str(other_company.api_key)

        res = self.testapp.post(
            '/v1/invoices', 
            dict(
                customer_guid=other_customer_guid,
                amount=1234,
            ),
            extra_environ=dict(REMOTE_USER=other_api_key), 
            status=200,
        )
        other_guid = res.json['guid']

        self.testapp.get(
            '/v1/invoices/{}'.format(other_guid), 
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=403,
        )

    def test_invoice_list(self):
        from billy.models.invoice import InvoiceModel
        invoice_model = InvoiceModel(self.testapp.session)
        with db_transaction.manager:
            guids = []
            for i in range(4):
                with freeze_time('2013-08-16 00:00:{:02}'.format(i + 1)):
                    guid = invoice_model.create(
                        customer_guid=self.customer_guid,
                        amount=(i + 1) * 1000,
                    )
                    guids.append(guid)
        guids = list(reversed(guids))

        res = self.testapp.get(
            '/v1/invoices',
            extra_environ=dict(REMOTE_USER=self.api_key), 
            status=200,
        )
        items = res.json['items']
        result_guids = [item['guid'] for item in items]
        self.assertEqual(result_guids, guids)

    def test_invoice_list_with_bad_api_key(self):
        self.testapp.get(
            '/v1/invoices',
            extra_environ=dict(REMOTE_USER=b'BAD_API_KEY'), 
            status=403,
        )
