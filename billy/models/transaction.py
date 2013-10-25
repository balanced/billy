from __future__ import unicode_literals

from billy.models import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.utils.generic import make_guid


class TransactionModel(BaseTableModel):

    TABLE = tables.Transaction

    #: the default maximum retry count
    DEFAULT_MAXIMUM_RETRY = 10

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

    #: subscription transaction
    CLS_SUBSCRIPTION = 0
    #: invoice transaction
    CLS_INVOICE = 1

    CLS_ALL = [
        CLS_SUBSCRIPTION,
        CLS_INVOICE,
    ]

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

    def get_last_transaction(self):
        """Get last transaction

        """
        query = (
            self.session
            .query(tables.Transaction)
            .order_by(tables.Transaction.created_at.desc())
        )
        return query.first()

    @decorate_offset_limit
    def list_by_company_guid(self, company_guid):
        """Get transactions of a company by given guid

        """
        from sqlalchemy.sql.expression import or_
        Transaction = tables.Transaction
        SubscriptionTransaction = tables.SubscriptionTransaction
        InvoiceTransaction = tables.InvoiceTransaction
        Subscription = tables.Subscription
        Invoice = tables.Invoice
        Plan = tables.Plan
        Customer = tables.Customer

        subscription_transaction_guids = (
            self.session
            .query(SubscriptionTransaction.guid)
            .join(
                Subscription, 
                Subscription.guid == SubscriptionTransaction.subscription_guid
            )
            .join(Plan, Plan.guid == Subscription.plan_guid)
            .filter(Plan.company_guid == company_guid)
            .subquery()
        )
        invoice_transaction_guids = (
            self.session
            .query(InvoiceTransaction.guid)
            .join(Invoice, 
                  Invoice.guid == InvoiceTransaction.invoice_guid)
            .join(Customer, Customer.guid == Invoice.customer_guid)
            .filter(Customer.company_guid == company_guid)
            .subquery()
        )
        query = (
            self.session
            .query(Transaction)
            .filter(or_(
                Transaction.guid.in_(subscription_transaction_guids),
                Transaction.guid.in_(invoice_transaction_guids),
            ))
            .order_by(Transaction.created_at.desc())
        )
        return query

    @decorate_offset_limit
    def list_by_subscription_guid(self, subscription_guid):
        """Get transactions of a subscription by given guid

        """
        Transaction = tables.SubscriptionTransaction
        query = (
            self.session
            .query(Transaction)
            .filter(Transaction.subscription_guid == subscription_guid)
            .order_by(Transaction.created_at.desc())
        )
        return query

    def create(
        self, 
        transaction_type, 
        transaction_cls, 
        amount,
        scheduled_at,
        subscription_guid=None, 
        invoice_guid=None, 
        payment_uri=None,
        refund_to_guid=None,
    ):
        """Create a transaction and return its ID

        """
        if transaction_type not in self.TYPE_ALL:
            raise ValueError('Invalid transaction_type {}'
                             .format(transaction_type))
        if transaction_cls not in self.CLS_ALL:
            raise ValueError('Invalid transaction_cls {}'
                             .format(transaction_cls))
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

        if transaction_cls == self.CLS_SUBSCRIPTION:
            table_cls = tables.SubscriptionTransaction
            if subscription_guid is None:
                raise ValueError('subscription_guid cannot be None')
            extra_args = dict(subscription_guid=subscription_guid)
        elif transaction_cls == self.CLS_INVOICE:
            table_cls = tables.InvoiceTransaction
            if invoice_guid is None:
                raise ValueError('invoice_guid cannot be None')
            extra_args = dict(invoice_guid=invoice_guid)
        now = tables.now_func()
        transaction = table_cls(
            guid='TX' + make_guid(),
            transaction_type=transaction_type,
            amount=amount, 
            payment_uri=payment_uri, 
            status=self.STATUS_INIT, 
            scheduled_at=scheduled_at, 
            refund_to_guid=refund_to_guid, 
            created_at=now, 
            updated_at=now, 
            **extra_args
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

    def process_one(
        self, 
        processor, 
        transaction, 
        maximum_retry=DEFAULT_MAXIMUM_RETRY
    ):
        """Process one transaction

        """
        from billy.models.invoice import InvoiceModel

        if transaction.status == self.STATUS_DONE:
            raise ValueError('Cannot process a finished transaction {}'
                             .format(transaction.guid))
        self.logger.debug('Processing transaction %s', transaction.guid)
        now = tables.now_func()

        if transaction.transaction_cls == self.CLS_SUBSCRIPTION:
            customer = transaction.subscription.customer
        else:
            customer = transaction.invoice.customer

        method = {
            self.TYPE_CHARGE: processor.charge,
            self.TYPE_PAYOUT: processor.payout,
            self.TYPE_REFUND: processor.refund,
        }[transaction.transaction_type]

        try:
            # create customer record in Balanced
            if customer.external_id is None:
                customer_id = processor.create_customer(customer)
                customer.external_id = customer_id
                self.session.add(customer)
                self.session.flush()

            self.logger.info('External customer %s', customer.external_id)
            # prepare customer (add bank account or credit card)
            processor.prepare_customer(customer, transaction.payment_uri)
            # do charge/payout/refund 
            transaction_id = method(transaction)
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
            # the failure times exceed the limitation
            if transaction.failure_count > maximum_retry:
                self.logger.error('Exceed maximum retry limitation %s, '
                                  'transaction %s failed', maximum_retry, 
                                  transaction.guid)
                transaction.status = self.STATUS_FAILED

                # the transaction is failed, update invoice status
                if transaction.transaction_cls == self.CLS_INVOICE:
                    invoice_status = {
                        self.TYPE_CHARGE: InvoiceModel.STATUS_PROCESS_FAILED,
                        self.TYPE_REFUND: InvoiceModel.STATUS_REFUND_FAILED,
                    }[transaction.transaction_type]
                    transaction.invoice.status = invoice_status
                    self.session.add(transaction.invoice)
            transaction.updated_at = now
            self.session.add(transaction)
            self.session.flush()
            return

        transaction.external_id = transaction_id
        transaction.status = self.STATUS_DONE
        transaction.updated_at = tables.now_func()
        self.session.add(transaction)

        # the transaction is done, update invoice status
        if transaction.transaction_cls == self.CLS_INVOICE:
            invoice_status = {
                self.TYPE_CHARGE: InvoiceModel.STATUS_SETTLED,
                self.TYPE_REFUND: InvoiceModel.STATUS_REFUNDED,
            }[transaction.transaction_type]
            transaction.invoice.status = invoice_status
            self.session.add(transaction.invoice)
        
        self.session.flush()
        self.logger.info('Processed transaction %s, status=%s, external_id=%s',
                         transaction.guid, transaction.status, 
                         transaction.external_id)

    def process_transactions(
        self, 
        processor, 
        guids=None, 
        maximum_retry=DEFAULT_MAXIMUM_RETRY
    ):
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
            self.process_one(processor, transaction, maximum_retry=maximum_retry)
            processed_transaction_guids.append(transaction.guid)
        return processed_transaction_guids
