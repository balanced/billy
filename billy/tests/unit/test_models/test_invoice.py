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

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
            )

        now = datetime.datetime.utcnow()

        invoice = model.get(guid)
        self.assertEqual(invoice.guid, guid)
        self.assert_(invoice.guid.startswith('IV'))
        self.assertEqual(invoice.customer_guid, self.customer_guid)
        self.assertEqual(invoice.title, title)
        self.assertEqual(invoice.status, model.STATUS_INIT)
        self.assertEqual(invoice.amount, amount)
        self.assertEqual(invoice.payment_uri, None)
        self.assertEqual(invoice.created_at, now)
        self.assertEqual(invoice.updated_at, now)
        self.assertEqual(len(invoice.transactions), 0)
        self.assertEqual(len(invoice.items), 0)

    def test_create_with_items(self):
        model = self.make_one(self.session)
        items = [
            dict(type='debit', name='foo', total=1234),
            dict(name='bar', total=5678, unit='unit'),
            dict(name='special service', total=9999, quantity=10, unit='hours'),
        ]

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                amount=556677,
                items=items,
            )

        invoice = model.get(guid)
        item_result = []
        for item in invoice.items:
            item_dict = dict(
                type=item.type,
                name=item.name,
                quantity=item.quantity,
                total=item.total,
                amount=item.amount,
                unit=item.unit,
            )
            for key, value in list(item_dict.iteritems()):
                if value is None:
                    del item_dict[key]
            item_result.append(item_dict)
        self.assertEqual(item_result, items)

    def test_create_with_adjustments(self):
        model = self.make_one(self.session)
        adjustments = [
            dict(total=50, reason='we own you, man!'),
            dict(total=-100, reason='lannister always pay debts!'),
            dict(total=-123),
        ]

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                amount=200,
                adjustments=adjustments,
            )

        invoice = model.get(guid)

        adjustment_result = []
        for adjustment in invoice.adjustments:
            adjustment_dict = dict(
                total=adjustment.total,
            )
            if adjustment.reason is not None:
                adjustment_dict['reason'] = adjustment.reason
            adjustment_result.append(adjustment_dict)
        self.assertEqual(adjustment_result, adjustments)
        self.assertEqual(invoice.effective_amount, 200 + 50 - 100 - 123)

    def test_create_with_payment_uri(self):
        from billy.models.transaction import TransactionModel
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
        self.assertEqual(invoice.status, model.STATUS_PROCESSING)
        self.assertEqual(invoice.title, title)
        self.assertEqual(invoice.amount, amount)
        self.assertEqual(invoice.payment_uri, payment_uri)
        self.assertEqual(invoice.created_at, now)
        self.assertEqual(invoice.updated_at, now)

        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.transaction_type, 
                         TransactionModel.TYPE_CHARGE)
        self.assertEqual(transaction.transaction_cls, 
                         TransactionModel.CLS_INVOICE)
        self.assertEqual(transaction.status, TransactionModel.STATUS_INIT)
        self.assertEqual(transaction.invoice_guid, invoice.guid)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, payment_uri)

    def test_create_with_payment_uri_with_adjustments(self):
        model = self.make_one(self.session)
        amount = 200 
        payment_uri = '/v1/cards/1234'

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                amount=amount,
                payment_uri=payment_uri,
                adjustments=[
                    dict(total=-100),
                    dict(total=20),
                    dict(total=3),
                ]
            )

        invoice = model.get(guid)
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.amount, invoice.effective_amount)

    def test_create_with_wrong_amount(self):
        model = self.make_one(self.session)
        with self.assertRaises(ValueError):
            model.create(
                customer_guid=self.customer_guid,
                amount=0,
            )

    def test_update_payment_uri(self):
        from billy.models.transaction import TransactionModel

        model = self.make_one(self.session)
        amount = 556677
        title = 'Foobar invoice'
        payment_uri = '/v1/cards/1234'

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
            )

        invoice = model.get(guid)
        self.assertEqual(len(invoice.transactions), 0)

        with freeze_time('2013-08-17'):
            with db_transaction.manager:
                model.update_payment_uri(guid, payment_uri)
            update_now = datetime.datetime.utcnow()

        invoice = model.get(guid)
        self.assertEqual(invoice.status, model.STATUS_PROCESSING)
        self.assertEqual(invoice.updated_at, update_now)
        self.assertEqual(len(invoice.transactions), 1)

        transaction = invoice.transactions[0]
        self.assertEqual(transaction.status, TransactionModel.STATUS_INIT)
        self.assertEqual(transaction.invoice_guid, guid)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, payment_uri)
        self.assertEqual(transaction.scheduled_at, update_now)

    def test_update_payment_uri_with_adjustments(self):
        model = self.make_one(self.session)
        amount = 200
        title = 'Foobar invoice'
        payment_uri = '/v1/cards/1234'

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
                adjustments=[
                    dict(total=-100),
                    dict(total=20),
                    dict(total=3),
                ]
            )

        invoice = model.get(guid)
        self.assertEqual(len(invoice.transactions), 0)

        with freeze_time('2013-08-17'):
            with db_transaction.manager:
                model.update_payment_uri(guid, payment_uri)

        invoice = model.get(guid)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.amount, invoice.effective_amount)

    def _get_transactions_in_order(self, guid):
        from billy.models import tables
        transactions = (
            self.session
            .query(tables.InvoiceTransaction)
            .filter_by(invoice_guid=guid)
            .order_by(tables.InvoiceTransaction.scheduled_at)
            .all()
        )
        return transactions

    def test_update_payment_uri_while_processing(self):
        from billy.models.transaction import TransactionModel

        model = self.make_one(self.session)
        amount = 556677
        title = 'Foobar invoice'
        payment_uri = '/v1/cards/1234'
        new_payment_uri = '/v1/cards/5678'
        create_now = datetime.datetime.utcnow()

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
                payment_uri=payment_uri,
            )
            with freeze_time('2013-08-17'):
                model.update_payment_uri(guid, new_payment_uri)
                update_now = datetime.datetime.utcnow()

        invoice = model.get(guid)
        self.assertEqual(invoice.status, model.STATUS_PROCESSING)
        self.assertEqual(invoice.updated_at, update_now)
        self.assertEqual(len(invoice.transactions), 2)

        transactions = self._get_transactions_in_order(guid)
        transaction = transactions[0]
        self.assertEqual(transaction.status, TransactionModel.STATUS_CANCELED)
        self.assertEqual(transaction.invoice_guid, guid)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, payment_uri)
        self.assertEqual(transaction.scheduled_at, create_now)

        transaction = transactions[1]
        self.assertEqual(transaction.status, TransactionModel.STATUS_INIT)
        self.assertEqual(transaction.invoice_guid, guid)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, new_payment_uri)
        self.assertEqual(transaction.scheduled_at, update_now)

    def test_update_payment_uri_while_processing_with_adjustments(self):
        from billy.models.transaction import TransactionModel

        model = self.make_one(self.session)
        amount = 200
        payment_uri = '/v1/cards/1234'
        new_payment_uri = '/v1/cards/5678'

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                amount=amount,
                payment_uri=payment_uri,
                adjustments=[
                    dict(total=-100),
                    dict(total=20),
                    dict(total=3),
                ]
            )
            with freeze_time('2013-08-17'):
                model.update_payment_uri(guid, new_payment_uri)

        invoice = model.get(guid)

        transactions = self._get_transactions_in_order(guid)
        transaction = transactions[0]
        self.assertEqual(transaction.amount, invoice.effective_amount)

        transaction = transactions[1]
        self.assertEqual(transaction.status, TransactionModel.STATUS_INIT)
        self.assertEqual(transaction.amount, invoice.effective_amount)

    def test_update_payment_uri_while_failed(self):
        from billy.models.transaction import TransactionModel

        model = self.make_one(self.session)
        tx_model = TransactionModel(self.session)
        amount = 556677
        title = 'Foobar invoice'
        payment_uri = '/v1/cards/1234'
        new_payment_uri = '/v1/cards/5678'
        create_now = datetime.datetime.utcnow()

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
                payment_uri=payment_uri,
            )
            invoice = model.get(guid)
            transaction = invoice.transactions[0]
            transaction.status = tx_model.STATUS_FAILED
            invoice.status = model.STATUS_PROCESS_FAILED
            self.session.add(transaction)
            self.session.add(invoice)

            with freeze_time('2013-08-17'):
                model.update_payment_uri(guid, new_payment_uri)
                update_now = datetime.datetime.utcnow()

        invoice = model.get(guid)
        self.assertEqual(invoice.status, model.STATUS_PROCESSING)
        self.assertEqual(invoice.updated_at, update_now)
        self.assertEqual(len(invoice.transactions), 2)

        transactions = self._get_transactions_in_order(guid)
        transaction = transactions[0]
        self.assertEqual(transaction.status, TransactionModel.STATUS_FAILED)
        self.assertEqual(transaction.invoice_guid, guid)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, payment_uri)
        self.assertEqual(transaction.scheduled_at, create_now)

        transaction = transactions[1]
        self.assertEqual(transaction.status, TransactionModel.STATUS_INIT)
        self.assertEqual(transaction.invoice_guid, guid)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, new_payment_uri)
        self.assertEqual(transaction.scheduled_at, update_now)

    def test_update_payment_uri_while_failed_with_adjustments(self):
        from billy.models.transaction import TransactionModel

        model = self.make_one(self.session)
        tx_model = TransactionModel(self.session)
        amount = 200
        payment_uri = '/v1/cards/1234'
        new_payment_uri = '/v1/cards/5678'

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                amount=amount,
                payment_uri=payment_uri,
                adjustments=[
                    dict(total=-100),
                    dict(total=20),
                    dict(total=3),
                ],
            )
            invoice = model.get(guid)
            transaction = invoice.transactions[0]
            transaction.status = tx_model.STATUS_FAILED
            invoice.status = model.STATUS_PROCESS_FAILED
            self.session.add(transaction)
            self.session.add(invoice)

            with freeze_time('2013-08-17'):
                model.update_payment_uri(guid, new_payment_uri)

        invoice = model.get(guid)

        transactions = self._get_transactions_in_order(guid)
        transaction = transactions[0]
        self.assertEqual(transaction.amount, invoice.effective_amount)

        transaction = transactions[1]
        self.assertEqual(transaction.amount, invoice.effective_amount)

    def test_update_payment_uri_with_wrong_status(self):
        from billy.models.invoice import InvalidOperationError

        model = self.make_one(self.session)
        amount = 556677
        payment_uri = '/v1/cards/1234'
        new_payment_uri = '/v1/cards/5678'

        def assert_invalid_update(current_status):
            with db_transaction.manager:
                guid = model.create(
                    customer_guid=self.customer_guid,
                    amount=amount,
                    payment_uri=payment_uri,
                )
                invoice = model.get(guid)
                invoice.status = current_status
                self.session.add(invoice)

                with self.assertRaises(InvalidOperationError):
                    model.update_payment_uri(guid, new_payment_uri)

        assert_invalid_update(model.STATUS_REFUNDED)
        assert_invalid_update(model.STATUS_REFUNDING)
        assert_invalid_update(model.STATUS_REFUND_FAILED)
        assert_invalid_update(model.STATUS_CANCELED)
        assert_invalid_update(model.STATUS_SETTLED)

    def test_update_title(self):
        model = self.make_one(self.session)
        amount = 556677
        title = 'Foobar invoice'

        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
            )

        with db_transaction.manager:
            model.update(
                guid=guid,
                title='new title',
            )

        invoice = model.get(guid)
        self.assertEqual(invoice.title, 'new title')

    def test_update_items(self):
        model = self.make_one(self.session)
        items = [
            dict(type='debit', name='foo', amount=100, total=1234),
            dict(name='bar', total=5678, unit='unit'),
            dict(name='special service', total=9999, unit='hours'),
        ]
        with db_transaction.manager:
            guid = model.create(
                customer_guid=self.customer_guid,
                amount=556677,
                items=items,
            )

        new_items = [
            dict(type='hold', name='new foo', total=55, quantity=123),
            dict(name='new bar', total=66, unit='new unit'),
        ]

        with db_transaction.manager:
            model.update(
                guid=guid,
                items=new_items, 
            )

        invoice = model.get(guid)
        item_result = []
        for item in invoice.items:
            item_dict = dict(
                type=item.type,
                name=item.name,
                quantity=item.quantity,
                total=item.total,
                amount=item.amount,
                unit=item.unit,
            )
            for key, value in list(item_dict.iteritems()):
                if value is None:
                    del item_dict[key]
            item_result.append(item_dict)
        self.assertEqual(item_result, new_items)
