from __future__ import unicode_literals

from billy.models import tables
from billy.models.base import BaseTableModel
from billy.models.transaction import TransactionModel
from billy.utils.generic import make_guid


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
