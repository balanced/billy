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
        query = (
            self.session.query(tables.Transaction)
            .filter_by(guid=guid)
            .first()
        )
        if raise_error and query is None:
            raise KeyError('No such transaction {}'.format(guid))
        return query

    def list_by_company_guid(self, company_guid, offset=None, limit=None):
        """Get transactions of a company by given guid

        """
        Transaction = tables.Transaction
        Subscription = tables.Subscription
        Plan = tables.Plan
        query = (
            self.session
            .query(Transaction)
            .join((Subscription, 
                   Subscription.guid == Transaction.subscription_guid))
            .join((Plan, Plan.guid == Subscription.plan_guid))
            .filter(Plan.company_guid == company_guid)
            .order_by(Transaction.created_at.asc())
        )
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query

    def create(
        self, 
        subscription_guid, 
        transaction_type, 
        amount,
        scheduled_at,
        payment_uri=None,
        refund_to_guid=None,
    ):
        """Create a transaction and return its ID

        """
        if transaction_type not in self.TYPE_ALL:
            raise ValueError('Invalid transaction_type {}'
                             .format(transaction_type))
        if refund_to_guid is not None:
            if transaction_type != self.TYPE_REFUND:
                raise ValueError('refund_to_guid can only be set to a refund '
                                 'transaction')
            if payment_uri is not None:
                raise ValueError('payment_uri cannot be set to a refund '
                                 'transaction')
            refund_transaction = self.get(refund_to_guid, raise_error=True)
            if refund_transaction.transaction_type != self.TYPE_CHARGE:
                raise ValueError('Only charge transaction can be refunded')

        now = tables.now_func()
        transaction = tables.Transaction(
            guid='TX' + make_guid(),
            subscription_guid=subscription_guid,
            transaction_type=transaction_type,
            amount=amount, 
            payment_uri=payment_uri, 
            status=self.STATUS_INIT, 
            scheduled_at=scheduled_at, 
            refund_to_guid=refund_to_guid, 
            created_at=now, 
            updated_at=now, 
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

    def process_one(self, processor, transaction):
        """Process one transaction

        """
        if transaction.status == self.STATUS_DONE:
            raise ValueError('Cannot process a finished transaction {}'
                             .format(transaction.guid))
        self.logger.debug('Processing transaction %s', transaction.guid)
        now = tables.now_func()
        customer = transaction.subscription.customer
        try:
            # create customer record in balanced
            if customer.external_id is None:
                customer_id = processor.create_customer(customer)
                customer.external_id = customer_id
                self.session.add(customer)
                self.session.flush()

            self.logger.info('External customer %s', customer.external_id)

            # prepare customer (add bank account or credit card)
            processor.prepare_customer(customer, transaction.payment_uri)

            if transaction.transaction_type == self.TYPE_CHARGE:
                method = processor.charge
            elif transaction.transaction_type == self.TYPE_PAYOUT:
                method = processor.payout
            elif transaction.transaction_type == self.TYPE_REFUND:
                method = processor.refund
            else:
                raise RuntimeError('Invalid transaction type to process')

            transaction_id = method(transaction)
            # TODO: generate an invoice here?
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e:
            transaction.status = self.STATUS_RETRYING
            # TODO: provide more expressive error message?
            transaction.error_message = unicode(e)
            transaction.failure_count += 1
            self.logger.error('Failed to process transaction %s, '
                              'failure_count=%s', 
                              transaction.guid, transaction.failure_count, 
                              exc_info=True)
            # TODO: maybe we should limit failure count here?
            #       such as too many faiure then transit to FAILED status?
            transaction.updated_at = now
            self.session.add(transaction)
            self.session.flush()
            return

        transaction.external_id = transaction_id
        transaction.status = self.STATUS_DONE
        transaction.updated_at = tables.now_func()
        self.session.add(transaction)
        self.session.flush()
        
        self.logger.info('Processed transaction %s, status=%s, external_id=%s',
                         transaction.guid, transaction.status, 
                         transaction.external_id)

    def process_transactions(self, processor, guids=None):
        """Process all transactions 

        """
        Transaction = tables.Transaction
        query = (
            self.session.query(Transaction)
            .filter(Transaction.status.in_([
                self.STATUS_INIT, 
                self.STATUS_RETRYING]
            ))
        )
        if guids is not None:
            query = query.filter(Transaction.guid.in_(guids))

        processed_transaction_guids = []
        for transaction in query:
            self.process_one(processor, transaction)
            processed_transaction_guids.append(transaction.guid)
        return processed_transaction_guids
