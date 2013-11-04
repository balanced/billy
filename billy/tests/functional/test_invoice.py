from __future__ import unicode_literals
import datetime

import transaction as db_transaction
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
class TestSubscriptionViews(ViewTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        self.settings = {
            'billy.processor_factory': DummyProcessor
        }
        super(TestSubscriptionViews, self).setUp()
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
