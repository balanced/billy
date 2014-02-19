from __future__ import unicode_literals

from sqlalchemy.sql.expression import func

from billy.db import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.models.plan import PlanModel
from billy.models.transaction import TransactionModel
from billy.errors import BillyError
from billy.utils.generic import make_guid


class InvalidOperationError(BillyError):
    """This error indicates an invalid operation to invoice model, such as
    updating an invoice's funding_instrument_uri in wrong status

    """


class DuplicateExternalIDError(BillyError):
    """This error indicates you have duplicate (Customer GUID, External ID)
    pair in database. The field `external_id` was designed to avoid duplicate
    invoicing.

    """


class InvoiceModel(BaseTableModel):

    TABLE = tables.Invoice

    # not set object
    NOT_SET = object()

    # type of invoice
    types = tables.InvoiceType

    # transaction type of invoice
    transaction_types = tables.InvoiceTransactionType

    # statuses of invoice
    statuses = tables.InvoiceStatus

    @decorate_offset_limit
    def list_by_context(self, context, external_id=NOT_SET):
        """Get invoices of a given context

        """
        Company = tables.Company
        Customer = tables.Customer
        Subscription = tables.Subscription
        Invoice = tables.Invoice
        Plan = tables.Plan
        SubscriptionInvoice = tables.SubscriptionInvoice
        CustomerInvoice = tables.CustomerInvoice

        # joined subscription invoice query
        subscription_invoice_query = self.session.query(SubscriptionInvoice)
        # joined customer invoice query
        customer_invoice_query = self.session.query(CustomerInvoice)
        # joined customer query
        customer_query = (
            customer_invoice_query
            .join(
                Customer,
                Customer.guid == CustomerInvoice.customer_guid,
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
        # joined plan query
        plan_query = (
            subscription_query
            .join(
                Plan,
                Plan.guid == Subscription.plan_guid,
            )
        )

        if isinstance(context, Customer):
            query = (
                customer_invoice_query
                .filter(CustomerInvoice.customer == context)
            )
        elif isinstance(context, Subscription):
            query = (
                subscription_invoice_query
                .filter(SubscriptionInvoice.subscription == context)
                .order_by(SubscriptionInvoice.scheduled_at.desc())
            )
        elif isinstance(context, Plan):
            query = (
                subscription_query
                .filter(Subscription.plan == context)
                .order_by(SubscriptionInvoice.scheduled_at.desc())
            )
        elif isinstance(context, Company):
            q1 = (
                plan_query
                .filter(Plan.company == context)
                .from_self(Invoice.guid)
            )
            q2 = (
                customer_query
                .filter(Customer.company == context)
                .from_self(Invoice.guid)
            )
            guid_query = q1.union(q2)
            query = (
                self.session.query(Invoice)
                .filter(Invoice.guid.in_(guid_query))
            )
        else:
            raise ValueError('Unsupported context {}'.format(context))

        if external_id is not self.NOT_SET:
            query = (
                query
                .join(
                    CustomerInvoice,
                    CustomerInvoice.guid == Invoice.guid,
                )
                .filter(CustomerInvoice.external_id == external_id)
            )

        query = query.order_by(Invoice.created_at.desc())
        return query

    def _create_transaction(self, invoice):
        """Create a charge/payout transaction from the given invoice and return

        """
        tx_model = self.factory.create_transaction_model()
        transaction = tx_model.create(
            invoice=invoice,
            amount=invoice.effective_amount,
            transaction_type=invoice.transaction_type,
            funding_instrument_uri=invoice.funding_instrument_uri,
            appears_on_statement_as=invoice.appears_on_statement_as,
        )
        return transaction

    def create(
        self,
        amount,
        funding_instrument_uri=None,
        customer=None,
        subscription=None,
        title=None,
        items=None,
        adjustments=None,
        external_id=None,
        appears_on_statement_as=None,
        scheduled_at=None,
    ):
        """Create a invoice and return its id

        """
        from sqlalchemy.exc import IntegrityError

        if customer is not None and subscription is not None:
            raise ValueError('You can only set either customer or subscription')

        if customer is not None:
            invoice_type = self.types.CUSTOMER
            invoice_cls = tables.CustomerInvoice
            # we only support charge type for customer invoice now
            transaction_type = self.transaction_types.DEBIT
            extra_kwargs = dict(
                customer=customer,
                external_id=external_id,
            )
        elif subscription is not None:
            if scheduled_at is None:
                raise ValueError('scheduled_at cannot be None')
            invoice_type = self.types.SUBSCRIPTION
            invoice_cls = tables.SubscriptionInvoice
            plan_type = subscription.plan.plan_type
            if plan_type == PlanModel.types.DEBIT:
                transaction_type = self.transaction_types.DEBIT
            elif plan_type == PlanModel.types.CREDIT:
                transaction_type = self.transaction_types.CREDIT
            else:
                raise ValueError('Invalid plan_type {}'.format(plan_type))
            extra_kwargs = dict(
                subscription=subscription,
                scheduled_at=scheduled_at,
            )
        else:
            raise ValueError('You have to set either customer or subscription')

        if amount < 0:
            raise ValueError('Negative amount {} is not allowed'.format(amount))

        now = tables.now_func()
        invoice = invoice_cls(
            guid='IV' + make_guid(),
            invoice_type=invoice_type,
            transaction_type=transaction_type,
            status=self.statuses.STAGED,
            amount=amount,
            funding_instrument_uri=funding_instrument_uri,
            title=title,
            created_at=now,
            updated_at=now,
            appears_on_statement_as=appears_on_statement_as,
            **extra_kwargs
        )

        self.session.add(invoice)

        # ensure (customer_guid, external_id) is unique
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
                    amount=item['amount'],
                    type=item.get('type'),
                    quantity=item.get('quantity'),
                    unit=item.get('unit'),
                    volume=item.get('volume'),
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
                    amount=adjustment['amount'],
                    reason=adjustment.get('reason'),
                )
                self.session.add(record)
            self.session.flush()

        # as if we set the funding_instrument_uri at very first, we want to charge it
        # immediately, so we create a transaction right away, also set the
        # status to PROCESSING
        if funding_instrument_uri is not None and invoice.amount > 0:
            invoice.status = self.statuses.PROCESSING
            self._create_transaction(invoice)
        # it is zero amount, nothing to charge, just switch to
        # SETTLED status
        elif invoice.amount == 0:
            invoice.status = self.statuses.SETTLED

        self.session.flush()
        return invoice

    def update_funding_instrument_uri(self, invoice, funding_instrument_uri):
        """Update the funding_instrument_uri of an invoice, as it may yield
        transactions, we don't want to put this in `update` method

        @return: a list of yielded transaction
        """
        Transaction = tables.Transaction

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
        self.get(invoice.guid, with_lockmode='update')

        # the invoice is just created, simply create a transaction for it
        if invoice.status == self.statuses.STAGED:
            transaction = self._create_transaction(invoice)
            transactions.append(transaction)
        # we are already processing, cancel current transaction and create
        # a new one
        elif invoice.status == self.statuses.PROCESSING:
            # find the running transaction and cancel it
            last_transaction = (
                self.session
                .query(Transaction)
                .filter(
                    Transaction.invoice == invoice,
                    Transaction.transaction_type.in_([
                        TransactionModel.types.DEBIT,
                        TransactionModel.types.CREDIT,
                    ]),
                    Transaction.submit_status.in_([
                        TransactionModel.submit_statuses.STAGED,
                        TransactionModel.submit_statuses.RETRYING,
                    ])
                )
            ).one()
            last_transaction.submit_status = tx_model.submit_statuses.CANCELED
            last_transaction.canceled_at = now
            # create a new one
            transaction = self._create_transaction(invoice)
            transactions.append(transaction)
        # the previous transaction failed, just create a new one
        elif invoice.status == self.statuses.FAILED:
            transaction = self._create_transaction(invoice)
            transactions.append(transaction)
        else:
            raise InvalidOperationError(
                'Invalid operation, you can only update funding_instrument_uri '
                'when the invoice status is one of STAGED, PROCESSING and '
                'FAILED'
            )
        invoice.status = self.statuses.PROCESSING

        self.session.flush()
        return transactions

    def cancel(self, invoice):
        """Cancel an invoice

        """
        Transaction = tables.Transaction
        now = tables.now_func()

        if invoice.status not in [
            self.statuses.STAGED,
            self.statuses.PROCESSING,
            self.statuses.FAILED,
        ]:
            raise InvalidOperationError(
                'An invoice can only be canceled when its status is one of '
                'STAGED, PROCESSING and FAILED'
            )
        self.get(invoice.guid, with_lockmode='update')
        invoice.status = self.statuses.CANCELED

        # those transactions which are still running
        running_transactions = (
            self.session.query(Transaction)
            .filter(
                Transaction.transaction_type != TransactionModel.types.REFUND,
                Transaction.submit_status.in_([
                    TransactionModel.submit_statuses.STAGED,
                    TransactionModel.submit_statuses.RETRYING,
                ])
            )
        )
        # cancel them
        running_transactions.update(dict(
            submit_status=TransactionModel.submit_statuses.CANCELED,
            updated_at=now,
        ), synchronize_session='fetch')

        self.session.flush()

    def refund(self, invoice, amount):
        """Refund the invoice

        """
        Transaction = tables.Transaction
        tx_model = self.factory.create_transaction_model()
        transactions = []

        self.get(invoice.guid, with_lockmode='update')

        if invoice.status != self.statuses.SETTLED:
            raise InvalidOperationError('You can only refund a settled invoice')

        refunded_amount = (
            self.session.query(
                func.coalesce(func.sum(Transaction.amount), 0)
            )
            .filter(
                Transaction.invoice == invoice,
                Transaction.transaction_type == TransactionModel.types.REFUND,
                Transaction.submit_status.in_([
                    TransactionModel.submit_statuses.STAGED,
                    TransactionModel.submit_statuses.RETRYING,
                    TransactionModel.submit_statuses.DONE,
                ])
            )
        ).scalar()
        # Make sure do not allow refund more than effective amount
        if refunded_amount + amount > invoice.effective_amount:
            raise InvalidOperationError(
                'Refund total amount {} + {} will exceed invoice effective amount {}'
                .format(
                    refunded_amount,
                    amount,
                    invoice.effective_amount,
                )
            )

        # the settled transaction
        settled_transaction = (
            self.session.query(Transaction)
            .filter(
                Transaction.invoice == invoice,
                Transaction.transaction_type == TransactionModel.types.DEBIT,
                Transaction.submit_status == TransactionModel.submit_statuses.DONE,
            )
        ).one()

        # create the refund transaction
        transaction = tx_model.create(
            invoice=invoice,
            transaction_type=TransactionModel.types.REFUND,
            amount=amount,
            reference_to=settled_transaction,
        )
        transactions.append(transaction)
        return transactions

    def transaction_status_update(self, invoice, transaction, original_status):
        """Called to handle transaction status update

        """
        # we don't have to deal with refund/reversal status change
        if transaction.transaction_type not in [
            TransactionModel.types.DEBIT,
            TransactionModel.types.CREDIT,
        ]:
            return

        def succeeded():
            invoice.status = self.statuses.SETTLED

        def processing():
            invoice.status = self.statuses.PROCESSING

        def failed():
            invoice.status = self.statuses.FAILED

        status_handlers = {
            # succeeded status
            TransactionModel.statuses.SUCCEEDED: succeeded,
            # processing
            TransactionModel.statuses.PENDING: processing,
            # failed
            TransactionModel.statuses.FAILED: failed,
        }
        new_status = transaction.status
        status_handlers[new_status]()

        invoice.updated_at = tables.now_func()
        self.session.flush()
