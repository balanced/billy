from __future__ import unicode_literals

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Unicode
from sqlalchemy import DateTime
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.orm import object_session

from .base import DeclarativeBase
from .base import now_func
from ..enum import DeclEnum


class InvoiceType(DeclEnum):

    SUBSCRIPTION = 'SUBSCRIPTION', 'Subscription'
    CUSTOMER = 'CUSTOMER', 'Credit'


class InvoiceTransactionType(DeclEnum):

    DEBIT = 'DEBIT', 'Debit'
    CREDIT = 'CREDIT', 'Credit'


class InvoiceStatus(DeclEnum):

    STAGED = 'STAGED', 'Staged'
    PROCESSING = 'PROCESSING', 'Processing'
    SETTLED = 'SETTLED', 'Settled'
    CANCELED = 'CANCELED', 'Canceled'
    PROCESS_FAILED = 'PROCESS_FAILED', 'Process failed'


class Invoice(DeclarativeBase):
    """An invoice

    """
    __tablename__ = 'invoice'
    __mapper_args__ = {
        'polymorphic_on': 'invoice_type',
    }

    guid = Column(Unicode(64), primary_key=True)
    # type of invoice, could be 0=subscription, 1=customer
    invoice_type = Column(InvoiceType.db_type(), index=True, nullable=False)
    #: what kind of transaction it is, could be DEBIT or CREDIT
    transaction_type = Column(InvoiceTransactionType.db_type(), nullable=False,
                              index=True)
    #: the funding instrument URI to charge to, such as bank account or credit
    #  card
    funding_instrument_uri = Column(Unicode(128), index=True)
    #: the total amount of this invoice
    amount = Column(Integer, nullable=False)
    #: current status of this invoice, could be
    #   - STAGED
    #   - PROCESSING
    #   - SETTLED
    #   - CANCELED
    #   - PROCESS_FAILED
    status = Column(InvoiceStatus.db_type(), index=True, nullable=False)
    #: a short optional title of this invoice
    title = Column(Unicode(128))
    #: the created datetime of this invoice
    created_at = Column(DateTime, default=now_func)
    #: the updated datetime of this invoice
    updated_at = Column(DateTime, default=now_func)
    #: the statement to appear on customer's transaction record (either
    #  bank account or credit card)
    appears_on_statement_as = Column(Unicode(32))

    #: transactions of this invoice
    transactions = relationship(
        'Transaction',
        cascade='all, delete-orphan',
        backref='invoice',
        order_by='Transaction.created_at',
    )

    #: items of this invoice
    items = relationship(
        'Item',
        cascade='all, delete-orphan',
        backref='invoice',
        order_by='Item.item_id',
    )

    #: adjustments of this invoice
    adjustments = relationship(
        'Adjustment',
        cascade='all, delete-orphan',
        backref='invoice',
        order_by='Adjustment.adjustment_id',
    )

    @property
    def total_adjustment_amount(self):
        """Sum of total adjustment amount

        """
        from sqlalchemy import func
        session = object_session(self)
        return (
            session.query(func.coalesce(func.sum(Adjustment.amount), 0))
            .filter(Adjustment.invoice_guid == self.guid)
            .scalar()
        )

    @property
    def effective_amount(self):
        """Effective amount of this invoice (amount + total_adjustment_amount)

        """
        return self.total_adjustment_amount + self.amount


class SubscriptionInvoice(Invoice):
    """An invoice generated from subscription (recurring charge or payout)

    """
    __tablename__ = 'subscription_invoice'
    __mapper_args__ = {
        'polymorphic_identity': InvoiceType.SUBSCRIPTION,
    }

    guid = Column(
        Unicode(64),
        ForeignKey(
            'invoice.guid',
            ondelete='CASCADE',
            onupdate='CASCADE'
        ),
        primary_key=True,
    )
    #: the guid of subscription which generated this invoice
    subscription_guid = Column(
        Unicode(64),
        ForeignKey(
            'subscription.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: the scheduled datetime of this invoice should be processed
    scheduled_at = Column(DateTime, default=now_func)

    @property
    def customer(self):
        return self.subscription.customer


class CustomerInvoice(Invoice):
    """A single invoice generated for customer

    """
    __tablename__ = 'customer_invoice'
    __table_args__ = (UniqueConstraint('customer_guid', 'external_id'), )
    __mapper_args__ = {
        'polymorphic_identity': InvoiceType.CUSTOMER,
    }

    guid = Column(
        Unicode(64),
        ForeignKey(
            'invoice.guid',
            ondelete='CASCADE',
            onupdate='CASCADE'
        ),
        primary_key=True,
    )
    #: the guid of customer who owns this invoice
    customer_guid = Column(
        Unicode(64),
        ForeignKey(
            'customer.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: the external_id for storing external resource ID in order to avoid
    #  duplication
    external_id = Column(Unicode(128), index=True)


class Item(DeclarativeBase):
    """An item of an invoice

    """
    __tablename__ = 'item'

    item_id = Column(Integer, autoincrement=True, primary_key=True)
    #: the guid of invoice which owns this item
    invoice_guid = Column(
        Unicode(64),
        ForeignKey(
            'invoice.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: type of this item
    type = Column(Unicode(128))
    #: name of item
    name = Column(Unicode(128), nullable=False)
    #: quantity of item
    quantity = Column(Integer)
    #: total processed transaction volume
    volume = Column(Integer)
    #: total fee to charge for this item
    amount = Column(Integer, nullable=False)
    #: unit of item
    unit = Column(Unicode(64))


class Adjustment(DeclarativeBase):
    """An adjustment to invoice

    """
    __tablename__ = 'adjustment'

    adjustment_id = Column(Integer, autoincrement=True, primary_key=True)
    #: the guid of invoice which owns this adjustment
    invoice_guid = Column(
        Unicode(64),
        ForeignKey(
            'invoice.guid',
            ondelete='CASCADE', onupdate='CASCADE'
        ),
        index=True,
        nullable=False,
    )
    #: reason of making this adjustment to invoice
    reason = Column(Unicode(128))
    #: the adjustment amount to be applied to invoice, could be negative
    amount = Column(Integer, nullable=False)

__all__ = [
    InvoiceType.__name__,
    InvoiceTransactionType.__name__,
    InvoiceStatus.__name__,
    Invoice.__name__,
    SubscriptionInvoice.__name__,
    CustomerInvoice.__name__,
    Item.__name__,
    Adjustment.__name__,
]
