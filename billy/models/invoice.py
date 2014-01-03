from __future__ import unicode_literals

from billy.models import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.utils.generic import make_guid


class InvalidOperationError(RuntimeError):
    """This error indicates an invalid operation to invoice model, such as 
    updating an invoice's funding_instrument_uri in wrong status

    """


class DuplicateExternalIDError(RuntimeError):
    """This error indicates you have duplicate (Customer GUID, External ID)
    pair in database. The field `external_id` was designed to avoid duplicate
    invoicing. 

    """


class InvoiceModel(BaseTableModel):

    TABLE = tables.Invoice

    #: initialized status
    STATUS_INIT = 0
    #: processing invoice status
    STATUS_PROCESSING = 1
    #: settled status (processed successfully)
    STATUS_SETTLED = 2
    #: canceled status
    STATUS_CANCELED = 3
    #: failed to process status
    STATUS_PROCESS_FAILED = 4
    #: refunding status
    STATUS_REFUNDING = 5
    #: refunded status
    STATUS_REFUNDED = 6
    #: failed to refund status
    STATUS_REFUND_FAILED = 7

    STATUS_ALL = [
        STATUS_INIT,
        STATUS_PROCESSING,
        STATUS_SETTLED,
        STATUS_CANCELED,
        STATUS_PROCESS_FAILED,
        STATUS_REFUNDING,
        STATUS_REFUNDED,
        STATUS_REFUND_FAILED,
    ]

    # not set object
    NOT_SET = object()

    @decorate_offset_limit
    def list_by_ancestor(self, ancestor, external_id=NOT_SET):
        """Get invoices of a given ancestor

        """
        Invoice = tables.Invoice
        Customer = tables.Customer
        query = (
            self.session
            .query(Invoice)
            .join(Customer, Customer.guid == Invoice.customer_guid)
            .filter(Customer.company == ancestor)
            .order_by(tables.Invoice.created_at.desc())
        )
        # TODO: support other ancestor, such as customer
        if external_id is not self.NOT_SET:
            query = query.filter(Invoice.external_id == external_id)
        return query

    def create(
        self, 
        customer, 
        amount,
        funding_instrument_uri=None, 
        title=None,
        items=None,
        adjustments=None,
        external_id=None,
        appears_on_statement_as=None,
    ):
        """Create a invoice and return its id

        """
        from sqlalchemy.exc import IntegrityError

        if amount < 0:
            raise ValueError('Negative amount {} is not allowed'.format(amount))

        now = tables.now_func()
        invoice = tables.Invoice(
            guid='IV' + make_guid(),
            status=self.STATUS_INIT,
            customer=customer,
            amount=amount, 
            funding_instrument_uri=funding_instrument_uri, 
            title=title,
            created_at=now,
            updated_at=now,
            external_id=external_id,
            appears_on_statement_as=appears_on_statement_as,
        )

        self.session.add(invoice)

        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateExternalIDError(
                'Invoice {} with external_id {} already exists'
                .format(customer.guid, external_id)
            )

        if items:
            for item in items:
                record = tables.Item(
                    invoice=invoice,
                    name=item['name'],
                    total=item['total'],
                    type=item.get('type'),
                    quantity=item.get('quantity'),
                    unit=item.get('unit'),
                    amount=item.get('amount'),
                )
                self.session.add(record)
            self.session.flush()

        # TODO: what about an invalid adjust? say, it makes the total of invoice
        # a negative value? I think we should not allow user to create such 
        # invalid invoice
        if adjustments:
            for adjustment in adjustments:
                record = tables.Adjustment(
                    invoice=invoice,
                    total=adjustment['total'],
                    reason=adjustment.get('reason'),
                )
                self.session.add(record)
            self.session.flush()

        tx_model = self.factory.create_transaction_model()
        # as if we set the funding_instrument_uri at very first, we want to charge it
        # immediately, so we create a transaction right away, also set the 
        # status to PROCESSING
        if funding_instrument_uri is not None and invoice.amount > 0:
            invoice.status = self.STATUS_PROCESSING
            tx_model.create(
                invoice=invoice, 
                funding_instrument_uri=funding_instrument_uri, 
                amount=invoice.amount, 
                transaction_type=tx_model.TYPE_CHARGE, 
                transaction_cls=tx_model.CLS_INVOICE, 
                appears_on_statement_as=invoice.appears_on_statement_as,
                scheduled_at=now, 
            )
        # it is zero amount, nothing to charge, just switch to
        # SETTLED status
        elif invoice.amount == 0:
            invoice.status = self.STATUS_SETTLED

        self.session.flush()
        return invoice

    def update(
        self, 
        invoice, 
        funding_instrument_uri=NOT_SET, 
        title=NOT_SET, 
        items=NOT_SET,
    ):
        """Update an invoice

        """
        now = tables.now_func()
        invoice.updated_at = now

        if title is not self.NOT_SET:
            invoice.title = title
        if items is not self.NOT_SET:
            # delete all old items
            old_items = invoice.items
            for item in old_items:
                self.session.delete(item)
            new_items = []
            for item in items:
                item = tables.Item(
                    invoice_guid=invoice.guid,
                    name=item['name'],
                    total=item['total'],
                    type=item.get('type'),
                    quantity=item.get('quantity'),
                    unit=item.get('unit'),
                    amount=item.get('amount'),
                )
                new_items.append(item)
                self.session.add(item)
            invoice.items = new_items
        self.session.flush()

    def update_funding_instrument_uri(self, invoice, funding_instrument_uri):
        """Update the funding_instrument_uri of an invoice, as it may yield 
        transactions, we don't want to put this in `update` method

        @return: a list of yielded transaction
        """
        tx_model = self.factory.create_transaction_model()
        now = tables.now_func()
        invoice.updated_at = now
        invoice.funding_instrument_uri = funding_instrument_uri
        transactions = []

        # We have nothing to do if the amount is zero, just return
        if invoice.amount == 0:
            return transactions 

        # think about race condition issue, what if we update the 
        # funding_instrument_uri during processing previous transaction? say
        # 
        #     DB Transaction A begin
        #     Call to Balanced API
        #                                   DB Transaction B begin
        #                                   Update invoice payment URI
        #                                   Update last transaction to CANCELED 
        #                                   Create a new transaction
        #                                   DB Transaction B commit
        #     Update transaction to DONE
        #     DB Transaction A commit
        #     DB Transaction conflicts
        #     DB Transaction rollback
        # 
        # call to balanced API is made, but we had confliction between two
        # database transactions
        #
        # to solve the problem mentioned above, we acquire a lock on the 
        # invoice at begin of transaction, in this way, there will be no
        # overlap between two transaction

        last_transaction = (
            self.session
            .query(tables.InvoiceTransaction)
            .filter(tables.InvoiceTransaction.invoice == invoice)
            .order_by(tables.InvoiceTransaction.created_at.desc())
            .first()
        )

        # the invoice is just created, simply create a transaction for it
        if invoice.status == self.STATUS_INIT:
            transaction = tx_model.create(
                invoice=invoice, 
                funding_instrument_uri=funding_instrument_uri, 
                amount=invoice.amount, 
                transaction_type=tx_model.TYPE_CHARGE, 
                transaction_cls=tx_model.CLS_INVOICE, 
                appears_on_statement_as=invoice.appears_on_statement_as, 
                scheduled_at=now, 
            )
            transactions.append(transaction)
        # we are already processing, abort current transaction and create
        # a new one
        elif invoice.status == self.STATUS_PROCESSING:
            assert last_transaction.status in [
                tx_model.STATUS_INIT, 
                tx_model.STATUS_RETRYING
            ], 'The last transaction status should be either INIT or ' \
               'RETRYING'
            # cancel old one
            last_transaction.status = tx_model.STATUS_CANCELED
            last_transaction.canceled_at = now
            self.session.add(last_transaction)
            # create a new one
            transaction = tx_model.create(
                invoice=invoice, 
                funding_instrument_uri=funding_instrument_uri, 
                amount=invoice.amount, 
                transaction_type=tx_model.TYPE_CHARGE, 
                transaction_cls=tx_model.CLS_INVOICE, 
                appears_on_statement_as=invoice.appears_on_statement_as, 
                scheduled_at=now, 
            )
            transactions.append(transaction)
        # the previous transaction failed, just create a new one
        elif invoice.status == self.STATUS_PROCESS_FAILED:
            assert last_transaction.status == tx_model.STATUS_FAILED, \
                'The last transaction status should be FAILED'
            transaction = tx_model.create(
                invoice=invoice, 
                funding_instrument_uri=funding_instrument_uri, 
                amount=invoice.amount, 
                transaction_type=tx_model.TYPE_CHARGE, 
                transaction_cls=tx_model.CLS_INVOICE, 
                appears_on_statement_as=invoice.appears_on_statement_as, 
                scheduled_at=now, 
            )
            transactions.append(transaction)
        else:
            raise InvalidOperationError(
                'Invalid operation, you can only update funding_instrument_uri when '
                'the status is one of INIT, PROCESSING and PROCESS_FAILED'
            )
        invoice.status = self.STATUS_PROCESSING

        self.session.flush()
        return transactions

    # TODO: implement invoice refund here
