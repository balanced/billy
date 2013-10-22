from __future__ import unicode_literals

from billy.models import tables
from billy.models.base import BaseTableModel
from billy.utils.generic import make_guid


class InvoiceModel(BaseTableModel):

    TABLE = tables.Invoice

    #: initialized status
    STATUS_INIT = 0
    #: we are retrying this transaction
    STATUS_RETRYING = 1
    #: this transaction is done
    STATUS_DONE = 2
    #: this transaction is failed
    STATUS_FAILED = 3
    #: this transaction is canceled
    STATUS_CANCELED = 4

    STATUS_ALL = [
        STATUS_INIT,
        STATUS_RETRYING,
        STATUS_DONE,
        STATUS_FAILED,
        STATUS_CANCELED,
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
        return invoice.guid
