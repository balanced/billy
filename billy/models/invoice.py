from __future__ import unicode_literals

from billy.models import tables
from billy.models.base import BaseTableModel
from billy.models.transaction import TransactionModel
from billy.utils.generic import make_guid


class InvalidOperationError(RuntimeError):
    """This error indicates an invalid operation to invoice model, such as 
    updating an invoice's payment_uri in wrong status

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

    def create(
        self, 
        customer_guid, 
        amount,
        payment_uri=None, 
        title=None,
    ):
        """Create a invoice and return its id

        """
        if amount <= 0:
            raise ValueError('Amount should be a non-zero postive integer')
        now = tables.now_func()
        invoice = tables.Invoice(
            guid='IV' + make_guid(),
            status=self.STATUS_INIT,
            customer_guid=customer_guid,
            amount=amount, 
            payment_uri=payment_uri, 
            title=title,
            created_at=now,
            updated_at=now,
        )
        
        self.session.add(invoice)
        self.session.flush()

        tx_model = TransactionModel(self.session)
        # as if we set the payment_uri at very first, we want to charge it
        # immediately, so we create a transaction right away, also set the 
        # status to PROCESSING
        if payment_uri is not None:
            invoice.status = self.STATUS_PROCESSING
            tx_model.create(
                invoice_guid=invoice.guid, 
                payment_uri=payment_uri, 
                amount=amount, 
                transaction_type=tx_model.TYPE_CHARGE, 
                transaction_cls=tx_model.CLS_INVOICE, 
                scheduled_at=now, 
            )

        self.session.add(invoice)
        self.session.flush()
        return invoice.guid

    def update(self, guid, payment_uri=NOT_SET):
        """Update an invoice

        """
        tx_model = TransactionModel(self.session)
        invoice = self.get(guid, raise_error=True)
        now = tables.now_func()
        invoice.updated_at = now

        # TODO: think about race condition issue, what if we update the 
        # payment_uri during processing previous transaction? say
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
        # database transactions, hum..... maybe we need a lock here?
        if payment_uri is not self.NOT_SET:
            last_transaction = (
                self.session
                .query(tables.InvoiceTransaction)
                .filter(tables.InvoiceTransaction.invoice_guid == guid)
                .order_by(tables.InvoiceTransaction.created_at.desc())
                .first()
            )

            invoice.payment_uri = payment_uri
            if invoice.status == self.STATUS_INIT:
                tx_model.create(
                    invoice_guid=invoice.guid, 
                    payment_uri=payment_uri, 
                    amount=invoice.amount, 
                    transaction_type=tx_model.TYPE_CHARGE, 
                    transaction_cls=tx_model.CLS_INVOICE, 
                    scheduled_at=now, 
                )
            # we are already processing, abort current transaction and create
            # a new one
            elif invoice.status == self.STATUS_PROCESSING:
                assert last_transaction.status in [
                    tx_model.STATUS_INIT, 
                    tx_model.STATUS_RETRYING
                ], 'The last transaction status should be either INIT or ' \
                   'RETRYING'
                last_transaction.status = tx_model.STATUS_CANCELED
                last_transaction.canceled_at = now
                self.session.add(last_transaction)
                tx_model.create(
                    invoice_guid=invoice.guid, 
                    payment_uri=payment_uri, 
                    amount=invoice.amount, 
                    transaction_type=tx_model.TYPE_CHARGE, 
                    transaction_cls=tx_model.CLS_INVOICE, 
                    scheduled_at=now, 
                )
            # the previous transaction failed, just create a new one
            elif invoice.status == self.STATUS_PROCESS_FAILED:
                assert last_transaction.status == tx_model.STATUS_FAILED, \
                    'The last transaction status should be FAILED'
                tx_model.create(
                    invoice_guid=invoice.guid, 
                    payment_uri=payment_uri, 
                    amount=invoice.amount, 
                    transaction_type=tx_model.TYPE_CHARGE, 
                    transaction_cls=tx_model.CLS_INVOICE, 
                    scheduled_at=now, 
                )
            else:
                raise InvalidOperationError(
                    'Invalid operation, you can only update payment_uri when '
                    'the status is one of INIT, PROCESSING and PROCESS_FAILED'
                )
            invoice.status = self.STATUS_PROCESSING
        self.session.add(invoice)
        self.session.flush()
