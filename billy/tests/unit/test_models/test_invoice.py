from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from freezegun import freeze_time

from billy.tests.unit.helper import ModelTestCase


@freeze_time('2013-08-16')
class TestInvoiceModel(ModelTestCase):

    def setUp(self):
        from billy.models.company import CompanyModel
        from billy.models.customer import CustomerModel
        super(TestInvoiceModel, self).setUp()
        # build the basic scenario for plan model
        self.company_model = CompanyModel(self.session)
        self.customer_model = CustomerModel(self.session)
        with db_transaction.manager:
            self.company_guid = self.company_model.create('my_secret_key')
            self.customer_guid = self.customer_model.create(
                company_guid=self.company_guid,
            )

    def make_one(self, *args, **kwargs):
        from billy.models.invoice import InvoiceModel
        return InvoiceModel(*args, **kwargs)

    def test_get_invoice(self):
        model = self.make_one(self.session)

        invoice = model.get('IV_NON_EXIST')
        self.assertEqual(invoice, None)

        with self.assertRaises(KeyError):
            model.get('IV_NON_EXIST', raise_error=True)

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                amount=1000,
            )

        invoice = model.get(guid)
        self.assertEqual(invoice.guid, guid)

    def test_create(self):
        model = self.make_one(self.session)
        amount = 556677
        title = 'Foobar invoice'
        payment_uri = '/v1/cards/1234'

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
                payment_uri=payment_uri,
            )

        now = datetime.datetime.utcnow()

        invoice = model.get(guid)
        self.assertEqual(invoice.guid, guid)
        self.assert_(invoice.guid.startswith('IV'))
        self.assertEqual(invoice.customer_guid, self.customer_guid)
        self.assertEqual(invoice.title, title)
        self.assertEqual(invoice.amount, amount)
        self.assertEqual(invoice.created_at, now)
        self.assertEqual(invoice.updated_at, now)

    def test_create_with_wrong_amount(self):
        model = self.make_one(self.session)
        with self.assertRaises(ValueError):
            model.create(
                customer_guid=self.customer_guid,
                amount=0,
            )
