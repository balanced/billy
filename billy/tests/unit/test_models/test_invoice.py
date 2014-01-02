from __future__ import unicode_literals
import datetime

import transaction as db_transaction
from freezegun import freeze_time

from billy.models import tables
from billy.models.invoice import DuplicateExternalIDError
from billy.models.invoice import InvalidOperationError
from billy.tests.unit.helper import ModelTestCase


@freeze_time('2013-08-16')
class TestInvoiceModel(ModelTestCase):

    def setUp(self):
        super(TestInvoiceModel, self).setUp()
        # build the basic scenario for plan model
        with db_transaction.manager:
            self.company_guid = self.company_model.create('my_secret_key')
            self.customer_guid = self.customer_model.create(
                company_guid=self.company_guid,
            )

    def test_get_invoice(self):
        invoice = self.invoice_model.get('IV_NON_EXIST')
        self.assertEqual(invoice, None)

        with self.assertRaises(KeyError):
            self.invoice_model.get('IV_NON_EXIST', raise_error=True)

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=1000,
            )

        invoice = self.invoice_model.get(guid)
        self.assertEqual(invoice.guid, guid)

    def test_create(self):
        amount = 556677
        title = 'Foobar invoice'
        external_id = 'external_id'
        appears_on_statement_as = 'hello baby'

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
                external_id=external_id,
                appears_on_statement_as=appears_on_statement_as,
            )

        now = datetime.datetime.utcnow()

        invoice = self.invoice_model.get(guid)
        self.assertEqual(invoice.guid, guid)
        self.assert_(invoice.guid.startswith('IV'))
        self.assertEqual(invoice.customer_guid, self.customer_guid)
        self.assertEqual(invoice.title, title)
        self.assertEqual(invoice.status, self.invoice_model.STATUS_INIT)
        self.assertEqual(invoice.amount, amount)
        self.assertEqual(invoice.payment_uri, None)
        self.assertEqual(invoice.created_at, now)
        self.assertEqual(invoice.updated_at, now)
        self.assertEqual(invoice.external_id, external_id)
        self.assertEqual(invoice.appears_on_statement_as, 
                         appears_on_statement_as)
        self.assertEqual(len(invoice.transactions), 0)
        self.assertEqual(len(invoice.items), 0)

    def test_create_with_negtive_amount(self):
        with self.assertRaises(ValueError):
            self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=-1,
            )

    def test_create_with_duplicated_external_id(self):
        amount = 556677
        external_id = 'external_id'

        with db_transaction.manager:
            self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=amount,
                external_id=external_id,
            )

        with self.assertRaises(DuplicateExternalIDError):
            self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=amount,
                external_id=external_id,
            )

    def test_create_with_items(self):
        items = [
            dict(type='debit', name='foo', total=1234),
            dict(name='bar', total=5678, unit='unit'),
            dict(name='special service', total=9999, quantity=10, unit='hours'),
        ]

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=556677,
                items=items,
            )

        invoice = self.invoice_model.get(guid)
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
        adjustments = [
            dict(total=50, reason='we owe you, man!'),
            dict(total=-100, reason='lannister always pay debts!'),
            dict(total=-123),
        ]

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=200,
                adjustments=adjustments,
            )

        invoice = self.invoice_model.get(guid)

        adjustment_result = []
        for adjustment in invoice.adjustments:
            adjustment_dict = dict(
                total=adjustment.total,
            )
            if adjustment.reason is not None:
                adjustment_dict['reason'] = adjustment.reason
            adjustment_result.append(adjustment_dict)
        self.assertEqual(adjustment_result, adjustments)
        self.assertEqual(invoice.amount, 200)
        self.assertEqual(invoice.total_adjustment_amount, 50 - 100 - 123)

    def test_create_with_payment_uri(self):
        amount = 556677
        title = 'Foobar invoice'
        payment_uri = '/v1/cards/1234'
        appears_on_statement_as = 'hello baby'

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
                payment_uri=payment_uri,
                appears_on_statement_as=appears_on_statement_as,
            )

        now = datetime.datetime.utcnow()

        invoice = self.invoice_model.get(guid)
        self.assertEqual(invoice.guid, guid)
        self.assert_(invoice.guid.startswith('IV'))
        self.assertEqual(invoice.customer_guid, self.customer_guid)
        self.assertEqual(invoice.status, self.invoice_model.STATUS_PROCESSING)
        self.assertEqual(invoice.title, title)
        self.assertEqual(invoice.amount, amount)
        self.assertEqual(invoice.payment_uri, payment_uri)
        self.assertEqual(invoice.appears_on_statement_as, appears_on_statement_as)
        self.assertEqual(invoice.created_at, now)
        self.assertEqual(invoice.updated_at, now)

        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.transaction_type, 
                         self.transaction_model.TYPE_CHARGE)
        self.assertEqual(transaction.transaction_cls, 
                         self.transaction_model.CLS_INVOICE)
        self.assertEqual(transaction.status, self.transaction_model.STATUS_INIT)
        self.assertEqual(transaction.invoice_guid, invoice.guid)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, payment_uri)
        self.assertEqual(transaction.appears_on_statement_as, appears_on_statement_as)

    def test_create_with_payment_uri_and_zero_amount(self):
        amount = 0
        payment_uri = '/v1/cards/1234'

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=amount,
                payment_uri=payment_uri,
            )

        invoice = self.invoice_model.get(guid)
        self.assertEqual(invoice.amount, amount)
        self.assertEqual(invoice.status, self.invoice_model.STATUS_SETTLED)
        self.assertEqual(len(invoice.transactions), 0)

    def test_create_with_payment_uri_with_adjustments(self):
        amount = 200 
        payment_uri = '/v1/cards/1234'

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=amount,
                payment_uri=payment_uri,
                adjustments=[
                    dict(total=-100),
                    dict(total=20),
                    dict(total=3),
                ]
            )

        invoice = self.invoice_model.get(guid)
        self.assertEqual(len(invoice.transactions), 1)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.amount, invoice.amount)

    def test_update_payment_uri(self):
        amount = 556677
        title = 'Foobar invoice'
        payment_uri = '/v1/cards/1234'
        appears_on_statement_as = 'hello baby'

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
                appears_on_statement_as=appears_on_statement_as,
            )

        invoice = self.invoice_model.get(guid)
        self.assertEqual(len(invoice.transactions), 0)

        with freeze_time('2013-08-17'):
            with db_transaction.manager:
                self.invoice_model.update_payment_uri(guid, payment_uri)
            update_now = datetime.datetime.utcnow()

        invoice = self.invoice_model.get(guid)
        self.assertEqual(invoice.status, self.invoice_model.STATUS_PROCESSING)
        self.assertEqual(invoice.updated_at, update_now)
        self.assertEqual(len(invoice.transactions), 1)

        transaction = invoice.transactions[0]
        self.assertEqual(transaction.status, self.transaction_model.STATUS_INIT)
        self.assertEqual(transaction.invoice_guid, guid)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, payment_uri)
        self.assertEqual(transaction.appears_on_statement_as, 
                         appears_on_statement_as)
        self.assertEqual(transaction.scheduled_at, update_now)

    def test_update_payment_uri_with_adjustments(self):
        amount = 200
        title = 'Foobar invoice'
        payment_uri = '/v1/cards/1234'

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
                adjustments=[
                    dict(total=-100),
                    dict(total=20),
                    dict(total=3),
                ]
            )

        invoice = self.invoice_model.get(guid)
        self.assertEqual(len(invoice.transactions), 0)

        with freeze_time('2013-08-17'):
            with db_transaction.manager:
                self.invoice_model.update_payment_uri(guid, payment_uri)

        invoice = self.invoice_model.get(guid)
        transaction = invoice.transactions[0]
        self.assertEqual(transaction.amount, invoice.amount)
        self.assertEqual(transaction.amount, 200)

    def _get_transactions_in_order(self, guid):
        transactions = (
            self.session
            .query(tables.InvoiceTransaction)
            .filter_by(invoice_guid=guid)
            .order_by(tables.InvoiceTransaction.scheduled_at)
            .all()
        )
        return transactions

    def test_update_payment_uri_while_processing(self):
        amount = 556677
        title = 'Foobar invoice'
        payment_uri = '/v1/cards/1234'
        new_payment_uri = '/v1/cards/5678'
        appears_on_statement_as = 'hello baby'
        create_now = datetime.datetime.utcnow()

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
                payment_uri=payment_uri,
                appears_on_statement_as=appears_on_statement_as,
            )
            with freeze_time('2013-08-17'):
                self.invoice_model.update_payment_uri(guid, new_payment_uri)
                update_now = datetime.datetime.utcnow()

        invoice = self.invoice_model.get(guid)
        self.assertEqual(invoice.status, self.invoice_model.STATUS_PROCESSING)
        self.assertEqual(invoice.updated_at, update_now)
        self.assertEqual(len(invoice.transactions), 2)

        transactions = self._get_transactions_in_order(guid)
        transaction = transactions[0]
        self.assertEqual(transaction.status, 
                         self.transaction_model.STATUS_CANCELED)
        self.assertEqual(transaction.invoice_guid, guid)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, payment_uri)
        self.assertEqual(transaction.appears_on_statement_as, 
                         appears_on_statement_as)
        self.assertEqual(transaction.scheduled_at, create_now)

        transaction = transactions[1]
        self.assertEqual(transaction.status, self.transaction_model.STATUS_INIT)
        self.assertEqual(transaction.invoice_guid, guid)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, new_payment_uri)
        self.assertEqual(transaction.appears_on_statement_as, appears_on_statement_as)
        self.assertEqual(transaction.scheduled_at, update_now)

    def test_update_payment_uri_while_processing_with_adjustments(self):
        amount = 200
        payment_uri = '/v1/cards/1234'
        new_payment_uri = '/v1/cards/5678'
        appears_on_statement_as = 'hello baby'

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=amount,
                payment_uri=payment_uri,
                appears_on_statement_as=appears_on_statement_as,
                adjustments=[
                    dict(total=-100),
                    dict(total=20),
                    dict(total=3),
                ]
            )
            with freeze_time('2013-08-17'):
                self.invoice_model.update_payment_uri(guid, new_payment_uri)

        invoice = self.invoice_model.get(guid)

        transactions = self._get_transactions_in_order(guid)
        transaction = transactions[0]
        self.assertEqual(transaction.amount, invoice.amount)

        transaction = transactions[1]
        self.assertEqual(transaction.status, self.transaction_model.STATUS_INIT)
        self.assertEqual(transaction.amount, invoice.amount)
        self.assertEqual(transaction.appears_on_statement_as, 
                         invoice.appears_on_statement_as)

    def test_update_payment_uri_while_failed(self):
        amount = 556677
        title = 'Foobar invoice'
        payment_uri = '/v1/cards/1234'
        new_payment_uri = '/v1/cards/5678'
        appears_on_statement_as = 'hello baby'
        create_now = datetime.datetime.utcnow()

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
                payment_uri=payment_uri,
                appears_on_statement_as=appears_on_statement_as,
            )
            invoice = self.invoice_model.get(guid)
            transaction = invoice.transactions[0]
            transaction.status = self.transaction_model.STATUS_FAILED
            invoice.status = self.invoice_model.STATUS_PROCESS_FAILED
            self.session.add(transaction)
            self.session.add(invoice)

            with freeze_time('2013-08-17'):
                self.invoice_model.update_payment_uri(guid, new_payment_uri)
                update_now = datetime.datetime.utcnow()

        invoice = self.invoice_model.get(guid)
        self.assertEqual(invoice.status, self.invoice_model.STATUS_PROCESSING)
        self.assertEqual(invoice.updated_at, update_now)
        self.assertEqual(len(invoice.transactions), 2)

        transactions = self._get_transactions_in_order(guid)
        transaction = transactions[0]
        self.assertEqual(transaction.status, self.transaction_model.STATUS_FAILED)
        self.assertEqual(transaction.invoice_guid, guid)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, payment_uri)
        self.assertEqual(transaction.appears_on_statement_as, 
                         appears_on_statement_as)
        self.assertEqual(transaction.scheduled_at, create_now)

        transaction = transactions[1]
        self.assertEqual(transaction.status, self.transaction_model.STATUS_INIT)
        self.assertEqual(transaction.invoice_guid, guid)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.payment_uri, new_payment_uri)
        self.assertEqual(transaction.appears_on_statement_as, 
                         appears_on_statement_as)
        self.assertEqual(transaction.scheduled_at, update_now)

    def test_update_payment_uri_while_failed_with_adjustments(self):
        amount = 200
        payment_uri = '/v1/cards/1234'
        new_payment_uri = '/v1/cards/5678'
        appears_on_statement_as = 'hello baby'

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=amount,
                payment_uri=payment_uri,
                appears_on_statement_as=appears_on_statement_as,
                adjustments=[
                    dict(total=-100),
                    dict(total=20),
                    dict(total=3),
                ],
            )
            invoice = self.invoice_model.get(guid)
            transaction = invoice.transactions[0]
            transaction.status = self.transaction_model.STATUS_FAILED
            invoice.status = self.invoice_model.STATUS_PROCESS_FAILED
            self.session.add(transaction)
            self.session.add(invoice)

            with freeze_time('2013-08-17'):
                self.invoice_model.update_payment_uri(guid, new_payment_uri)

        invoice = self.invoice_model.get(guid)

        transactions = self._get_transactions_in_order(guid)
        transaction = transactions[0]
        self.assertEqual(transaction.amount, invoice.amount)
        self.assertEqual(transaction.appears_on_statement_as, 
                         invoice.appears_on_statement_as)

        transaction = transactions[1]
        self.assertEqual(transaction.amount, invoice.amount)
        self.assertEqual(transaction.appears_on_statement_as, 
                         invoice.appears_on_statement_as)

    def test_update_payment_uri_with_wrong_status(self):
        amount = 556677
        payment_uri = '/v1/cards/1234'
        new_payment_uri = '/v1/cards/5678'

        def assert_invalid_update(current_status):
            with db_transaction.manager:
                guid = self.invoice_model.create(
                    customer_guid=self.customer_guid,
                    amount=amount,
                    payment_uri=payment_uri,
                )
                invoice = self.invoice_model.get(guid)
                invoice.status = current_status
                self.session.add(invoice)

                with self.assertRaises(InvalidOperationError):
                    self.invoice_model.update_payment_uri(guid, new_payment_uri)

        assert_invalid_update(self.invoice_model.STATUS_REFUNDED)
        assert_invalid_update(self.invoice_model.STATUS_REFUNDING)
        assert_invalid_update(self.invoice_model.STATUS_REFUND_FAILED)
        assert_invalid_update(self.invoice_model.STATUS_CANCELED)
        assert_invalid_update(self.invoice_model.STATUS_SETTLED)

    def test_update_title(self):
        amount = 556677
        title = 'Foobar invoice'

        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                title=title,
                amount=amount,
            )

        with db_transaction.manager:
            self.invoice_model.update(
                guid=guid,
                title='new title',
            )

        invoice = self.invoice_model.get(guid)
        self.assertEqual(invoice.title, 'new title')

    def test_update_items(self):
        items = [
            dict(type='debit', name='foo', amount=100, total=1234),
            dict(name='bar', total=5678, unit='unit'),
            dict(name='special service', total=9999, unit='hours'),
        ]
        with db_transaction.manager:
            guid = self.invoice_model.create(
                customer_guid=self.customer_guid,
                amount=556677,
                items=items,
            )

        new_items = [
            dict(type='hold', name='new foo', total=55, quantity=123),
            dict(name='new bar', total=66, unit='new unit'),
        ]

        with db_transaction.manager:
            self.invoice_model.update(
                guid=guid,
                items=new_items, 
            )

        invoice = self.invoice_model.get(guid)
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