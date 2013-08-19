from __future__ import unicode_literals
import logging

from billy.models import tables
from billy.utils.generic import make_guid


class TransactionModel(object):

    #: charge type transaction
    TYPE_CHARGE = 0
    #: refund type transaction
    TYPE_REFUND = 1
    #: Paying out type transaction
    TYPE_PAYOUT = 2

    TYPE_ALL = [
        TYPE_CHARGE,
        TYPE_REFUND,
        TYPE_PAYOUT, 
    ]

    #: initialized status
    STATUS_INIT = 0
    #: we are retrying this transaction
    STATUS_RETRYING = 1
    #: this transaction is done
    STATUS_DONE = 2
    #: this transaction is failed
    STATUS_FAILED = 3

    STATUS_ALL = [
        STATUS_INIT,
        STATUS_RETRYING,
        STATUS_DONE,
        STATUS_FAILED,
    ]

    def __init__(self, session, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.session = session

    def get(self, guid, raise_error=False):
        """Find a transaction by guid and return it

        :param guid: The guild of transaction to get
        :param raise_error: Raise KeyError when cannot find one
        """
        query = self.session.query(tables.Transaction) \
            .filter_by(guid=guid) \
            .first()
        if raise_error and query is None:
            raise KeyError('No such transaction {}'.format(guid))
        return query

    def create(
        self, 
        subscription_guid, 
        transaction_type, 
        amount,
        payment_uri,
        scheduled_at,
    ):
        """Create a transaction and return its ID

        """
        if transaction_type not in self.TYPE_ALL:
            raise ValueError('Invalid transaction_type {}'.format(transaction_type))
        transaction = tables.Transaction(
            guid='TX' + make_guid(),
            subscription_guid=subscription_guid,
            transaction_type=transaction_type,
            amount=amount, 
            payment_uri=payment_uri, 
            status=self.STATUS_INIT, 
            scheduled_at=scheduled_at, 
        )
        self.session.add(transaction)
        self.session.flush()
        return transaction.guid

    def update(self, guid, **kwargs):
        """Update a transaction 

        """
        transaction = self.get(guid, raise_error=True)
        now = tables.now_func()
        transaction.updated_at = now
        if 'status' in kwargs:
            status = kwargs.pop('status')
            if status not in self.STATUS_ALL:
                raise ValueError('Invalid status {}'.format(status))
            transaction.status = status
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.add(transaction)
        self.session.flush()
