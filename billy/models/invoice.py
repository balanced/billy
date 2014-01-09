from __future__ import unicode_literals

from sqlalchemy.sql.expression import func

from billy.models import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.models.plan import PlanModel
from billy.models.transaction import TransactionModel
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

    STATUS_ALL = [
        STATUS_INIT,
        STATUS_PROCESSING,
        STATUS_SETTLED,
        STATUS_CANCELED,
        STATUS_PROCESS_FAILED,
    ]

    #: subscription type invoice
    TYPE_SUBSCRIPTION = 0
    #: customer type invoice
    TYPE_CUSTOMER = 1
    TYPE_ALL = [
        TYPE_SUBSCRIPTION,
        TYPE_CUSTOMER,
    ]

    # not set object
    NOT_SET = object()

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

        basic_query = self.session.query(Invoice)
        # joined subscription invoice query
        subscription_invoice_query = (
            basic_query
            .join(
                SubscriptionInvoice, 
                SubscriptionInvoice.guid == Invoice.guid,
            )
        )
        # joined customer invoice query
        customer_invoice_query = (
            basic_query
            .join(
                CustomerInvoice, 
                CustomerInvoice.guid == Invoice.guid,
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
            subscription_invoice_query
            .join(
                Subscription, 
                Subscription.guid == SubscriptionInvoice.subscription_guid,
            )
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
            invoice_type = self.TYPE_CUSTOMER
            invoice_cls = tables.CustomerInvoice
            # we only support charge type for customer invoice now
            transaction_type = TransactionModel.TYPE_CHARGE
            extra_kwargs = dict(
                customer=customer,
                external_id=external_id,
            )
        elif subscription is not None:
            if scheduled_at is None:
                raise ValueError('scheduled_at cannot be None')
            invoice_type = self.TYPE_SUBSCRIPTION
            invoice_cls = tables.SubscriptionInvoice
            plan_type = subscription.plan.plan_type
            if plan_type == PlanModel.TYPE_CHARGE:
                transaction_type = TransactionModel.TYPE_CHARGE
            elif plan_type == PlanModel.TYPE_PAYOUT:
                transaction_type = TransactionModel.TYPE_PAYOUT
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
            status=self.STATUS_INIT,
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

        tx_model = self.factory.create_transaction_model()
        # as if we set the funding_instrument_uri at very first, we want to charge it
        # immediately, so we create a transaction right away, also set the 
        # status to PROCESSING
        if funding_instrument_uri is not None and invoice.amount > 0:
            invoice.status = self.STATUS_PROCESSING
            tx_model.create(invoice=invoice)
        # it is zero amount, nothing to charge, just switch to
        # SETTLED status
        elif invoice.amount == 0:
            invoice.status = self.STATUS_SETTLED

        self.session.flush()
        return invoice

    def update(
        self, 
        invoice, 
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
                    amount=item['amount'],
                    type=item.get('type'),
                    quantity=item.get('quantity'),
                    unit=item.get('unit'),
                    volume=item.get('volume'),
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
        if invoice.status == self.STATUS_INIT:
            transaction = tx_model.create(invoice=invoice)
            transactions.append(transaction)
        # we are already processing, cancel current transaction and create
        # a new one
        elif invoice.status == self.STATUS_PROCESSING:
            # find the running transaction and cancel it 
            last_transaction = (
                self.session
                .query(Transaction)
                .filter(
                    Transaction.invoice == invoice,
                    Transaction.transaction_type.in_([
                        TransactionModel.TYPE_CHARGE,
                        TransactionModel.TYPE_PAYOUT,
                    ]),
                    Transaction.status.in_([
                        TransactionModel.STATUS_INIT,
                        TransactionModel.STATUS_RETRYING,
                    ])
                )
            ).one()
            last_transaction.status = tx_model.STATUS_CANCELED
            last_transaction.canceled_at = now
            # create a new one
            transaction = tx_model.create(invoice=invoice)
            transactions.append(transaction)
        # the previous transaction failed, just create a new one
        elif invoice.status == self.STATUS_PROCESS_FAILED:
            transaction = tx_model.create(invoice=invoice)
            transactions.append(transaction)
        else:
            raise InvalidOperationError(
                'Invalid operation, you can only update funding_instrument_uri '
                'when the invoice status is one of INIT, PROCESSING and '
                'PROCESS_FAILED'
            )
        invoice.status = self.STATUS_PROCESSING

        self.session.flush()
        return transactions

    def cancel(self, invoice):
        """Cancel an invoice

        """
        Transaction = tables.Transaction
        now = tables.now_func()

        if invoice.status not in [
            self.STATUS_INIT,
            self.STATUS_PROCESSING,
            self.STATUS_PROCESS_FAILED,
        ]:
            raise InvalidOperationError(
                'An invoice can only be canceled when its status is one of '
                'INIT, PROCESSING and PROCESS_FAILED'
            )
        self.get(invoice.guid, with_lockmode='update')
        invoice.status = self.STATUS_CANCELED

        # those transactions which are still running
        running_transactions = (
            self.session.query(Transaction)
            .filter(
                Transaction.transaction_type != TransactionModel.TYPE_REFUND,
                Transaction.status.in_([
                    TransactionModel.STATUS_INIT,
                    TransactionModel.STATUS_RETRYING,
                ])
            )
        )
        # cancel them
        running_transactions.update(dict(
            status=TransactionModel.STATUS_CANCELED,
            updated_at=now, 
        ), synchronize_session='fetch')

        self.session.flush()

    def refund(self, invoice, amount, appears_on_statement_as=None):
        """Refund the invoice

        """
        Transaction = tables.Transaction
        tx_model = self.factory.create_transaction_model()
        transactions = []

        self.get(invoice.guid, with_lockmode='update')

        if invoice.status != self.STATUS_SETTLED:
            raise InvalidOperationError('You can only refund a settled invoice')

        refunded_amount = (
            self.session.query(
                func.coalesce(func.sum(Transaction.amount), 0)
            )
            .filter(
                Transaction.invoice == invoice,
                Transaction.transaction_type == TransactionModel.TYPE_REFUND,
                Transaction.status.in_([
                    TransactionModel.STATUS_INIT,
                    TransactionModel.STATUS_RETRYING,
                    TransactionModel.STATUS_DONE,
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
                Transaction.transaction_type == TransactionModel.TYPE_CHARGE,
                Transaction.status == TransactionModel.STATUS_DONE,
            )
        ).one()

        # create the refund transaction
        transaction = tx_model.create(
            invoice=invoice,
            transaction_type=TransactionModel.TYPE_REFUND,
            amount=amount,
            reference_to=settled_transaction,
            appears_on_statement_as=appears_on_statement_as,
        )
        transactions.append(transaction)
        return transactions
