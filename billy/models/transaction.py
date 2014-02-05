from __future__ import unicode_literals

from sqlalchemy.exc import IntegrityError

from billy.db import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.errors import BillyError
from billy.utils.generic import make_guid


class DuplicateEventError(BillyError):
    """This error indicates the given event already exists in Billy system for
    the transaction

    """


class TransactionModel(BaseTableModel):

    TABLE = tables.Transaction

    #: the default maximum retry count
    DEFAULT_MAXIMUM_RETRY = 10

    types = tables.TransactionType

    submit_statuses = tables.TransactionSubmitStatus

    statuses = tables.TransactionStatus

    @property
    def maximum_retry(self):
        maximum_retry = int(self.factory.settings.get(
            'billy.transaction.maximum_retry',
            self.DEFAULT_MAXIMUM_RETRY,
        ))
        return maximum_retry

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
        SubscriptionInvoice = tables.SubscriptionInvoice
        CustomerInvoice = tables.CustomerInvoice

        # joined subscription transaction query
        basic_query = self.session.query(Transaction)
        # joined subscription invoice query
        subscription_invoice_query = (
            basic_query
            .join(
                SubscriptionInvoice,
                SubscriptionInvoice.guid == Transaction.invoice_guid,
            )
        )
        # joined customer invoice query
        customer_invoice_query = (
            basic_query
            .join(
                CustomerInvoice,
                CustomerInvoice.guid == Transaction.invoice_guid,
            )
        )
        # joined subscription query
        subscription_query = (
            subscription_invoice_query
            .join(
                Subscription,
                Subscription.guid == SubscriptionInvoice.subscription_guid,
            )
        )
        # joined customer query
        customer_query = (
            customer_invoice_query
            .join(
                Customer,
                Customer.guid == CustomerInvoice.customer_guid,
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

        if isinstance(context, Invoice):
            query = (
                basic_query
                .filter(Transaction.invoice == context)
            )
        elif isinstance(context, Subscription):
            query = (
                subscription_invoice_query
                .filter(SubscriptionInvoice.subscription == context)
            )
        elif isinstance(context, Customer):
            query = (
                customer_invoice_query
                .filter(CustomerInvoice.customer == context)
            )
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
                customer_query
                .filter(Customer.company == context)
            )
            query = q1.union(q2)
        else:
            raise ValueError('Unsupported context {}'.format(context))

        query = query.order_by(Transaction.created_at.desc())
        return query

    def create(
        self,
        invoice,
        amount,
        transaction_type=None,
        funding_instrument_uri=None,
        reference_to=None,
        appears_on_statement_as=None,
    ):
        """Create a transaction and return

        """
        if transaction_type is None:
            transaction_type = invoice.transaction_type

        if reference_to is not None:
            if transaction_type not in [self.types.REFUND, self.types.REVERSE]:
                raise ValueError('reference_to can only be set to a refund '
                                 'transaction')
            if funding_instrument_uri is not None:
                raise ValueError(
                    'funding_instrument_uri cannot be set to a refund/reverse '
                    'transaction'
                )
            if (
                reference_to.transaction_type not in
                [self.types.DEBIT, self.types.CREDIT]
            ):
                raise ValueError(
                    'Only charge/payout transaction can be refunded/reversed'
                )

        now = tables.now_func()
        transaction = tables.Transaction(
            guid='TX' + make_guid(),
            transaction_type=transaction_type,
            amount=amount,
            funding_instrument_uri=funding_instrument_uri,
            appears_on_statement_as=appears_on_statement_as,
            submit_status=self.submit_statuses.STAGED,
            reference_to=reference_to,
            created_at=now,
            updated_at=now,
            invoice=invoice,
        )
        self.session.add(transaction)
        self.session.flush()
        return transaction

    def update(self, transaction, **kwargs):
        """Update a transaction

        """
        now = tables.now_func()
        transaction.updated_at = now
        if kwargs:
            raise TypeError('Unknown attributes {} to update'.format(tuple(kwargs.keys())))
        self.session.flush()

    def add_event(self, transaction, status, processor_id, occurred_at):
        """Add a status updating event of transaction from callback

        """
        now = tables.now_func()
        # the latest event of this transaction
        last_event = transaction.events.first()

        event = tables.TransactionEvent(
            guid='TE' + make_guid(),
            transaction=transaction,
            processor_id=processor_id,
            occurred_at=occurred_at,
            status=status,
            created_at=now,
        )
        self.session.add(event)
        
        # ensure won't duplicate
        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            raise DuplicateEventError(
                'Event {} already exists for {}'.format(
                    processor_id, transaction.guid,
                ),
            )

        # Notice: we only want to update transaction status if this event
        # is the latest one we had seen in Billy system. Why we are doing
        # here is because I think of some scenarios like
        #
        #  1. Balanced cannot reach Billy for a short while, and retry later
        #  2. Attacker want to fool us with old events
        #
        # These will lead the status of invoice to be updated incorrectly.
        # For case 1, events send to Billy like this:
        #
        #     succeeded (failed to send to Billy, retry 1 minute later)
        #     failed
        #     succeeded (retry)
        #
        # See? The final status should be `failed`, but as the `succeeded`
        # was resent later, so it became `succeded` eventually. Similarly,
        # attackers can send us an old `succeeded` event to make the invoice
        # settled.  This is why we need to ensure only the latest event can
        # affect status of invoice.
        if last_event is not None and occurred_at <= last_event.occurred_at:
            return

        old_status = transaction.status
        transaction.updated_at = now
        transaction.status = status
        # update invoice status
        invoice_model = self.factory.create_invoice_model()
        invoice_model.transaction_status_update(
            invoice=transaction.invoice,
            transaction=transaction,
            original_status=old_status,
        )
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

        if transaction.submit_status == self.submit_statuses.DONE:
            raise ValueError('Cannot process a finished transaction {}'
                             .format(transaction.guid))
        self.logger.debug('Processing transaction %s', transaction.guid)
        now = tables.now_func()

        if transaction.invoice.invoice_type == invoice_model.types.SUBSCRIPTION:
            customer = transaction.invoice.subscription.customer
        else:
            customer = transaction.invoice.customer

        processor = self.factory.create_processor()

        method = {
            self.types.DEBIT: processor.debit,
            self.types.CREDIT: processor.credit,
            self.types.REFUND: processor.refund,
        }[transaction.transaction_type]

        try:
            processor.configure_api_key(customer.company.processor_key)
            self.logger.info(
                'Preparing customer %s (processor_uri=%s)',
                customer.guid,
                customer.processor_uri,
            )
            # prepare customer (add bank account or credit card)
            processor.prepare_customer(
                customer=customer,
                funding_instrument_uri=transaction.funding_instrument_uri,
            )
            # do charge/payout/refund
            result = method(transaction)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e:
            transaction.submit_status = self.submit_statuses.RETRYING
            failure_model = self.factory.create_transaction_failure_model()
            failure_model.create(
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
                transaction.submit_status = self.submit_statuses.FAILED

                # the transaction is failed, update invoice status
                if transaction.transaction_type in [
                    self.types.DEBIT,
                    self.types.CREDIT,
                ]:
                    transaction.invoice.status = invoice_model.statuses.FAILED
            transaction.updated_at = now
            self.session.flush()
            return

        old_status = transaction.status
        transaction.processor_uri = result['processor_uri']
        transaction.status = result['status']
        transaction.submit_status = self.submit_statuses.DONE
        transaction.updated_at = tables.now_func()
        invoice_model.transaction_status_update(
            invoice=transaction.invoice,
            transaction=transaction,
            original_status=old_status,
        )
       
        self.session.flush()
        self.logger.info('Processed transaction %s, submit_status=%s, '
                         'result=%s',
                         transaction.guid, transaction.submit_status,
                         result)

    def process_transactions(self, transactions=None):
        """Process all transactions

        """
        Transaction = tables.Transaction
        query = (
            self.session.query(Transaction)
            .filter(Transaction.submit_status.in_([
                self.submit_statuses.STAGED,
                self.submit_statuses.RETRYING]
            ))
        )
        if transactions is not None:
            query = transactions

        processed_transactions = []
        for transaction in query:
            self.process_one(transaction)
            processed_transactions.append(transaction)
        return processed_transactions
