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

    @property
    def maximum_retry(self):
        maximum_retry = int(self.factory.settings.get(
            'billy.transaction.maximum_retry', 
            self.DEFAULT_MAXIMUM_RETRY,
        ))
        return maximum_retry

    @property
    def processor(self):
        processor = self.factory.create_processor()
        return processor

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
    def list_by_context(self, context):
        """List transactions by a given context

        """
        Company = tables.Company
        Customer = tables.Customer
        Invoice = tables.Invoice
        Plan = tables.Plan
        Subscription = tables.Subscription
        Transaction = tables.Transaction
        SubscriptionTransaction = tables.SubscriptionTransaction
        InvoiceTransaction = tables.InvoiceTransaction

        # joined subscription transaction query
        subscription_tx_query = (
            self.session.query(Transaction)
            .join(
                SubscriptionTransaction, 
                Transaction.guid == SubscriptionTransaction.guid,
            )
        )
        # joined invoice transaction query
        invoice_tx_query = (
            self.session.query(Transaction)
            .join(
                InvoiceTransaction, 
                Transaction.guid == InvoiceTransaction.guid,
            )
        )
        # joined subscription query
        subscription_query = (
            subscription_tx_query
            .join(
                Subscription, 
                Subscription.guid == SubscriptionTransaction.subscription_guid
            )
        )
        # joined invoice query
        invoice_query = (
            invoice_tx_query
            .join(
                Invoice, 
                Invoice.guid == InvoiceTransaction.invoice_guid
            )
        )
        # joined plan query
        plan_query = (
            subscription_query
            .join(
                Plan,
                Plan.guid == Subscription.plan_guid,
            )
        )

        if isinstance(context, Subscription):
            query = (
                subscription_tx_query
                .filter(SubscriptionTransaction.subscription == context)
            )
        elif isinstance(context, Invoice):
            query = (
                invoice_tx_query
                .filter(InvoiceTransaction.invoice == context)
            )
        elif isinstance(context, Customer):
            q1 = (
                subscription_query
                .filter(Subscription.customer == context)
            )
            q2 = (
                invoice_query
                .filter(Invoice.customer == context)
            )
            query = q1.union(q2)
        elif isinstance(context, Plan):
            query = (
                subscription_query
                .filter(Subscription.plan == context)
            )
        elif isinstance(context, Company):
            q1 = (
                plan_query
                .filter(Plan.company == context)
            )
            q2 = (
                invoice_query
                .join(
                    Customer,
                    Customer.guid == Invoice.customer_guid,
                )
                .filter(Customer.company == context)
            )
            query = q1.union(q2)
        else:
            raise ValueError('Unsupported context {}'.format(context))

        query = query.order_by(Transaction.created_at.desc())
        return query

    def create(
        self, 
        transaction_type, 
        transaction_cls, 
        amount,
        scheduled_at,
        subscription=None, 
        invoice=None, 
        funding_instrument_uri=None,
        refund_to=None,
        appears_on_statement_as=None,
    ):
        """Create a transaction and return its ID

        """
        if transaction_type not in self.TYPE_ALL:
            raise ValueError('Invalid transaction_type {}'
                             .format(transaction_type))
        if transaction_cls not in self.CLS_ALL:
            raise ValueError('Invalid transaction_cls {}'
                             .format(transaction_cls))
        if refund_to is not None:
            if transaction_type != self.TYPE_REFUND:
                raise ValueError('refund_to can only be set to a refund '
                                 'transaction')
            if funding_instrument_uri is not None:
                raise ValueError('funding_instrument_uri cannot be set to a refund '
                                 'transaction')
            if refund_to.transaction_type != self.TYPE_CHARGE:
                raise ValueError('Only charge transaction can be refunded')

        if transaction_cls == self.CLS_SUBSCRIPTION:
            table_cls = tables.SubscriptionTransaction
            if subscription is None:
                raise ValueError('subscription cannot be None')
            extra_args = dict(subscription=subscription)
        elif transaction_cls == self.CLS_INVOICE:
            table_cls = tables.InvoiceTransaction
            if invoice is None:
                raise ValueError('invoice cannot be None')
            extra_args = dict(invoice=invoice)
        now = tables.now_func()
        transaction = table_cls(
            guid='TX' + make_guid(),
            transaction_type=transaction_type,
            amount=amount, 
            funding_instrument_uri=funding_instrument_uri, 
            appears_on_statement_as=appears_on_statement_as, 
            status=self.STATUS_INIT, 
            scheduled_at=scheduled_at, 
            refund_to=refund_to, 
            created_at=now, 
            updated_at=now, 
            **extra_args
        )
        self.session.add(transaction)
        self.session.flush()
        return transaction

    def update(self, transaction, **kwargs):
        """Update a transaction 

        """
        now = tables.now_func()
        transaction.updated_at = now
        if 'status' in kwargs:
            status = kwargs.pop('status')
            if status not in self.STATUS_ALL:
                raise ValueError('Invalid status {}'.format(status))
            transaction.status = status
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.flush()

    def process_one(self, transaction):
        """Process one transaction

        """
        invoice_model = self.factory.create_invoice_model()

        # there is still chance we duplicate transaction, for example
        # 
        #     (Thread 1)                    (Thread 2)
        #     Check existing transaction
        #                                   Check existing transaction
        #                                   Called to balanced
        #     Call to balanced
        #                           
        # we need to lock transaction before we process it to avoid 
        # situations like that
        self.get(transaction.guid, with_lockmode='update')

        if transaction.status == self.STATUS_DONE:
            raise ValueError('Cannot process a finished transaction {}'
                             .format(transaction.guid))
        self.logger.debug('Processing transaction %s', transaction.guid)
        now = tables.now_func()

        if transaction.transaction_cls == self.CLS_SUBSCRIPTION:
            customer = transaction.subscription.customer
        else:
            customer = transaction.invoice.customer
            # acquire the lock on invoice row
            invoice_model.get(transaction.invoice_guid, with_lockmode='update')

        method = {
            self.TYPE_CHARGE: self.processor.charge,
            self.TYPE_PAYOUT: self.processor.payout,
            self.TYPE_REFUND: self.processor.refund,
        }[transaction.transaction_type]

        try:
            self.logger.info(
                'Preparing customer %s (processor_uri=%s)', 
                customer.guid,
                customer.processor_uri,
            )
            # prepare customer (add bank account or credit card)
            self.processor.prepare_customer(customer, transaction.funding_instrument_uri)
            # do charge/payout/refund 
            transaction_id = method(transaction)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e:
            transaction.status = self.STATUS_RETRYING

            failure_model = self.factory.create_transaction_failure_model()

            failure = failure_model.create(
                transaction=transaction,
                error_message=unicode(e),
                # TODO: error number and code?
            )
            self.logger.error('Failed to process transaction %s, '
                              'failure_count=%s', 
                              transaction.guid, transaction.failure_count, 
                              exc_info=True)
            # the failure times exceed the limitation
            if transaction.failure_count > self.maximum_retry:
                self.logger.error('Exceed maximum retry limitation %s, '
                                  'transaction %s failed', self.maximum_retry, 
                                  transaction.guid)
                transaction.status = self.STATUS_FAILED

                # the transaction is failed, update invoice status
                if transaction.transaction_cls == self.CLS_INVOICE:
                    invoice_status = {
                        self.TYPE_CHARGE: invoice_model.STATUS_PROCESS_FAILED,
                        self.TYPE_REFUND: invoice_model.STATUS_REFUND_FAILED,
                    }[transaction.transaction_type]
                    transaction.invoice.status = invoice_status
                    self.session.add(transaction.invoice)
            transaction.updated_at = now
            self.session.flush()
            return

        transaction.processor_uri = transaction_id
        transaction.status = self.STATUS_DONE
        transaction.updated_at = tables.now_func()
        self.session.add(transaction)

        # the transaction is done, update invoice status
        if transaction.transaction_cls == self.CLS_INVOICE:
            invoice_status = {
                self.TYPE_CHARGE: invoice_model.STATUS_SETTLED,
                self.TYPE_REFUND: invoice_model.STATUS_REFUNDED,
            }[transaction.transaction_type]
            transaction.invoice.status = invoice_status
            self.session.add(transaction.invoice)
        
        self.session.flush()
        self.logger.info('Processed transaction %s, status=%s, external_id=%s',
                         transaction.guid, transaction.status, 
                         transaction.processor_uri)

    def process_transactions(self, transactions=None):
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
        if transactions is not None:
            query = transactions

        processed_transactions = []
        for transaction in query:
            self.process_one(transaction)
            processed_transactions.append(transaction)
        return processed_transactions
